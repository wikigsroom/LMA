# Native foundation for old MOSS Local and Realtime

[中文](MOSS_RQ_ENGINE.md) · [Other MOSS routes](OPENMOSS_ENGINE.en.md) · [Complete release scope](MULTIMODAL_RELEASE_PLAN.md) · [Bilingual checkpoint notes](releases/v0.3.0-dev.19.md)

Internal **0.3.0-dev.19 / code 23** adds the ARM64 CPU `moss_rq_native` engine. The production Java adapter invokes compiled tokenization, global/depth Transformer, sampling, reference encoding and audio decoding code. **No complete model or physical Android inference has run.** Selectable recipes and successful compilation do not establish phone support. All frozen targets remain in one complete v0.3.0; no new Release exists.

## 1. Two separate layouts

| ID | Equal-peer recipe / model | Native model format and structure | Output / interface |
| --- | --- | --- | --- |
| D19-01 | `moss_local_v10_rq_cpu_v1` / old MOSS-TTS-Local-Transformer | `moss-tts-local`; Qwen3-1.7B global, four-layer Qwen3 depth, input and 33 channel-specific output MLPs, 32 audio codebooks | 24 kHz mono PCM16 WAV; one text request, optional voice/language hints |
| D19-02 | `moss_realtime_rq_cpu_v1` / MOSS-TTS-Realtime | `moss-tts-rt`; Qwen3-1.7B global, four-layer RoPE depth, 16 audio codebooks, 15 depth input embedding tables | 24 kHz mono PCM16 WAV; one text request with remaining text fed step by step |

Old Local's official config calls the architecture `MossTTSDelayModel`, but its actual model source establishes the depth/adaptor structure. It differs from Local-v1.5's single-layer GPT-J / 12-codebook / 48 kHz stereo structure and cannot use a generic Delay switch.

Realtime is the model's name. Requests still contain the complete text. Dev.29 adds opt-in [frame-by-frame audio and playback](AUDIO_STREAMING.en.md) with a sample-identical final WAV; default whole-file mode retains its original gain handling. There is no incremental text session, WebSocket output or latency promise. Voice/language hints and text-sampling fields ignored by the native offline path are not exposed. Actual speed and RTF require phone measurement.

Pinned official model/processor/codec/tokenizer revisions and hashes appear in the [publisher audit](../catalogue/evidence/moss-rq-publishers.json). Only JSON/Markdown/Python source text was read; no weights were downloaded or publisher Python executed.

## 2. Three explicitly selected components

| Role | Required file | Validation |
| --- | --- | --- |
| `model` | Matching `moss-tts-local` / `moss-tts-rt` GGUF | Global vocabulary capacity 155648 / 151936, layers, heads, depth geometry, audio head/embedding shapes |
| `codec` | `moss-audio-tokenizer` GGUF | v1: 24 kHz, hop 1920, 32 quantizers, codebook size 1024, dim 8, RVQ dim 512 |
| `tokenizer` | Matching `moss-tokenizer` / `qwen2-bbpe` GGUF | Nonempty BPE arrays, vocabulary within model capacity, required special IDs/content; old Local and Realtime tokenizers are incompatible |

The converted token array need not fill the model embedding capacity: conversion ends at the highest actual token ID, with publisher additions through 151668. Requiring array length to equal embedding capacity would reject valid files. Geometry and special-token validation **cannot authenticate weight identity or quality**; users still need matching origins, pinned revisions, conversion relationships and hashes.

Users explicitly select or import all three components and see their dependencies. The APK carries no weights, codec, BPE or voice assets and performs no automatic model transfer, conversion or replacement. moss-tts.cpp, openmoss, Nano and first-class GGUF layouts are incompatible. Image LoRAs are rejected for these speech recipes.

## 3. Usage and model-owned parameters

1. Select the correct recipe and three matching GGUFs, review origins/sizes/dependencies, then explicitly download or import. There is no fully accepted model bundle; an arbitrary similarly named GGUF is not labelled compatible.
2. Once installed, open the model from Local and edit its own settings using presets or free input. Numeric values clamp to declared limits; invalid strings, unknown fields and template markers fail.
3. Enter plain narration text and optionally import one **24 kHz mono, 1–10 second, ≤1 MiB PCM16 or finite float32 WAV**. No automatic resampling/downmixing; negative prompts, duplicate/unknown reference roles are rejected.
4. Task parameters form a separate snapshot. Explicitly choose the unmeasured route, use the existing FIFO, inspect stages, cancel and read local artifacts/receipts. Every inference stage runs on the same phone.

| Parameter group | Old Local | Realtime |
| --- | --- | --- |
| CPU / seed | `threads` 1–32, default 4; `seed` -1 automatic or 0–2147483647 | Same |
| Input / generated steps | `maxInputTokens` 1–2048 / default 1024; `maxNewTokens` 1–750 / default 375 | Same; formatted input includes remaining streamed text |
| Audio defaults | Temperature 1.7, Top P .8, Top K 25, repetition penalty 1.1 | Temperature .8, Top P .6, Top K 30, penalty 1.1 |
| Audio limits | Temperature 0–3, Top P .01–1, Top K 1–1024, penalty 1–2 | Same |
| Text continue/stop head | Temperature 1.5 / 0–3, Top P 1 / .01–1, Top K 50 / 1–1024 | Not exposed |
| Voice / language hints | Plain text, 1000 / 64 characters; blank becomes `None` | Not exposed |

Step budgets include stopping steps and do not promise exact duration. Up to roughly 60 seconds of code frames is neither a speed nor quality claim. After formatting actual text/reference inputs and before prefill, native guards enforce the selected input limit and prefill + generated steps + 8 ≤4096. Realtime rejects a step limit too small to consume remaining text rather than silently bypassing the budget.

## 4. Execution, API and resource limits

Use authenticated `POST /v1/jobs` with `speech.synthesize` and existing jobs/input/artifact endpoints. No speech-stream or remote-execution endpoint is introduced. Tokenization, reference encoding, generation and WAV decoding execute on the same phone. Missing files and unsupported layouts fail locally.

Components use private hardlinks and shared leases; originals are preserved. Workspaces close after the owned child terminates. Parent death binds `SIGKILL`; stdout is JSON only and library diagnostics do not reach logcat. CPU selection and GGML thread count are applied; head-level parallelism is disabled to respect the thread budget. No upstream CLI/HTTP server or Python is linked into the APK.

Receipts expose actual seed/backend, formatted prefill and remaining-text/reference counts, generated steps/frames, load/prefill/generation/whole-pipeline timing, audio duration, RTF, stop reason and `single_text_to_wav`. Preprocessing and first depth-step overhead belong to their labelled measured stages; development checks do not fabricate phone RTF.

The CPU route keeps all three components resident. A 1.7B backbone does not describe the full package: codec, KV and graph allocations also count. Z20 6/8 GB loading or generation is unproven. There is no GPU or off-device fallback.

## 5. Pinned source and verification

Community source: [mudler/moss-tts.cpp](https://github.com/mudler/moss-tts.cpp/tree/ee722b8e9205ee9b1b1c398a4e87e4e393e9be41), GGML `e705c5fed490514458bdd2eaddc43bd098fcce9b`; see [source lock](../third_party/moss-rq-source-lock.json). Its README declares MIT and names Ettore Di Giacinto. **There is no standalone LICENSE file at that revision**: LMA preserves the actual [README declaration](../third_party/notices/moss-rq-upstream-README.txt) and [GGML license](../third_party/notices/moss-rq-ggml-LICENSE.txt), without inventing an upstream license file. Model licenses remain separate.

The pinned checkout stays pristine. Reviewed generated Local/Realtime copies add actual-input guards and measured stage callbacks, with their hashes recorded. Native Windows NDK r30 / API 28 / `armv8-a` / static C++ / 16 KiB alignment builds are checked for network, shell/exec and logcat imports. No Docker, WSL, VM or emulator is used.

```powershell
python tools/fetch_moss_rq.py
python tools/build_moss_rq.py
python tools/collect_moss_rq_notices.py
python tools/test_moss_rq.py
python tools/build.py
```

178 scoped checks comprise 132 Java checks (10 actual host children), 30 C++ policy checks, 14 actual GGUF metadata checks and two pinned tiny graph tests. The graph tests execute the Local depth block and two Realtime depth steps using synthetic 3360 / 15616-byte tensor fixtures, **not model checkpoints or complete speech inference**. Structural WAVs are also not neural output. See [development evidence](../verification/development/moss-rq.json).

| Pending ID | Work retained in complete v0.3.0 |
| --- | --- |
| P19-01 | Full model/codec fresh-input offline output, quality, memory/temperature/RTF and load/unload records |
| P19-02 | Separate acceptance for all nine MOSS subtargets; these three integrations do not establish phone support |
| P19-03 | Every frozen F-01–F-12 and 01–14 / 16 / 17 subtarget, A1–A11 and R-01–R-05 |
| P19-04 | 15-minute screen-off, one-hour alternating API, upgrade/zero-model/asset preservation gates before the full Release |
