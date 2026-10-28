# MOSS Delay: first-class on-phone CPU speech pipeline

[中文](MOSS_DELAY_ENGINE.md) · [User model assets](ASSET_CONTROL_AUDIT.en.md) · [Complete release scope](MULTIMODAL_RELEASE_PLAN.en.md)

This is an internal implementation checkpoint within the same complete v0.3.0. A real Android ARM64 CPU worker does not establish support for all nine frozen MOSS subtargets or any phone's speech quality, speed or background endurance. App updates deliver the foundation; models, embedded vocabulary and codecs remain explicit user choices.

## Pipeline, format and source

Optional reference WAV → native audio encoder → embedded BPE / 32-channel autoregressive Delay generation → de-delay / complete-code extraction → native waveform decoder → 24 kHz mono PCM16 WAV. Every stage executes inside the signed App on the same phone. No Python, ROOT, Termux, off-device stages or inference providers are used.

Source is the MIT [OpenMOSS/llama.cpp fork](https://github.com/OpenMOSS/llama.cpp/tree/b785003ba497794ecfa337c3e47f01af79489888), revision `b785003ba497794ecfa337c3e47f01af79489888`. LMA extracts reviewed native primitives from the pinned `tools/tts/run-moss-tts-delay.cpp`, excluding its CLI, Python/ONNX wrapper, shell helper, raw-code dumps and permissive WAV reader. Two BPE utilities call llama APIs directly; the common download/network library is not linked. The extractor and complete upstream file hashes are covered by the [source lock](../third_party/moss-delay-source-lock.json); the original checkout is unchanged.

**Only the first-class conversion layout is accepted.** Ordinary `OpenMOSS/MOSS-TTS-GGUF`, a generic Qwen3 backbone, Nano/Local/Realtime and v2 codecs are different formats. The [upstream guide](https://github.com/OpenMOSS/llama.cpp/blob/b785003ba497794ecfa337c3e47f01af79489888/docs/moss-tts-firstclass-e2e.md) explicitly distinguishes these; a GGUF extension alone proves no compatibility.

The current contract is 8B / hidden 4096 / 36 layers / 32 audio quantizers / codebook 1024 / 24 kHz / hop 1920. Before loading tensors, the worker checks architecture, dimensions, BPE arrays, all audio embedding/output heads and codec metadata. Layout checks do not prove checkpoint attribution, quality or individual family acceptance. The original MOSS-TTS 1.0 conversion is still needed for that subtarget's final acceptance; other frozen members retain individual implementation and validation work.

## User choices and management

Select a GGUF through All/search, choose **MOSS Delay 8B · first-class 原生语音**, explicitly select the components below, review the plan and start downloading. A compatible converted model folder can also be imported. This checkpoint does not promote an unchecked public GGUF to a pinned recommendation.

| Role | Required | Purpose |
| --- | --- | --- |
| `backbone` | Yes | Complete first-class model with embedded BPE and 32-channel embeddings/heads; `provides` discloses its tokenizer dependency |
| `audio_decoder` | Yes | Matching 24 kHz / 32-channel `moss-tts-audio-decoder` GGUF |
| `audio_encoder` | Optional | Matching `moss-tts-audio-encoder`; required only for reference-audio synthesis |

Without the encoder, plain speech remains available and the task form offers no reference selector. To add reference support, users explicitly select a complete recipe or independently update their bundle with the encoder. The App never fetches missing components. Local settings, shared jobs and artifacts are reused. Recommended remains `m08 → m06 → m01`.

The peer record carries **audio / TTS** tags and separate `moss_delay_native`, `moss_delay_firstclass_v1`, `moss_delay_8b_v1`, GGUF, CPU and component requirements. Installation and device evidence are independent. This speech route does not automatically receive sound-effect, music, Realtime, multiple-speaker or complete-family tags.

The actual pages below use explicitly simulated installed state, without model downloads or speech generation:

![MOSS component details — UI FIXTURE](media/development/40-moss-delay-components.png)

## Per-model settings and inputs

Editable values clamp to bounds, persist with the model and freeze into submitted jobs. Java and C++ validate them again. These are application guards, **not measured phone limits or publisher training limits**.

Model settings save that model's defaults. The Use model form's current-job parameters override only that job and never silently rewrite saved defaults.

| Setting | Default | Application range |
| --- | --- | --- |
| CPU threads | 4 | 1–32 |
| Formatted-input budget `maxInputTokens` | 512 | 1–2048, including prompt framing and reference occupancy |
| Generation steps `maxNewTokens` | 375 | 64–1500, including 32-channel delay flush; not final audio-frame count |
| Text temperature / Top P / Top K | 1.5 / 1 / 50 | 0–3 / 0.01–1 / 1–1024 |
| Audio temperature / Top P / Top K | 1.7 / 0.8 / 25 | Same ranges |
| Audio repetition penalty | 1 | 1–2 |
| Seed | -1 | Automatic, or 0–2147483647; the actual seed is recorded |
| Language hint | auto | Publisher-listed codes shown in the form; auto supplies no specific hint, without quality claims |

Formatted input + generation budget + 8 must fit both actual training context and the 4096 application guard. An explicitly imported reference must be **24 kHz mono PCM16 or float32 WAV, 1–10 seconds, at most 1 MiB**. RIFF extents, whole samples and finite normalized floats are checked. No automatic resampling or bundled default voice is provided.

This 8B route has substantial memory needs; no Z20/other-phone RAM, speed or real-time claim is established. The backbone uses mmap and 128-frame prefill batches. Reference encoding is released first, then the backbone/KV are released before waveform decoding. Reducing simultaneous live components does not guarantee the model fits a device.

![MOSS independent sampling — UI FIXTURE, not model output](media/development/41-moss-delay-parameters.png)

[Complete development walkthrough](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif). These media show production forms with a simulated native bridge only.

## Shared jobs and API

After explicitly installing a compatible bundle, use authenticated `POST /v1/jobs` with `speech.synthesize`. Replace these IDs with real local installed/imported IDs:

```json
{"bundleId":"YOUR_INSTALLED_BUNDLE_ID","type":"speech.synthesize","input":{"prompt":"A new test sentence","artifacts":[{"role":"reference_audio","artifactId":"YOUR_IMPORTED_WAV_ID"}]},"parameters":{},"allowUnmeasured":true}
```

Omit `artifacts` for plain speech. Available parameters/input roles come from local model details. `allowUnmeasured` permits an unmeasured recipe; it cannot make incompatible assets executable. This adds no `/v1/audio/speech` compatibility claim.

Private leased hardlinks remain until the actual child exits on cancellation/failure; original files remain intact. The worker dies with its parent. Stages and generated-step counts are indeterminate progress. Execution records contain actual seeds, formatted frames, reference encoding/model load/generation/codec timings, duration, stop reason and pipeline RTF. RTF includes native validation/loading/synthesis/save, excluding queue/process spawn; no phone performance values are prefilled.

## Building and current evidence

Use native Windows tools, with sources/cache/temp files inside the project and no virtualization:

```powershell
python tools/fetch_moss_delay.py
python tools/build_moss_delay.py
python tools/collect_moss_delay_notices.py
python tools/build_recipe_templates.py
python tools/test_moss_delay.py
python tools/build.py
```

NDK r30, API 28, ARM64 `armv8-a` CPU, static C++, 16 KiB ELF. GPU/OpenMP/dynamic backends/CURL and server/CLI builds are disabled. Build checks reject network, shell/exec and logcat imports. Model data is always external user-selected data.

**176 checks = 69 production-Java/actual-host-child assertions + 107 C++ algorithm/policy assertions.** C++ executes the pinned upstream Delay/sampler/de-delay self-test, frame-major codec handling and reference guards. The host supplies only a fatal assertion sink; no tensor/backend/model API is implemented or simulated. WAVs are structural fixtures, not synthesized speech. Compilation, host tests and fixture media do not replace every frozen target's physical-Android fresh-input output, speech/voice quality, resources, three load/unload cycles, 15-minute screen-off, one-hour service and upgrade acceptance. The complete v0.3.0 scope and gates remain intact.
