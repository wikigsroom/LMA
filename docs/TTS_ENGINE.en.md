# Local speech foundation: implementation, assets and evidence

[中文](TTS_ENGINE.md) · [Development status](DEVELOPMENT.en.md) · [Complete v0.3.0 scope](MULTIMODAL_RELEASE_PLAN.en.md)

Internal **0.3.0-dev.3 / code 7** adds a compiled ARM64 CPU `sherpa_tts` worker using the sherpa-onnx 2.0.1 C API. Kokoro, Piper / VITS and Matcha have implementation paths, pinned candidate bundles and a speech form. **No Android inference has run. Selection 10 has not passed complete acceptance, and this is not a Release.** All other mandatory v0.3.0 work remains in scope.

## User flow and asset ownership

Filter All by audio, inspect the engine, license, complete components, total size and reusable data, then explicitly choose Download. Manage installed models and their settings in Local, enter narration text and submit through the shared queue. Media jobs currently still require stopping the legacy text model first. Use the shared audio preview, original-file export and API artifact access. The task API accepts `speech.synthesize`, `input.prompt` and an installed bundle ID.

The App delivers engine code, without voice or language assets. Installation, upgrades, browsing, API startup and missing-asset requests never download models. These are data-only candidates, **not preinstalled models**:

| Recipe | User-selected components | Tags and current boundary |
| --- | --- | --- |
| Kokoro 82M v1.0 · English | Pinned ONNX, 54-voice voices.bin, tokens.txt, English lexicon | Audio / TTS / sherpa_tts / CPU; this recipe is English only, without claiming every language supported by the multilingual weights |
| Piper en_US Lessac medium | Pinned VITS ONNX, tokens.txt, English lexicon | Audio / TTS / CPU; one voice; publisher MODEL_CARD references Lessac dataset terms |
| Matcha en_US LJSpeech / Vocos | Pinned acoustic ONNX, Vocos 22 kHz vocoder, tokens.txt, English lexicon | Audio / TTS / CPU; one voice; the acoustic card does not explicitly state a weight license, so review remains open |

See [model-bundles.json](../catalogue/model-bundles.json) and [component evidence](../catalogue/bundle-evidence.json) for hashes, sizes and sources. HF files use full commit pins. Shared English lexicon and Vocos use upstream GitHub assets, with content pinned by SHA256 and asset IDs recorded. The vocoder hash was also checked against the publisher's HF file page. Builds fetch no weights. Component license review remains a complete-release requirement; an engine license does not establish model-data rights.

## Parameters and execution

Each model / recipe retains separate editable preset settings. The signed engine enforces additional application bounds even when an imported manifest declares wider limits:

| Parameter | Application range | Handling |
| --- | --- | --- |
| CPU threads | 1–16 | Default 2; no measured optimal device value |
| Speed | 0.25–3 | Default 1 |
| Speaker ID | Recipe declaration, checked again against loaded model metadata | Clamp excess values; record the actual effective speaker |
| Silence scale | 0–3 | Default 1 |
| Duration guard | 1–600 seconds | Default 180; exceeding it fails instead of accepting truncated speech |
| Piper / Matcha noise | 0–2 | Piper also supports duration noise; unsupported pipeline parameters are rejected |
| Input text | 1–4000 characters | Requires selected-language lexicon coverage; negative prompts and NUL characters are rejected |

sherpa 2.x no longer uses legacy espeak-ng-data. This integration explicitly requires a user-owned lexicon. Additional lexicon_2–lexicon_8 components are possible, with language / phoneme compatibility still requiring recipe testing. Detected upstream skipped-word diagnostics reject success to avoid silently accepting incomplete speech; that diagnostic path and punctuation / number behavior still need Android checks. Current candidates do not provide voice cloning.

`NativeWorker` handles both diffusion and speech process ownership. Text travels in private JSON files; argv contains only the request file path. Jobs lease component objects and cancellation terminates the owned process. The native worker binds its lifetime to the parent and writes mono 16-bit PCM WAV after checking sample count, finite values, non-silence, sample rate, bounds and persistence. Provenance retains effective parameters, speaker count, duration, peak and RMS. These checks do not establish pronunciation accuracy or listening quality.

Third-party stdout / stderr are private. The worker interposes the three liblog symbols imported by the pinned libraries, and the build checks the import / export set. **Android log binding and privacy behavior remain untested on a device.** Computation stays on the same phone; missing language coverage or insufficient resources fails locally.

## Build and verification

```powershell
python tools/fetch_tts.py --transport ssh
python tools/build_tts.py
python tools/collect_tts_notices.py
python tools/test_tts.py
python tools/build.py
python tools/verify_package.py
```

Prepare the [common native toolchain](BUILD.en.md) first. Source revision is `af2d8d81dbfa61c4cea4c568da78f3982edca005`. C API / ONNX Runtime libraries are **upstream prebuilts** from the official v2.0.1 Android archive; the LMA worker is built locally with native Windows NDK r30. Their ELF API notes are 21 / 27, with 28 for the worker, compatible with the declared Android 9 floor; all are 16 KiB aligned. See [source pins](../third_party/tts-source-lock.json), [engine lock](../third_party/engine-lock.json) and [notice sources](../third_party/tts-notice-sources.json). Bootstrap and notice collection process code / generic notices only; caches stay inside the project.

62 host assertions cover production component contracts, parameter bounds, private requests, process cancellation, error / duplicate / missing completion events, nonzero exits and cleanup. Child fixtures write explicit arbitrary bytes, **not WAV, speech or model output**. Offline phone speech, pronunciation coverage, three load/unload cycles, speed / RAM / heat, screen-off endurance and Android log checks remain missing. They and language / voice license checks must pass the full release gates.

Primary references: [Android guide](https://k2-fsa.github.io/sherpa/onnx/android/build-sherpa-onnx.html), [TTS C API](https://k2-fsa.github.io/sherpa/onnx/c-api/html/tts.html), [pinned source](https://github.com/k2-fsa/sherpa-onnx/tree/af2d8d81dbfa61c4cea4c568da78f3982edca005). Upstream capabilities remain separate from LMA device evidence.
