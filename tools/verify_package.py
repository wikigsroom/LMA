"""Check APK contents, pinned ELF dependencies and catalogue integrity; no execution on Android."""
import hashlib
import json
from pathlib import Path
import struct
import os
import subprocess
import zipfile
import shutil
import re
from evidence import version, build_inputs, fingerprint

ROOT = Path(__file__).resolve().parents[1]
APK = ROOT / ("dist/LMA-" + version() + "-arm64-v8a.apk")
LIBS = ROOT / "app/src/main/jniLibs/arm64-v8a"
SYSTEM_LIBS = {"libc.so", "libm.so", "libdl.so", "liblog.so", "libandroid.so", "libz.so"}


def elf_info(data):
    if data[:6] != b"\x7fELF\x02\x01":
        raise AssertionError("Expected a little-endian ELF64 binary")
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine != 183:
        raise AssertionError("Expected ARM64 machine type")
    phoff = struct.unpack_from("<Q", data, 32)[0]
    phsize, phcount = struct.unpack_from("<HH", data, 54)
    segments = [struct.unpack_from("<IIQQQQQQ", data, phoff + i * phsize) for i in range(phcount)]
    loads = [p for p in segments if p[0] == 1]
    interpreter = next((data[p[2]:p[2] + p[5]].rstrip(b"\0").decode("ascii") for p in segments if p[0] == 3), None)
    android_api = []
    for p in segments:
        if p[0] != 4: continue
        position, end = p[2], p[2] + p[5]
        while position + 12 <= end:
            name_length, descriptor_length, kind = struct.unpack_from("<III", data, position); position += 12
            assert position + ((name_length + 3) // 4 * 4) + descriptor_length <= end, "Invalid ELF note"
            name = data[position:position + name_length].rstrip(b"\0"); position += (name_length + 3) // 4 * 4
            descriptor = data[position:position + descriptor_length]; position += (descriptor_length + 3) // 4 * 4
            if name == b"Android" and kind == 1 and len(descriptor) >= 4: android_api.append(struct.unpack_from("<I", descriptor)[0])
    dynamic = next((p for p in segments if p[0] == 2), None)
    needed, string_table = [], None
    if dynamic:
        for off in range(dynamic[2], dynamic[2] + dynamic[5], 16):
            tag, value = struct.unpack_from("<qQ", data, off)
            if tag == 0: break
            if tag == 1: needed.append(value)
            if tag == 5: string_table = value
    dependencies = []
    if needed:
        assert string_table is not None
        mapping = next(p for p in loads if p[3] <= string_table < p[3] + p[5])
        start = mapping[2] + string_table - mapping[3]
        for item in needed:
            off = start + item
            dependencies.append(data[off:data.index(b"\0", off)].decode("ascii"))
    return {"machine": "aarch64", "needed": dependencies, "load_segment_alignment": sorted(set(p[7] for p in loads)),
            "interpreter": interpreter, "entry_point": struct.unpack_from("<Q", data, 24)[0], "android_api_notes": android_api,
            "16k_elf_aligned": all(p[7] >= 16384 and (p[3] - p[2]) % 16384 == 0 for p in loads)}


def main():
    (ROOT / "build/package-verification.json").unlink(missing_ok=True)
    lock = json.loads((ROOT / "third_party/runtime-lock.json").read_text(encoding="utf-8"))
    engines = json.loads((ROOT / "third_party/engine-lock.json").read_text(encoding="utf-8"))["engines"]
    lock["files"].extend({"name": item["file"], "sha256": item["sha256"], "android_api_notes": item.get("android_api_notes", [28])} for engine in engines for item in [engine] + engine.get("dependencies", []))
    assert len({item["name"] for item in lock["files"]}) == len(lock["files"]), "Duplicate native module file"
    names = {item["name"] for item in lock["files"]}
    assert {p.name for p in LIBS.glob("*.so")} == names, "Unexpected or missing native payload"
    assert "libggml-cpu-android_armv8.0_1.so" in names, "Baseline ARMv8 CPU kernel missing"
    native = {}
    with zipfile.ZipFile(APK) as archive:
        assert archive.testzip() is None, "APK ZIP corruption"
        members = archive.namelist()
        assert len(members) == len(set(members)), "Duplicate APK members"
        for name in ["classes.dex", "AndroidManifest.xml", "resources.arsc", "assets/index.html", "assets/app.css", "assets/app.js", "assets/license.js", "assets/licenses/LLAMA_CPP_LICENSE", "assets/models.json"]:
            assert name in members, "Missing APK entry: " + name
        assert archive.read("classes.dex").startswith(b"dex\n"), "DEX header missing"
        source = ROOT / "app/src/main"
        ui_assets = ("index.html", "app.css", "app.js", "foundation.css", "foundation.js", "recipes.js", "recipe-templates.json", "license.js", "models.json", "model-bundles.json", "engine-builds.json")
        for name in ui_assets:
            assert archive.read("assets/" + name) == (source / "assets" / name).read_bytes(), "Stale packaged UI: " + name
        for name in ("license.js", "app.js"):
            assert name in archive.read("assets/index.html").decode("utf-8"), "Missing UI script reference"
        for item in lock["files"]:
            data = archive.read("lib/arm64-v8a/" + item["name"])
            assert hashlib.sha256(data).hexdigest() == item["sha256"], "Packaged runtime hash mismatch"
            assert (LIBS / item["name"]).read_bytes() == data
            native[item["name"]] = elf_info(data)
            assert native[item["name"]]["android_api_notes"] == item.get("android_api_notes", [28]) and max(native[item["name"]]["android_api_notes"]) <= 28, "Native minimum API differs from reviewed Android 9-compatible binary: " + item["name"]
            missing = set(native[item["name"]]["needed"]) - names - SYSTEM_LIBS
            assert not missing, "Unresolved native dependencies: " + str(missing)
        assert len([name for name in members if name.startswith("lib/")]) == len(names)
        launcher = native["libllama-server.so"]
        assert launcher["entry_point"] > 0 and launcher["interpreter"] == "/system/bin/linker64", "Native launcher is not an Android ARM64 executable"
        catalogue = json.loads(archive.read("assets/models.json"))
        assert catalogue["scope"] == "local-models-with-uncensored-tags"
        assert catalogue["discovery"] == "huggingface-hub-paginated"
        assert [m["id"] for m in catalogue["models"] if m["recommended"]] == ["m08", "m06", "m01"]
        uncensored = json.loads((ROOT / "catalogue/uncensored-evidence.json").read_text(encoding="utf-8"))
        declarations = {m["id"]: m for m in uncensored["models"]}
        ids = set()
        for model in catalogue["models"]:
            assert model["id"] not in ids; ids.add(model["id"])
            assert model["url"].startswith("https://") and model["url"].endswith(".gguf")
            assert re.fullmatch(r"[0-9a-f]{64}", model["sha256"])
            assert re.fullmatch(r"[0-9a-f]{40}", model["revision"])
            assert "/resolve/" + model["revision"] + "/" in model["url"]
            assert model["bytes"] > 0 and model["sizeIsApproximate"] is False
            assert model["deviceTested"] is False
            declaration = declarations[model["id"]]
            assert declaration["qualified"] is True and declaration["weight_sha256"] == model["sha256"]
            assert model["uncensored"]["declared"] is True
            assert model["uncensored"]["basis"] == "publisher-declared-uncensored"
            assert model["uncensored"]["evidenceUrl"] == declaration["author_card_url"]
        for name in members:
            assert not name.startswith("signing/") and not name.endswith((".p12", ".part", ".gguf")), "Private key or model weight accidentally packaged"
            if name.startswith("assets/"):
                assert name[7:] in ui_assets or name.startswith("assets/licenses/"), "Unreviewed model-specific or other asset in APK: " + name
        engine_manifest = json.loads(archive.read("assets/engine-builds.json"))
        assert len(engine_manifest["engines"]) == len(engines)
        for engine in engines:
            included = next(e for e in engine_manifest["engines"] if e["engine"] == engine["engine"])
            assert included["sha256"] == engine["sha256"] and not included["model_inference_tested"]
            for name, digest in engine["notices"].items():
                assert hashlib.sha256(archive.read("assets/licenses/" + name)).hexdigest() == digest
    metadata = json.loads((ROOT / "dist/build-info.json").read_text(encoding="utf-8"))
    assert metadata["sha256"] == hashlib.sha256(APK.read_bytes()).hexdigest()
    assert metadata["input_fingerprint"] == build_inputs(), "APK build inputs have changed since compilation"
    sdk = Path(os.environ.get("ANDROID_SDK_ROOT", str(Path(os.environ.get("LOCALAPPDATA", "C:/Users/carzy/AppData/Local")) / "Android/Sdk")))
    aligned = subprocess.run([str(sdk / "build-tools/35.0.1/zipalign.exe"), "-c", "-P", "16", "4", str(APK.relative_to(ROOT))], cwd=ROOT, capture_output=True, text=True)
    assert aligned.returncode == 0, "Final APK alignment failed: " + aligned.stderr
    signature = subprocess.run([shutil.which("java"), "-jar", str(sdk / "build-tools/35.0.1/lib/apksigner.jar"), "verify", "--verbose", "--print-certs", str(APK.relative_to(ROOT))], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8")
    badging = subprocess.run([str(sdk / "build-tools/35.0.1/aapt.exe"), "dump", "badging", str(APK.relative_to(ROOT))], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    for expected in ("package: name='com.lma.app'", "versionName='" + version() + "'", "sdkVersion:'28'", "targetSdkVersion:'35'", "native-code: 'arm64-v8a'", "application-label:'LMA'"):
        assert expected in badging, "Wrong APK identity: " + expected
    assert "application-debuggable" not in badging, "Delivery APK must not be debuggable"
    permissions = re.findall(r"uses-permission: name='([^']+)'", badging)
    assert "android.permission.FOREGROUND_SERVICE_SPECIAL_USE" in permissions
    assert not set(permissions) & {"android.permission.MANAGE_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE", "android.permission.READ_EXTERNAL_STORAGE"}
    certificate = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-f]+)", signature.stdout)
    assert certificate, "Signing certificate digest missing"
    manifest = subprocess.run([str(sdk / "build-tools/35.0.1/aapt.exe"), "dump", "xmltree", str(APK.relative_to(ROOT)), "AndroidManifest.xml"], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    service = manifest.split("E: service ", 1)[1].split("E: receiver ", 1)[0]
    assert '=".LmaService"' in service
    assert re.search(r"android:exported\([^\n]+\)=\(type 0x12\)0x0", service)
    assert re.search(r"android:stopWithTask\([^\n]+\)=\(type 0x12\)0x0", service)
    assert "0x40000000" in service and "android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE" in service
    provider = json.loads((ROOT / "third_party/BUILD_INFO.json").read_text(encoding="utf-8"))
    assert provider["androidApiLevel"] == 28 and provider["androidAbi"] == "arm64-v8a"
    assert all(n["16k_elf_aligned"] for n in native.values()), "An ELF LOAD segment is not 16K aligned"
    result = {"apk": APK.name, "sha256": metadata["sha256"], "native_libraries_verified": len(native), "all_native_dependencies_resolved": True,
              "all_elf_load_segments_16k_aligned": all(n["16k_elf_aligned"] for n in native.values()), "final_apk_zip_alignment_verified": True, "packaged_ui_matches_source": True, "catalogue_models": len(ids),
              "known_publisher_hashes": sum(bool(m["sha256"]) for m in catalogue["models"]), "private_keys_in_apk": False,
              "builtin_uncensored_declarations_verified": len(ids), "refusal_rates_measured": False,
              "native": native, "physical_device_tested": False, "source_inputs_match_build": True,
              "apk_signatures_independently_verified": True, "signing_certificate_sha256": certificate.group(1), "permissions": permissions,
              "provider_declared_native_api_level": provider["androidApiLevel"], "packaged_service_manifest_verified": True,
              "input_fingerprint": fingerprint("tools/verify_package.py", "third_party/BUILD_INFO.json", "catalogue/uncensored-evidence.json")}
    (ROOT / "build/package-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("native", "input_fingerprint")}, ensure_ascii=True))


if __name__ == "__main__":
    main()
