"""Build and sign LMA using the Windows Android SDK, with no Gradle downloads.

Uses javac, AAPT2, D8, zipalign and apksigner. No emulator or virtualization.
ANDROID_SDK_ROOT / --sdk may select a different existing SDK installation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import zipfile
from evidence import version, build_inputs
from package_native import prepare as prepare_native

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DIST = ROOT / "dist"


def run(stage, args, env=None):
    print(stage, flush=True)
    # Some Windows SDK binaries still mishandle non-ASCII absolute paths.
    # Keep the working directory in the requested project and pass ASCII relative paths.
    command = []
    for value in args:
        if isinstance(value, Path) and value.is_absolute() and ROOT in value.parents:
            value = value.relative_to(ROOT).as_posix()
        command.append(str(value))
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    with (BUILD / "build.log").open("a", encoding="utf-8") as log: log.write(stage + "\n" + result.stdout + "\n")
    if result.stdout.strip(): print(result.stdout.strip(), flush=True)
    if result.returncode: raise RuntimeError(f"{stage} failed (exit {result.returncode})")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", default=os.environ.get("ANDROID_SDK_ROOT", str(Path(os.environ.get("LOCALAPPDATA", "C:/Users/carzy/AppData/Local")) / "Android/Sdk")))
    args = parser.parse_args()
    sdk = Path(args.sdk); tools = sdk / "build-tools/35.0.1"; android = sdk / "platforms/android-35/android.jar"
    java = shutil.which("java"); javac = shutil.which("javac"); keytool = shutil.which("keytool")
    if not all((java, javac, keytool)) or not android.exists() or not (tools / "aapt2.exe").exists():
        raise RuntimeError("Need a JDK and Android SDK platform 35 / build-tools 35.0.1; use --sdk to select an SDK")
    for folder in (BUILD, DIST, BUILD / "generated", BUILD / "classes", BUILD / "dex", ROOT / "signing"):
        folder.mkdir(parents=True, exist_ok=True)
    for name in ("generated", "classes", "dex"):
        folder = (BUILD / name).resolve()
        assert folder.parent == BUILD.resolve()
        shutil.rmtree(folder); folder.mkdir()
    (BUILD / "build.log").write_text("", encoding="utf-8")
    run("Generate checked model catalogue", [sys.executable, ROOT / "tools/build_catalogue.py"])
    run("Generate data-only bundle catalogue", [sys.executable, ROOT / "tools/build_bundle_catalogue.py"])
    engines = prepare_native()
    native = ROOT / "app/src/main/jniLibs/arm64-v8a"
    if not (native / "libllama-server.so").exists(): raise RuntimeError("Run python tools/bootstrap_runtime.py first")
    source = ROOT / "app/src/main"
    for name in ("index.html", "app.css", "app.js", "foundation.css", "foundation.js", "models.json", "model-bundles.json", "engine-builds.json"):
        if not (source / "assets" / name).is_file(): raise RuntimeError("Missing application UI asset: " + name)
    license_text = (ROOT / "third_party/LLAMA_CPP_LICENSE").read_text(encoding="utf-8")
    (source / "assets/licenses").mkdir(exist_ok=True)
    (source / "assets/licenses/LLAMA_CPP_LICENSE").write_text(license_text, encoding="utf-8")
    notices = {"LMA MIT License": (ROOT / "LICENSE").read_text(encoding="utf-8")}
    if len(list((ROOT / "third_party/notices").glob("*.txt"))) < 11:
        raise RuntimeError("Missing dependency notices; run python tools/collect_notices.py")
    for notice in sorted((ROOT / "third_party/notices").glob("*.txt")):
        text = notice.read_text(encoding="utf-8")
        (source / "assets/licenses" / notice.name).write_bytes(notice.read_bytes())
        notices[notice.name] = text
    (source / "assets/licenses/LMA_LICENSE").write_text(notices["LMA MIT License"], encoding="utf-8")
    (source / "assets/license.js").write_text("window.LMA_LICENSE = " + json.dumps(license_text, ensure_ascii=True) + ";\nwindow.LMA_NOTICES = " + json.dumps(notices, ensure_ascii=True) + ";\n", encoding="utf-8")
    lock = json.loads((ROOT / "third_party/runtime-lock.json").read_text(encoding="utf-8"))
    for record in lock["files"]:
        path = native / record["name"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise RuntimeError("Pinned runtime file mismatch: " + record["name"])
    native_names = {record["name"] for record in lock["files"]} | {engine["file"] for engine in engines}
    if {path.name for path in native.glob("*.so")} != native_names:
        raise RuntimeError("Unreviewed native libraries exist in the APK input directory")
    run("Compile Android resources", [tools / "aapt2.exe", "compile", "--dir", source / "res", "-o", BUILD / "resources.zip"])
    run("Link application resources", [tools / "aapt2.exe", "link", "-o", BUILD / "resources.apk", "-I", android,
                                          "--manifest", source / "AndroidManifest.xml", "--java", BUILD / "generated",
                                          "-A", source / "assets", "--min-sdk-version", "28", "--target-sdk-version", "35", BUILD / "resources.zip"])
    sources = sorted((source / "java").rglob("*.java")) + sorted((BUILD / "generated").rglob("*.java"))
    response = BUILD / "sources.rsp"
    response.write_text("\n".join('"' + p.as_posix() + '"' for p in sources), encoding="utf-8")
    run("Compile Java application", [javac, "-J-Duser.language=en", "-J-Dfile.encoding=UTF-8", "-encoding", "UTF-8", "--release", "8", "-classpath", android, "-d", BUILD / "classes", "@" + response.relative_to(ROOT).as_posix()])
    with zipfile.ZipFile(BUILD / "classes.jar", "w", zipfile.ZIP_DEFLATED) as jar:
        for path in sorted((BUILD / "classes").rglob("*.class")): jar.write(path, path.relative_to(BUILD / "classes").as_posix())
    run("Compile Android DEX", [java, "-cp", tools / "lib/d8.jar", "com.android.tools.r8.D8", "--release", "--min-api", "28", "--lib", android, "--output", BUILD / "dex", BUILD / "classes.jar"])
    unsigned = BUILD / "LMA-unsigned.apk"
    # Normalize local ZIP headers before alignment rather than append through an
    # SDK-created central directory with producer-specific padding fields.
    with zipfile.ZipFile(BUILD / "resources.apk") as resources, zipfile.ZipFile(unsigned, "w", zipfile.ZIP_DEFLATED) as apk:
        for entry in resources.infolist():
            normalized = zipfile.ZipInfo(entry.filename, entry.date_time)
            normalized.compress_type = entry.compress_type
            normalized.external_attr = entry.external_attr
            apk.writestr(normalized, resources.read(entry))
        for path in sorted((BUILD / "dex").glob("*.dex")): apk.write(path, path.name)
        for path in sorted(native.glob("*.so")): apk.write(path, "lib/arm64-v8a/" + path.name)
    run("Align APK", [tools / "zipalign.exe", "-P", "16", "-f", "4", unsigned, BUILD / "LMA-aligned.apk"])
    password_file = ROOT / "signing/local-key-password.txt"
    if not password_file.exists(): password_file.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    env = os.environ.copy(); env["LMA_SIGNING_PASSWORD"] = password_file.read_text(encoding="utf-8").strip()
    keystore = ROOT / "signing/lma-local.p12"
    if not keystore.exists():
        run("Create persistent local signing key", [keytool, "-genkeypair", "-keystore", keystore, "-storetype", "PKCS12", "-alias", "lma", "-keyalg", "RSA", "-keysize", "3072", "-validity", "10000", "-dname", "CN=LMA Local Build,O=LMA", "-storepass:env", "LMA_SIGNING_PASSWORD", "-keypass:env", "LMA_SIGNING_PASSWORD"], env)
    release = version()
    apk = DIST / ("LMA-" + release + "-arm64-v8a.apk")
    run("Sign APK", [java, "-jar", tools / "lib/apksigner.jar", "sign", "--ks", keystore, "--ks-key-alias", "lma", "--ks-pass", "env:LMA_SIGNING_PASSWORD", "--key-pass", "env:LMA_SIGNING_PASSWORD", "--v1-signing-enabled", "true", "--v2-signing-enabled", "true", "--v3-signing-enabled", "true", "--out", apk, BUILD / "LMA-aligned.apk"], env)
    signature = run("Verify APK signatures", [java, "-jar", tools / "lib/apksigner.jar", "verify", "--verbose", "--print-certs", apk])
    badging = run("Inspect APK identity", [tools / "aapt.exe", "dump", "badging", apk])
    if "package: name='com.lma.app'" not in badging or "application-label:'LMA'" not in badging: raise ValueError("Unexpected APK identity")
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    (DIST / (apk.name + ".sha256")).write_text(digest + "  " + apk.name + "\n", encoding="utf-8")
    record = {"apk": apk.name, "bytes": apk.stat().st_size, "sha256": digest, "package": "com.lma.app", "version": release, "min_sdk": 28,
              "target_sdk": 35, "abi": "arm64-v8a", "backend": "CPU", "native_libraries": len(native_names), "native_engines": engines, "java_source_files": len(sources), "build_tools": "35.0.1", "sdk_platform": "35",
              "signatures_verified": True, "physical_device_tests": 0, "emulator_used": False, "docker_or_wsl_used": False,
              "signing": "project-local persistent key; signing/ must be preserved for updates", "input_fingerprint": build_inputs()}
    (DIST / "build-info.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (BUILD / "signature-verification.txt").write_text(signature, encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if k != "input_fingerprint"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
