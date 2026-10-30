"""Export only current development checks, explicitly excluding Release/device completion."""
import json
from pathlib import Path
import shutil
from evidence import current, version
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]


def main():
    if version() == "0.3.0-dev.31":
        from checkpoint_evidence import export
        print(json.dumps(export())); return
    if "-dev" not in version():
        raise RuntimeError("Use the full release workflow for release candidates")
    sources = {
        "build-info.json": "dist/build-info.json",
        "package.json": "build/package-verification.json",
        "native-payload.json": "build/native-payload-tests/results.json",
        "assembly-core.json": "build/assembly-tests/results.json",
        "assembly-trained.json": "build/assembly-tests/trained-results.json",
        "preparation-core.json": "build/preparation-tests/results.json",
        "preparation-trained.json": "build/preparation-tests/trained-results.json",
        "foundation.json": "build/foundation-tests/results.json",
        "tts.json": "build/tts-tests/results.json",
        "tts-assets.json": "build/tts-trained/receipt.json",
        "tts-trained.json": "build/tts-trained-tests/results.json",
        "tts-app-host.json": "build/tts-app-host-tests/results.json",
        "tts-capture-audit.json": "build/tts-trained-tests/capture-audit.json",
        "text.json": "build/text-tests/results.json",
        "migration.json": "build/migration-tests/results.json",
        "scheduler.json": "build/scheduler-tests/results.json",
        "inputs.json": "build/input-tests/results.json",
        "diffusion.json": "build/diffusion-tests/results.json",
        "sd15-assets.json": "build/sd15-trained/receipt.json",
        "sd-variants-assets.json": "build/sd-variants-trained/receipt.json",
        "lcm-preparation-core.json": "build/lcm-preparation-evidence/lcm-preparation-core.json",
        "lcm-preparation-arm64.json": "build/lcm-preparation-evidence/lcm-preparation-arm64.json",
        "lcm-preparation-trained.json": "build/lcm-preparation-evidence/lcm-preparation-trained.json",
        "lcm-overlay-trained.json": "build/lcm-preparation-evidence/lcm-overlay-trained.json",
        "lcm-preparation-capture-audit.json": "build/lcm-preparation-evidence/lcm-preparation-capture-audit.json",
        "sd-distilled-assets.json": "build/sd-distilled-tests/sd-distilled-assets.json",
        "sd-distilled-native.json": "build/sd-distilled-tests/sd-distilled-native.json",
        "sd-distilled-lcm-analysis.json": "build/sd-distilled-tests/sd-distilled-lcm-analysis.json",
        "sd-turbo-app-host.json": "build/sd-distilled-tests/sd-turbo-app-host.json",
        "sd-distilled-capture-audit.json": "build/sd-distilled-tests/sd-distilled-capture-audit.json",
        "sd-variants-trained.json": "build/sd-variants-trained-tests/results.json",
        "sd-variants-lcm-effect.json": "build/sd-variants-lcm-effect-tests/results.json",
        "sd-variants-app-host.json": "build/sd-variants-app-host-tests/results.json",
        "sd-variants-capture-audit.json": "build/sd-variants-trained-tests/capture-audit.json",
        "sd15-trained.json": "build/sd15-trained-tests/results.json",
        "moss-nano.json": "build/moss-nano-tests/results.json",
        "moss-nano-assets.json": "build/moss-nano-trained/receipt.json",
        "moss-nano-trained.json": "build/moss-nano-trained-tests/results.json",
        "moss-nano-app-host.json": "build/moss-nano-app-host-tests/results.json",
        "moss-nano-capture-audit.json": "build/moss-nano-trained-tests/capture-audit.json",
        "mnn.json": "build/mnn-tests/results.json",
        "qwen-tts.json": "build/qwen-tts-tests/results.json",
        "qwen-tts-assets.json": "build/qwen-tts-trained/receipt.json",
        "qwen-tts-trained.json": "build/qwen-tts-trained-tests/results.json",
        "qwen-tts-app-host.json": "build/qwen-tts-app-host-tests/results.json",
        "qwen-tts-capture-audit.json": "build/qwen-tts-trained-tests/capture-audit.json",
        "moss-delay.json": "build/moss-delay-tests/results.json",
        "openmoss.json": "build/openmoss-tests/results.json",
        "moss-rq.json": "build/moss-rq-tests/results.json",
        "stable-audio.json": "build/stable-audio-tests/results.json",
        "soulx.json": "build/soulx-tests/results.json",
        "soulx-worker-trained.json": "build/soulx-worker-trained-tests/results.json",
        "soulx-dsp.json": "build/soulx-dsp-tests/results.json",
        "soulx-dsp-arm64.json": "build/soulx-dsp-arm64/receipt.json",
        "soulx-acoustic.json": "build/soulx-acoustic-tests/results.json",
        "soulx-acoustic-arm64.json": "build/soulx-acoustic-arm64/receipt.json",
        "soulx-reference.json": "build/soulx-reference-tests/results.json",
        "soulx-reference-arm64.json": "build/soulx-reference-arm64/receipt.json",
        "soulx-trained.json": "build/soulx-trained-tests/results.json",
        "soulx-language.json": "build/soulx-language-tests/results.json",
        "soulx-language-host.json": "build/soulx-language-host/receipt.json",
        "soulx-language-arm64.json": "build/soulx-language-arm64/receipt.json",
        "soulx-pipeline.json": "build/soulx-pipeline-tests/results.json",
        "ltx098-transformer.json": "build/ltx098-tests/results.json",
        "ltx098-transformer-arm64.json": "build/ltx098-arm64-vulkan/receipt.json",
        "ltx098-sampling.json": "build/ltx098-sampling-tests/results.json",
        "ltx098-text.json": "build/ltx098-text-tests/results.json",
        "ltx098-text-host.json": "build/ltx098-text-host/receipt.json",
        "ltx098-text-arm64.json": "build/ltx098-text-arm64/receipt.json",
        "ltx098-vae.json": "build/ltx098-vae-tests/results.json",
        "ltx098-vae-host.json": "build/ltx098-vae-host/receipt.json",
        "ltx098-vae-arm64.json": "build/ltx098-vae-arm64/receipt.json",
        "ltx098-tensors.json": "build/ltx098-tensors-tests/results.json",
        "ltx098-tensors-host.json": "build/ltx098-tensors-host/receipt.json",
        "ltx098-tensors-arm64.json": "build/ltx098-tensors-arm64/receipt.json",
        "ltx098-pipeline.json": "build/ltx098-pipeline-tests/results.json",
        "ltx098-text-diagnosis.json": "build/ltx098-text-diagnosis/current-results.json",
        "ltx098-text-operators.json": "build/ltx098-text-diagnosis/current-operators.json",
        "ltx098-text-diagnosis-review.json": "build/ltx098-text-diagnosis/review.json",
        "ltx098-text-precision-attention.json": "build/ltx098-text-precision-experiments/attention-results.json",
        "ltx098-text-precision-linear.json": "build/ltx098-text-precision-experiments/linear-results.json",
        "ltx098-precision-sampling-attention.json": "build/ltx098-text-precision-sampling/attention-results.json",
        "ltx098-precision-sampling-linear.json": "build/ltx098-text-precision-sampling/linear-results.json",
        "ltx098-staging-analysis.json": "build/ltx098-staging-analysis/results.json",
        "ltx098-accuracy-activation.json": "build/ltx098-text-accuracy-experiments/activation-results.json",
        "ltx098-accuracy-order.json": "build/ltx098-text-order-experiments/results.json",
        "ltx098-accuracy-staging.json": "build/ltx098-text-staging-experiments/baseline-results.json",
        "ltx098-accuracy-f32.json": "build/ltx098-text-f32-experiments/results.json",
        "ltx098-accuracy-trajectory-f32.json": "build/ltx098-text-accuracy-trajectories/f32-results.json",
        "ltx098-context-reference-vulkan.json": "build/ltx098-sampling-context-diagnosis/vulkan-reference-case-1-results.json",
        "ltx098-context-reference-cpu.json": "build/ltx098-sampling-context-diagnosis/cpu-reference-case-1-results.json",
        "ltx098-compute-f32-reference-cpu.json": "build/ltx098-compute-precision-tests/f32-cpu-reference-case-1-results.json",
        "ltx098-compute-f32-reference-vulkan.json": "build/ltx098-compute-precision-tests/f32-vulkan-reference-case-1-results.json",
        "ltx098-compute-f32-rms-reference-cpu.json": "build/ltx098-compute-precision-tests/f32-rms-cpu-reference-case-1-results.json",
        "ltx098-modulation-step0.json": "build/ltx098-modulation-analysis/case-1-step-0-results.json",
        "ltx098-modulation-step7.json": "build/ltx098-modulation-analysis/case-1-step-7-results.json",
        "ltx098-modulation-reference-vulkan.json": "build/ltx098-modulation-tests/publisher_modulation-vulkan-reference-case-1-results.json",
        "ltx098-modulation-f32-vulkan.json": "build/ltx098-modulation-tests/publisher_modulation-vulkan-f32-case-1-results.json",
        "ltx098-modulation-capture-audit.json": "build/ltx098-modulation-tests/capture-audit.json",
        "ltx098-prepare.json": "build/ltx098-prepare-tests/results.json",
        "ltx098-prepare-host.json": "build/ltx098-prepare-host/receipt.json",
        "ltx098-prepare-arm64.json": "build/ltx098-prepare-arm64/receipt.json",
        "ltx098-vae-templates.json": "build/ltx098-vae-template-tests/results.json",
        "ltx098-vae-prepare.json": "build/ltx098-vae-prepare-tests/results.json",
        "ltx098-vae-prepare-host.json": "build/ltx098-vae-prepare-host/receipt.json",
        "ltx098-vae-prepare-arm64.json": "build/ltx098-vae-prepare-arm64/receipt.json",
        "qwen-headers.json": "build/qwen-headers.json",
        "api.json": "build/api-tests/results.json",
        "backend.json": "build/backend-tests/results.json",
        "hub.json": "build/hub-tests/results.json",
        "hub-live.json": "build/hub-tests/live-results.json",
        "ui.json": "build/ui-qa/results.json",
        "lint.json": "build/android-lint/results.json",
    }
    trained_sd = json.loads((ROOT / sources["sd15-trained.json"]).read_text(encoding="utf-8"))
    sd_executable = (ROOT / trained_sd["compilation"]["executable"]).resolve()
    if not sd_executable.is_relative_to(ROOT / "build/sd-worker-host"):
        raise ValueError("SD host build must remain below its ignored developer directory")
    sources["sd15-host-build.json"] = (sd_executable.parent.parent / "receipt.json").relative_to(ROOT).as_posix()
    trained_nano = json.loads((ROOT / sources["moss-nano-trained.json"]).read_text(encoding="utf-8"))
    nano_executable = (ROOT / trained_nano["compilation"]["executable"]).resolve()
    if not nano_executable.is_relative_to(ROOT / "build/moss-nano-worker-host"):
        raise ValueError("Nano host build must remain below its ignored developer directory")
    sources["moss-nano-host-build.json"] = (nano_executable.parent.parent / "receipt.json").relative_to(ROOT).as_posix()
    trained_tts = json.loads((ROOT / sources["tts-trained.json"]).read_text(encoding="utf-8"))
    tts_executable = (ROOT / trained_tts["compilation"]["executable"]).resolve()
    if not tts_executable.is_relative_to(ROOT / "build/tts-worker-host"):
        raise ValueError("TTS host build must remain below its ignored developer directory")
    sources["tts-host-build.json"] = (tts_executable.parent.parent / "receipt.json").relative_to(ROOT).as_posix()
    trained_qwen = json.loads((ROOT / sources["qwen-tts-trained.json"]).read_text(encoding="utf-8"))
    qwen_executable = (ROOT / trained_qwen["compilation"]["executable"]).resolve()
    if not qwen_executable.is_relative_to(ROOT / "build/qwen-tts-worker-host"):
        raise ValueError("Qwen host build must remain below its ignored developer directory")
    sources["qwen-tts-host-build.json"] = (qwen_executable.parent.parent / "receipt.json").relative_to(ROOT).as_posix()
    out = ROOT / "verification/development"
    out.mkdir(parents=True, exist_ok=True)
    records = {}
    checked = {}
    for name, source in sources.items():
        record = json.loads((ROOT / source).read_text(encoding="utf-8"))
        recorded = record["input_fingerprint"]
        if not recorded: raise RuntimeError("Missing verification input fingerprints")
        if any(path in checked and checked[path] != identity for path, identity in recorded.items()):
            raise RuntimeError("Conflicting verification input fingerprints: " + name)
        pending = {path: identity for path, identity in recorded.items() if path not in checked}
        if pending: current(pending)
        checked.update(recorded)
        if name == "build-info.json" and record["input_fingerprint"] != build_inputs():
            raise RuntimeError("Rebuild development APK first")
        shutil.copyfile(ROOT / source, out / name)
        records[name] = record
    current(checked)  # Recheck the complete union after copying; detect concurrent source changes.
    pipeline = records["soulx-pipeline.json"]
    soulx = next(engine for engine in records["build-info.json"]["native_engines"] if engine["engine"] == "soulx_native")
    soulx_registered = soulx["file"] in records["package.json"]["native"] and soulx["required_model_components"] == 14
    status = {"version": version(), "kind": "development_checkpoint", "release_ready": False, "published": False,
              "physical_device_tests": 0, "model_inference_tested": False, "all_selected_models_supported": False,
              "trained_soulx_components_tested": pipeline["trained_reference_models"] + pipeline["trained_language_backbones"] + pipeline["trained_acoustic_checkpoints"],
              "host_model_inference_tested": pipeline["full_trained_host_pipeline_executed"],
              "soulx_complete_host_text_to_speech_tested": pipeline["full_trained_host_pipeline_executed"],
              "soulx_complete_text_to_speech_tested": False, "soulx_complete_android_text_to_speech_tested": False,
              "soulx_speech_quality_tested": False,
              "soulx_production_worker_host_tested": records["soulx-worker-trained.json"]["full_trained_production_worker_executed"],
              "soulx_app_engine_registered": soulx_registered,
              "soulx_complete_public_download_candidate_verified": False,
              "sd15_trained_production_source_host_executed": records["sd15-trained.json"]["trained_model_executed"],
              "sd15_trained_host_execution_checks_passed": records["sd15-trained.json"]["host_execution_checks_passed"],
              "sd_variants_trained_production_source_host_executed": records["sd-variants-trained.json"]["trained_model_executed"],
              "sd_variants_trained_host_execution_checks_passed": records["sd-variants-trained.json"]["host_execution_checks_passed"],
              "sd_variants_lcm_weights_effect_host_tested": records["sd-variants-lcm-effect.json"]["host_weight_effect_checks_passed"],
              "sd_variants_production_java_native_host_executed": records["sd-variants-app-host.json"]["production_java_native_host_executed"],
              "sd_turbo_production_java_native_host_executed": records["sd-turbo-app-host.json"]["production_java_native_host_executed"],
              "lcm_checkpoint_fixed_guidance_native_host_tested": records["sd-distilled-native.json"]["host_execution_checks_passed"],
              "lcm_checkpoint_complete_trained_unet_fold_host_tested": records["sd-distilled-lcm-analysis.json"]["numerical_fold_checks_passed"],
              "lcm_checkpoint_native_asset_preparation_host_tested": records["lcm-preparation-trained.json"]["passed"],
              "lcm_checkpoint_small_overlay_native_host_tested": len(records["lcm-overlay-trained.json"]["jobs"]) == 5 and all(j["passed"] for j in records["lcm-overlay-trained.json"]["jobs"]),
              "lcm_checkpoint_small_overlay_image_gate_passed": records["lcm-overlay-trained.json"]["passed"],
              "lcm_checkpoint_preparer_arm64_compiled": records["lcm-preparation-arm64.json"]["android_arm64_compiled"],
              "lcm_checkpoint_product_preparation_implemented": False,
              "sd_distilled_complete_android_image_tested": False,
              "sd_distilled_image_quality_accepted": False,
              "sd_variants_complete_android_image_tested": False,
              "sd_variants_image_quality_accepted": False,
              "sd15_complete_android_image_tested": False,
              "moss_nano_trained_production_source_host_executed": records["moss-nano-trained.json"]["trained_production_worker_executed"],
              "moss_nano_production_java_native_host_executed": records["moss-nano-app-host.json"]["production_java_native_host_executed"],
              "moss_nano_complete_android_speech_tested": False,
              "moss_nano_speech_quality_accepted": False,
              "tts_trained_production_source_host_executed": records["tts-trained.json"]["trained_production_worker_executed"],
              "tts_production_java_native_host_executed": records["tts-app-host.json"]["production_java_native_host_executed"],
              "tts_complete_android_speech_tested": False,
              "tts_speech_quality_accepted": False,
              "qwen_tts_trained_production_source_host_executed": records["qwen-tts-trained.json"]["trained_production_worker_executed"],
              "qwen_tts_production_java_native_host_executed": records["qwen-tts-app-host.json"]["production_java_native_host_executed"],
              "qwen_tts_complete_android_speech_tested": False,
              "qwen_tts_speech_quality_accepted": False,
              "ltx098_native_dit_host_parity_tested": records["ltx098-transformer.json"]["actual_publisher_forward"] and records["ltx098-transformer.json"]["backends"] == ["cpu", "vulkan"],
              "ltx098_android_vulkan_compiled": records["ltx098-transformer-arm64.json"]["android_arm64_compiled"],
              "ltx098_native_sampling_host_tested": records["ltx098-sampling.json"]["neural_trajectories"] == 10,
              "ltx098_trained_dit_latent_host_tested": records["ltx098-sampling.json"]["trained_weights_loaded"],
              "ltx098_t5_executed": records["ltx098-text.json"]["host_model_inference_tested"],
              "ltx098_t5_host_tested": records["ltx098-text.json"]["host_model_inference_tested"],
              "ltx098_t5_android_compiled": records["ltx098-text-arm64.json"]["android_arm64_compiled"],
              "ltx098_t5_android_tested": False,
              "ltx098_t5_intermediate_diagnostic_executed": records["ltx098-text-diagnosis-review.json"]["recomputed_tensor_comparisons"] == 314,
              "ltx098_t5_roundoff_repair_accepted": False,
              "ltx098_native_asset_prepare_host_tested": records["ltx098-prepare.json"]["actual_trained_conversions"] == 1,
              "ltx098_native_asset_prepare_android_compiled": records["ltx098-prepare-arm64.json"]["android_arm64_compiled"],
              "app_asset_preparation_registered": len(json.loads((ROOT / "app/src/main/assets/engine-builds.json").read_text(encoding="utf-8")).get("preparations", [])) == 2,
              "app_model_assembly_registered": True,
              "app_model_assembly_core_host_tested": records["assembly-core.json"]["passed"],
              "app_model_assembly_trained_host_tested": records["assembly-trained.json"]["actualTrainedAssociations"] == 1,
              "app_model_assembly_android_executed": False,
              "app_asset_preparation_core_host_tested": records["preparation-core.json"]["passed"],
              "app_asset_preparation_trained_host_tested": records["preparation-trained.json"]["actual_trained_preparations"] == 1,
              "app_asset_preparation_android_executed": False,
              "ltx098_vae_asset_prepare_host_tested": records["ltx098-vae-prepare.json"]["actual_trained_conversions"] == 1,
              "ltx098_vae_asset_prepare_android_compiled": records["ltx098-vae-prepare-arm64.json"]["android_arm64_compiled"],
              "ltx098_prepared_vae_decode_host_tested": records["ltx098-vae-prepare.json"]["actual_trained_decode_jobs"] == 4,
              "ltx098_t5_precision_candidates_host_executed": records["ltx098-text-precision-attention.json"]["aba_bitwise_identical"] and records["ltx098-text-precision-linear.json"]["aba_bitwise_identical"],
              "ltx098_f32_staging_analysis_host_checked": records["ltx098-staging-analysis.json"]["mean_bitwise_identical"] and records["ltx098-staging-analysis.json"]["activation_order_bitwise_identical"],
              "ltx098_staged_t5_candidates_host_executed": all(records["ltx098-accuracy-" + name + ".json"]["actual_trained_jobs"] == 3 for name in ["activation", "order", "staging", "f32"]),
              "ltx098_staged_full_chain_host_executed": len(records["ltx098-accuracy-trajectory-f32.json"]["jobs"]) == 3,
              "ltx098_staged_full_chain_numerical_passed": records["ltx098-accuracy-trajectory-f32.json"]["full_chain_original_numeric_gates_passed"],
              "ltx098_same_caption_sampler_diagnosis_host_executed": all(records["ltx098-context-reference-" + backend + ".json"]["captured_native_children"] == 1 for backend in ["cpu", "vulkan"]),
              "ltx098_cpu_f32_operands_diagnostic_host_executed": records["ltx098-compute-f32-reference-cpu.json"]["captured_native_children"] == 1,
              "ltx098_cpu_f32_operands_diagnostic_latent_matched": records["ltx098-compute-f32-reference-cpu.json"]["latent_gate_matched"],
              "ltx098_cpu_staged_rms_diagnostic_host_executed": records["ltx098-compute-f32-rms-reference-cpu.json"]["captured_native_children"] == 1,
              "ltx098_cpu_staged_rms_diagnostic_latent_matched": records["ltx098-compute-f32-rms-reference-cpu.json"]["latent_gate_matched"],
              "ltx098_modulation_host_diagnosis_executed": all(records["ltx098-modulation-step" + str(step) + ".json"]["trained_tensors"] == 715 for step in [0, 7]) and all(records["ltx098-modulation-" + context + "-vulkan.json"]["captured_native_children"] == 1 for context in ["reference", "f32"]),
              "ltx098_publisher_modulation_full_model_repair_accepted": False,
              "ltx098_vae_executed": records["ltx098-vae.json"]["host_model_inference_tested"],
              "ltx098_vae_host_tested": records["ltx098-vae.json"]["full_trained_decoder"],
              "ltx098_vae_android_compiled": records["ltx098-vae-arm64.json"]["android_arm64_compiled"],
              "ltx098_vae_android_tested": False,
              "ltx098_tensor_primitives_host_tested": records["ltx098-tensors.json"]["rng_matches_frozen_definition"],
              "ltx098_tensor_primitives_android_compiled": records["ltx098-tensors-arm64.json"]["android_arm64_compiled"],
              "ltx098_complete_prompt_to_video_host_tested": records["ltx098-pipeline.json"]["real_prompt_to_video_host_tested"],
              "ltx098_complete_prompt_to_video_host_executed": records["ltx098-pipeline.json"]["real_prompt_to_video_host_executed"],
              "ltx098_full_chain_numeric_accepted": records["ltx098-pipeline.json"]["numerical_acceptance_passed"],
              "ltx098_complete_android_video_tested": False,
              "ltx098_video_quality_accepted": False,
              "ltx098_trained_video_tested": False, "ltx098_app_engine_registered": False,
              "scope_definitions": {
                  "tts_trained_production_source_host_executed": "All three frozen English recipes, 68 actual WAV jobs covering 54 Kokoro/one Piper/one Matcha voices plus 13 controls and info, using unchanged production C++ and official sherpa 2.0.1/ORT1.28.2 Windows C API; no phone/quality/license acceptance",
                  "tts_production_java_native_host_executed": "Production BundleStore/BundleTransfers/SherpaEngine/NativeWorker with all nine trained objects/eleven references, independent settings, twelve actual native children, partial-synthesis cancellation, duration errors, cleanup and recovery; Application/AtomicFile host ports, not Android Service/SAF",
                  "tts_complete_android_speech_tested": "False: host model execution and existing Android packaging do not establish physical-phone inference, Android liblog binding, resource fit, lifecycle, API or background endurance",
                  "tts_speech_quality_accepted": "False: English test text through every voice ID and valid waveforms do not certify pronunciation, intelligibility, speaker quality, other languages or component license clearance",
                  "moss_nano_trained_production_source_host_executed": "Seven actual trained WAV jobs plus seven controls using unchanged production C++ on native Windows; all eleven user-external assets verified; HOST ORT 1.28.0/API28 differs from Android ORT 1.28.2/API28",
                  "moss_nano_production_java_native_host_executed": "Forty actual production-core/Java/NativeWorker checks: full local eleven-component import, per-model settings and clamps, three actual native children, cancellation/recovery and workspace cleanup; filesystem Application/AtomicFile ports, not Android Service or SAF",
                  "moss_nano_complete_android_speech_tested": "False: trained host WAVs, a user-importable pinned metadata manifest and the existing packaged Android worker do not establish physical-phone execution, quality, resource fit, lifecycle or background endurance",
                  "moss_nano_speech_quality_accepted": "False: waveform validity, distinct outputs and same-runtime repeatability do not establish intelligibility, pronunciation, speaker similarity or every voice/language quality",
                  "sd_variants_trained_production_source_host_executed": "Unchanged production C++ on native Windows CPU: complete trained SDXL, SD1.5/SDXL style and LCM-LoRAs, actual PNGs and sampler cancellation; not Android, quality, all target03 subtargets or full-version acceptance",
                  "sd_variants_lcm_weights_effect_host_tested": "Two native-only counterfactual zero-scale LCM controls keep every other request parameter and trained file fixed; App deliberately rejects zero-scale LCM tasks",
                  "sd_variants_production_java_native_host_executed": "Unchanged production Java HF composition of five recipes, full import/settings/adapter leases and eight actual host workers with seven full objects; Java cancellation is at generating-stage entry; a Windows metadata port omits metadata fsync and establishes no Android AtomicFile or power-loss durability; not a claimed sampler-step or Android test",
                  "sd15_trained_production_source_host_executed": "Actual CPU PNG generation by the unchanged production C++ worker/vocabulary source using user-external pinned Q4_0/CLIP files; native Windows parent-lifetime port only, not Java Service/App/Android execution",
                  "sd15_trained_host_execution_checks_passed": "Scoped A/B/A PNG determinism/distinct prompts, actual sampler cancellation/recovery, request errors and sampled host resources; never semantic quality, all image targets or device/endurance acceptance",
                  "sd15_complete_android_image_tested": "False until the selected trained assets execute and meet all output/quality/resource/background/App/API gates on the same physical Android phone",
                  "ltx098_modulation_host_diagnosis_executed": "Two unmodified original trained forward observations, 114 modulation sites, two native eight-step Vulkan candidates and an independent retained-array/trajectory audit; all candidates remain unregistered and unpackaged",
                  "ltx098_publisher_modulation_full_model_repair_accepted": "False: reference-caption and actual native-T5-caption candidate B samplers still fail unchanged maximum-error gates; no repaired full chain, App or Android acceptance",
                  "app_model_assembly_registered": "Signed plan identities and explicit model.assemble jobs associate user-prepared outputs with a separate runtime model; missing dependencies stay paused; no inference engine is enabled",
                  "app_model_assembly_core_host_tested": "47 production-core storage/request/lease/cancellation contracts; additional production queue/API checks use host Android framework ports",
                  "app_model_assembly_trained_host_tested": "Twenty actual trained files, 6,061,184,991 bytes, fully verified and hardlinked without copying; T5 dependencies remain absent and no model execution takes place",
                  "app_model_assembly_android_executed": "False until installation, on-device filesystem association, Service lifecycle and background tests pass on a physical phone",
                  "app_asset_preparation_registered": "Two signed ARM64 preparation programs and audited model-free architecture resources packaged in dev.22, separate from generation engines; no Android execution",
              "app_asset_preparation_core_host_tested": "44 production-core filesystem/lifecycle contracts and four protocol-fixture children on Windows; no Service, SAF or model inference",
                  "app_asset_preparation_trained_host_tested": "One full original checkpoint through production Java storage/jobs/native preparation, two actual native children and 20 fully verified runtime outputs; no neural inference or Android execution",
                  "app_asset_preparation_android_executed": "False until actual same-phone Service/SAF/preparation and background evidence exists",

                  "ltx098_t5_intermediate_diagnostic_executed": "314 trained host intermediate comparisons, 628 hashed raw tensors and 120 matched-native-input operator comparisons; trace retention changes diagnostic memory, not the accepted native caption or original forward",
                  "ltx098_t5_roundoff_repair_accepted": "Remains false until a repaired implementation passes unchanged complete-chain gates and required regression checks; local operator diagnostics or isolated precision candidates do not close this gate",
                  "ltx098_f32_staging_analysis_host_checked": "72 matched-input diagnostics: 2544 NumPy-simulated F32 means and 24 Torch activation-order comparisons; not native replacement or model/Android acceptance",
                  "ltx098_staged_t5_candidates_host_executed": "Four isolated trained T5 candidates, each A/B/A; explicit RMS/GeGLU operation staging, not production promotion or Android",
                  "ltx098_staged_full_chain_host_executed": "Three actual host native stage chains bound to captured trained T5 A/B/A; native DiT, seeded noise, layout, VAE, frames and host FFmpeg; unchanged original references and gates",
                  "ltx098_staged_full_chain_numerical_passed": "Scoped candidate's original-forward float/RGB gates only; production regression, semantics, phone resources/endurance, all other frozen targets and Release remain separate",
                  "ltx098_same_caption_sampler_diagnosis_host_executed": "B uses the exact original caption in separate CPU/Vulkan eight-step diagnostic runs; reference-conditioned diagnostics never count as native model acceptance",
                  "ltx098_cpu_f32_operands_diagnostic_host_executed": "An isolated native compute candidate explicitly casts matmul operands to F32 before CPU execution with frozen weights and the reference B caption; no App registration or complete-chain acceptance",
                  "ltx098_cpu_f32_operands_diagnostic_latent_matched": "Only a reference-caption sampler diagnostic's unchanged latent thresholds; never native T5 conditioning, VAE/video, quality, phone or Release acceptance",
                  "ltx098_cpu_staged_rms_diagnostic_host_executed": "Isolated F32 operand/CPU grouped-RMS candidate, exact original B caption, full eight-step trained sampler; unregistered and diagnostic only",
                  "ltx098_cpu_staged_rms_diagnostic_latent_matched": "Only the grouped-RMS reference-caption diagnostic's latent thresholds, never a repaired full model or Android acceptance",
                  "ltx098_native_asset_prepare_host_tested": "Bounded model-free native CLI converted the whole user-local old DiT checkpoint and matched independent Python GGUF bytes; conversion is not inference or production App acquisition",
                  "ltx098_native_asset_prepare_android_compiled": "ARM64 API28/16KiB portable CLI compiled; dev.22 packages it as an explicit asset-preparation program, separately from generation engines; not executed on Android",
                  "ltx098_vae_asset_prepare_host_tested": "Native streaming preparation of all 132 decoder tensors and two statistics vectors; 18 output assets match Python bytes; model-free graph audit is separate from the full-source SHA verification",
                  "ltx098_vae_asset_prepare_android_compiled": "Python/ONNX/Torch-free native asset preparation CLI, ARM64 API28/16KiB compiled and packaged separately from generation engines; not executed on Android",
                  "ltx098_prepared_vae_decode_host_tested": "Four real native ORT decoder geometries consuming newly prepared trained assets, 40 original-forward comparisons; synthetic latent inputs, not prompt-to-video quality or phone acceptance",
                  "ltx098_t5_precision_candidates_host_executed": "Two isolated trained CPU variants, each with three A/B/A jobs; attention F64 and optional dense F64 accumulation, not promoted encoder, complete-chain repair, Android or performance acceptance",
                  "model_inference_tested": "Legacy complete physical-Android acceptance flag; scoped host execution has a separate flag",
                  "soulx_complete_text_to_speech_tested": "Complete user-facing Android SoulX TTS acceptance, including App integration and quality",
                  "soulx_complete_host_text_to_speech_tested": "Sequential trained native developer-host execution with synthetic references, without quality or phone acceptance",
                  "ltx098_native_dit_host_parity_tested": "Unregistered old-0.9.8 DiT component only: untrained reduced-width 2/3/28-layer CPU/Vulkan forwards against original publisher PyTorch, with no complete trained video, App or phone acceptance",
                  "ltx098_trained_dit_latent_host_tested": "Full pinned trained 28-layer DiT, synthetic caption embeddings and eight-step latent denoising on host Vulkan against original publisher PyTorch; no T5, VAE, video, quality, App or Android execution",
                  "ltx098_t5_executed": "Host-only alias: separate unregistered trained quantized T5 encoder component; not T5 Android execution or complete video support",
                  "ltx098_t5_host_tested": "Independent GGML CPU F32-GELU graph against unmodified installed Transformers using pinned dequantized Q5_K_M weights, original external tokenizer config and full learned-vocabulary identity; no unquantized-weight or prompt/video quality acceptance",
                  "ltx098_vae_executed": "Host-only legacy alias for ltx098_vae_host_tested; not Android, App, complete prompt-to-video or quality acceptance",
                  "ltx098_vae_host_tested": "Nine sequential native ORT CPU stages using all 132 original trained decoder tensors cast to F32, explicit noise/statistics and independent unmodified publisher Decoder.forward; four geometries, not complete video generation",
                  "ltx098_vae_android_compiled": "Unregistered ARM64/API28 research CLI linked to pinned Android ORT; not packaged in APK or executed on a phone",
                  "ltx098_complete_prompt_to_video_host_tested": "Strict fixed full-chain numerical acceptance; actual execution is separate and a failed gate keeps this false",
                  "ltx098_complete_prompt_to_video_host_executed": "Three actual real-prompt single-scale host jobs with complete trained Google/community Q5 T5 and old 0.9.8 distilled DiT/VAE; not numerical, official-default/PixArt identity, quality or Android acceptance",
                  "ltx098_trained_video_tested": "Legacy complete Android target-17 acceptance flag; actual host videos have their own explicit flag",
                  "ltx098_tensor_primitives_android_compiled": "Portable RNG/layout/frame CLI ARM64/API28/16KiB compile only; no model data, APK registration or phone execution",
              },
              "scope": "A model-free native LCM condition preparer now passes24 real host children/105 checks, verifies the full original trained UNet and emits one source/base-bound5696-byte GGUF. A separately compiled ARM64/API28/16KiB program is not packaged or executed on a phone. All five trained small-overlay execution checks pass, but the image-comparison max8 exceeds the unchanged gate5 (mean0.0838928 passes0.1); this candidate remains rejected. Sampler-step cancellation/recovery and an independently retained strict-observer blank-line diagnostic remain HOST observations; App routing, user preparation/association, canonical pipeline and image quality are still open. The standalone distilled-model follow-up adds ten unchanged native CPU SD-Turbo/LCM checkpoint children, nine PNGs including three from five real production Java/native SD-Turbo children, complete explicit two-object import, and original trained687-tensor UNet condition-fold analysis across30 complete reduced-geometry synthetic forwards. A prepared LCM candidate alters only5120 bias bytes; no product preparation or canonical-pipeline/quality/Android equivalence is claimed. Source APK inputs and bytes remain unchanged. This Qwen developer-source follow-up executes the complete frozen 920MB Base/12Hz codec through unchanged production C++ on native Windows: eighteen WAV jobs across ten languages, reference conditioning, parameter changes and recovery, twelve controls and info. Production Java performs94 checks, complete two-object import and six actual children with zero network; independent audit rereads145 raw files,31 protocol streams,22 WAVs and two full imported objects. Original WAV and labelled waveform media retain HOST-only scope. A greedy short-text output equals the30-second budget without a distinct EOS/budget finish reason; quality, voice similarity, phone fit, Android and complete target11 remain unaccepted. APK inputs/bytes are unchanged. The previous developer-source follow-up executes all three frozen selection-10 English recipes through unchanged production C++ and official sherpa2.0.1/ORT1.28.2 Windows libraries: 68 actual WAV jobs covering all54 Kokoro/one Piper/one Matcha voices, thirteen controls and info. Production Java performs157 checks, full import of nine distinct objects/eleven references, twelve actual children, independent settings, partial-synthesis cancellation, duration errors and recovery with zero network calls. An independent audit rereads394 raw files,82 protocol streams,74 WAVs and nine imported objects; original audio and labelled waveform media retain explicit host scope. Windows does not test Android liblog interposition or skipped-word rejection; quality, licenses, physical-phone/background and complete target10 remain unaccepted. APK inputs/bytes are unchanged. The earlier metadata/source follow-up verifies eleven trained Nano assets, seven actual production-C++ WAV jobs plus seven controls, forty production Java/native checks, and independently rereads original outputs/imported objects. A user-importable pinned manifest and actual HOST audio/waveform media are supplied without changing APK inputs or bytes. Host ORT 1.28.0/API28 remains distinct from production Android 1.28.2/API28; phone, SAF, quality and endurance are untested. Development APK dev.24 corrects diffusion callback phases to loading/generating without changing model math; it includes signed explicit runtime association plans, hardlink reuse and independently managed source/runtime models, alongside user-selected native asset preparation and shared queued jobs. This checkpoint adds actual trained SD1.5 CPU host generation, sampler cancellation/recovery and A/B/A output checks using unchanged production C++ inference with a Windows-only parent-lifetime port. It also retains isolated T5 F32 staging and adds old-LTX publisher-modulation observations and native diagnostics; both new B sampling conditions still fail frozen latent gates. The full F32 candidate passes case A but fails case B; neither it nor the sampler diagnostics are registered or packaged. Two signed preparation programs and nine audited model-free architecture graphs are packaged without learned model data. The production Java core performed one full trained host preparation with 20 verified outputs; Android Service, SAF, converter execution and background endurance remain untested. The original signing identity is preserved. Packaged SoulX and other existing App engine contracts retain their scoped records; complete trained SoulX host speech is separate from quality, public user acquisition and Android acceptance. Retained old-LTX evidence records three real-prompt single-scale trained HOST video jobs with explicit Google/community Q5 T5, original 0.9.8 distilled DiT/VAE, independent original-forward comparison and actual RGB/MP4 media. Frozen full-chain float gates remain failed despite passing RGB gates; numerical acceptance is false. Separate tensor/T5/DiT/VAE Android compilation is not App registration or phone execution. Official default multi-scale/PixArt text-weight identity, video quality, complete public assets and target-17 Android acceptance remain open. Older component receipts retain their original scope. App updates deliver foundation code only; users explicitly select/manage all model assets, with no automatic model retrieval. One complete v0.3.0 still requires F-01-F-12, existing text, selections 01-14/16/17 and every frozen subtarget, trained quality/resources, physical-phone load/unload/screen-off/API/upgrade evidence and A1-A11/R01-R05. No complete Release, physical-device acceptance or all-selected-model support is claimed.",
              "required_scope": "docs/MULTIMODAL_RELEASE_PLAN.md", "sources": sources}
    (out / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    # Keep complete Android/Release acceptance false despite real host video output.
    print(json.dumps(status))


if __name__ == "__main__":
    main()
