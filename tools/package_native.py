"""Verify signed-in native workers and their build inputs before APK packaging."""
import hashlib
import json
from pathlib import Path
from evidence import current
from verify_package import elf_info
from native_payload import engine_files
from package_preparations import prepare as prepare_preparations

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = {"sd_cpp": "native-build-info.json", "sherpa_tts": "tts-build-info.json", "moss_nano_ort": "moss-nano-build-info.json", "mnn_diffusion": "mnn-build-info.json", "qwen_tts_native": "qwen-tts-build-info.json", "moss_delay_native": "moss-delay-build-info.json", "openmoss_native": "openmoss-build-info.json", "moss_rq_native": "moss_rq-build-info.json", "stable_audio_litert": "stable-audio-build-info.json", "soulx_native": "soulx-build-info.json", "ltx098_native": "ltx098-app-build-info.json", "wan_sd_cpp": "wan-vulkan-build-info.json"}


def text_runtime():
    runtime = json.loads((ROOT / "third_party/runtime-lock.json").read_text(encoding="utf-8"))
    info = json.loads((ROOT / "third_party/BUILD_INFO.json").read_text(encoding="utf-8"))
    records = []
    for item in runtime["files"]:
        data = (ROOT / "app/src/main/jniLibs/arm64-v8a" / item["name"]).read_bytes()
        if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]: raise RuntimeError("Text runtime differs from reviewed lock: " + item["name"])
        elf = elf_info(data)
        if not elf["16k_elf_aligned"] or any(api > 28 for api in elf["android_api_notes"]): raise RuntimeError("Text runtime ELF contract changed")
        records.append(dict(file=item["name"], bytes=item["size"], sha256=item["sha256"], android_api_notes=elf["android_api_notes"]))
    worker = next(x for x in records if x["file"] == "libllama-server.so")
    return dict(worker, engine="llama_text", abi="arm64-v8a", backend="cpu", source_revision=info["llamaCppCommit"], version=runtime["version"],
        provenance="existing_pinned_prebuilt_runtime", dependencies=[x for x in records if x is not worker],
        deviceValidated=False, model_inference_tested=False, status="packaged_not_device_tested", vocabularies="external_user_selected_gguf")


def prepare():
    lock = json.loads((ROOT / "third_party/engine-lock.json").read_text(encoding="utf-8"))
    engines = []
    engine_files(lock["engines"] + lock.get("preparations", []))
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
    preparations = prepare_preparations()
    path.write_text(json.dumps({"schema": "lma.engine-builds/1", "engines": engines, "preparations": preparations, "textRuntime": text_runtime()}, indent=2) + "\n", encoding="utf-8")
    return engines


if __name__ == "__main__":
    print(json.dumps({"engines": prepare()}))
