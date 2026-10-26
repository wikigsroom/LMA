# Build and verification

[中文](BUILD.md) · [Documentation](README.md)

## Verified toolchain

Use native Windows JDK 21 (`java`, `javac`, `keytool` on PATH), Python 3, Android SDK Platform 35, and Build Tools 35.0.1. Standalone Lint additionally needs SDK Command-line Tools. The builder explicitly invokes Windows `.exe` tools; Linux and macOS are unverified. No Docker, WSL, virtual machine, or emulator is used.

UI checks need Node.js, Playwright, and Edge / Chromium. Recording additionally needs FFmpeg / FFprobe and Playwright's FFmpeg component (`npx playwright install ffmpeg`). Keep dependencies in the project or the user's selected dependency location; never commit them.

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
python tools/bootstrap_runtime.py
python tools/build.py --sdk C:/path/to/Android/Sdk
```

Without `--sdk`, the builder checks `ANDROID_SDK_ROOT`, then the current user's default LocalAppData Android SDK. It does not install SDK packages. Android Studio / Gradle files are included for development, but the standard Gradle path was not validated and no Gradle wrapper is included.

## Runtime and catalogue

The bootstrap fetches the pinned ServLlama 1.2.2 ARM64 bundle, checks SHA256 `551e5be8494bd2ae9955992faaaca1a4f5cf29e3a97f90d2e04205eb460fcde6`, and extracts 14 CPU libraries to `app/src/main/jniLibs/arm64-v8a/`. Optional OpenCL / Hexagon components are excluded. Native binaries/cache are ignored by Git. The dedicated Release source ZIP includes the checked libraries. ARM native compilation happens upstream, not locally.

`build_catalogue.py` gates all built-in entries on matching publisher evidence, pinned GGUF revision, and weight hash. Ordinary rebuilds reuse checked evidence without visiting every model card again. Catalogue additions or provenance changes require the related audits and review of attribution, not merely a renamed entry.

That gate protects preserved curated/verified labels, rather than general HF eligibility. Recommended stays `m08 → m06 → m01`; native HubClient / HubCatalog feed ordinary HF file selections into Store / Downloads, with every source managed in Local. After backend compilation, `test_hub.py --live` runs 45 HF logic checks plus 5 public API checks through HF Mirror, without full weights or private-account access. Omit `--live` for offline fixture checks; release packaging still requires current live evidence.

`build.py` runs AAPT2, javac, D8, native-library packaging, zipalign, signing, and signature inspection. Verification uses exact-byte SHA256 inputs; `.gitattributes` disables line-ending rewriting to preserve fingerprints across checkout.

## Signing and outputs

The first build creates an RSA3072 identity and random password in `signing/`. Preserve it privately for in-place upgrades. Never commit, share, or upload it. A fresh clone signs with a different identity and cannot update the distributed APK unless it uses the original key. Uninstalling removes private models and history.

- `dist/LMA-0.2.0-arm64-v8a.apk`: signed application.
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
