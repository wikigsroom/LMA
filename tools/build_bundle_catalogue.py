"""Package pinned bundle metadata only, without fetching model files."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / "catalogue/model-bundles.json"
    data = path.read_bytes(); catalogue = json.loads(data)
    evidence = json.loads((ROOT / "catalogue/bundle-evidence.json").read_text(encoding="utf-8"))
    assert catalogue["schema"] == "lma.bundle-catalogue/1" and not evidence["model_inference_tested"]
    assert evidence["physical_device_tests"] == 0 and not evidence["model_weights_downloaded"]
    ids = set()
    for bundle in catalogue["bundles"]:
        assert bundle["id"] not in ids and bundle["schema"] == "lma.model-bundle/1"
        ids.add(bundle["id"])
        assert bundle["catalogue"] and bundle["evidence"]["physicalDeviceTests"] == 0
        assert bundle["tasks"] and all(task in ("text", "image", "video", "audio") for task in bundle["tasks"])
        for c in bundle["components"]:
            assert re.fullmatch("[0-9a-f]{40,64}", c["revision"]) and re.fullmatch("[0-9a-f]{64}", c["sha256"])
            assert c["bytes"] > 0 and c["url"] == "https://huggingface.co/" + c["repository"] + "/resolve/" + c["revision"] + "/" + c["path"]
        assert bundle["id"] == evidence["bundleId"], "Add individual source evidence before extending this catalogue"
        model = next(c for c in bundle["components"] if c["role"] == "model")
        tokenizer = next(c for c in bundle["components"] if c["role"] == "clip_merges")
        assert model["repository"] == evidence["weight"]["repository"] and model["revision"] == evidence["weight"]["revision"] and model["path"] == evidence["weight"]["file"]["rfilename"]
        assert all(tokenizer[key] == evidence["tokenizer"][key] for key in ("repository", "revision", "path"))
        assert model["sha256"] == evidence["weight"]["file"]["lfs"]["sha256"] and model["bytes"] == evidence["weight"]["file"]["size"]
        assert tokenizer["sha256"] == evidence["tokenizer"]["sha256"] and tokenizer["bytes"] == evidence["tokenizer"]["bytes"]
    (ROOT / "app/src/main/assets/model-bundles.json").write_bytes(data)
    print(json.dumps({"bundles": len(ids), "model_assets_downloaded": False, "catalogue_sha256": hashlib.sha256(data).hexdigest()}))


if __name__ == "__main__":
    main()
