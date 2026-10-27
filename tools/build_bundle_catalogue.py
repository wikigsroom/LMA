"""Package pinned bundle metadata only, without fetching model files."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / "catalogue/model-bundles.json"
    data = path.read_bytes(); catalogue = json.loads(data)
    evidence = json.loads((ROOT / "catalogue/bundle-evidence.json").read_text(encoding="utf-8"))
    assert catalogue["schema"] == "lma.bundle-catalogue/1" and not evidence["model_inference_tested"]
    assert evidence["physical_device_tests"] == 0 and not evidence["model_weights_downloaded"]
    assert evidence["schema"] == "lma.bundle-metadata-evidence/2"
    proofs = {b["bundleId"]: b for b in evidence["bundles"]}
    assert len(proofs) == len(evidence["bundles"])
    ids = set()
    for bundle in catalogue["bundles"]:
        assert bundle["id"] not in ids and bundle["schema"] == "lma.model-bundle/1"
        ids.add(bundle["id"])
        assert bundle["catalogue"] and bundle["evidence"]["physicalDeviceTests"] == 0
        assert bundle["tasks"] and all(task in ("text", "image", "video", "audio") for task in bundle["tasks"])
        proof = proofs[bundle["id"]]
        components = {c["role"]: c for c in proof["components"]}
        assert len(components) == len(proof["components"]) == len(bundle["components"])
        for c in bundle["components"]:
            assert re.fullmatch("[0-9a-f]{64}", c["sha256"]) and c["bytes"] > 0
            checked = components[c["role"]]
            assert all(c[key] == checked[key] for key in ("path", "bytes", "sha256", "repository", "revision"))
            if checked["kind"] in ("hf_lfs", "downloaded_small_data"):
                assert re.fullmatch("[0-9a-f]{40,64}", c["revision"])
                assert c["url"] == "https://huggingface.co/" + c["repository"] + "/resolve/" + c["revision"] + "/" + c["path"]
            elif checked["kind"] == "github_release_asset":
                assert c["repository"] == "k2-fsa/sherpa-onnx" and c["revision"] == "github_asset_" + str(checked["assetId"])
                assert c["url"].startswith("https://github.com/k2-fsa/sherpa-onnx/releases/download/") and c["url"].endswith("/" + c["path"])
                assert checked.get("publisherDigest") == "sha256:" + c["sha256"] or urlparse(checked["crossCheckedShaSource"]).netloc == "huggingface.co"
            else: raise AssertionError("Unreviewed catalogue component evidence")
    assert ids == set(proofs), "Each shipped candidate requires individual component evidence"
    (ROOT / "app/src/main/assets/model-bundles.json").write_bytes(data)
    print(json.dumps({"bundles": len(ids), "model_assets_downloaded": False, "catalogue_sha256": hashlib.sha256(data).hexdigest()}))


if __name__ == "__main__":
    main()
