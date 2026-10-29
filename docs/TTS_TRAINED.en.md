# Selection 10: trained Kokoro, Piper and Matcha validation

[中文](TTS_TRAINED.md) · [Speech foundation and user flow](TTS_ENGINE.en.md) · [Numbered delivery/full pending scope](releases/v0.3.0-dev.24-tts.md) · [Complete requirements](MULTIMODAL_RELEASE_PLAN.en.md)

This is development work inside the single complete v0.3.0 scope. The App remains **0.3.0-dev.24/code28**. New native Windows tools run unchanged production C++ and Java against actual trained files; the computer is not an App inference provider. Existing Android APK inputs and bytes are unchanged. **Speech quality, component licenses, Android log binding, phone resources/endurance, complete selection-10 acceptance and the formal Release remain open.**

## 1. Frozen recipes and user assets

All three existing recipes in [frozen selection 10](proposals/multimodal-release-scope.json) are covered. Other Piper languages/voices or Matcha weights require their own recipes and tests. Models remain peers, with independent audio/TTS, sherpa_tts/CPU/ONNX dependency, device/evidence, license and content tags.

| Bundle ID | Pinned publisher revision | Tested voice scope | Full component bytes |
| --- | --- | --- | --- |
| `kokoro82_en_v1_rf7b96bb` | `csukuangfj/kokoro-multi-lang-v1_0` / `f7b96bb6bef5c5da4d3aa4f4e0498fbbf62dc78b` | Loaded model reports 54; IDs0–53 individually synthesize the same English text | 360,067,976 |
| `piper_lessac_en_r83f7470` | `csukuangfj/vits-piper-en_US-lessac-medium` / `83f7470750b36549037551ef7007fa3b4b8697e0` | Lessac, ID0 | 69,508,119 |
| `matcha_ljs_en_rbe5535c` | `csukuangfj/matcha-icefall-en_US-ljspeech` / `be5535c9e754d0dfd3ab66dac34f78c5b5d66d50` | LJSpeech, ID0, separate Vocos vocoder | 134,348,008 |

Eleven component references resolve to nine distinct objects, **551,312,557 bytes** after deduplication. All recipes share the same 6,305,773-byte English lexicon; Matcha also needs the 53,884,024-byte Vocos. [Developer asset pins](../research/tts_trained/assets.json) record each size, SHA256, immutable URL/revision and GitHub asset ID, checked against the [existing App recipes](../catalogue/model-bundles.json). Real weights, voices.bin, tokens, lexicons and vocoder data remain ignored developer files or user assets. Git/APK contains code and metadata only.

Every Kokoro voice ID uses this **English lexicon**. Voice names and multilingual weights do not establish other-language support; valid waveforms do not establish pronunciation or voice quality. Kokoro's publisher LICENSE is Apache-2.0, while shared-lexicon terms still need review. Piper needs MODEL_CARD/Lessac terms checked; the Matcha acoustic card does not explicitly declare a weight license. The engine's Apache-2.0 license does not substitute for model-data terms; see the [asset notice](../research/tts_trained/NOTICE).

Users inspect the recipe, size, provenance and license under Models → All → Audio, then explicitly download, or [import a complete local folder](HF_RECIPES.en.md). Local manages installed models and separate settings. Installation, upgrades, browsing, API startup and missing-asset jobs retrieve no model. Download/pause/resume/update/rollback/delete remain user actions. Recommended stays m08→m06→m01; developer assets become no mandatory installation.

## 2. Actual execution and parameters

The native Windows build compiles `native/tts/worker.cpp` directly with a [CRT/parent-lifetime port](../research/tts_host/NOTICE); production neural code is unchanged. It uses the pinned official sherpa-onnx **2.0.1** Windows C API and ORT **1.28.2**, confirmed by actual `--info`. The official archive is 7,899,712 bytes, SHA256 `afa4de3ca4ab0afd53bb4aab40d28ee15608364b549ffc0fe0caf6489bfc39a5`; every DLL/import library has [separate pinned identity](../research/tts_host/runtime.json). There is no global installation, virtualization, Docker, WSL or emulator.

Matching ORT version strings do not establish Windows/Android numerical or lifecycle parity. **Windows libraries do not pass through Android liblog interposition.** The English host runs therefore prove neither Android skipped-word rejection nor log privacy. Public `android_log_interposition_tested` and `host_oov_guard_accepted` remain false; word, number and punctuation coverage require separate checks.

Each pipeline runs A, B, speed1.5, excessive-speaker clamping, a duration-limit error, cancellation after actual partial synthesis, and recovery A. Kokoro additionally executes voices1–53. Successful outputs check mono PCM16, sample rate/count, finite/non-silent waveform, bounds and effective settings. Error/cancel paths accept no partial WAV. Original requests, stdout protocols, raw outputs and 20ms host-process memory observations remain in separate ignored run directories. Timings include startup/model loading; they are not phone measurements, and the host is not an exclusive benchmark environment.

Settings remain independently editable and clamped per model. Production Java tests import every complete object, verify deduplication, save three different profiles, freeze request snapshots, and invoke the actual worker through `SherpaEngine` → `NativeWorker`. Each model performs initial output, partial-synthesis cancellation, a one-second duration error and recovery, checking process exit, private-request deletion, ownership release and restored assets/settings. Application/AtomicFile are explicit host ports; Android Service, SAF, MediaPlayer and screen-off behavior do not run here.

These C API paths expose no deterministic seed control. Actual A/recovery byte equality is recorded without requiring it for stochastic models. Hash differences certify neither prompt semantics nor speaker quality. The speed experiment establishes shorter output for the chosen text, without claiming linear speed or listening quality for every input.

The Java harness first needed a shadowed-method compilation fix. A later actual Piper run exposed an incorrect exact-double assertion: an independent real call confirmed that C API float speed records1.1 as1.100000023841858. The corrected assertion requires **the exact IEEE float conversion**, without broad tolerances or production-parameter changes. Earlier failures remain captured; public results come from a fresh complete execution after correction.

## 3. Measurements and media

See the [trained report](../verification/development/tts-trained.json), [actual Java binding](../verification/development/tts-app-host.json) and [independent raw audit](../verification/development/tts-capture-audit.json). The three WAVs below copy original generated bytes, without gain or amplitude normalization. The silent GIF and actual-audio MP4 show waveform slides, **not an App or phone screen recording**. MP4 AAC conversion/48kHz resampling is disclosed separately.

All 68 successful WAV jobs, 13 controls and info pass across 82 actual native children, covering 54 Kokoro/one Piper/one Matcha voice IDs. All three A/recovery pairs differ bytewise in this run; the actual values remain recorded without a determinism claim. Independent raw review covers 394 files, 82 protocol streams, 74 WAVs (including six Java outputs) and nine imported objects.

| Pipeline | Hz | A audio s | Speed1.5 audio s | A process s incl. load | HOST peak WS MiB | Cancel-to-exit s |
| --- | --- | --- | --- | --- | --- | --- |
| kokoro | 24000 | 3.000 | 2.000 | 2.653 | 522.0 | 0.062 |
| piper_vits | 22050 | 2.171 | 1.382 | 9.213 | 206.4 | 0.042 |
| matcha | 22050 | 2.392 | 1.591 | 16.929 | 262.4 | 0.052 |

| Actual speech | Original bytes |
| --- | --- |
| Kokoro voice0 | [WAV](media/development/tts-trained-kokoro.wav) |
| Piper Lessac voice0 | [WAV](media/development/tts-trained-piper_vits.wav) |
| Matcha LJSpeech/Vocos voice0 | [WAV](media/development/tts-trained-matcha.wav) |

![Actual host waveforms and scope](media/development/tts-trained-contact-sheet.png)

[Waveform GIF](media/development/tts-trained-waveforms.gif) · [Actual-audio MP4](media/development/tts-trained-speech.mp4) · [Media identities/provenance](media/development/tts-trained-media.json)

## 4. Developer reproduction

Prepare the [native toolchain](BUILD.en.md) and existing pinned sherpa source. Run inside this repository using native Windows Python/MSVC/Java/FFmpeg, keeping temporary files and models under the designated workspace:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
python tools/fetch_tts_host_runtime.py --download
python tools/fetch_tts_trained.py --download
python tools/build_tts_host.py
python tools/test_tts_trained.py
python tools/test_tts_app_host.py
python tools/check_tts_trained_evidence.py --raw --self-test
python tools/render_tts_trained.py
python tools/export_development.py
python tools/check_repository.py --development
```

Only the first two explicit download commands acquire developer runtime/assets. Without `--download`, they verify existing files. If HF is unreachable, explicitly add `--hf-origin https://hf-mirror.com` to the developer-asset command; identical commit/size/full-SHA checks remain mandatory and App settings do not change. The first mirrored Piper tokens Range response declared a length inconsistent with received bytes; acquisition rejected it and retained the raw attempt. Fixed Git-blob and whole-response checks confirmed the original 921-byte/SHA pins. The tool now omits Range for files fitting one whole request, retaining full-file checks. No hash relaxation, catalogue change or reconstructed success was used.

Media generation refuses to overwrite published names; new captures need distinct names and updated provenance. Current-input and false-scope checks do not establish model or Release acceptance. Continue the [full numbered pending scope](releases/v0.3.0-dev.24-tts.md), preserving failed LTX gates and every frozen target in one version, without automatic deferral.
