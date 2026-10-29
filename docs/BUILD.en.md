# Build and verification

Internal dev.27 uses `tools/test_recovery.py` for real host process interruption, output reconciliation, persistent cleanup and authenticated HTTP. Scheduler/full UI suites cover actual capacity and confirmation. Signed APK, package checks, Lint and current fingerprints must match; see [numbered delivery](releases/v0.3.0-dev.27.md).

[中文](BUILD.md) · [Documentation](README.md)

For dev.25, use `tools/export_development.py` and `tools/check_repository.py --development`. Current business checks are fresh; historical model JSON is compared byte for byte against commit `6b1f345` in the complete Git history, without serving as current-APK inference acceptance. Full Release export does not accept a development checkpoint.

## Verified toolchain

Use native Windows JDK 21 (`java`, `javac`, `keytool` on PATH), Python 3, Android SDK Platform 35, and Build Tools 35.0.1. Standalone Lint additionally needs SDK Command-line Tools. The builder explicitly invokes Windows `.exe` tools; Linux and macOS are unverified. No Docker, WSL, virtual machine, or emulator is used.

UI checks need Node.js, Playwright, and Edge / Chromium. Recording additionally needs FFmpeg / FFprobe and Playwright's FFmpeg component (`npx playwright install ffmpeg`). Keep dependencies in the project or the user's selected dependency location; never commit them.

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
python tools/bootstrap_runtime.py
python tools/bootstrap_native.py
python tools/fetch_native.py --transport ssh
python tools/build_native.py --jobs 4
python tools/collect_native_notices.py
# Review the rebuilt engine-lock.json diff before APK packaging
python tools/build.py --sdk C:/path/to/Android/Sdk
```

Without `--sdk`, the builder checks `ANDROID_SDK_ROOT`, then the current user's default LocalAppData Android SDK. It does not install SDK packages. Android Studio / Gradle files are included for development, but the standard Gradle path was not validated and no Gradle wrapper is included.

## Runtime and catalogue

The bootstrap fetches the pinned ServLlama 1.2.2 ARM64 bundle, checks SHA256 `551e5be8494bd2ae9955992faaaca1a4f5cf29e3a97f90d2e04205eb460fcde6`, and extracts 14 CPU libraries to `app/src/main/jniLibs/arm64-v8a/`. Optional OpenCL / Hexagon components are excluded. Native binaries/cache are ignored by Git. The dedicated Release source ZIP includes the checked libraries. These 14 text-runtime files are prebuilt; the added diffusion worker is compiled locally with the Windows NDK.

`build_catalogue.py` gates all built-in entries on matching publisher evidence, pinned GGUF revision, and weight hash. Ordinary rebuilds reuse checked evidence without visiting every model card again. Catalogue additions or provenance changes require the related audits and review of attribution, not merely a renamed entry.

That gate protects preserved curated/verified labels, rather than general HF eligibility. Recommended stays `m08 → m06 → m01`; native HubClient / HubCatalog feed ordinary HF file selections into Store / Downloads, with every source managed in Local. After backend compilation, `test_hub.py --live` runs 45 HF logic checks plus 5 public API checks through HF Mirror, without full weights or private-account access. Omit `--live` for offline fixture checks; release packaging still requires current live evidence.

`build.py` runs AAPT2, javac, D8, native-library packaging, zipalign, signing, and signature inspection. Verification uses exact-byte SHA256 inputs; `.gitattributes` disables line-ending rewriting to preserve fingerprints across checkout.

## Added native worker and development builds

`bootstrap_native.py` verifies/extracts NDK 30.0.16248370 and CMake 3.31.6 into ignored `build/toolchain/`, without changing the system SDK. `fetch_native.py` gets the exact sd.cpp/ggml sources from engine-lock, without model weights. `build_native.py` uses native Windows tools; its temporary SUBST path alias works around a CMake crash on non-ASCII paths and is always removed, without virtualization. `collect_native_notices.py` captures exact notices and updates the binary lock for review before commit.

Packaging checks build receipts, native input fingerprints, the exact file set, hashes and notice bytes, then generates engine-builds.json. User-provided components replace embedded model vocabularies. Git excludes native binaries; the internal signed output is `dist/LMA-0.3.0-dev-arm64-v8a.apk`, not a complete Release.

Development checks use `test_foundation.py`, existing backend/HF/UI checks, `verify_package.py`, `test_android_lint.py`, `capture_foundation.cjs`, `export_development.py` and `check_repository.py --development`. See [DEVELOPMENT.en.md](DEVELOPMENT.en.md) for boundaries. Full delivery still requires all selected models and physical-device gates; publishing tools reject `-dev`.

## Signing and outputs

The first build creates an RSA3072 identity and random password in `signing/`. Preserve it privately for in-place upgrades. Never commit, share, or upload it. A fresh clone signs with a different identity and cannot update the distributed APK unless it uses the original key. Uninstalling removes private models and history.

- `dist/LMA-<version>-arm64-v8a.apk`: signed application for the current Manifest; internally 0.3.0-dev, with public v0.2.0 preserved.
- `dist/*.sha256`: actual artifact hashes.
- `dist/build-info.json`: package information and input fingerprints.
- `build/`: ignored compiler, test, Lint, and media intermediates.
- `verification/`: public release evidence, without signing material or device API keys.

## Checks

```powershell
python tools/test_protocol.py
python tools/test_backend.py
python tools/test_hub.py --live
python tools/test_sqlite.py
python tools/test_android_lint.py
node tests/ui-smoke.cjs
python tools/verify_package.py
python tools/build_acceptance.py
```

Backend dependencies fetch a pinned-hash org.json JAR into `build/test-deps/`. Backend checks execute production Java, real TLS, and JVM subprocesses with explicit Android framework adapters; they do not execute ARM models. SQLite runs on the host. The UI bridge is a fixture. Browser pages/processes close in `finally`.

Set `LMA_PLAYWRIGHT` to an installed Playwright module and `LMA_BROWSER` to a browser executable if necessary. Dependencies may be installed in ignored `build/ui-deps/`; use the corresponding absolute module path. Otherwise normal Node resolution finds `playwright`.

`build_acceptance.py` compiles a separate same-signed instrumentation APK. Compilation is not execution. Follow [physical-device acceptance](DEVICE_ACCEPTANCE.en.md) when a phone is available. Missing devices never trigger an emulator or successful phone flags.

## Media and delivery

```powershell
node tools/capture_media.cjs
python tools/package_delivery.py
python tools/prepare_release.py
python tools/check_repository.py
```

Recording uses local UI assets and an explicit demo bridge; FFmpeg creates MP4/GIF files. The packager checks current evidence, exports public records, and rebuilds the dedicated source ZIP including native libraries. Release preparation writes versioned assets and SHA256SUMS. Unchanged code with matching fingerprints does not require redundant test runs.

Git tracks sources, guides, media, and public evidence. `dist/` stays ignored and is uploaded as Release assets. Follow [the release procedure](RELEASING.md) for synchronization and publishing.

开发接口另运行 / Development API checks: `python tools/test_api.py`。该检查使用生产 HTTP / 路由和真实本机 socket，执行器是显式测试替身，不是手机推理。

## Development speech engine

After preparing diffusion sources and the Windows NDK, run `python tools/fetch_tts.py --transport ssh`, `python tools/build_tts.py`, then `python tools/collect_tts_notices.py`; follow with `python tools/test_tts.py` and the common APK build/checks. Bootstrap fetches pinned code and generic notices, without models. sherpa / ORT are upstream prebuilts; the LMA worker is compiled locally. See [TTS_ENGINE.en.md](TTS_ENGINE.en.md) for provenance, parameters and evidence boundaries.

## Nano native worker

After the shared ORT/sd.cpp prerequisites, run `fetch_moss_nano.py`, `build_moss_nano.py`, `collect_moss_nano_notices.py`, and `test_moss_nano.py` before the ordinary APK checks. Sources are pinned and built with native Windows tools; the native host parser check needs MSVC (`LMA_VCVARS` may select its setup script). No virtualization is used. See [full instructions](MOSS_NANO_ENGINE.en.md).

Run the added `python tools/test_text.py` for actual host children/loopback HTTP and metadata-only GGUF, without model or Android execution. Existing text runtime metadata derives from `runtime-lock.json` and `BUILD_INFO.json`, with all dependencies checked and no weights. See [text foundation](TEXT_ENGINE.en.md).

For dev.9, `python tools/test_migration.py` compiles actual Store / BundleStore / EngineHost code and checks host files, hardlinks, concurrent settings and a real protocol child in isolated `build/migration-tests/`. Dependencies/prerequisites match backend checks. Zero-tensor GGUFs test metadata only, without inference. App startup reconciliation and physical Android upgrades still need separate acceptance. See [migration](MODEL_MIGRATION.en.md).

Shared scheduling regression: after building, run `python tools/test_scheduler.py`, then `python tools/test_android_lint.py` and `python tools/verify_package.py`. The scheduler check compiles production `LocalJobs`/`EngineHost`/`ChatRunner`/`ApiHost` with explicit host Android ports, real children and literal HTTP protocols. It uses no emulator, weights or inference. `build/scheduler-tests/results.json` exports to `verification/development/scheduler.json`.

Run `python tools/test_inputs.py` for production-core/actual-file/WAV/HTTP checks. It requires the pinned host org.json and exports `build/input-tests/results.json` to `verification/development/inputs.json`. No Android/model or inference sample is involved; see [inputs](LOCAL_INPUTS.en.md).

Dev.12 diffusion / 扩散检查：`python tools/test_diffusion.py` 编译生产 Java 绑定并运行实际主机协议子进程、编译执行共用 C++ 采样 / 架构约束；不是 Android 或图像推理。Native Windows host checks are exported as `verification/development/diffusion.json`.


dev.13 rebuilds the diffusion worker: 8,836,200 bytes, SHA256 `01e6c0a37fc56bb9268d0890c71d8dae57bd0ac41922cb2ec64ad6e5e7fd1d3c`, with the same pinned sd.cpp/ggml sources, CPU, API28/16KiB alignment and original APK signing identity. [Notes](releases/v0.3.0-dev.13.md) identify the exact APK/checks, without claiming phone execution.

Build Sana MNN with the same native Windows tools: `python tools/fetch_mnn.py`, `python tools/build_mnn.py`, `python tools/collect_mnn_notices.py`, `python tools/test_mnn.py`, then the shared APK/Lint/package checks. Source/header/overlays/notices are pinned; no model is downloaded. Its 74 host/C++ checks perform no MNN inference. See [MNN Sana build and components](MNN_SANA_ENGINE.en.md).

Native Qwen speech uses the same Windows toolchain: `fetch_qwen_tts.py` → `build_qwen_tts.py` → `collect_qwen_tts_notices.py` → `test_qwen_tts.py`, all under `tools/`. CPU/API 28/16 KiB, pinned sources/notices, without automatic model downloads. Developers may explicitly run `python tools/audit_qwen_headers.py --origin https://hf-mirror.com` to review pinned headers without tensor reads. See [Qwen speech build details](QWEN_TTS_ENGINE.en.md).

## MOSS Delay native engine

See [MOSS Delay](MOSS_DELAY_ENGINE.en.md) for the pinned fork, native extraction, NDK build and notices. Run `tools/fetch_moss_delay.py`, `tools/build_moss_delay.py`, then `tools/collect_moss_delay_notices.py`; `tools/test_moss_delay.py` executes Java host contracts and the upstream native Delay self-test. All files stay in the project; these commands fetch or convert no model weights.

The [openmoss build](OPENMOSS_ENGINE.en.md#5-pinned-sources-and-build) runs fetch_openmoss.py / build_openmoss.py / collect_openmoss_notices.py before shared APK packaging. It downloads/converts no model data.

Stable Audio native build: `fetch_stable_audio.py` → `build_stable_audio.py` → `collect_stable_audio_notices.py` → `test_stable_audio.py`（`tools/`）。 Native Windows NDK, pinned official LiteRT AAR/SDK, CPU, caches under build/. Host tests also require Python flatbuffers (25.12.19 in this checkpoint), MSVC and Java; the pinned Windows DLL runs synthetic tiny graphs and stays out of the APK. See [components, commands and provenance](STABLE_AUDIO_ENGINE.en.md).


SoulX production worker: `build_soulx.py` (host) → `build_soulx.py --android` → `collect_soulx_notices.py` → `test_soulx.py` / explicitly prepared trained assets with `test_soulx_worker_trained.py` → shared APK build. Pinned llama/ggml/ORT runtimes are reused. Native Windows/NDK tools and build-local caches only; no model assets enter the App. See the [complete build/license guide](SOULX_ENGINE.en.md).

Old LTX0.9.8 research uses `tools/fetch_native.py`, `tools/fetch_ltx098.py --python-dependencies`, `tools/test_ltx098.py`, then `tools/build_ltx098.py --android --vulkan`. Native MSVC/NDK, pinned project-local shaderc/Vulkan/SPIRV headers; sequential builds release their temporary SUBST in finally. Source/tool preparation downloads no weights. See [DiT build details](LTX098_DIT.en.md).

The [trained sampling reproduction](LTX098_SAMPLING.en.md) separately requires explicit `tools/fetch_ltx098_trained.py --download`, local `tools/export_ltx098.py`, untrained/trained `tools/ltx098_sampling_oracle.py`, and `tools/test_ltx098_sampling.py --trained --skip-build`. Missing assets never trigger downloads. External checkpoints/GGUF stay outside APK; probe and sampler ARM64 ELF checks remain separate from phone acceptance and complete public asset candidates.

The [old-LTX T5 reproduction](LTX098_TEXT.en.md) explicitly prepares the quantized encoder and original external tokenizer config, then sequentially runs `tools/build_ltx098_text.py`, `tools/ltx098_text_oracle.py --trained`, `tools/test_ltx098_text.py --trained` and `tools/build_ltx098_text.py --android`. No automatic model acquisition, virtualization or APK payload is added. Dependencies/assets stay project-local. The CLI requires the separate original tokenizer config; temporary F32 matrix-buffer reuse, host evidence and Android compilation have separate scopes.


The [trained old-LTX VAE reproduction](LTX098_VAE.en.md) explicitly prepares the pinned checkpoint, then runs `tools/ltx098_vae.py export`, `references`, `tools/build_ltx098_vae.py`, its `--android` compilation and `tools/test_ltx098_vae.py`. Original publisher forwards provide independent references. Existing exports are not overwritten; no implicit model download occurs. Run native compilations sequentially; each releases only its own SUBST alias in finally. Cache/temp files remain project-local, no virtualization is used, and research executables/model graphs stay outside APK.


Follow the [real-prompt old-LTX reproduction](LTX098_PIPELINE.en.md), explicitly preparing existing pinned components/assets before sequential `tools/build_ltx098_tensors.py` / `--android` builds and primitive/pipeline checks. The pipeline suite executes three actual trained A/B/A jobs and two independent original-forward references, without automatic retrieval or virtualization/emulators. Developer MP4 uses host FFmpeg; production still requires same-phone MediaCodec. APK bytes are unchanged.

The current full pipeline check returns exit 1 and records six failed float gates among 163 checks; both RGB comparisons pass. Captured-output replay discloses reuse instead of claiming fresh inference. See [numerical failure and replay semantics](LTX098_PIPELINE.en.md).

The [old-LTX precision guide](LTX098_PRECISION.en.md) / [中文](LTX098_PRECISION.md) uses native Windows MSVC, existing pinned GGML archives and isolated source copies. No accepted encoder mutation or implicit model retrieval occurs. Counts 314 / 628 / 120 represent intermediates, files and local operators. F64 candidates do not establish Android builds or acceptance; APK version and full-chain gates remain unchanged.

For [portable old-LTX asset conversion](LTX098_PREPARE.en.md), run `tools/build_ltx098_prepare.py`, its `--android` build, then `tools/test_ltx098_prepare.py --trained`, development export, `tools/plot_ltx098_prepare.py` and development repository audit in sequence. Tests reuse explicitly acquired local developer assets without downloading. The component uses its own SHA/half conversion and the existing pinned JSON header; ARM64/API28/16KiB compilation is separate from this unchanged APK.

For [native old-VAE asset preparation](LTX098_VAE_PREPARE.en.md), audit the templates, build both preparers with native MSVC/NDK in sequence, then execute their full trained-file checks and actual VAE decoding. `tools/prepare_ltx098_vae_templates.py` is developer tooling; Android conversion needs no Python/Torch/ONNX/network. A build using the public audit fallback still validates its input and graph-output fingerprints.

## dev.22: packaging preparation programs and evidence

Build both [preparers](MODEL_PREPARATION.en.md) sequentially with native Windows/NDK tools. `tools/package_preparations.py` packages pinned programs and nine audited model-free graphs, without downloading or converting weights. `tools/preparation_build_inputs.py` extends APK fingerprints with all preparation sources/locks/contracts, leaving the unchanged generic helper used by neural-math records intact. Run `tools/build.py`, `tools/test_preparations.py`, its optional `--trained` execution using the existing pinned source, package verification/Lint/relevant regressions, development export and repository audit separately. Conversion outputs/checkpoints never enter APK or Git. The build has 77 Java compilation inputs and 29 native files; original local signing files are preserved. Android, complete video numerical/quality acceptance and complete Release remain open.


## dev.24 native incremental builds

`tools/build_native.py` reuses the existing CMake cache ASCII drive identity instead of opening a T: cache through R:. An occupied alias fails explicitly and preserves the cache. Only this workspace is mapped; the owner releases its own alias without borrowing/removing other mappings. See the [SD1.5 developer workflow](SD15_TRAINED.en.md); the Windows test executable is not packaged.
