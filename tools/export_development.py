"""Export only current development checks, explicitly excluding Release/device completion."""
import json
from pathlib import Path
import shutil
from evidence import current, build_inputs, version

ROOT = Path(__file__).resolve().parents[1]


def main():
    if "-dev" not in version():
        raise RuntimeError("Use the full release workflow for release candidates")
    sources = {
        "build-info.json": "dist/build-info.json",
        "package.json": "build/package-verification.json",
        "foundation.json": "build/foundation-tests/results.json",
        "tts.json": "build/tts-tests/results.json",
        "text.json": "build/text-tests/results.json",
        "migration.json": "build/migration-tests/results.json",
        "scheduler.json": "build/scheduler-tests/results.json",
        "inputs.json": "build/input-tests/results.json",
        "diffusion.json": "build/diffusion-tests/results.json",
        "moss-nano.json": "build/moss-nano-tests/results.json",
        "mnn.json": "build/mnn-tests/results.json",
        "qwen-tts.json": "build/qwen-tts-tests/results.json",
        "qwen-headers.json": "build/qwen-headers.json",
        "api.json": "build/api-tests/results.json",
        "backend.json": "build/backend-tests/results.json",
        "hub.json": "build/hub-tests/results.json",
        "ui.json": "build/ui-qa/results.json",
        "lint.json": "build/android-lint/results.json",
    }
    out = ROOT / "verification/development"
    out.mkdir(parents=True, exist_ok=True)
    for name, source in sources.items():
        record = json.loads((ROOT / source).read_text(encoding="utf-8"))
        current(record["input_fingerprint"])
        if name == "build-info.json" and record["input_fingerprint"] != build_inputs():
            raise RuntimeError("Rebuild development APK first")
        shutil.copyfile(ROOT / source, out / name)
    status = {"version": version(), "kind": "development_checkpoint", "release_ready": False, "published": False,
              "physical_device_tests": 0, "model_inference_tested": False, "all_selected_models_supported": False,
              "scope": "real Qwen3-TTS 0.6B Base ARM64 CPU compilation, production two-GGUF binding, optional reference WAV, embedded dependency disclosure, actual host child/file checks with structural WAV fixtures, pinned header review without tensor reads or model inference; real MNN Sana ARM64 CPU compilation and production 13-component binding with sanitized metadata, parameter snapshots, actual host children and deferred workspace cleanup (no image inference); production diffusion binding, strict classic/Z-Image/FLUX/Qwen/Wan components, actual flow-shift/sampler/scheduler bindings and Qwen/Wan geometry policies with actual host protocol children and shared native C++ checks; local input imports, bounded resumable upload HTTP and production WAV validation, immutable input receipts/leases in the production job runner with host child fixtures; shared FIFO scheduling across production jobs, resident text, chat and HTTP with actual host child ownership and cancellation; actual host legacy model migration, hardlinks, fixed aliases and shared leases without auto-resume; host GGUF text bundle constraints, typed text artifacts and actual loopback HTTP/child fixtures, host storage/transfers, user-reviewed atomic model version changes/rollback and HF component recipes/Git integrity, explicit adapter pairing/leases, speech worker contracts/child fixtures, Nano native external-data validation and private hardlink workspaces, authenticated HTTP/streams/text proxy, UI fixtures, native compilation and APK/lint checks only",
              "required_scope": "docs/MULTIMODAL_RELEASE_PLAN.md", "sources": sources}
    (out / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status))


if __name__ == "__main__":
    main()
