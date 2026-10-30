# LMA · Local model workbench for Android

[中文](README.md) · [Download v0.3.0](https://github.com/wikigsroom/LMA/releases/tag/v0.3.0) · [User guide](docs/USER_GUIDE.en.md) · [Documentation](docs/README.md)

LMA lets users select, download, manage and run local models on an Android phone, with chat, multimodal jobs, artifacts and a local API. App updates deliver the foundation. Users explicitly choose every model and dependency. The APK contains no model weights and requires no ROOT, Termux, containers or other computing devices.

**v0.3.0 implements the frozen program scope: F-01–F-12, existing text and selections 01–14, 16 and 17. Validation is program-only, as requested by the user.** Builds, packages, native contracts, production job logic, APIs and UI checks do not establish phone inference, image/audio quality, speed or screen-off endurance. Those remain untested. A catalogue entry does not establish that a Nubia Z20 can run it.

## Install and use

1. Download `LMA-0.3.0-arm64-v8a.apk` from the Release and compare its hash with `SHA256SUMS`. Requires **64-bit Android 9 / API 28 or later**. The original signing identity is retained for upgrades and existing data.
2. Open LMA and allow notifications when prompted. For screen-off work, allow background activity and remove the relevant battery restrictions in Android settings. Installation and upgrades do not download models.
3. Open Models → Recommended / All / Local. **Recommended retains m08 → m06 → m01.** All supports HF keywords, repository IDs/URLs, pagination and discovery of every format. Local manages downloaded/imported models and unfinished transfers.
4. Filter by text, image, video or audio tags. Inspect architecture, recipe, backend, license, dependencies, pinned revision and size before explicitly downloading or importing with Android's document picker.
5. Open a model's settings in Local. Editable preset inputs save independently per model; excessive values clamp to the applicable model, recipe or application bound. Temporary job overrides preserve saved defaults.
6. Load a text model for chat or copy the local API address. For other models, choose Use, fill the capability-specific form, attach compatible references, review preflight and submit to the shared queue.
7. Inspect progress, cancel or explicitly retry from Tasks. Preview/export artifacts with parameters, seed, provenance and hashes, or restore them as a new editable request. Drafts are stored independently.

HF discovery and executable support are separate. Compatible files enter their matching text engine or multi-component recipe; arbitrary safetensors, GGUF or Diffusers repositories are not universally executable. Custom components can be registered through recipes. Missing components fail locally without implicit downloads or off-device execution.

## Model and foundation scope

Every model is a peer, classified by output task, capability, engine, format, component, backend, license and installation tags. Uncensored / Abliterated is an independent label. Checked publisher declarations and unverified metadata hints are distinguished; neither implies measured refusal rates.

| Selection | Model / option | Local program route and boundary |
| --- | --- | --- |
| Existing | Text GGUF | llama.cpp, chat, SSE and per-model context/output constraints |
| 01, 02, 05 | SD 1.5, SDXL and both LoRA families | sd.cpp; base models and LoRAs are independently managed and matched |
| 03 | SD-Turbo, LCM checkpoint, LCM-LoRA | Dedicated sampling profiles; SD1.5/SDXL LCM-LoRA; explicit preparation and association where needed |
| 04 | Sana-Sprint 0.6B and separate Sana Edit | MNN with matching encoders, converted graphs and sampling rules; variants remain distinct |
| 06–08 | Z-Image-Turbo, FLUX.2-klein-4B, Qwen-Image-2.1 | Native sd.cpp multi-component routes with separate encoders, VAE and tokenizers |
| 09 | MOSS-TTS-Nano 100M | Local ORT, tokenizer and audio codec |
| 10 | Kokoro-82M / Piper / Matcha | sherpa-onnx; 54 Kokoro voices, pinned Piper Lessac / Matcha LJSpeech options |
| 11 | Qwen3-TTS 0.6B Base | Native GGML, reference audio and local codec |
| 12 | All nine frozen MOSS targets | TTS 1.0/1.5, original Local/1.5, TTSD, VoiceGenerator, original SoundEffect/v2 and Realtime; architecture-specific OpenMOSS, delay or RQ adapters |
| 13, 14 | SoulX-Podcast 1.7B, Stable Audio Open Small | Local language/acoustic/codec and audio sampling stages |
| 16 | Wan 2.1 T2V 1.3B Q4 | sd.cpp CPU/Vulkan with explicit components and video encoding |
| 17 | LTX-Video 2B 0.9.8 distilled | Original PixArt T5 F32 with 7-step generation / spatial upsampling / 3-step refinement; Google T5 Q5 single-scale remains a separate variant |

This release has **38 data-only recipe templates, 23 catalogue bundles, 12 extension engine families and the existing text engine**. These are program integration counts, not counts of models passing phone tests. See the [implementation matrix](docs/IMPLEMENTATION_V030.en.md).

## Architecture and asset lifecycle

Bundles pin revisions, paths, sizes and SHA256 values for weights, encoders, VAE, codecs, tokenizer and voice resources. Management includes pause/resume, atomic installation, shared-reference protection, explicit updates, import and deletion. Running tasks lease their input assets. Some architectures require explicit preparation of user-owned source files with programs signed into the APK, followed by runtime association. Downloaded code and arbitrary user scripts are never executed.

Versioned internal adapters implement loading, stage progress, cancellation, errors and unloading. Resource admission and the common scheduler default to one large inference task at a time. Jobs freeze model identity, parameters and inputs. Artifacts are staged, validated and committed; interruption recovery reconciles existing results. A stage resumes only with a real checkpoint; otherwise the user explicitly retries it. There is no ComfyUI wiring, infinite canvas, public node system or plugin marketplace.

Original LTX multiscale runs CPU T5 → initial Vulkan sampling → CPU learned upsampling/AdaIN → Vulkan refinement → CPU VAE → local AVC. The two original T5 shards occupy about **17.74 GiB**, and the entire runtime bundle about **23.86 GiB**. This is not a Z20 suitability claim. The APK carries only upsampler structure; all 72 learned tensors reference separately acquired user assets. [Identity, settings and stages](docs/LTX_MULTISCALE.en.md).

## Local API and background operation

Default base URL: `http://127.0.0.1:8080/v1`, authenticated with the local API key shown in LMA. Existing `/models`, `/chat/completions` and SSE remain available. Multimodal work uses asynchronous `/jobs`, preflight, events, cancellation and authenticated artifact endpoints. UI and API share scheduling and validation. See the [API guide](docs/API.en.md). Optional LAN exposure still performs computation on this phone; LMA has no external inference provider.

A visible foreground service, stop notification and task-scoped wake locks support continued work after leaving the UI. Force-stop, vendor battery management, thermal pressure and memory limits can still terminate work. Recovery code is not evidence of prolonged screen-off operation on a Z20. Model licenses, storage requirements and runtime memory budgets are separate; LMA does not silently substitute a model.

## Screenshots and recordings

These show **v0.3.0 production pages with an explicitly labelled desktop bridge fixture**, without weight downloads or generated model content. Owned browsers close after recording.

![Components, independent settings and video jobs](docs/media/development/ltx-official/ltx-official-ui.gif)

[MP4](docs/media/development/ltx-official/ltx-official-ui.mp4) · [Components](docs/media/development/ltx-official/01-ltx-official-components.png) · [Settings](docs/media/development/ltx-official/02-ltx-official-settings.png) · [Task form](docs/media/development/ltx-official/03-ltx-official-task.png) · [Queue](docs/media/development/ltx-official/04-ltx-official-queue.png) · [Workbench recording](docs/media/development/release-workbench/release-workbench-ui.mp4)

## Validation, builds and documentation

[Release notes](docs/releases/v0.3.0.md) list program checks, APK identity and deliverables. The [validation policy](docs/PROGRAM_VALIDATION.en.md) records the user's decision to omit complete-model runtime acceptance. Current evidence is in [verification/program](verification/program/status.json); historical failures and earlier records retain their identity and are not current-APK model results.

Native Windows builds use JDK, Android SDK/NDK and CMake, without Docker, WSL or emulators. Local `signing/` material is preserved for upgrades and excluded from Git and release assets. [Build](docs/BUILD.en.md) · [Release workflow](docs/RELEASING.md) · [Contributing](CONTRIBUTING.md).

The [documentation index](docs/README.md) links model management, settings, tasks, background recovery, API, architecture details and historical research. LMA code is MIT; engines and user models retain their own terms. See [third-party notices](third_party/README.md).
