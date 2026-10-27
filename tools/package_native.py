"""Verify signed-in native workers and their build inputs before APK packaging."""
import hashlib
import json
from pathlib import Path
from evidence import current

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    lock = json.loads((ROOT / "third_party/engine-lock.json").read_text(encoding="utf-8"))
    receipt = json.loads((ROOT / "build/native-build-info.json").read_text(encoding="utf-8"))
    current(receipt["source_inputs"])
    engines = []
    for expected in lock["engines"]:
        for key in ("engine", "file", "source_revision", "ggml_revision", "abi", "backend", "ndk", "sha256", "bytes"):
            if receipt.get(key) != expected.get(key):
                raise RuntimeError("Native build receipt differs from the reviewed lock: " + key)
        binary = ROOT / "app/src/main/jniLibs/arm64-v8a" / expected["file"]
        if binary.stat().st_size != expected["bytes"] or hashlib.sha256(binary.read_bytes()).hexdigest() != expected["sha256"]:
            raise RuntimeError("Native worker hash mismatch; rebuild and review the engine lock")
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
