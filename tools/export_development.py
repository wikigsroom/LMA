"""Export only current development checks, explicitly excluding Release/device completion."""
import json
from pathlib import Path
import shutil
from evidence import current, version
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]


def main():
    if "-dev" not in version():
        raise RuntimeError("Use the full release workflow for release candidates")
    sources = {
        "build-info.json": "dist/build-info.json",
        "package.json": "build/package-verification.json",
        "native-payload.json": "build/native-payload-tests/results.json",
        "preparation-core.json": "build/preparation-tests/results.json",
        "preparation-trained.json": "build/preparation-tests/trained-results.json",
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
    out = ROOT / "verification/development"
    out.mkdir(parents=True, exist_ok=True)
    records = {}
    for name, source in sources.items():
        record = json.loads((ROOT / source).read_text(encoding="utf-8"))
        current(record["input_fingerprint"])
        if name == "build-info.json" and record["input_fingerprint"] != build_inputs():
            raise RuntimeError("Rebuild development APK first")
        shutil.copyfile(ROOT / source, out / name)
        records[name] = record
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
              "app_asset_preparation_core_host_tested": records["preparation-core.json"]["passed"],
              "app_asset_preparation_trained_host_tested": records["preparation-trained.json"]["actual_trained_preparations"] == 1,
              "app_asset_preparation_android_executed": False,
              "ltx098_vae_asset_prepare_host_tested": records["ltx098-vae-prepare.json"]["actual_trained_conversions"] == 1,
              "ltx098_vae_asset_prepare_android_compiled": records["ltx098-vae-prepare-arm64.json"]["android_arm64_compiled"],
              "ltx098_prepared_vae_decode_host_tested": records["ltx098-vae-prepare.json"]["actual_trained_decode_jobs"] == 4,
              "ltx098_t5_precision_candidates_host_executed": records["ltx098-text-precision-attention.json"]["aba_bitwise_identical"] and records["ltx098-text-precision-linear.json"]["aba_bitwise_identical"],
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
                  "app_asset_preparation_registered": "Two signed ARM64 preparation programs and audited model-free architecture resources packaged in dev.22, separate from generation engines; no Android execution",
                  "app_asset_preparation_core_host_tested": "44 production-core filesystem/lifecycle contracts and four protocol-fixture children on Windows; no Service, SAF or model inference",
                  "app_asset_preparation_trained_host_tested": "One full original checkpoint through production Java storage/jobs/native preparation, two actual native children and 20 fully verified runtime outputs; no neural inference or Android execution",
                  "app_asset_preparation_android_executed": "False until actual same-phone Service/SAF/preparation and background evidence exists",

                  "ltx098_t5_intermediate_diagnostic_executed": "314 trained host intermediate comparisons, 628 hashed raw tensors and 120 matched-native-input operator comparisons; trace retention changes diagnostic memory, not the accepted native caption or original forward",
                  "ltx098_t5_roundoff_repair_accepted": "Remains false until a repaired implementation passes unchanged complete-chain gates and required regression checks; local operator diagnostics or isolated precision candidates do not close this gate",
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
              "scope": "Development APK dev.22 adds explicit user-selected native asset preparation, independent derived-asset management and shared queued jobs. Two signed preparation programs and nine audited model-free architecture graphs are packaged without learned model data. The production Java core performed one full trained host preparation with 20 verified outputs; Android Service, SAF, converter execution and background endurance remain untested. The original signing identity is preserved. Packaged SoulX and other existing App engine contracts retain their scoped records; complete trained SoulX host speech is separate from quality, public user acquisition and Android acceptance. Retained old-LTX evidence records three real-prompt single-scale trained HOST video jobs with explicit Google/community Q5 T5, original 0.9.8 distilled DiT/VAE, independent original-forward comparison and actual RGB/MP4 media. Frozen full-chain float gates remain failed despite passing RGB gates; numerical acceptance is false. Separate tensor/T5/DiT/VAE Android compilation is not App registration or phone execution. Official default multi-scale/PixArt text-weight identity, video quality, complete public assets and target-17 Android acceptance remain open. Older component receipts retain their original scope. App updates deliver foundation code only; users explicitly select/manage all model assets, with no automatic model retrieval. One complete v0.3.0 still requires F-01-F-12, existing text, selections 01-14/16/17 and every frozen subtarget, trained quality/resources, physical-phone load/unload/screen-off/API/upgrade evidence and A1-A11/R01-R05. No complete Release, physical-device acceptance or all-selected-model support is claimed.",
              "required_scope": "docs/MULTIMODAL_RELEASE_PLAN.md", "sources": sources}
    (out / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    # Keep complete Android/Release acceptance false despite real host video output.
    print(json.dumps(status))


if __name__ == "__main__":
    main()
