# LMA · Uncensored models on Android

[中文](README.md) · [English](README.en.md) · [Releases](https://github.com/wikigsroom/LMA/releases) · [Documentation](docs/README.md) · [Changelog](CHANGELOG.md)

**Choose an uncensored small model, download it, chat locally, and serve an OpenAI-compatible API from an Android phone.**

LMA (Local Model App) brings a desktop model-workbench workflow into one APK: model selection, downloads, local chat, and an API server. It requires no ROOT, Termux, or separate server. This is an independent community project, unaffiliated with LM Studio. The application UI is currently primarily Chinese; the documentation is bilingual.

| Version | Platform | Backend | License | Stage |
| --- | --- | --- | --- | --- |
| **0.1.2 / versionCode 3** | Android 9+, ARM64 | llama.cpp, CPU | MIT for LMA code | Prerelease; physical-device acceptance pending |

> **Validation status:** A signed APK is available, with 115 desktop assertions and separate APK, native-library, and Android Lint checks. No physical Android device was available. Installation, actual model inference, tokens/s, and screen-off endurance have **not** been tested. Images and recordings use the shipped UI with explicitly simulated native state; they are **not phone inference recordings**. See [validation](docs/VALIDATION.en.md).

<p>
  <img src="docs/media/01-library.png" width="260" alt="Uncensored model library; UI demonstration data">
  <img src="docs/media/05-api.png" width="260" alt="OpenAI-compatible API; UI demonstration data">
  <img src="docs/media/07-dark.png" width="260" alt="Dark theme; UI demonstration data">
</p>

## Download and start

Download `LMA-0.1.2-arm64-v8a.apk` from the [v0.1.2 Release](https://github.com/wikigsroom/LMA/releases/tag/v0.1.2). The APK is about 10.9 MB and contains no model weights. Installation and runtime storage require additional space.

1. Install the APK, allow the installation source if Android asks, and open LMA.
2. In **模型库 / Model library**, select a model and tap **下载 / Download**. Start with `Dolphin 3 · Qwen 0.5B Uncensored` (`m01`, about 398 MB) to check the full flow.
3. Wait for GGUF, length, and publisher SHA256 verification, then tap **加载 / Load**. By default, the first completed download loads automatically if no model was previously selected.
4. Open **对话 / Chat** to send a message, or **服务 / Server** to copy the endpoint, key, and connection example.
5. For background serving, allow foreground-service notifications and open Android battery settings from the Server page. Vendor settings may also require background network, autostart, and unrestricted background activity.
6. After leaving the app or turning off the screen, a native foreground service owns downloads and inference. **停止服务 / Stop service** in its notification stops the model and current download. Work can be resumed later in LMA.

The first download needs networking; inference with downloaded weights runs locally. No LMA login or cloud inference API is required.

### Verify the package

```text
File: LMA-0.1.2-arm64-v8a.apk
SHA256: e9e3b7103f5e63c86953acdb986387f73cae9e3fb42851f6af1b9fffe6c1cc28
Package: com.lma.app / versionCode 3
Signing certificate SHA256: 90444a717a55549e2094364d8d7d005cf8b7f4df24562da62cc1884a2f341c17
```

On Windows, run `Get-FileHash .\LMA-0.1.2-arm64-v8a.apk -Algorithm SHA256`. Release assets include hashes, the dedicated source ZIP, validation JSON, and the walkthrough video. Updates must use the same signing identity; personal builds have their own key.

## Features and workflow

| Page | Actions | State and lifecycle |
| --- | --- | --- |
| Model library | Recommended / lightweight / advanced / installed / all filters, search, publisher evidence, download, pause, resume, load, delete | Download completion and model readiness are separate; chat and API share one loaded model |
| Chat | Streaming, stop generation, reasoning disclosure, code copy, SQLite history, new / previous sessions | A native thread reads SSE and persists received text roughly every 160ms; reopening restores it |
| Server | Start/stop, LAN switch, endpoint / key / curl copy, battery settings, log export | Localhost by default; LAN access is user-enabled and requires an API key |
| Settings | Source, first-download auto-load, optional boot restore, threads / context / output / temperature / port / reasoning, system prompt and theme | Runtime changes reload an active model; saving waits for a matching native acknowledgement |

One model and one inference slot are used. Switching models reloads the engine; stop a running model before deleting its file. **Stop generation** cancels one reply; the notification's **Stop service** stops background work.

## Uncensored model policy

The built-in library contains **only publisher-declared Uncensored / Abliterated weight variants**. This includes publisher-described Dolphin instruction tuning, refusal-direction ablation, and explicit uncensored weights. Ordinary base models are not relabeled, and a system prompt is not used as a substitute for modified weights.

- All 14 candidates have checked author cards, GGUF attribution, pinned commits, exact sizes, and publisher SHA256.
- The catalogue build checks the evidence against the actual weight repository, revision, and hash. Missing evidence stops the build.
- Model details expose the method and pinned author-card link.
- User-added URLs and imported GGUFs display **属性未核对 / Unverified attribute** rather than built-in verification.
- LMA adds no keyword blocklist, prompt classifier, cloud moderation, or response-content filter to its production chat path. The system prompt is editable or may be empty. Format, size, resource, and API authentication checks still apply.

Publisher declarations do not guarantee zero refusals. **Refusal rates have not been independently measured; these models have not been run on Android by this project.** See [models and pinned evidence](docs/UNCENSORED_MODELS.en.md) and the [structured audit](catalogue/uncensored-evidence.json).

### Built-in candidates

All selected weights are `Q4_K_M` GGUF. These approximate decimal download sizes are **not RAM requirements**. Exact bytes, hashes, filenames, and revisions are in [models.json](app/src/main/assets/models.json).

| ID | Model | Download | Role |
| --- | --- | ---: | --- |
| `m01` | Dolphin 3 · Qwen 0.5B Uncensored | 398 MB | Smallest initial candidate |
| `m04` | Dolphin 3 · Llama 1B Uncensored | 808 MB | Lightweight, English |
| `m05` | Gemma 3 · 1B Abliterated | 806 MB | Lightweight, multilingual |
| `m06` | LFM 2.5 · 1.2B Uncensored | 731 MB | Recommended candidate |
| `m08` | Qwen 3 · 1.7B Abliterated | 1.11 GB | Recommended Chinese candidate |
| `m10` | LFM 2.5 · 2.6B Uncensored | 1.67 GB | Advanced, reasoning model |
| `m11` | Dolphin 3 · Qwen 3B Uncensored | 1.93 GB | Advanced, Chinese |
| `m12` | Dolphin 3 · Llama 3B Uncensored | 2.02 GB | Advanced, English |
| `m13` | Llama 3.2 · 3B Uncensored | 2.24 GB | Advanced, English |
| `m14` | Qwen 3 · 4B Instruct 2507 Abliterated | 2.50 GB | Advanced, Chinese |
| `m16` | Gemma 3 · 4B Abliterated v2 | 2.49 GB | Advanced, multilingual |
| `m03` | Qwen 3.5 · 0.8B Abliterated | 528 MB | Experimental architecture candidate |
| `m09` | Qwen 3.5 · 2B Abliterated | 1.27 GB | Experimental architecture candidate |
| `m15` | Qwen 3.5 · 4B Uncensored · HauhauCS Aggressive | 2.71 GB | Experimental architecture candidate |

### nubia Z20 and older phones

The APK targets **ARM64 Android 9+**, with an ARMv8.0 CPU baseline and optimized kernels selected at runtime. A starting configuration for Snapdragon 855+-class devices is **4 threads / 2048-token context / 512 output tokens / reasoning off / temperature 0.7**. Try `m01` first, then compare `m06` and `m08`. Use 3B–4B only after observing actual free memory, temperature, and sustained speed.

This configuration awaits device testing. **No Z20 throughput, peak-memory, thermal, or battery measurements exist.** RAM includes KV cache, working buffers, and Android overhead. If loading fails, close large apps, reduce context to 1024 / 512, and use a smaller model. Downloadability does not establish successful phone inference.

## Architecture and background serving

```mermaid
flowchart TD
  UI[Local WebView: library / chat / server / settings] -->|JSON commands and snapshots| FGS[Native Android foreground service]
  FGS --> DL[HTTPS download / resume / SHA256 / SAF import]
  FGS --> ENGINE[Separate ARM64 llama-server process]
  FGS --> CHAT[Native ChatRunner / SSE / SQLite]
  CHAT -->|Loopback HTTP| ENGINE
  CLIENT[Local or LAN client] -->|Bearer API key| ENGINE
```

The UI handles interaction; native code owns transfers, SSE consumption, and the engine lifecycle. A `specialUse` foreground service shows a notification and stop action and holds CPU / Wi-Fi locks. An API-serving model keeps the service active while idle; no-work state releases resources.

`ProcessBuilder` starts the packaged native executable from the APK's native-library directory without ROOT or shell. Readiness requires `/health` and authenticated `/v1/models` with the expected alias; unexpected exits are retried at most three times. Boot restore is off by default and only attempts a previously enabled, still-present model when enabled.

**Background streaming means SSE can continue during an active generation request.** EOS, output limits, and cancellation still end a request. An ordinary Android application cannot guarantee permanent survival through force-stop, low memory, heat, or vendor power policies. First-run downloads, notification consent, and system battery settings are not silently bypassed.

The [architecture](docs/ARCHITECTURE.en.md) documents download states, process recovery, conversation persistence, and network boundaries.

## API integration

Default Base URL: `http://127.0.0.1:8080/v1`. For another device, enable LAN access and use the phone's displayed address. Each installation generates a random API key. The in-app copy example fills the endpoint, model ID, and actual key.

```bash
curl http://PHONE_IP:8080/v1/models \
  -H "Authorization: Bearer YOUR_LMA_API_KEY"

curl -N http://PHONE_IP:8080/v1/chat/completions \
  -H "Authorization: Bearer YOUR_LMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"m08","messages":[{"role":"user","content":"Hello"}],"max_tokens":256,"stream":true}'
```

Replace `m08` with the ID returned by `/v1/models`. The documented surface is models, chat completions, and SSE, not every OpenAI endpoint. LAN uses HTTP; TLS and public tunneling are not built in. External clients send their own system messages and parameters; in-app settings primarily control in-app chat. See the [API guide](docs/API.en.md) for Python / PowerShell, stream parsing, and errors.

## Downloads and local data

Automatic selection tries Hugging Face and falls back to HF Mirror on connection or source-status failure; fixed sources are available. Only HTTPS and HTTPS redirects are accepted. Other custom hosts are not rewritten to the mirror.

Transfers run serially, validating `Content-Range`, length, GGUF magic, and known publisher SHA256. Hash failures are isolated as `.rejected`. A 12 GiB file limit and 64 MiB free-space reserve apply. Android's system file picker supports streamed GGUF import, without reading an entire model into Java memory.

Weights, progress, and SQLite history live in private app storage; uninstalling deletes them. Offline UI assets use no remote scripts or fonts. Log export redacts the current API key and excludes the chat database. Downloads contact the selected host; LAN clients can request inference only after LAN is enabled and they supply the key.

## Screenshots, recording, and GIFs

<p><img src="docs/media/lma-walkthrough.gif" width="320" alt="LMA UI walkthrough with explicitly simulated native state"></p>

The media uses **the HTML / CSS / JavaScript shipped in the APK**, driven by an explicit demonstration bridge. A UI DEMO banner is always visible. Downloads are simulated, chat is scripted, and IP / API key values are placeholders. No Android runtime or model executes.

[Full MP4 recording](docs/media/lma-walkthrough.mp4) · [API / theme GIF](docs/media/lma-api-theme.gif) · [Seven screenshots and reproduction](docs/MEDIA.md) · [Media hashes and provenance](docs/media/manifest.json).

## Build from source

The verified path is **native Windows JDK 21, Python 3, Android SDK Platform 35 and Build Tools 35.0.1**. It uses no Gradle dependency downloads, NDK, Docker, WSL, or emulator. Android Studio / Gradle files are included, but that path has not been validated.

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
python tools/bootstrap_runtime.py
python tools/build.py
```

The bootstrap downloads the pinned ServLlama 1.2.2 llama.cpp v0.4.1 ARM64 CPU bundle, checks SHA256, and extracts 14 libraries. Re-fetchable binaries are excluded from Git; the dedicated Release source ZIP contains them and verification records. The builder runs catalogue admission checks, AAPT2, javac, D8, zipalign, and apksigner and writes to `dist/`. Set `--sdk` or `ANDROID_SDK_ROOT` for a different SDK.

**Preserve local `signing/` for in-place upgrades.** The first build creates a local signing identity; private keys and passwords are never published. See [build instructions](docs/BUILD.en.md).

```powershell
python tools/test_protocol.py
python tools/test_backend.py
python tools/test_sqlite.py
python tools/test_android_lint.py
node tests/ui-smoke.cjs
python tools/verify_package.py
python tools/build_acceptance.py
python tools/package_delivery.py
python tools/prepare_release.py
python tools/check_repository.py
```

UI work requires Node.js, Playwright, and Edge / Chromium. Set `LMA_PLAYWRIGHT` and `LMA_BROWSER` if necessary. Media additionally needs FFmpeg / FFprobe. Standalone Lint needs SDK Command-line Tools. All test pages and browser processes close in `finally`.

Current evidence is **54 backend + 25 protocol + 5 SQLite + 31 UI = 115 desktop assertions**, plus **Lint: 0 errors, 7 warnings**. Android framework adapters, host SQLite, and a test UI bridge are explicitly identified. Separate APK, signature, native-library, alignment, and author-evidence checks do not replace Android execution. **Physical-device checks: 0.** See [validation](docs/VALIDATION.en.md) and [`verification/`](verification/).

## Documentation and source layout

| Path | Contents |
| --- | --- |
| [Documentation index](docs/README.md) | All Chinese / English guides |
| [User guide](docs/USER_GUIDE.en.md) / [中文](docs/USER_GUIDE.md) | Installation, pages, background use, troubleshooting |
| [Architecture](docs/ARCHITECTURE.en.md) / [中文](docs/ARCHITECTURE.md) | Services, engine, downloads, chat, storage, boundaries |
| [API](docs/API.en.md) / [中文](docs/API.md) | Client integration and SSE |
| [Build](docs/BUILD.en.md) / [中文](docs/BUILD.md) | Toolchain and verification |
| [Uncensored models](docs/UNCENSORED_MODELS.en.md) / [中文](docs/UNCENSORED_MODELS.md) | Complete model / author evidence |
| [Device acceptance](docs/DEVICE_ACCEPTANCE.en.md) / [中文](docs/DEVICE_ACCEPTANCE.md) | Compiled tools awaiting a real phone |
| [`app/src/main/java/com/lma/app/`](app/src/main/java/com/lma/app/) | Production Android code |
| [`app/src/main/assets/`](app/src/main/assets/) | Offline interface, catalogue, licenses |
| [`catalogue/`](catalogue/) / [`third_party/`](third_party/) | Model evidence, runtime locks, license notices |
| [`tools/`](tools/) / [`tests/`](tests/) / [`verification/`](verification/) | Build, audit, test tooling and results |
| [Changelog](CHANGELOG.md) / [release notes](docs/releases/) | Bilingual version history |

## Future updates and licensing

Each subsequent authorized LMA update must synchronize code, both READMEs / guides, affected screenshots and GIFs, `CHANGELOG.md`, and version notes before committing and pushing to `git@github.com:wikigsroom/LMA.git`. This standing instruction is recorded in [AGENTS.md](AGENTS.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [the release procedure](docs/RELEASING.md). Do not force-push, rewrite published tags, or replace released assets with different bytes under the same filename.

`v0.1.2` is the first public repository release. Earlier 0.1.0 / 0.1.1 builds were local iterations, not historical GitHub releases. This release is marked as a prerelease while Android acceptance remains outstanding.

For post-release documentation/tool updates, `python tools/check_repository.py --published` compares the immutable source archive with its tag while checking current public files and guides. Draft releases are resolved through the authenticated list to handle GitHub's draft-by-tag 404 behavior. Maintenance notes go in the Unreleased changelog; published APKs, tags, and assets are not rewritten.

LMA code uses [MIT](LICENSE). The CPU engine is supplied by [ServLlama 1.2.2](https://github.com/ArkaneFans/servllama/releases/tag/1.2.2), from a [pinned llama.cpp revision](https://github.com/ggml-org/llama.cpp/tree/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4). Licenses and dependency notices are preserved in [third_party/](third_party/README.md). LMA's build did not run containers, WSL, or virtualized environments. Models and base models retain their publishers' licenses, and no weights are bundled in the APK or Git.
