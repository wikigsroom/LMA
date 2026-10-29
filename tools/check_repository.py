"""Check public files, local documentation links, evidence and prepared release bytes."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
from urllib.parse import unquote, urlsplit
import zipfile
from evidence import version, current
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", action="store_true", help="Verify immutable source ZIP against its published tag after later documentation/tool updates")
    parser.add_argument("--development", action="store_true", help="Check a development checkpoint; never claims Release or phone readiness")
    args = parser.parse_args()
    run = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True)
    names = sorted(set(run.stdout.decode("utf-8").strip("\0").split("\0")))
    assert names and all(names)
    protected_parts = {"signing", "build", "dist", ".git", "node_modules", "__pycache__", ".gradle", ".idea", ".vscode"}
    protected_suffixes = {".p12", ".jks", ".keystore", ".pem", ".key", ".gguf", ".part", ".idsig", ".apk", ".pyc"}
    secrets = [re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
               re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
               re.compile(rb"\blma_[a-f0-9]{48}\b")]
    for name in names:
        p = Path(name)
        assert not set(p.parts) & protected_parts, "Private/generated path staged: " + name
        assert p.suffix not in protected_suffixes and not p.name.startswith(".env"), "Private artifact: " + name
        assert p.parts[:2] != ("third_party", "cache") and "jniLibs" not in p.parts, "Re-fetchable native bytes staged: " + name
        if name == "app/src/main/assets/license.js":
            # This existing protected asset is authorized for hashing only.
            assert (ROOT / p).stat().st_size < 25 * 1024 * 1024
            with (ROOT / p).open("rb") as stream: hashlib.file_digest(stream, "sha256")
            continue
        data = (ROOT / p).read_bytes()
        assert len(data) < 25 * 1024 * 1024, "Oversized repository file: " + name
        assert not any(pattern.search(data) for pattern in secrets), "Possible secret in public file: " + name
    documents = [ROOT / name for name in names if name.endswith(".md") and (
        len(Path(name).parts) == 1 or name.startswith(("docs/", "verification/", ".github/")) or name == "third_party/README.md")]
    links = 0
    for document in documents:
        text = document.read_text(encoding="utf-8")
        targets = re.findall(r"!?\[[^\]]*\]\(([^)\n]+)\)", text)
        targets += re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', text)
        for raw in targets:
            target = raw.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("#"):
                continue
            target = unquote(parsed.path)
            if not target:
                continue
            resolved = (document.parent / target).resolve()
            assert resolved.is_relative_to(ROOT.resolve()) and resolved.exists(), "Broken local link: " + str(document.relative_to(ROOT)) + " -> " + target
            links += 1
    release = version()
    if args.development and release == "0.3.0-dev.30":
        assert not args.published
        from checkpoint_evidence import check
        scoped = check()
        result = dict(scoped, development_only=True, public_files=len(names), documents=len(documents), local_links=links)
        (ROOT / "build/repository-check-development.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result)); return
    if args.development:
        assert not args.published and "-dev" in release
        directory = ROOT / "verification/development"
        status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
        assert status["version"] == release and not status["release_ready"] and not status["all_selected_models_supported"]
        assert status["physical_device_tests"] == 0 and not status["model_inference_tested"]
        assert status["trained_soulx_components_tested"] == 5 and not status["soulx_complete_text_to_speech_tested"]
        assert status["host_model_inference_tested"] and status["soulx_complete_host_text_to_speech_tested"]
        assert not status["soulx_complete_android_text_to_speech_tested"] and not status["soulx_speech_quality_tested"]
        records = {name: json.loads((directory / name).read_text(encoding="utf-8")) for name in status["sources"]}
        for record in records.values(): current(record["input_fingerprint"])
        ltx = records["ltx098-transformer.json"]
        ltx_arm = records["ltx098-transformer-arm64.json"]
        assert ltx["passed"] >= 675 and ltx["actual_host_children"] >= 80 and ltx["guard_assertions"] >= 31
        assert ltx["actual_publisher_forward"] and ltx["backends"] == ["cpu", "vulkan"] and len(ltx["precision_metrics"]) == 48 and ltx["full_layer_depth"] == 28
        assert ltx["oracle"]["full_tensors"] == 715 and ltx["oracle"]["full_parameters"] == 1923385472 and not ltx["oracle"]["full_weights_loaded"]
        assert ltx["vulkan_device_identity"] and all("fp16: 0" in item and "matrix cores: none" in item for item in ltx["vulkan_device_identity"])
        for metric in ltx["precision_metrics"]:
            assert metric["precision"] in ["f32", "f16"] and metric["backend"] in ["cpu", "vulkan"]
            maximum, rmse = (1e-4, 3e-5) if metric["precision"] == "f32" else (.005, .001)
            assert metric["max_abs_gate"] == maximum and metric["rmse_gate"] == rmse and metric["max_abs"] <= maximum and metric["rmse"] <= rmse
        assert ltx_arm["android_arm64_compiled"] and ltx_arm["backend"] == "vulkan" and ltx_arm["min_sdk"] == 28
        assert ltx_arm["elf"]["machine"] == "aarch64" and ltx_arm["elf"]["16k_elf_aligned"] and ltx_arm["elf"]["android_api_notes"] == [28]
        assert ltx_arm["elf"]["interpreter"] == "/system/bin/linker64" and set(ltx_arm["elf"]["needed"]) == {"libc.so", "libm.so", "libdl.so", "libvulkan.so"}
        for item in [ltx, ltx_arm]:
            assert not any(item[key] for key in ["model_inference", "engine_registered", "packaged_in_apk", "physical_android", "complete_video_pipeline"])
        assert not ltx["trained_weights_loaded"] and not ltx["video_outputs"]
        assert status["ltx098_native_dit_host_parity_tested"] and status["ltx098_android_vulkan_compiled"]
        assert not status["ltx098_trained_video_tested"] and not status["ltx098_app_engine_registered"]
        sampling = records["ltx098-sampling.json"]
        assert sampling["passed"] >= 692 and sampling["guard_assertions"] >= 33 and sampling["actual_host_children"] >= 58
        assert sampling["actual_publisher_forward"] and sampling["math_cases"] == 22 and sampling["neural_trajectories"] == 10 and sampling["neural_steps"] == 80
        assert sampling["trained_weights_loaded"] and len(sampling["precision_metrics"]) == 111 and sampling["vulkan_device_identity"]
        assert all("fp16: 0" in item and "matrix cores: none" in item for item in sampling["vulkan_device_identity"])
        for metric in sampling["precision_metrics"]:
            name = metric["name"]
            gates = (2e-3, 5e-4) if name == "trained-forward" else (1e-2, 2e-3) if name.startswith("trained-step-") else (2e-3, 5e-4) if name.startswith("cpu-") and ("f16" in name or "converted" in name) else (2e-5, 4e-6) if name.startswith(("cpu-", "vulkan-")) else (2e-6, 5e-7)
            assert (metric["max_gate"], metric["rmse_gate"]) == gates and metric["max_abs"] <= gates[0] and metric["rmse"] <= gates[1]
        trained_ltx = sampling["trained"]
        assert trained_ltx["trained_weights_loaded"] and trained_ltx["synthetic_text_embeddings"] and trained_ltx["backend"] == "vulkan"
        assert trained_ltx["oracle"]["tensors"] == 715 and trained_ltx["oracle"]["parameters"] == 1923385472 and trained_ltx["oracle"]["layers"] == 28
        assert len(trained_ltx["oracle"]["steps"]) == 8 and trained_ltx["oracle"]["parameter_paging"]["max_scheduled_parameter_bytes"] == 268623872
        assert trained_ltx["sampling"]["steps"] == 8 and trained_ltx["sampling"]["layers"] == 28 and trained_ltx["sampling"]["parameters"] == 1923385472
        trained_asset = json.loads((ROOT / "third_party/ltx098-trained-assets.json").read_text(encoding="utf-8"))["models"][0]
        assert trained_ltx["conversion"]["source_sha256"] == trained_ltx["oracle"]["source_sha256"] == trained_asset["sha256"]
        assert trained_ltx["conversion"]["source_bytes"] == trained_asset["bytes"] == 6340744492 and not trained_ltx["conversion"]["synthetic_parameters"]
        current(trained_ltx["conversion"]["input_fingerprint"]); current(trained_ltx["oracle"]["input_fingerprint"])
        for oracle in [sampling["oracle"], trained_ltx["oracle"]]:
            current(oracle["input_fingerprint"])
            assert oracle["artifacts"]
            for name, artifact in oracle["artifacts"].items():
                assert Path(name).name == name and artifact["bytes"] > 0 and re.fullmatch(r"[a-f0-9]{64}", artifact["sha256"])
        for native_run in sampling["native_runs"]:
            if native_run["name"].startswith("trained-"):
                memory = native_run["host_process_memory"]
                assert memory["observed"] and memory["samples"] > 0 and memory["observed_peak_working_set_bytes"] > 0 and not memory["gpu_memory_measured"]
        for key in ["model_inference", "complete_video_pipeline", "video_outputs", "t5_executed", "vae_executed", "engine_registered", "packaged_in_apk", "physical_android"]: assert not sampling[key]
        assert ltx_arm["sampler_binary_bytes"] > 0 and len(ltx_arm["sampler_binary_sha256"]) == 64
        assert ltx_arm["sampler_elf"]["machine"] == "aarch64" and ltx_arm["sampler_elf"]["16k_elf_aligned"] and ltx_arm["sampler_elf"]["android_api_notes"] == [28]
        assert ltx_arm["sampler_elf"]["needed"] == ltx_arm["elf"]["needed"] and ltx_arm["sampler_elf"]["interpreter"] == "/system/bin/linker64"
        assert status["ltx098_native_sampling_host_tested"] and status["ltx098_trained_dit_latent_host_tested"]
        assert status["ltx098_t5_executed"] and status["ltx098_t5_host_tested"] and status["ltx098_t5_android_compiled"]
        assert not status["ltx098_t5_android_tested"] and status["ltx098_vae_executed"]
        assert status["ltx098_vae_host_tested"] and status["ltx098_vae_android_compiled"] and not status["ltx098_vae_android_tested"]
        vae = records["ltx098-vae.json"]
        from check_ltx098_pipeline_evidence import check as check_ltx_pipeline
        check_ltx_pipeline(records, status, ROOT, digest)
        from check_ltx098_text_diagnosis_evidence import check as check_ltx_text_diagnosis
        check_ltx_text_diagnosis(records, status, ROOT, digest)
        from check_ltx098_text_precision_evidence import check as check_ltx_text_precision
        check_ltx_text_precision(records, status, digest, ROOT)
        from check_ltx098_staging_evidence import check as check_ltx_staging
        check_ltx_staging(records, status, digest, ROOT)
        from check_ltx098_modulation_evidence import check as check_ltx_modulation
        check_ltx_modulation(records, status, digest, ROOT)
        from check_sd15_trained_evidence import check as check_sd15_trained
        check_sd15_trained(records, status, digest, ROOT)
        from check_moss_nano_trained_evidence import check as check_nano_trained
        check_nano_trained(records, status, digest, ROOT)
        from check_tts_trained_evidence import check as check_tts_trained
        check_tts_trained(records, status, digest, ROOT)
        from check_qwen_tts_trained_evidence import check as check_qwen_trained
        check_qwen_trained(records, status, ROOT)
        from check_sd_variants_trained_evidence import check as check_sd_variants_trained
        check_sd_variants_trained(records, status, ROOT)
        from check_sd_distilled_evidence import check as check_sd_distilled
        check_sd_distilled(records, status, ROOT)
        from check_lcm_preparation_evidence import check as check_lcm_preparation
        check_lcm_preparation(records, status, ROOT)
        from check_lcm_preparation_media import check as check_lcm_preparation_media
        check_lcm_preparation_media(records, ROOT)
        from check_ltx098_prepare_evidence import check as check_ltx_prepare
        check_ltx_prepare(records, status, digest, ROOT)
        from check_ltx098_vae_prepare_evidence import check as check_ltx_vae_prepare
        check_ltx_vae_prepare(records, status, digest, ROOT)
        from check_preparation_evidence import check as check_preparations
        check_preparations(records, status, digest, ROOT)
        from check_assembly_evidence import check as check_assemblies
        check_assemblies(records, status, digest, ROOT)
        vae_lock = json.loads((ROOT / "third_party/ltx098-vae-source-lock.json").read_text(encoding="utf-8"))
        assert vae["checks"] >= 355 and vae["native_children"] >= 36 and len(vae["metrics"]) == 40 and len(vae["guards"]) >= 31
        assert vae["trained_decoder_tensors"] == 132 and vae["trained_decoder_parameters"] == 552814641
        assert vae["trained_checkpoint_loaded"] and vae["full_trained_decoder"] and vae["original_publisher_decoder_forward"]
        assert vae["gates"] == vae_lock["gates"] and len(vae["assets"]) == 18 and len(vae["oracle_files"]) == 44
        assert vae["host_model_inference_tested"] and not any(vae[k] for k in ["complete_video_pipeline", "t5_executed", "dit_executed", "video_quality_tested", "engine_registered", "packaged_in_apk", "physical_android"])
        for metric in vae["metrics"]:
            assert metric["max_absolute_error"] <= vae_lock["gates"]["max_absolute_error"]
            assert metric["relative_rmse"] <= vae_lock["gates"]["max_relative_rmse"] and metric["cosine"] >= vae_lock["gates"]["min_cosine"]
        assert all(run["session_loads"] == run["session_unloads"] and run["max_live_sessions"] <= 1 for run in vae["runs"])
        assert vae["executable_sha256"] == records["ltx098-vae-host.json"]["executable_sha256"]
        assert all(run["runtime_version"] == vae_lock["host_runtime"]["version"] and run["graph_runs"] == 9 for run in vae["runs"] if run["ok"])
        assert {run["name"]: run["output_shape"] for run in vae["runs"] if run["name"].startswith("case-")} == {
            "case-0": [1, 3, 17, 64, 64], "case-1": [1, 3, 1, 32, 32], "case-2": [1, 3, 17, 32, 64], "case-3": [1, 3, 9, 64, 32]}
        assert any(run.get("terminated_runs", 0) > 0 for run in vae["runs"])
        assert all(run["resources"]["observed"] and run["resources"]["samples"] > 0 for run in vae["runs"] if run["name"] in ["case-0", "case-1", "case-2", "case-3"])
        vae_arm = records["ltx098-vae-arm64.json"]
        assert vae_arm["android_arm64_compiled"] and vae_arm["android_platform"] == 28 and vae_arm["runtime"] == vae_lock["android_runtime"]
        assert vae_arm["elf"]["machine"] == "aarch64" and vae_arm["elf"]["16k_elf_aligned"] and vae_arm["elf"]["android_api_notes"] == [28]
        assert set(vae_arm["elf"]["needed"]) == {"libonnxruntime.so", "libm.so", "libdl.so", "libc.so"}
        assert not vae_arm["physical_android"] and not vae_arm["packaged_in_apk"] and not vae_arm["engine_registered"]
        text = records["ltx098-text.json"]
        text_lock = json.loads((ROOT / "third_party/ltx098-text-source-lock.json").read_text(encoding="utf-8"))
        assert text["checks"] >= 491 and text["actual_native_children"] >= 76 and text["negative_guards"] >= 39
        assert text["tokenization_cases"] == 27 and text["untrained_cases"] == 8 and text["padding_comparisons"] == 6
        assert text["host_model_inference_tested"] and len(text["metrics"]) == 12 and text["numerical_gates"] == text_lock["numerical_gates"]
        for metric in text["metrics"]:
            prefix = "trained" if metric["trained"] else "untrained"
            assert metric["max_abs"] <= text_lock["numerical_gates"][prefix + "_max_abs"] and metric["rmse"] <= text_lock["numerical_gates"][prefix + "_rmse"]
            if metric["trained"]:
                assert metric["relative_rmse"] <= text_lock["numerical_gates"]["trained_relative_rmse"] and metric["min_token_cosine"] >= text_lock["numerical_gates"]["trained_min_token_cosine"]
        assert text["trained"]["model"] == text_lock["model"] and text["trained"]["evaluated_tensors"] == 219
        assert text["trained"]["tensor_parameters"] == 4762310656
        buffers = text["trained"]["native_buffers"]
        assert buffers["mapped_file_bytes"] == text_lock["model"]["bytes"] and buffers["tensor_bytes"] == 3385823232 and 0 < buffers["peak_compute_bytes"] < 1024**3
        assert text["trained"]["native_inputs"] == 4 and text["trained"]["distinct_prompts"] == 3 and text["trained"]["actual_neural_cancellation"]
        assert not text["trained"]["original_unquantized_weights_compared"] and not text["trained"]["prompt_quality_tested"] and not text["trained"]["video_quality_tested"]
        identity = text["vocabulary_identity"]
        assert identity["learned_tokens_compared"] == identity["learned_scores_compared"] == 32000 and identity["sentinel_definitions_from_external_config"] == 100
        assert identity["normalized_charsmap_bytes"] == 237539 and identity["gguf_sentinel_names_missing"]
        memory = text["trained"]["host_process_memory"]
        assert memory["observed"] and memory["samples"] > 0 and memory["observed_peak_working_set_bytes"] > 0 and not memory["gpu_memory_measured"]
        for key in ["android_model_inference_tested", "engine_registered", "packaged_in_apk", "complete_video_tested", "physical_android", "remote_inference", "virtualization_used"]: assert not text[key]
        oracle = text["oracle"]; current(oracle["input_fingerprint"])
        assert len(oracle["artifacts"]) == text["oracle_artifact_files"] == 49
        assert text["observed_stage_counts"]["t5_compute"] >= 15 and text["observed_stage_counts"]["t5_encode_done"] >= 15
        for name, artifact in oracle["artifacts"].items():
            assert Path(name).name == name and artifact["bytes"] > 0 and re.fullmatch(r"[a-f0-9]{64}", artifact["sha256"])
        text_arm = records["ltx098-text-arm64.json"]
        assert text_arm["android_arm64_compiled"] and text_arm["android_platform"] == 28 and text_arm["runtime_files"] == text_lock["android_runtime_files"]
        assert text_arm["elf"]["machine"] == "aarch64" and text_arm["elf"]["16k_elf_aligned"] and text_arm["elf"]["android_api_notes"] == [28]
        assert not text_arm["network_process_imports"] and not text_arm["physical_android"] and not text_arm["packaged_in_apk"] and not text_arm["engine_registered"]
        soulx = records["soulx-dsp.json"]
        assert soulx["passed"] >= 155 and soulx["actual_host_children"] >= 49 and soulx["guard_assertions"] >= 31
        assert soulx["actual_upstream_function_bodies"] and soulx["native_library_under_test"] and not soulx["apk_runtime_used"]
        assert soulx["trained_checkpoints_loaded"] == 0 and not soulx["generated_model_audio"] and not soulx["model_inference"] and not soulx["physical_android"] and not soulx["engine_registered"]
        arm64 = records["soulx-dsp-arm64.json"]
        assert arm64["android_arm64_compiled"] and arm64["android_platform"] == 28 and arm64["objects"] == 3
        assert not arm64["engine_registered"] and not arm64["packaged_in_apk"] and not arm64["model_inference"] and not arm64["physical_android"]
        acoustic = records["soulx-acoustic.json"]
        assert acoustic["passed"] >= 244 and acoustic["actual_host_children"] == 12 and acoustic["successful_syntheses"] == 3
        assert acoustic["actual_ort_graph_runs"] >= 57 and acoustic["actual_ort_terminations"] == 1 and acoustic["max_live_sessions"] == 1
        assert acoustic["full_flow_parameters"] == 112549360 and acoustic["full_hift_parameters"] == 20821295 and not acoustic["reduced_network"]
        assert acoustic["synthetic_parameters"] and acoustic["production_converter_executed"] and acoustic["actual_upstream_forward_references"]
        assert len(acoustic["metrics"]) == 63 and all(m["maximum_absolute_error"] <= m["maximum_allowed"] for m in acoustic["metrics"])
        assert acoustic["trained_checkpoints_loaded"] == 0 and not acoustic["full_soulx_inference"] and not acoustic["model_audio_quality_tested"]
        assert not acoustic["physical_android"] and not acoustic["apk_runtime_used"] and not acoustic["engine_registered"]
        acoustic_arm = records["soulx-acoustic-arm64.json"]
        assert acoustic_arm["android_arm64_compiled"] and acoustic_arm["android_platform"] == 28 and acoustic_arm["c_api_minimum"] == 17
        assert acoustic_arm["elf"]["16k_elf_aligned"] and "libonnxruntime.so" in acoustic_arm["elf"]["needed"]
        assert acoustic_arm["runtime_version"] == "1.28.2" and not acoustic_arm["engine_registered"] and not acoustic_arm["packaged_in_apk"]
        assert not acoustic_arm["model_inference"] and not acoustic_arm["physical_android"] and not acoustic_arm["virtualization_used"]
        reference = records["soulx-reference.json"]
        assert reference["passed"] >= 145 and reference["actual_host_children"] == 15 and reference["successful_references"] == 4
        assert reference["actual_ort_graph_runs"] == 10 and reference["actual_ort_terminations"] == 2 and reference["max_live_sessions"] == 1
        assert reference["trained_reference_components_loaded"] == 2 and reference["complete_graph_tensor_identity_verified"]
        assert reference["original_publisher_graphs_used_for_references"] and reference["upstream_audio_function_bodies"] and reference["synthetic_pcm"]
        assert reference["reference_samples"] == [24000, 29537, 360000] and len(reference["metrics"]) == 20
        assert all(m["maximum_absolute_error"] <= m["maximum_allowed"] and m["rmse"] <= m["rmse_allowed"] for m in reference["metrics"])
        assert len(reference["layouts"]) == 2 and len(reference["assets"]) == 4
        original_hashes = {m["sha256"] for m in reference["publisher_models"]}
        assert {m["graph_tensor_identity_sha256"] for m in reference["layouts"]} == original_hashes
        assert not any(reference[k] for k in ["full_soulx_inference", "language_backbone_executed", "speech_generated", "model_audio_quality_tested", "physical_android", "apk_runtime_used", "engine_registered"])
        reference_arm = records["soulx-reference-arm64.json"]
        assert reference_arm["android_arm64_compiled"] and reference_arm["android_platform"] == 28 and reference_arm["c_api_minimum"] == 17
        assert reference_arm["elf"]["16k_elf_aligned"] and "libonnxruntime.so" in reference_arm["elf"]["needed"] and reference_arm["runtime_version"] == "1.28.2"
        assert not any(reference_arm[k] for k in ["engine_registered", "packaged_in_apk", "model_inference", "physical_android", "virtualization_used"])
        trained = records["soulx-trained.json"]
        current(trained["reference_evidence_fingerprint"])
        assert trained["reference_evidence_fingerprint"] == reference["input_fingerprint"]
        assert trained["passed"] >= 253 and trained["actual_host_children"] == 3 and trained["successful_acoustic_reconstructions"] == 3
        assert trained["actual_ort_graph_runs"] == 54 and trained["max_live_sessions"] == 1
        assert trained["trained_acoustic_checkpoints_loaded"] == 2 and trained["trained_reference_components_used"] == 2
        assert trained["production_converter_executed"] and trained["original_upstream_forward_executed"]
        assert trained["semantic_codes_source"] == "trained_s3_from_synthetic_target_pcm" and not trained["semantic_codes_from_language_backbone"]
        assert len(trained["metrics"]) == 63 and len(trained["isolation"]) == 12
        assert all(m["maximum_absolute_error"] <= m["maximum_allowed"] for m in trained["metrics"])
        assert all(m["maximum_absolute_error"] <= m["maximum_allowed"] and m["rmse"] <= m["rmse_allowed"] for m in trained["isolation"])
        waves = [m for m in trained["metrics"] if m["stage"] == "wave"]
        assert len(waves) == 3 and all(m["maximum_allowed"] == .001 and m["rmse_allowed"] == .0001 and m["snr_minimum_db"] == 50 and m["rmse"] <= .0001 and m["snr_db"] >= 50 for m in waves)
        assert all(m["maximum_allowed"] == .0005 for m in acoustic["metrics"] if m["stage"] == "wave")
        assert not any(trained[k] for k in ["trained_text_to_speech", "full_soulx_inference", "speech_quality_tested", "real_person_audio_used", "physical_android", "apk_runtime_used", "engine_registered"])
        language = records["soulx-language.json"]
        language_host = records["soulx-language-host.json"]
        current(language["reference_evidence_fingerprint"]); current(language["host_compile_fingerprint"])
        assert language["reference_evidence_fingerprint"] == reference["input_fingerprint"]
        assert language["host_compile_fingerprint"] == language_host["input_fingerprint"]
        assert language["native_binary_sha256"] == language_host["executable_sha256"] and language["policy_binary_sha256"] == language_host["policy_sha256"]
        assert language["passed"] >= 500 and language["actual_host_children"] >= 20 and language["actual_original_hf_oracle_children"] == 1
        assert language["actual_trained_language_generations"] == 2 and language["actual_neural_decode_calls"] > 0 and language["actual_aborted_decodes"] == 1
        assert language["full_language_layers"] == 28 and language["full_language_tensors"] == 311 and language["trained_reference_components_used"] == 2
        assert language["official_layout"] == dict(vocabulary=160156, speech_offset=153595, speech_eos=153478, audio_start=153477)
        assert language["older_community_layout"] == dict(vocabulary=159488, speech_offset=152927, speech_eos=151675, audio_start=151674)
        assert all(language[k] for k in ["official_source_hashes_verified", "original_upstream_ras_blocks_executed", "original_upstream_history_blocks_executed", "original_normalization_executed", "exact_publisher_tokenizer_ids", "original_full_hf_forward_executed"])
        hf = language["original_hf_reference"]
        assert hf["original_publisher_hf_forward"] and hf["complete_tensor_index_derived"] and hf["publisher_embedding_head_equal"]
        assert hf["full_layers"] == 28 and hf["output_logits"] == 160156 and hf["reference_dtype"] == "bfloat16" and not hf["model_inference_on_phone"]
        assert len(language["metrics"]) == 12 and all(m["maximum_absolute_error"] <= m["maximum_allowed"] == 2e-6 for m in language["metrics"])
        logits = language["logit_metrics"]
        assert logits["values"] == 160156 and logits["cosine"] >= logits["minimum_cosine"] == .99 and logits["rmse"] <= logits["maximum_rmse"] == .5
        assert logits["top20_overlap"] >= logits["minimum_top20_overlap"] == .4
        assert len(language["successful_turns"]) == 2 and all(t["semantic_codes"] > 0 and t["history_delimiter_inserted"] == (not t["eos"]) for t in language["successful_turns"])
        assert not any(language[k] for k in ["full_soulx_text_to_speech", "speech_quality_tested", "real_person_audio_used", "physical_android", "apk_runtime_used", "engine_registered"])
        language_arm = records["soulx-language-arm64.json"]
        assert language_arm["android_arm64_compiled"] and language_arm["android_platform"] == 28 and language_arm["elf"]["16k_elf_aligned"]
        assert "libllama.so" in language_arm["elf"]["needed"] and language_arm["backend"] == language_host["backend"] == "cpu"
        assert not any(language_arm[k] for k in ["network_process_imports", "engine_registered", "packaged_in_apk", "model_inference", "physical_android", "virtualization_used"])
        pipeline = records["soulx-pipeline.json"]
        assert pipeline["passed"] >= 55 and pipeline["full_trained_host_pipeline_executed"] and pipeline["same_host_sequential_children"] and pipeline["no_network_inference"]
        assert pipeline["actual_host_children"] == 5 and pipeline["actual_reference_graph_runs"] == 4 and pipeline["actual_acoustic_graph_runs"] == 36 and pipeline["actual_neural_decode_calls"] > 0
        assert pipeline["trained_reference_models"] == 2 and pipeline["trained_language_backbones"] == 1 and pipeline["trained_acoustic_checkpoints"] == 2
        assert pipeline["synthetic_reference_pcm"] and len(pipeline["fresh_texts"]) == len(pipeline["artifacts"]) == 2
        for key, record in [("soulx-reference-tests", reference), ("soulx-trained-tests", trained), ("soulx-language-tests", language)]:
            assert pipeline["source_evidence_fingerprints"][key] == record["input_fingerprint"]
        assert pipeline["native_binary_sha256"]["language"] == language["native_binary_sha256"]
        assert pipeline["converted_language_assets"] == language["converted_language_assets"]
        assert all(a["samples"] == a["semantic_codes"] * 960 and a["seconds"] == a["samples"] / 24000 and a["bytes"] == 44 + a["samples"] * 2 and a["rms"] > 0 and len(a["sha256"]) == 64 for a in pipeline["artifacts"])
        assert not any(pipeline[k] for k in ["speech_quality_tested", "complete_target_13_accepted", "real_person_audio_used", "physical_android", "apk_runtime_used", "engine_registered"])
        assert records["migration.json"]["passed"] >= 69 and records["migration.json"]["actual_host_hardlinks"] and records["migration.json"]["actual_host_child"] and not records["migration.json"]["model_inference_tested"] and not records["migration.json"]["physical_device_tested"]
        assert records["inputs.json"]["passed"] >= 64 and records["inputs.json"]["actual_socket_io"] and records["inputs.json"]["actual_private_file_io"] and records["inputs.json"]["production_wav_validation"] and not records["inputs.json"]["android_execution_tested"] and not records["inputs.json"]["model_inference_tested"]
        assert records["scheduler.json"]["passed"] >= 49 and records["scheduler.json"]["production_job_runner"] and records["scheduler.json"]["actual_host_children"] and records["scheduler.json"]["actual_loopback_http"] and not records["scheduler.json"]["physical_android"] and not records["scheduler.json"]["model_inference"]
        assert records["diffusion.json"]["passed"] >= 174 and records["diffusion.json"]["production_sd_binding"] and records["diffusion.json"]["actual_host_children"] and records["diffusion.json"]["native"]["production_cpp_policy"] and not records["diffusion.json"]["physical_android"] and not records["diffusion.json"]["model_inference"] and not records["diffusion.json"]["image_outputs"]
        assert records["build-info.json"]["input_fingerprint"] == build_inputs()
        assert records["build-info.json"]["sha256"] == records["package.json"]["sha256"]
        assert records["native-payload.json"]["passed"] >= 10 and records["native-payload.json"]["exact_shared_base_runtime_reuse"] and records["native-payload.json"]["native_files"] == 29
        assert records["foundation.json"]["passed"] >= 302 and records["foundation.json"]["model_update_assertions"] >= 62 and records["foundation.json"]["recipe_integrity_assertions"] >= 87 and records["foundation.json"]["adapter_contract_assertions"] >= 45 and records["backend.json"]["passed"] >= 85 and records["hub.json"]["passed"] >= 74
        assert records["text.json"]["passed"] >= 66 and records["text.json"]["actual_host_child_processes"] and records["text.json"]["actual_loopback_http"] and not records["text.json"]["model_inference"]
        assert records["tts.json"]["passed"] >= 62 and records["tts.json"]["actual_host_child_processes"] and not records["tts.json"]["model_inference"]
        assert records["mnn.json"]["passed"] >= 74 and records["mnn.json"]["production_mnn_binding"] and records["mnn.json"]["actual_host_children"] and not records["mnn.json"]["model_inference"] and not records["mnn.json"]["physical_android"] and not records["mnn.json"]["image_outputs"]
        assert records["qwen-tts.json"]["passed"] >= 81 and records["qwen-tts.json"]["production_qwen_binding"] and records["qwen-tts.json"]["actual_host_children"] and not records["qwen-tts.json"]["model_inference"] and not records["qwen-tts.json"]["physical_android"] and not records["qwen-tts.json"]["generated_audio_outputs"]
        assert records["moss-delay.json"]["passed"] >= 176 and records["moss-delay.json"]["production_moss_delay_binding"] and records["moss-delay.json"]["actual_host_children"] and records["moss-delay.json"]["native"]["upstream_delay_self_test"] and not records["moss-delay.json"]["physical_android"] and not records["moss-delay.json"]["model_inference"]
        assert records["openmoss.json"]["passed"] >= 514 and records["openmoss.json"]["production_openmoss_binding"] and records["openmoss.json"]["java"]["actual_host_children"] == 21 and records["openmoss.json"]["native"]["upstream_sound_primitives"] and records["openmoss.json"]["native"]["upstream_prompt_primitives"] and records["openmoss.json"]["generation_budget_in_actual_pipeline"] and not records["openmoss.json"]["physical_android"] and not records["openmoss.json"]["model_inference"]
        assert records["stable-audio.json"]["passed"] >= 144 and records["stable-audio.json"]["production_stable_audio_binding"] and records["stable-audio.json"]["actual_host_children"] == 6 and records["stable-audio.json"]["actual_litert_graph_runs"] == 6 and records["stable-audio.json"]["native"]["arm_sampler_equivalence"] and not records["stable-audio.json"]["physical_android"] and not records["stable-audio.json"]["model_inference"]
        assert records["soulx.json"]["passed"] >= 222 and records["soulx.json"]["production_soulx_binding"] and records["soulx.json"]["actual_host_children"] == 6 and not records["soulx.json"]["model_inference"] and not records["soulx.json"]["physical_android"]
        worker = records["soulx-worker-trained.json"]
        assert worker["passed"] >= 95 and worker["full_trained_production_worker_executed"] and worker["actual_host_children"] == 4
        assert worker["reference_speakers_tested"] == [2, 4] and worker["trained_model_components"] == 14 and worker["actual_forced_host_terminations"] == 2
        assert len(worker["outputs"]) == 2 and len(worker["runs"]) == 4 and len(worker["assets"]) == 14
        assert not any(worker[k] for k in ["speech_quality_tested", "physical_android", "complete_target13_accepted", "remote_inference", "model_assets_packaged_in_apk", "android_cooperative_cancellation_tested"])
        assert status["soulx_production_worker_host_tested"] and status["soulx_app_engine_registered"] and not status["soulx_complete_public_download_candidate_verified"]
        assert records["moss-rq.json"]["passed"] >= 178 and records["moss-rq.json"]["production_rq_binding"] and records["moss-rq.json"]["java"]["actual_host_children"] == 10 and records["moss-rq.json"]["actual_graph_processes"] == 2 and records["moss-rq.json"]["layout"]["metadata_only"] and not records["moss-rq.json"]["layout"]["tensor_weights_read"] and not records["moss-rq.json"]["physical_android"] and not records["moss-rq.json"]["model_inference"]
        assert records["qwen-headers.json"]["passed"] and not records["qwen-headers.json"]["tensor_weights_read"] and not records["qwen-headers.json"]["model_inference"]
        assert records["moss-nano.json"]["passed"] >= 190 and records["moss-nano.json"]["native_parser"]["native_host_execution"] and records["moss-nano.json"]["java_contracts"]["actual_host_hardlinks"] and not records["moss-nano.json"]["model_inference"]
        assert records["api.json"]["passed"] >= 67 and records["api.json"]["actual_socket_io"] and not records["api.json"]["physical_device"]
        assert records["ui.json"]["passed"] >= 112 and not records["ui.json"]["errors"] and records["lint.json"]["errors"] == 0
        media = json.loads((ROOT / "docs/media/development/manifest.json").read_text(encoding="utf-8"))
        current(media["input_fingerprint"])
        assert not media["android_device"] and not media["model_inference"] and media["browser_closed"] and not media["browser_errors"]
        for item in media["files"]:
            data = (ROOT / "docs/media/development" / item["file"]).read_bytes()
            assert len(data) == item["bytes"] and digest(data) == item["sha256"]
        result = {"development_only": True, "release_ready": False, "public_files": len(names), "documents": len(documents), "local_links": links, "version": release, "passed": True}
        (ROOT / "build/repository-check-development.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result)); return
    build = json.loads((ROOT / "dist/build-info.json").read_text(encoding="utf-8"))
    assert build["input_fingerprint"] == build_inputs() and build["version"] == release
    records = sorted((ROOT / "verification").glob("*.json"))
    assert len(records) >= 13
    for path in records:
        record = json.loads(path.read_text(encoding="utf-8"))
        if "input_fingerprint" in record:
            current(record["input_fingerprint"])
    validation = json.loads((ROOT / "verification/validation.json").read_text(encoding="utf-8"))
    assert validation["sha256"] == build["sha256"] and validation["version"] == release
    assert validation["physical_device_tests"] == 0 and not validation["phone_inference_tested"]
    media = json.loads((ROOT / "docs/media/manifest.json").read_text(encoding="utf-8"))
    current(media["input_fingerprint"])
    assert not media["android_device"] and not media["model_inference"] and not media["browser_errors"] and media["browser_closed"]
    for item in media["files"]:
        data = (ROOT / "docs/media" / item["file"]).read_bytes()
        assert len(data) == item["bytes"] and digest(data) == item["sha256"]
    source = ROOT / "dist" / ("LMA-" + release + "-source.zip")
    if args.published:
        snapshot = subprocess.run(["git", "archive", "--format=tar", "v" + release], cwd=ROOT, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(snapshot), mode="r:") as repository:
            expected_source = {member.name: repository.extractfile(member).read() for member in repository.getmembers() if member.isfile()}
    else:
        expected_source = {name: (ROOT / name).read_bytes() for name in names}
    with zipfile.ZipFile(source) as archive:
        members = archive.namelist()
        assert len(members) == len(set(members)) and archive.testzip() is None
        for name, data in expected_source.items():
            assert archive.read("LMA/" + name) == data, "Source ZIP differs from " + ("published tag: " if args.published else "current source: ") + name
        assert len([n for n in members if "/jniLibs/" in n and n.endswith(".so")]) == 14
        assert not any("/signing/" in n or "/cache/" in n or "/.git/" in n or "/node_modules/" in n for n in members)
    output = ROOT / "dist/releases" / ("v" + release)
    manifest = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == release and manifest["repository"] == "wikigsroom/LMA" and manifest["prerelease"]
    for item in manifest["assets"]:
        data = (output / item["name"]).read_bytes()
        assert len(data) == item["bytes"] and digest(data) == item["sha256"]
    for line in (output / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert digest((output / name).read_bytes()) == expected
    result = {"public_files": len(names), "documents": len(documents), "local_links": links,
              "evidence_records": len(records), "screenshots": len(media["screenshots"]),
              "release_assets": len(manifest["assets"]) + 1, "source_matches_current_public_files": not args.published,
              "source_matches_published_tag": args.published,
              "private_files_excluded": True, "version": release, "passed": True}
    (ROOT / "build/repository-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
