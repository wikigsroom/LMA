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
              "scope": "host storage/transfers/contracts and explicit adapter pairing/leases, speech worker contracts/child fixtures, authenticated HTTP/streams/text proxy, UI fixtures, native compilation and APK/lint checks only",
              "required_scope": "docs/MULTIMODAL_RELEASE_PLAN.md", "sources": sources}
    (out / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status))


if __name__ == "__main__":
    main()
