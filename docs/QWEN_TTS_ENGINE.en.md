# Local Qwen3-TTS 0.6B Base pipeline

[中文](QWEN_TTS_ENGINE.md) · [Development status](DEVELOPMENT.en.md) · [Component recipes](HF_RECIPES.en.md) · [Local inputs](LOCAL_INPUTS.en.md) · [Complete release requirements](MULTIMODAL_RELEASE_PLAN.en.md)

**dev.24 follow-up:** [Complete trained validation](QWEN_TTS_TRAINED.en.md) adds both full GGUFs, eighteen actual WAVs/twelve controls, ten languages/references and94 production Java checks without changing APK bytes. The dev.15 header/contract record below retains its historical scope. Complete HOST inference now exists; quality, Android and full Release acceptance remain open. A greedy short-text case reaches30 seconds; a valid WAV does not establish complete reading.

Applies to **0.3.0-dev.15 / code 19**, development within the same complete v0.3.0. No new Release exists. Selection 11 now has a compiled native CPU route and production Java adapter. **There is no complete-model inference, Android output, quality, real-time or background acceptance evidence.** Header review and host children do not establish those results.

## User choice and components

App updates supply the signed `qwen_tts_native` worker, `qwen3_tts_06b_base` pipeline and catalogue/recipe metadata. Models remain user-owned assets: installation, upgrades, browsing and tasks with missing assets never download them. Installing this model is optional; the original `m08 → m06 → m01` recommendations remain intact.

All/search offers `qwen3_tts_06b_base_cpu_v1` for selecting two matching GGUFs. The catalogue also offers pinned optional bundle `qwen3_tts_06b_base_q4_rb7ee2e8`. Users review components/size and explicitly download or import them. Shared management handles transfers, updates and deletion; Local saves settings by model ID.

| Physical file / role | Logical dependencies provided | Pinned size |
| --- | --- | --- |
| `qwen-talker-0.6b-base-Q4_K_M.gguf` / `talker` | Talker, text BPE, Code Predictor and speaker encoder; `provides` identifies the embedded roles | 628,905,056 bytes |
| `qwen-tokenizer-12hz-Q8_0.gguf` / `audio_codec` | Sixteen-codebook decoder, 24 kHz mono, 1920 samples/frame | 291,150,624 bytes |

Total **920,055,680 bytes**, from [Serveurperso/Qwen3-TTS-GGUF](https://huggingface.co/Serveurperso/Qwen3-TTS-GGUF), revision `b7ee2e8c7459c3bea99da23e3d178125a7d1713c`. Sizes/SHA256 come from pinned HF LFS metadata. The [header review](../catalogue/qwen-gguf-headers.json) checks structures without reading tensor weights or executing a model. The publisher card declares Apache-2.0; the worker source and ggml are MIT with separate notices.

Physical file counts differ from logical dependency counts. Shared `Component.provides` exposes embedded roles in dependency tags and details; it creates no extra downloads and enables no runtime capability by itself. TTS uses `task:audio`, plus engine/pipeline/CPU/GGUF/component tags. Text input does not give it a text-generation tag. Installation and device evidence remain separate.

## Use and parameters

1. Select an installed complete model in Local, open speech synthesis and enter 1–4000 characters.
2. Optionally import/select a **1–30 second, 24 kHz mono PCM16 or float32 WAV, at most 4 MiB**. This route exposes speaker-embedding conditioning only, without ICL reference transcripts, named speakers or instruction-based voice design. Omitting a reference never downloads a default voice; actual output quality remains untested.
3. Edit this model's parameters or choose presets. Values above/below the permitted range are clamped. These are **application guards, not publisher training limits or measured phone performance**.
4. Explicitly submit to the shared queue. Missing components, invalid input and resource limits fail locally. WAV results reuse playback/export/retry management.

| Parameter | Default | Application guard |
| --- | --- | --- |
| `threads` | 4 | 1–32 |
| `maxInputTokens` | 512 | 1–2048, using actual BPE and TTS formatting; over-budget text fails |
| `maxAudioTokens` | 375 | 1–1500, about 12.5 frames/sec; a maximum budget, with early EOS possible |
| `temperature` / `topP` | 0.9 / 1 | 0–2 / 0.01–1 |
| `topK` / `repetitionPenalty` | 50 / 1.05 | 1–1024 / 1–2 |
| `seed` | -1 | -1 automatic, otherwise 0–2147483647; actual seed recorded before execution |
| `language` | auto | auto, zh, en, ja, ko, de, fr, ru, pt, es, it |

Progress reports actual stages and generated audio frames, without treating a maximum frame budget as a completion percentage. Execution metadata retains effective parameters, input tokens, audio samples/duration, loading/synthesis/pipeline time and `synthesisRTF`/`pipelineRTF`. RTF is elapsed time divided by audio duration. Pipeline time includes validation, loading, synthesis and saving, excluding queue delay/process startup. Real-time claims require physical-device measurements.

## Execution and API

The production path is BPE → autoregressive Talker → multi-codebook prediction → 12Hz codec → PCM16 WAV, entirely on the same Android phone. CPU baseline, API 28, ARMv8-A, 16 KiB ELF alignment; no GPU/CoreML/HTTP model-fetch or download utilities are compiled. No ROOT, Termux, remote provider or user plugin nodes.

Model/input leases hold private hardlink workspaces containing only two fixed GGUF names and an explicitly selected reference WAV. Actual GGUF identities, dimensions, predictor, vocabulary, speaker encoder and codec are checked. 1.7B, CustomVoice, VoiceDesign, ordinary text GGUF and incompatible conversions fail. Reference samples must be finite and normalized. Cancellation terminates the child; workspace cleanup waits for actual exit and preserves originals. Low-memory mode releases Talker before codec decoding. Resource figures are unmeasured estimates, with no Z20 capacity/speed guarantee.

This uses the existing authenticated task API; it **does not claim OpenAI `/v1/audio/speech` compatibility**:

```json
{"bundleId":"qwen3_tts_06b_base_q4_rb7ee2e8","type":"speech.synthesize","input":{"prompt":"This speech will be generated on this phone."},"parameters":{"language":"en","maxAudioTokens":125},"allowUnmeasured":true}
```

Submit to `POST /v1/jobs` with authentication and the required idempotency key. Optional `input.artifacts` binds `reference_audio` to a local `artifactId`; paths/remote URLs are not inputs. Query, events, cancellation and Range artifact delivery retain the [shared API](API.en.md).

## Build and evidence

Pinned [Danmoreng/qwen3-tts.cpp](https://github.com/Danmoreng/qwen3-tts.cpp) `16bb5afcd06311031c72a8488f8d59660dc2fb46`, ggml `af97976c7810cdabb1863172f31c432dab767de7`; see the [source lock](../third_party/qwen-tts-source-lock.json). Thirty-five explicitly listed library sources exclude CLI/JNI/converters/download scripts, with a clean upstream checkout.

```powershell
python tools/fetch_qwen_tts.py
python tools/build_qwen_tts.py
python tools/collect_qwen_tts_notices.py
python tools/audit_qwen_headers.py --origin https://hf-mirror.com
python tools/test_qwen_tts.py
python tools/build.py
```

The header tool is an explicitly invoked developer review. App installation, browsing, task submission and builds never invoke it. Only GGUF headers are read; recorded summaries contain dimensions/metadata, without vocabularies or tensor data.

81 checks comprise 48 production Java/file/child contracts and 33 native parameter/WAV cases. Host children write static structural WAV or explicit JSON fixtures to test output rejection, failure propagation and cleanup. They synthesize no speech. Selection 11 still requires actual-model quality/RTF, three load/unload cycles, screen-off and sustained-service acceptance on physical Android, alongside every other frozen target in the same complete v0.3.0.

![Qwen component disclosure, UI FIXTURE](media/development/38-qwen-tts-components.png)
![Qwen independent speech sampling settings, UI FIXTURE](media/development/39-qwen-tts-parameters.png)
