# Build and program verification · v0.3.3

[中文](BUILD.md) · [Release workflow](RELEASING.md) · [Validation policy](PROGRAM_VALIDATION.en.md) · [Archived build notes](BUILD_HISTORY.en.md)

Use a **full Git clone with history**, checked out at `v0.3.3` for reproduction. Historical evidence checks intentionally read earlier immutable Git blobs. The source ZIP is for code/docs/evidence review: its manifest lists exact files, while `.git`, native binaries, model data, build dependencies and signing material are excluded. It is not a self-contained binary SDK. No trained model is required to compile or program-check the APK.

## Toolchain

Native Windows: JDK21, Python3 (this build: 3.13), Node22, Android SDK Platform35 / Build Tools35.0.1 / Command-line Tools for Lint. C++ uses MSVC and pinned NDK30.0.16248370 / CMake3.31.6. The verified path is the Python builder; no Gradle wrapper or verified Android Studio/Gradle build is claimed. No Docker, WSL, VM or emulator.

UI checks use Playwright with Edge/Chromium; recordings additionally use FFmpeg/FFprobe and Playwright's recording component. Set `LMA_PLAYWRIGHT`, `LMA_BROWSER` or `LMA_FFMPEG` if needed. Install dependencies only into ignored/task-selected folders. Browser contexts close in finally. Native builders temporarily create a free ASCII drive alias and remove only that owned alias; never replace existing mappings such as `S:`.

## Source and native dependencies

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
git checkout v0.3.3
python tools/bootstrap_runtime.py
python tools/bootstrap_native.py
python tools/fetch_native.py --transport ssh
python tools/build_native.py --jobs 4
python tools/collect_native_notices.py
```

Bootstrap downloads fixed runtime/toolchain code, not model assets. The 14 ServLlama text libraries are pinned prebuilt components. Other workers are compiled locally against their locked sources/dependencies. Git and the source ZIP exclude all native binaries. Before APK packaging, prepare **every enabled engine** and its receipts/notices; the package gate rejects missing/stale files instead of silently dropping capabilities.

| Engine family | Source/build/notice entry points in tools/ | Detailed prerequisite guide |
| --- | --- | --- |
| sherpa / Kokoro / Melo / Piper / Matcha | fetch_tts.py → build_tts.py → collect_tts_notices.py | [TTS](TTS_ENGINE.en.md), [Melo](SPEECH_3D_EXPANSION.en.md) |
| MNN / Sana | fetch_mnn.py → build_mnn.py → collect_mnn_notices.py | [MNN](MNN_SANA_ENGINE.en.md), [Sprint](SANA_SPRINT.en.md) |
| MOSS Nano | fetch_moss_nano.py → build_moss_nano.py → collect_moss_nano_notices.py | [Nano](MOSS_NANO_ENGINE.en.md) |
| Qwen3-TTS | fetch_qwen_tts.py → build_qwen_tts.py → collect_qwen_tts_notices.py | [Qwen](QWEN_TTS_ENGINE.en.md) |
| MOSS Delay | fetch_moss_delay.py → build_moss_delay.py → collect_moss_delay_notices.py | [Delay](MOSS_DELAY_ENGINE.en.md) |
| OpenMOSS | fetch_openmoss.py → build_openmoss.py → collect_openmoss_notices.py | [OpenMOSS](OPENMOSS_ENGINE.en.md) |
| MOSS RQ / Realtime | fetch_moss_rq.py → build_moss_rq.py → collect_moss_rq_notices.py | [RQ](MOSS_RQ_ENGINE.en.md) |
| SoulX | build_soulx.py → build_soulx.py --android → collect_soulx_notices.py | [SoulX locked prerequisites](SOULX_ENGINE.en.md) |
| Stable Audio | fetch_stable_audio.py → build_stable_audio.py → collect_stable_audio_notices.py | [LiteRT](STABLE_AUDIO_ENGINE.en.md) |
| LTX and preparation workers | build_ltx098_app.py / --android; package_ltx098_app.py | [Original multiscale route](LTX_MULTISCALE.en.md), [prepared graphs](LTX098_VAE_PREPARE.en.md) |
| audio.cpp / single-image 3D | fetch_expansion_sources.py --fetch; build_expansion.py speech_extra / mesh | [Speech/3D](SPEECH_3D_EXPANSION.en.md) |
| Pixal3D MV | fetch_multiview_sources.py --fetch; build_multiview.py --host / default Android | [MV sources, generated patches and checks](MULTIVIEW_DIAGNOSTICS.en.md) |

Run `collect_expansion_notices.py` after rebuilding the added speech/single-image/MV workers. Review receipt and `engine-lock.json` changes. User dictionaries/tokenizers/codecs remain external components, never embedded weight data. Individual guides retain earlier trained experiments as **history**; their `--trained`/model-download commands are not part of current validation.

## APK and bounded program checks

```powershell
python tools/build.py --sdk C:/path/to/Android/Sdk
python tools/verify_package.py
python tools/test_android_lint.py
python tools/run_program_checks.py
python tools/test_foundation.py
python tools/test_expansion.py
python tools/test_multiview.py
node tests/ui-smoke.cjs
```

Without `--sdk`, use `ANDROID_SDK_ROOT` or the default LocalAppData SDK. SDK packages are not silently installed. `build.py` generates catalogue/templates, compiles resources/Java/DEX, validates native receipts, aligns/signs the APK and inspects its identity. Exact-byte fingerprints prevent stale passes; `.gitattributes` preserves line endings and raw header padding.

The runner first compiles backend production classes consumed by HF/community checks, then runs three bounded groups. Sana/LTX defaults execute small synthetic graphs and process controls, never complete trained models. The other three Python commands and full UI complete the 26-suite set. Host tests use explicit Android ports, real files, sockets and children; they are not phone tests. Preserve current records and rerun only when inputs change or failures require it.

Current package: `com.lma.app`, version0.3.3/code53, ARM64, API28+/target35, **38 native libraries**, 16 KiB ELF and APK alignment. The package gate independently verifies signatures, dependency closure, receipt identities, source/UI equality and absence of model assets. Lint currently has zero errors and 16 retained warnings.

## Media, evidence and packaging

```powershell
node tools/capture_workbench.cjs community
node tools/capture_workbench.cjs release-workbench
node tools/capture_workbench.cjs expansion
node tools/capture_workbench.cjs multiview
python tools/release_scope.py
python tools/program_evidence.py --export
python tools/package_delivery.py
python tools/check_repository.py
python tools/prepare_release.py
```

Four explicitly labelled desktop UI captures produce 20 screenshots, four GIFs and four MP4s. `verification/program/` contains current evidence; v0.3.2's 34 original records and three recordings are archived. The original frozen scope and the separate unported benchmark architectures are checked independently. No visual/phone/endurance claim is manufactured from program counts.

Outputs: `dist/LMA-0.3.3-arm64-v8a.apk`, build/validation/source manifests, source/verification/screenshots ZIPs and version-specific release assets. These are ignored by Git; publish attachments through the authorized release workflow. After source/doc changes, repackage before publishing. After publication, use `check_repository.py --published` to check the immutable tag/source archive; never overwrite old assets.

## Signing and private files

Preserve the existing project-local RSA3072 identity in ignored `signing/` for upgrades. A fresh clone creates a different identity unless you privately supply the original; it cannot overwrite the distributed installation with a different signer. Never commit/print keys or passwords. Model weights, voices, tokenizers, dictionaries, caches and personal browser profiles stay outside Git/source ZIP/APK.

`license.js`, `foundation.js` and upstream `*.header.json` are protected hash/copy-only inputs; do not inspect, dump or stage them. Repository/archive checks hash them without content inspection. User models and settings are independent from foundation updates. See [contribution rules](../CONTRIBUTING.md) and [numbered current scope](IMPLEMENTATION_V033.en.md).
