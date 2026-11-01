"""Validate versioned protocol files and illustrative examples; never exercise runtime endpoints or models."""
import argparse
import copy
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "docs/proposals"
META_SHA256 = "da01ba28852cac0de53893797cb8d1942bc3b05084f526dcc216717dec314ed0"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meta-schema", type=Path, required=True, help="Saved official OpenAPI 3.1 schema, 2022-10-07 revision")
    parser.add_argument("--upstream-cache", type=Path, help="Optional saved pinned public Sub2API files and source-records.json")
    parser.add_argument("--export", action="store_true", help="Write the public schema-only validation record")
    args = parser.parse_args()
    assert sha256(args.meta_schema) == META_SHA256, "Unexpected official meta-schema identity"
    spec = read_json(PROPOSALS / "sub2api-openai.openapi.json")
    profile = read_json(PROPOSALS / "sub2api-openai-profile.json")
    example = read_json(PROPOSALS / "sub2api-local-models.example.json")
    Draft202012Validator(read_json(args.meta_schema), format_checker=FormatChecker()).validate(spec)
    schemas = spec["components"]["schemas"]
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)

    refs = []

    def visit(value):
        if isinstance(value, dict):
            if "$ref" in value:
                pointer = value["$ref"]
                assert pointer.startswith("#/"), "Unexpected external protocol reference"
                target = spec
                for part in pointer[2:].split("/"):
                    target = target[part.replace("~1", "/").replace("~0", "~")]
                refs.append(pointer)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(spec)
    operations = []
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method not in HTTP_METHODS:
                continue
            operations.append(operation["operationId"])
            declared = {p["name"] for p in operation.get("parameters", []) if p["in"] == "path"}
            assert declared == set(re.findall(r"\{([^}]+)\}", path)), path
            assert operation["x-lma-status"] in {"implemented-subset", "unsupported-explicit-error"}
    assert len(operations) == len(set(operations))
    assert profile["status"] == "implemented_subset_with_scoped_evidence" and profile["runtime_changed"]
    assert profile["acceptance_executed"] and spec["x-lma-status"] == "implemented-subset"
    assert not profile["live_production_sub2api_tested"]
    assert not profile["pending_implementation_ids"] and profile["completed_implementation_ids"] == profile["implementation_ids"]
    for name in ["SUB2API_OPENAI.md", "SUB2API_OPENAI.en.md"]:
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        for prefix, key in [("R", "requirement_ids"), ("D", "implementation_ids"), ("A", "acceptance_ids")]:
            ids = re.findall(r"^\| (" + prefix + r"\d{2}) \|", text, re.M)
            assert len(ids) == len(set(ids)) and set(ids) == set(profile[key]), (name, prefix)

    cases = []

    def check(label, schema, value, valid=True):
        wrapper = {"components": spec["components"], "$ref": "#/components/schemas/" + schema}
        errors = list(Draft202012Validator(wrapper, format_checker=FormatChecker()).iter_errors(value))
        assert bool(errors) != valid, (label, [error.message for error in errors[:3]])
        cases.append({"case": label, "expected": "valid" if valid else "invalid", "passed": True})

    check("catalogue.six_unloaded_peers", "ModelList", example)
    assert len(example["data"]) == 6
    assert {m["x_lma"]["operations"][0] for m in example["data"]} == set(profile["operations"])
    assert len({m["id"] for m in example["data"]}) == 6
    for model in example["data"]:
        check("catalogue." + model["x_lma"]["operations"][0], "Model", model)
        assert not any(model["x_lma"]["evidence"][key] for key in ["program_verified", "phone_real_output_verified", "quality_accepted", "background_endurance_verified"])
        Draft202012Validator.check_schema(model["x_lma"]["parameter_schema"])
        Draft202012Validator(model["x_lma"]["parameter_schema"]).validate(model["x_lma"]["saved_parameters"])
        for schema in model["x_lma"]["input_schemas"].values():
            Draft202012Validator.check_schema(schema)
    original = example["data"][1]
    for state, loaded, available in [("loaded", True, True), ("busy", True, True), ("busy", True, False), ("resource_limited", False, False), ("offline", False, False), ("stale", False, False)]:
        model = copy.deepcopy(original)
        model["x_lma"]["ready"].update(status=state, loaded=loaded, available=available)
        check("catalogue.state_" + state + "_" + str(available).lower(), "Model", model)
    for key in ["assets_complete", "runner_available", "configuration_valid"]:
        model = copy.deepcopy(original)
        model["x_lma"]["ready"][key] = False
        check("catalogue.exclude_" + key, "Model", model, False)
    model = copy.deepcopy(original)
    model["x_lma"]["publication"]["eligible"] = False
    check("catalogue.exclude_ineligible", "Model", model, False)
    model = copy.deepcopy(original)
    del model["x_lma"]["publication"]["bundle_id"]
    check("catalogue.exclude_unregistered", "Model", model, False)
    for status in ["offline", "stale", "resource_limited"]:
        model = copy.deepcopy(original)
        model["x_lma"]["ready"]["status"] = status
        check("catalogue.reject_false_availability_" + status, "Model", model, False)
    for status, loaded in [("unloaded", True), ("loaded", False)]:
        model = copy.deepcopy(original)
        model["x_lma"]["ready"].update(status=status, loaded=loaded)
        check("catalogue.reject_loaded_contradiction_" + status, "Model", model, False)
    model = copy.deepcopy(original)
    model["x_lma"]["operations"] = ["lora.generate"]
    check("catalogue.reject_standalone_lora_generation", "Model", model, False)
    catalogue = copy.deepcopy(example)
    del catalogue["x_lma"]
    check("catalogue.require_snapshot_identity", "ModelList", catalogue, False)
    capabilities = {"schema": "lma.capabilities/1", "instance_id": example["x_lma"]["instance_id"], "catalogue": example["x_lma"], "models": example["data"], "limits": {}, "profiles": ["openai_subset", "lma_extension"], "execution": "same_android_phone"}
    check("capabilities.six_models_same_snapshot", "Capabilities", capabilities)
    for path in ["/v1/models", "/v1/models/{model}", "/v1/lma/capabilities"]:
        operation = spec["paths"][path]["get"]
        assert any(p["name"] == "If-None-Match" and p["in"] == "header" for p in operation["parameters"])
        assert "content" not in operation["responses"]["304"]
        assert {"ETag", "Cache-Control"} <= operation["responses"]["304"]["headers"].keys()

    image = {"model": "lma-example-image", "prompt": "A ceramic cup", "n": 1, "response_format": "b64_json", "output_format": "png", "stream": False}
    check("image.request", "ImageRequest", image)
    for field, value in [("n", 2), ("stream", True), ("output_format", "jpeg")]:
        check("image.unsupported_" + field, "ImageRequest", dict(image, **{field: value}), False)
    check("image.response", "ImageResponse", {"created": 1793577600, "data": [{"b64_json": "c2NoZW1hLWV4YW1wbGU="}]})
    check("image.no_job_as_response", "ImageResponse", {"id": "job-example", "state": "queued"}, False)
    check("speech.wav_shape", "SpeechRequest", {"model": "lma-example-speech", "input": "Hello", "voice": "default", "response_format": "wav"})
    check("speech.default_mp3_shape_not_runtime_support", "SpeechRequest", {"model": "lma-example-speech", "input": "Hello", "voice": "default"})
    check("speech.missing_input", "SpeechRequest", {"model": "lma-example-speech", "voice": "default"}, False)
    for operation in profile["operations"]:
        job = {"model": "lma-example-" + operation.split(".")[0], "type": operation, "input": {"prompt": "Program contract"}}
        check("job." + operation, "JobRequest", job)
    check("job.image_only_mesh_no_dummy_prompt", "JobRequest", {"model": "lma-example-mesh", "type": "mesh.generate", "input": {"artifacts": [{"role": "image", "artifactId": "input-example"}]}})
    check("job.reject_internal_bundle_id", "JobRequest", {"model": "lma-example-mesh", "bundleId": "private-internal-id", "type": "mesh.generate", "input": {}}, False)
    check("job.reject_unknown_operation", "JobRequest", {"model": "lma-example-mesh", "type": "remote.generate", "input": {}}, False)
    check("upload.with_destination", "UploadCreate", {"model": "lma-example-mesh", "name": "input.png", "bytes": 10, "sha256": "0" * 64})
    check("upload.require_destination", "UploadCreate", {"name": "input.png", "bytes": 10, "sha256": "0" * 64}, False)
    check("upload.limit", "UploadCreate", {"model": "lma-example-mesh", "name": "input.png", "bytes": 536870913, "sha256": "0" * 64}, False)
    error = {"message": "Unavailable", "type": "invalid_request_error", "param": "model", "code": "lma_model_unavailable"}
    check("error.envelope", "Error", {"error": error})
    check("error.detail", "ErrorDetail", error)
    check("error.no_bare_detail", "Error", error, False)
    for state in ["submitting", "acceptance_unknown", "cancel_pending", "running", "failed"]:
        check("job.state_" + state, "Job", {"id": "example-job", "object": "lma.job", "model": "lma-example-video", "type": "video.generate", "state": state, "stage": "", "progress": None, "outputs": []})

    for source in profile["lma_source_identity"]:
        data = (ROOT / source["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
    upstream_verified = 0
    if args.upstream_cache:
        records = read_json(args.upstream_cache / "source-records.json")
        assert len(records) == 15
        for source in records:
            data = (args.upstream_cache / source["path"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == source["sha256"]
            blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            assert hashlib.sha1(blob).hexdigest() == source["blob_sha"]
            upstream_verified += 1
    inputs = ["docs/proposals/sub2api-openai.openapi.json", "docs/proposals/sub2api-openai-profile.json", "docs/proposals/sub2api-local-models.example.json", "docs/SUB2API_OPENAI.md", "docs/SUB2API_OPENAI.en.md", "tools/validate_sub2api_design.py"]
    report = {
        "scope": "schema_and_traceability_only_not_endpoint_or_model_acceptance",
        "official_openapi_3_1_schema_valid": True, "component_schemas_valid": len(schemas),
        "resolved_internal_refs": len(refs), "unique_operations": len(operations), "paths": len(spec["paths"]),
        "positive_negative_schema_examples": len(cases), "catalogue_example_models": 6,
        "upstream_blobs_verified": upstream_verified, "bilingual_ids_aligned": True,
        "native_sources_match_declared_identity": True, "new_runtime_endpoints_tested": False,
        "checked_at": "2026-11-02", "validator": "jsonschema " + version("jsonschema"),
        "official_meta_schema": {"url": "https://spec.openapis.org/oas/3.1/schema/2022-10-07", "sha256": META_SHA256},
        "inputs": [{"path": path, "sha256": sha256(ROOT / path)} for path in inputs], "cases": cases,
    }
    if args.export:
        (PROPOSALS / "sub2api-openai-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"cases", "inputs", "official_meta_schema"}}, indent=2))


if __name__ == "__main__":
    main()
