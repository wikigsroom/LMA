"""Verify signed-in native workers and their build inputs before APK packaging."""
import hashlib
import json
from pathlib import Path
from evidence import current
from verify_package import elf_info
from native_payload import engine_files

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = {"sd_cpp": "native-build-info.json", "sherpa_tts": "tts-build-info.json", "moss_nano_ort": "moss-nano-build-info.json"}


def prepare():
    lock = json.loads((ROOT / "third_party/engine-lock.json").read_text(encoding="utf-8"))
    engines = []
    engine_files(lock["engines"])
    for expected in lock["engines"]:
        receipt = json.loads((ROOT / "build" / RECEIPTS[expected["engine"]]).read_text(encoding="utf-8"))
        current(receipt["source_inputs"])
        for key in ("engine", "file", "source_revision", "ggml_revision", "abi", "backend", "ndk", "sha256", "bytes", "dependencies"):
            if receipt.get(key) != expected.get(key):
                raise RuntimeError("Native build receipt differs from the reviewed lock: " + key)
        for item in [expected] + expected.get("dependencies", []):
            name = item["file"]
            if Path(name).name != name: raise RuntimeError("Invalid native dependency name")
            binary = ROOT / "app/src/main/jniLibs/arm64-v8a" / name
            data = binary.read_bytes()
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]: raise RuntimeError("Native binary differs from reviewed lock: " + name)
            info = elf_info(data)
            if not info["16k_elf_aligned"] or info["android_api_notes"] != item.get("android_api_notes", [28]): raise RuntimeError("Native ELF/API contract changed: " + name)
        if receipt.get("vocabularies") != "external_user_selected_components" or min(receipt["elf_load_alignment"]) < 16384:
            raise RuntimeError("Native worker violates the asset separation or page alignment contract")
        notices = expected["notices"]
        for name, digest in notices.items():
            path = ROOT / "third_party/notices" / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise RuntimeError("Native dependency notice changed: " + name)
        build = {k: v for k, v in receipt.items() if k != "source_inputs"}
        build.update({"deviceValidated": False, "status": "compiled_not_device_tested", "notices": list(notices)})
        engines.append(build)
    path = ROOT / "app/src/main/assets/engine-builds.json"
    path.write_text(json.dumps({"schema": "lma.engine-builds/1", "engines": engines}, indent=2) + "\n", encoding="utf-8")
    return engines


if __name__ == "__main__":
    print(json.dumps({"engines": prepare()}))
