"""Package pinned bundle metadata only, without fetching model files."""
import hashlib
import json
from pathlib import Path
import re
from evidence import current
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
            assert all(c.get(key, "") == checked.get(key, "") for key in ("path", "bytes", "sha256", "repository", "revision"))
            if checked["kind"] in ("hf_lfs", "downloaded_small_data"):
                assert re.fullmatch("[0-9a-f]{40,64}", c["revision"])
                assert c["url"] == "https://huggingface.co/" + c["repository"] + "/resolve/" + c["revision"] + "/" + c["path"]
            elif checked["kind"] == "github_release_asset":
                assert c["repository"] == "k2-fsa/sherpa-onnx" and c["revision"] == "github_asset_" + str(checked["assetId"])
                assert c["url"].startswith("https://github.com/k2-fsa/sherpa-onnx/releases/download/") and c["url"].endswith("/" + c["path"])
                assert checked.get("publisherDigest") == "sha256:" + c["sha256"] or urlparse(checked["crossCheckedShaSource"]).netloc == "huggingface.co"
            elif checked["kind"] == "measured_prepared_output":
                preparation = next(p for p in json.loads((ROOT / "catalogue/asset-preparations.json").read_text(encoding="utf-8"))["plans"] if p["id"] == checked["preparationId"])
                declared = next(o for stage in preparation["stages"] for o in stage["outputs"] if o["role"] == c["role"])
                assert (c["path"], c["bytes"], c["sha256"]) == (declared["file"], declared["bytes"], declared["sha256"]) and not c.get("url")
                path = ROOT / checked["source"]; measured = json.loads(path.read_text(encoding="utf-8")); current(measured["input_fingerprint"])
                assert measured["passed"] and measured["actual_trained_conversions"] == 1
                if c["role"] == "diffusion_model":
                    assert checked["source"] == "verification/development/ltx098-prepare.json"
                    actual = measured["trained"]["native"]
                    assert (c["bytes"], c["sha256"]) == (actual["output_bytes"], actual["output_sha256"])
                else:
                    assert checked["source"] == "verification/development/ltx098-vae-prepare.json"
                    actual = measured["trained_conversion"]
                    if c["role"] == "vae_manifest": assert (c["bytes"], c["sha256"]) == (actual["manifest_bytes"], actual["manifest_sha256"])
                    else:
                        item = next(item for item in actual["assets"] if item["file"] == c["path"])
                        assert (c["bytes"], c["sha256"]) == (item["bytes"], item["sha256"])
            elif checked["kind"] == "measured_text_input":
                assert checked["source"] == "verification/development/ltx098-text.json" and checked["live_hf_metadata_checked_this_update"] is False
                measured = json.loads((ROOT / checked["source"]).read_text(encoding="utf-8")); current(measured["input_fingerprint"])
                lock = json.loads((ROOT / "third_party/ltx098-text-source-lock.json").read_text(encoding="utf-8"))
                assert measured["host_model_inference_tested"] and measured["trained"]["model"] == lock["model"]
                assert c["role"] in ("text_encoder", "tokenizer_config")
                item = lock["model"] if c["role"] == "text_encoder" else lock["runtime_tokenizer_config"]
                assert (c["repository"], c["revision"], c["path"], c["bytes"], c["sha256"]) == (item["repo"], item["revision"], item["file"], item["bytes"], item["sha256"])
                assert c["url"] == "https://huggingface.co/" + item["repo"] + "/resolve/" + item["revision"] + "/" + item["file"]
            elif checked["kind"] == "measured_checkpoint":
                # Immutable source identity measured from the complete developer-selected file.
                # This does not claim that the current HF metadata/download endpoint was reached.
                assert checked["source"] == "verification/development/ltx098-vae-prepare.json" and checked["live_hf_metadata_checked_this_update"] is False
                path = ROOT / "build/ltx098-vae-prepare-tests/results.json"
                if not path.exists(): path = ROOT / checked["source"]
                measured = json.loads(path.read_text(encoding="utf-8")); current(measured["input_fingerprint"])
                assert measured["passed"] and measured["actual_trained_conversions"] == 1
                source = measured["trained_conversion"]
                assert source["source_sha256_verified"] and source["source_sha256"] == c["sha256"] and source["source_bytes"] == c["bytes"]
                identity = json.loads((ROOT / "research/ltx098_vae_prepare/contract.json").read_text(encoding="utf-8"))["checkpoint"]
                assert (c["repository"], c["revision"], c["path"]) == (identity["repository"], identity["revision"], identity["file"])
                assert c["url"] == "https://huggingface.co/" + c["repository"] + "/resolve/" + c["revision"] + "/" + c["path"]
            elif checked["kind"] in ("measured_lcm_source", "measured_lcm_base", "measured_lcm_condition"):
                # Identity evidence is independent from the explicitly failed image-equivalence gate.
                assert checked["live_hf_metadata_checked_this_update"] is False
                trained = json.loads((ROOT / "verification/development/lcm-preparation-trained.json").read_text(encoding="utf-8"))
                assert trained["passed"] and trained["source_complete_sha256_verified"]
                if checked["kind"] == "measured_lcm_source":
                    assert checked["source"] == "verification/development/lcm-preparation-trained.json"
                    assert all(c[k] == trained["source"][k] for k in ("path", "bytes", "sha256", "repository", "revision", "url"))
                elif checked["kind"] == "measured_lcm_base":
                    assert checked["source"] == "verification/development/lcm-overlay-trained.json"
                    capture = json.loads((ROOT / checked["source"]).read_text(encoding="utf-8"))
                    assert capture["base_whole_sha256_verified"] and not capture["passed"] and not capture["image_quality_accepted"]
                    assert all(c[k] == capture["base"][k] for k in ("path", "bytes", "sha256", "repository", "revision", "url"))
                else:
                    assert checked["source"] == "verification/development/lcm-preparation-trained.json" and not c.get("url")
                    assert (c["bytes"], c["sha256"]) == (trained["output"]["bytes"], trained["output"]["sha256"])
                    preparation = next(p for p in json.loads((ROOT / "catalogue/asset-preparations.json").read_text(encoding="utf-8"))["plans"] if p["id"] == checked["preparationId"])
                    output = next(o for stage in preparation["stages"] for o in stage["outputs"] if o["role"] == c["role"])
                    assert (c["path"], c["bytes"], c["sha256"]) == (output["file"], output["bytes"], output["sha256"])
            else: raise AssertionError("Unreviewed catalogue component evidence")
    assert ids == set(proofs), "Each shipped candidate requires individual component evidence"
    (ROOT / "app/src/main/assets/model-bundles.json").write_bytes(data)
    # Association plans are signed metadata, with identity bindings computed by
    # the production Java constructor from these exact App-delivered manifests.
    assembly_path = ROOT / "catalogue/model-assemblies.json"
    assembly_data = assembly_path.read_bytes(); assemblies = json.loads(assembly_data)
    assert assemblies["schema"] == "lma.model-assembly-catalogue/1"
    preparations = {p["id"]: p for p in json.loads((ROOT / "catalogue/asset-preparations.json").read_text(encoding="utf-8"))["plans"]}
    models = {b["id"]: b for b in catalogue["bundles"]}; assembly_ids = set()
    for plan in assemblies["plans"]:
        assert plan["schema"] == "lma.model-assembly/1" and plan["id"] not in assembly_ids
        assembly_ids.add(plan["id"]); assert plan["sourceBundleId"] in models and plan["sourceBundleId"] != plan["bundleId"]
        outputs = {o["role"]: o for stage in preparations[plan["preparationId"]]["stages"] for o in stage["outputs"]}
        target = {c["role"]: c for c in models[plan["bundleId"]]["components"]}
        assert len({r["source"] for r in plan["roles"]}) == len({r["target"] for r in plan["roles"]}) == len(plan["roles"])
        for role in plan["roles"]:
            assert all(outputs[role["source"]][k] == target[role["target"]][k] for k in ("bytes", "sha256"))
    (ROOT / "app/src/main/assets/model-assemblies.json").write_bytes(assembly_data)
    print(json.dumps({"bundles": len(ids), "model_assets_downloaded": False, "catalogue_sha256": hashlib.sha256(data).hexdigest()}))


if __name__ == "__main__":
    main()
