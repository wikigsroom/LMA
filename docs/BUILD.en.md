# Build and program verification · v1.2.2

For v1.2.2, also run `python tools/build_llama_chat_runtime.py --jobs 4`. It rebuilds only `libllama-common.so` from the pinned llama.cpp b29 source and reviewed repository patch over the original ServLlama archive. It verifies the other 13 libraries remain identical, 217 actually required exports, shared dependencies and 16 KiB alignment. `runtime-lock.json` distinguishes the original archive from the locally modified library. Repeat this step after bootstrapping; packaging rejects an unpatched or stale runtime. No model weights are downloaded or modified.

**Current: v1.2.2 / code71, preserving the complete engine scope.** Prepare every enabled engine, including the added locked-source / vision / surface steps at the end of this page. Use `tools/program_evidence.py --export` and `tools/audit_adaptations.py --require-complete`; `adaptation_evidence.py` remains historical development tooling. Model assets are user-selected and excluded from build/validation.

[中文](BUILD.md) · [Release workflow](RELEASING.md) · [Validation policy](PROGRAM_VALIDATION.en.md) · [Archived build notes](BUILD_HISTORY.en.md)

Use a **full Git clone with history**, checked out at `v1.2.2` for reproduction. Historical evidence checks intentionally read earlier immutable Git blobs. The source ZIP is for code/docs/evidence review: its manifest lists exact files, while `.git`, native binaries, model data, build dependencies and signing material are excluded. It is not a self-contained binary SDK. No trained model is required to compile or program-check the APK.

## Toolchain

Native Windows: JDK21, Python3 (this build: 3.13), Node22, Android SDK Platform35 / Build Tools35.0.1 / Command-line Tools for Lint. C++ uses MSVC and pinned NDK30.0.16248370 / CMake3.31.6. The verified path is the Python builder; no Gradle wrapper or verified Android Studio/Gradle build is claimed. No Docker, WSL, VM or emulator.

UI checks use Playwright with Edge/Chromium; recordings additionally use FFmpeg/FFprobe and Playwright's recording component. Set `LMA_PLAYWRIGHT`, `LMA_BROWSER` or `LMA_FFMPEG` if needed. Install dependencies only into ignored/task-selected folders. Browser contexts close in finally. Native builders temporarily create a free ASCII drive alias and remove only that owned alias; never replace existing mappings such as `S:`.

## Source and native dependencies

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
git checkout v1.2.2
python tools/bootstrap_runtime.py
python tools/bootstrap_native.py
python tools/build_llama_chat_runtime.py --jobs 4
python tools/fetch_native.py --transport ssh
python tools/build_native.py --jobs 4
python tools/collect_native_notices.py
```

Bootstrap downloads fixed runtime/toolchain code, not model assets. The 14 text libraries start from the pinned ServLlama archive; rebuild libllama-common.so as above and retain the other 13 libraries byte-for-byte. Other workers are compiled locally against their locked sources/dependencies. Git and the source ZIP exclude all native binaries. Before APK packaging, prepare **every enabled engine** and its receipts/notices; the package gate rejects missing/stale files instead of silently dropping capabilities.

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
python tools/test_shape.py
node tests/ui-smoke.cjs
python tools/test_template_profiles.py
node tests/mica-ui.cjs
node tests/workspace-ui.cjs
node tests/conversation-ui.cjs
python tools/workspace_evidence.py
python tools/conversation_evidence.py
python tools/mica_evidence.py
```

Without `--sdk`, use `ANDROID_SDK_ROOT` or the default LocalAppData SDK. SDK packages are not silently installed. `build.py` generates catalogue/templates, compiles resources/Java/DEX, validates native receipts, aligns/signs the APK and inspects its identity. Exact-byte fingerprints prevent stale passes; `.gitattributes` preserves line endings and raw header padding.

The runner first compiles backend production classes consumed by HF/community checks, then runs three bounded groups. Sana/LTX defaults execute small synthetic graphs and process controls, never complete trained models. The runner covers24 bounded suites; the additional native, protocol, architecture and UI suites are required by the current version-specific evidence manifest. The workspace media export must run before its Mica evidence check. Host tests use explicit Android ports, real files, sockets and children; they are not phone tests. Preserve current records and rerun only when inputs change or failures require it.

Current package: `com.lma.app`, version1.2.2/code71, ARM64, API28+/target35, **41 native libraries**, 16 KiB ELF and APK alignment. The package gate independently verifies signatures, dependency closure, receipt identities, source/UI equality and absence of model assets. Lint currently has zero errors and 17 retained warnings.

## Media, evidence and packaging

```powershell
node tools/capture_workbench.cjs community
node tools/capture_workbench.cjs release-workbench
node tools/capture_workbench.cjs expansion
node tools/capture_workbench.cjs multiview
node tools/capture_workbench.cjs shape
node tools/capture_workbench.cjs spatial
node tools/capture_workbench.cjs material
node tools/capture_workbench.cjs ultratex
node tools/capture_workbench.cjs adaptation
node tools/capture_workbench.cjs recommendations
python tools/release_scope.py
python tools/program_evidence.py --export
python tools/package_delivery.py
python tools/check_repository.py
python tools/prepare_release.py
```

Ten explicitly labelled workbench recordings plus conversation/workspace media are exported with exact file hashes. Current evidence is under `verification/releases/v1.2.2/`; previous version records and failed experiments retain their original identity. The original frozen scope and the separate unported benchmark architectures are checked independently. No visual/phone/endurance claim is manufactured from program counts.

Outputs: `dist/LMA-1.2.2-arm64-v8a.apk`, build/validation/source manifests, source/verification/screenshots ZIPs and version-specific release assets. These are ignored by Git; publish attachments through the authorized release workflow. After source/doc changes, repackage before publishing. After publication, use `check_repository.py --published` to check the immutable tag/source archive; never overwrite old assets.

## Signing and private files

Preserve the existing project-local RSA3072 identity in ignored `signing/` for upgrades. A fresh clone creates a different identity unless you privately supply the original; it cannot overwrite the distributed installation with a different signer. Never commit/print keys or passwords. Model weights, voices, tokenizers, dictionaries, caches and personal browser profiles stay outside Git/source ZIP/APK.

`license.js`, `foundation.js` and upstream `*.header.json` are protected hash/copy-only inputs; do not inspect, dump or stage them. Repository/archive checks hash them without content inspection. User models and settings are independent from foundation updates. See [contribution rules](../CONTRIBUTING.md) and [numbered current scope](IMPLEMENTATION_V035.en.md).

## RF Shape source / 本地形状源码

```powershell
python tools/fetch_shape_sources.py --fetch
python tools/build_shape.py
python tools/build_shape.py --android
python tools/collect_expansion_notices.py
```

复用已经按 SoulX / sherpa 锁构建的 ORT 头、JSON、MV 的 stb 及 Android `libonnxruntime.so`；全部输入固定核对，API28 / 16 KiB / 禁网络进程接口检查。Host build uses MSVC; Android uses the pinned native NDK. All model conversion is a separate user asset operation; see [中文](RF_SHAPE.md) / [English](RF_SHAPE.en.md). Never invoke the exporter as a validation prerequisite with complete trained weights.

## Spatial CPU / Hunyuan shape / UltraShape

[中文方案](SPATIAL_SHAPE.md) · [English workflow](SPATIAL_SHAPE.en.md)

```powershell
python tools/fetch_spatial_sources.py
python tools/build_spatial.py
python tools/build_spatial.py --android
python tools/collect_expansion_notices.py
python tools/test_spatial_shape_graphs.py
python tools/test_spatial.py
python tools/test_spatial_sparse.py
```

Only pinned code/config/license files are fetched. These checks use tiny random or synthetic graphs, not trained models. Android links ORT API17 and built-in CPU custom operations; no downloaded native plugins. 仅获取源码，先构建 host / Android 并收集许可后打包；41 native libraries, 62 templates / 82 bundles / 18 extensions plus text. Source lock, sidecars, input budgets and process cleanup are checked. 九组当前页面录制：community / release-workbench / expansion / multiview / shape / spatial / material / ultratex / adaptation，全部 finally 关闭浏览器。

## v0.3.6 adapters / 完整适配新增依赖

Source-review helpers require an authenticated GitHub CLI at `build/github-cli/gh.exe`; install the official Windows CLI and copy its executable there if that cache is absent. 本地源码检查工具还需准备其文档声明的 PyTorch / ONNX / tokenizer 等程序依赖；只安装程序包，不取得完整模型。

The baseline engine table above remains required. 下列仅为追加引擎，不是替代上方全部引擎的简化构建。These commands fetch pinned code/config/licenses only, never weights, tokenizers, voices or model tables. 按 [适配方案](ADAPTER_PROFILES.md) / [profiles](ADAPTER_PROFILES.en.md) 为导出工具单独准备其 Python 依赖；不运行完整权重验证。

```powershell
python tools/fetch_f5_sources.py
python tools/fetch_paint_sources.py
python tools/fetch_shape_sources.py --fetch
python tools/fetch_spatial_sources.py
python tools/fetch_surface_sources.py --fetch
python tools/fetch_fdg_sources.py --fetch
python tools/fetch_depth_sources.py
python tools/fetch_vision_sources.py --fetch
python tools/lock_portable_sources.py
python tools/build_shape.py --android
python tools/build_spatial.py --android
python tools/build_vision.py --android
python tools/collect_expansion_notices.py
python tools/build_recipe_templates.py
python tools/build.py --sdk C:/path/to/Android/Sdk
python tools/verify_package.py
python tools/test_android_lint.py
```

Source preparation is sequential; generated FDG / surface sources are prepared by the locked builders. 源码准备按顺序执行，必要的 FDG / surface 生成补丁由固定构建器处理。Host program tests additionally build the matching Windows workers (omit `--android` for shape/spatial/vision); they use the existing Windows C++ toolchain. Never use Docker, WSL, VMs or emulators.

All 59 current suites, source receipts and native build records are linked in [v0.3.6 implementation](IMPLEMENTATION_V036.en.md#program-checks). 精确的测试输入与结果见 [当前状态](../verification/releases/v0.3.6/status.json)。先运行受影响套件，完成九组页面录制，再执行完整审计、证据导出和打包；不可仅运行旧基线测试就复用新版本通过状态。Original-signer upgrade builds require the existing private local key; fresh clones use their own signer and cannot replace an installation signed differently.

The bundled DISO CPU component is **CC BY-NC 4.0**. [完整许可 / notices](../THIRD_PARTY_NOTICES.md). The source ZIP contains code, docs and program evidence, not the native binaries, toolchain or user model files.
