"""Build a separately signed instrumentation APK for later physical-device testing."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile
from build import run
from evidence import fingerprint
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/device-tests"


def main():
    build = json.loads((ROOT / "dist/build-info.json").read_text(encoding="utf-8"))
    assert build["input_fingerprint"] == build_inputs(), "Build the current application first"
    sdk = Path(os.environ.get("ANDROID_SDK_ROOT", str(Path(os.environ["LOCALAPPDATA"]) / "Android/Sdk")))
    sdk_tools = sdk / "build-tools/35.0.1"; android = sdk / "platforms/android-35/android.jar"
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("classes", "dex"):
        folder = (OUT / name).resolve(); assert OUT.resolve() == folder.parent
        if folder.exists(): shutil.rmtree(folder)
        folder.mkdir()
    java, javac = shutil.which("java"), shutil.which("javac")
    run("Link physical-device acceptance manifest", [sdk_tools / "aapt2.exe", "link", "-o", OUT / "resources.apk", "-I", android, "--manifest", ROOT / "tests/android/AndroidManifest.xml", "--min-sdk-version", "28", "--target-sdk-version", "35"])
    sources = sorted((ROOT / "tests/android").rglob("*.java"))
    response = OUT / "sources.rsp"; response.write_text("\n".join('"' + p.as_posix() + '"' for p in sources), encoding="utf-8")
    run("Compile physical-device instrumentation", [javac, "-J-Duser.language=en", "-encoding", "UTF-8", "--release", "8", "-cp", str(android) + os.pathsep + "build/classes.jar", "-d", OUT / "classes", "@" + response.relative_to(ROOT).as_posix()])
    with zipfile.ZipFile(OUT / "classes.jar", "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted((OUT / "classes").rglob("*.class")): archive.write(file, file.relative_to(OUT / "classes").as_posix())
    run("DEX physical-device instrumentation", [java, "-cp", sdk_tools / "lib/d8.jar", "com.android.tools.r8.D8", "--release", "--min-api", "28", "--lib", android, "--classpath", ROOT / "build/classes.jar", "--output", OUT / "dex", OUT / "classes.jar"])
    with zipfile.ZipFile(OUT / "resources.apk") as resources, zipfile.ZipFile(OUT / "unsigned.apk", "w", zipfile.ZIP_DEFLATED) as apk:
        for item in resources.infolist(): apk.writestr(item.filename, resources.read(item))
        apk.write(OUT / "dex/classes.dex", "classes.dex")
    run("Align physical-device instrumentation", [sdk_tools / "zipalign.exe", "-f", "4", OUT / "unsigned.apk", OUT / "aligned.apk"])
    env = os.environ.copy(); env["LMA_SIGNING_PASSWORD"] = (ROOT / "signing/local-key-password.txt").read_text(encoding="utf-8").strip()
    apk = OUT / "LMA-acceptance.apk"
    run("Sign physical-device instrumentation", [java, "-jar", sdk_tools / "lib/apksigner.jar", "sign", "--ks", ROOT / "signing/lma-local.p12", "--ks-key-alias", "lma", "--ks-pass", "env:LMA_SIGNING_PASSWORD", "--key-pass", "env:LMA_SIGNING_PASSWORD", "--out", apk, OUT / "aligned.apk"], env)
    run("Verify physical-device instrumentation", [java, "-jar", sdk_tools / "lib/apksigner.jar", "verify", "--verbose", apk])
    record = {"apk": apk.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(), "applicationApkSha256": build["sha256"], "input_fingerprint": fingerprint("tests/android", "tools/build_acceptance.py"), "compiled": True, "executed_on_device": False}
    (OUT / "acceptance-build.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if k != "input_fingerprint"}))


if __name__ == "__main__": main()
