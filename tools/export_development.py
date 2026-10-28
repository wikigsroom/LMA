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
        "native-payload.json": "build/native-payload-tests/results.json",
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
              "ltx098_t5_executed": False, "ltx098_vae_executed": False,
              "ltx098_trained_video_tested": False, "ltx098_app_engine_registered": False,
              "scope_definitions": {
                  "model_inference_tested": "Legacy complete physical-Android acceptance flag; scoped host execution has a separate flag",
                  "soulx_complete_text_to_speech_tested": "Complete user-facing Android SoulX TTS acceptance, including App integration and quality",
                  "soulx_complete_host_text_to_speech_tested": "Sequential trained native developer-host execution with synthetic references, without quality or phone acceptance",
                  "ltx098_native_dit_host_parity_tested": "Unregistered old-0.9.8 DiT component only: untrained reduced-width 2/3/28-layer CPU/Vulkan forwards against original publisher PyTorch, with no complete trained video, App or phone acceptance",
                  "ltx098_trained_dit_latent_host_tested": "Full pinned trained 28-layer DiT, synthetic caption embeddings and eight-step latent denoising on host Vulkan against original publisher PyTorch; no T5, VAE, video, quality, App or Android execution",
              },
              "scope": "registered packaged SoulX production worker, fourteen user-controlled assets, paired reference transcripts, bounded per-model snapshots and shared jobs/API/artifacts; 222 contract checks, 95 trained production-worker checks, two/four speakers and two forced host terminations; 10 exact shared-runtime verification checks, 27 verified unique APK native files; no verified complete public converted-asset candidate, quality or Android acceptance. Earlier independent research executors below remain separate from the packaged production worker and their evidence is not relabeled: complete trained SoulX HOST execution with fresh English/Chinese text, synthetic PCM references and 24kHz WAV via sequential native S3/CAMPPlus, full official Qwen3 Q4_K_M and Flow/HiFT; independent original full HF BF16 logits, exact publisher tokenizer, original RAS/history function blocks and actual neural cancellation, plus Android language ARM64/API28/16KiB compilation (not in APK, no App binding, speech quality, physical Android or complete-target acceptance; legacy model_inference_tested flag denotes complete Android acceptance, host_model_inference_tested is separate); unregistered trained SoulX S3 v2/CAMPPlus native reference execution with exact publisher graph/tensor identity, 145 host checks/actual in-run termination and Android compilation; independently pinned trained Flow/HiFT reconstruction using native trained references, 253 host checks/63 stage and 12 identical-input comparisons with explicit waveform RMSE/SNR gates (synthetic PCM codes, no language backbone/text-to-speech, App registration, phone execution or complete-model acceptance); shared CPU ORT contracts/lifetimes/cancellation; unregistered SoulX full acoustic four-graph export and native ORT/CPU chain with complete Flow/HiFT architectures, UNTRAINED synthetic parameters, actual upstream forward comparisons, sequential sessions and actual in-run termination, Android ARM64/API28/16KiB compilation (not in APK; separate untrained suite, no language model or complete trained speech); unregistered SoulX native DSP static library, Android ARM64/API28 compilation and pinned upstream numerical equivalence with synthetic PCM/F0/noise/estimator fixtures (not in APK, no complete model or speech output); real Stable Audio Open Small ARM64 LiteRT CPU worker with sequential T5/DiT/decoder lifetimes, four user-selected assets, effective-token/fixed-latent guards, actual host children, six real synthetic LiteRT graph runs and Arm sampler equivalence (no full-model audio); real old MOSS Local / Realtime RQ ARM64 CPU worker with separate model/codec/tokenizer layouts, actual prompt budget guards, host children/cancellation, metadata-only GGUF validation and two actual tiny depth graphs (no full-model inference); real old SoundEffect Ambient Sound binding; real openmoss TTS/v1.5/TTSD/VoiceGenerator/Local-Transformer-v1.5/SoundEffect-v2 ARM64 CPU worker with actual generation-grid budget guard, paired speaker references and bounded per-model voice/language hints, explicit two-GGUF user assets, optional stereo reference, independent speech/sound parameters, production Java and actual host child checks, pinned sound-format/noise/sigma primitives without model inference; real MOSS Delay first-class ARM64 CPU worker, user-selected GGUF backbone/decoder and optional reference encoder, sequential memory release, production Java binding and actual host child/WAV checks, pinned upstream native delay algorithm self-test without model inference; real Qwen3-TTS 0.6B Base ARM64 CPU compilation, production two-GGUF binding, optional reference WAV, embedded dependency disclosure, actual host child/file checks with structural WAV fixtures, pinned header review without tensor reads or model inference; real MNN Sana ARM64 CPU compilation and production 13-component binding with sanitized metadata, parameter snapshots, actual host children and deferred workspace cleanup (no image inference); production diffusion binding, strict classic/Z-Image/FLUX/Qwen/Wan components, actual flow-shift/sampler/scheduler bindings and Qwen/Wan geometry policies with actual host protocol children and shared native C++ checks; local input imports, bounded resumable upload HTTP and production WAV validation, immutable input receipts/leases in the production job runner with host child fixtures; shared FIFO scheduling across production jobs, resident text, chat and HTTP with actual host child ownership and cancellation; actual host legacy model migration, hardlinks, fixed aliases and shared leases without auto-resume; host GGUF text bundle constraints, typed text artifacts and actual loopback HTTP/child fixtures, host storage/transfers, user-reviewed atomic model version changes/rollback and HF component recipes/Git integrity, explicit adapter pairing/leases, speech worker contracts/child fixtures, Nano native external-data validation and private hardlink workspaces, authenticated HTTP/streams/text proxy, UI fixtures, native compilation and APK/lint checks only",
              "required_scope": "docs/MULTIMODAL_RELEASE_PLAN.md", "sources": sources}
    status["scope"] = "Unregistered exact old LTX-Video 0.9.8 DiT: 675 host checks/80 native children/48 publisher-PyTorch CPU-Vulkan comparisons, reduced-width untrained 2/3/28-layer forwards, pinned baseline F32 GPU arithmetic and optional F16 weight storage, separate ARM64 Vulkan compilation; no trained video, complete pipeline, App registration or physical Android. " + status["scope"]
    status["scope"] = "Old LTX follow-up: explicit pinned external checkpoint and streaming DiT conversion; original geometry/RF/unpatchify parity, ten UNTRAINED eight-step CPU/Vulkan trajectories and full trained 28-layer native Vulkan velocity/eight-step latent comparison with synthetic caption embeddings; separately compiled Android sampler, host process memory counters only, no T5/VAE/video/App/phone/complete-target acceptance. " + status["scope"]
    (out / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status))


if __name__ == "__main__":
    main()
