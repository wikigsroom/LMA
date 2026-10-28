# Native MOSS Delay / 原生 MOSS Delay

`moss_delay/` builds a CPU-only first-class MOSS backbone + optional reference encoder + waveform decoder from the pinned OpenMOSS fork. It extracts reviewed native primitives, excludes the upstream CLI/Python/shell helper, releases each model before the next stage and carries no model data. Source/build/asset boundaries: [中文](../docs/MOSS_DELAY_ENGINE.md) / [English](../docs/MOSS_DELAY_ENGINE.en.md). Compilation and host algorithm tests do not establish Android speech acceptance.

# Internal Android worker / Android 内部执行器

This directory contains App code, not model weights or an executable model plugin system. 当前有实际编译的 `sd_cpp`、`sherpa_tts` 与 `moss_nano_ort` CPU worker，不代表所有模型目标已经适配或经手机验证。

- `CMakeLists.txt` builds the exact pinned upstream sd.cpp / ggml from `third_party/engine-lock.json` using the Android ARM64 NDK. Builds stay under ignored `build/`, without Docker/WSL/emulation.
- `vocab_external.cpp` replaces every upstream embedded model vocabulary loader. The Android host supplies private, hash-verified user component paths through `LMA_VOCAB_*`; missing tokenizer data fails locally. No vocabulary byte arrays enter the APK.
- `sd_worker.cpp` accepts one private JSON request with schema `lma.engine-request/1`. Prompt text is kept out of argv and raw engine logs. Stdout contains bounded newline-delimited progress/stage/error/completion records.
- Images are actual engine-generated PNG outputs. The video branch emits engine-generated RGB frames in an internal `LMAFRM1` format for Android MediaCodec/MediaMuxer; these paths still require physical-device acceptance.
- The Java foreground-service host owns process cancellation, queue generation tokens, staged outputs and provenance. The worker requests `PR_SET_PDEATHSIG` so a dead host cannot leave generation running without its service.

Rebuild with `bootstrap_native.py`, `fetch_native.py`, `build_native.py`, then collect/review notices and `engine-lock.json`. The APK builder rejects extra native binaries, changed hashes, stale source inputs and changed notices. `engine-builds.json` describes compiled modules; its device status remains unvalidated.

开发界限、模型资产规则与全部未完成项见 [中文实施记录](../docs/DEVELOPMENT.md) / [English development record](../docs/DEVELOPMENT.en.md)。完整 v0.3.0 仍须全部冻结目标的新输入离线真机输出及发布验收。

- `moss_nano/` implements SentencePiece, autoregressive ONNX and codec decoding. Model-specific data stays external. Sources, user component roles, shared ORT rules and 190 host checks: [中文](../docs/MOSS_NANO_ENGINE.md) / [English](../docs/MOSS_NANO_ENGINE.en.md).

- `mnn/` builds the actual matched Sana/Qwen3 CPU pipeline with generated upstream load/token/thread guards, isolated diagnostics and external user-selected components. No image/phone inference is claimed. [中文](../docs/MNN_SANA_ENGINE.md) / [English](../docs/MNN_SANA_ENGINE.en.md).

Qwen3-TTS 0.6B Base: `qwen_tts/` builds the pinned native Talker/MTP/BPE/speaker/codec pipeline with ggml CPU, Android API 28 and 16 KiB alignment. Two user-selected GGUFs and optional strict local reference WAV remain outside the APK. See [中文](../docs/QWEN_TTS_ENGINE.md) / [English](../docs/QWEN_TTS_ENGINE.en.md); native compilation and header checks do not prove model/device output.

`openmoss/` builds the pinned Apache-2.0 community openmoss core and MIT llama.cpp as an isolated ARM64 CPU worker, excluding upstream CLI/server/WAV code. Local-v1.5 and SoundEffect-v2 use distinct user-selected backbone/extras layouts, real graphs and task receipts. No models/tokenizers/codecs are bundled; host math/child checks are not Android inference. See the [guide](../docs/OPENMOSS_ENGINE.en.md).
