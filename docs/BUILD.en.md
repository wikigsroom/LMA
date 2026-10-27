# Build and verification

[中文](BUILD.md) · [Documentation](README.md)

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
