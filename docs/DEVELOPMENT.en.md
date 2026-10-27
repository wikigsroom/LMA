# v0.3.0 development status and evidence

[中文](DEVELOPMENT.md) · [Full scope](MULTIMODAL_RELEASE_PLAN.en.md) · [Build](BUILD.en.md) · [English home](../README.en.md)

The current public release remains **v0.2.0**. This branch is **0.3.0-dev / versionCode 5**, not the complete v0.3.0, and has no new Release. All F-01–F-12 requirements, selections 01–14/16/17 and frozen subtargets still belong to one delivery. This is implementation progress within that release, not a split roadmap.

## Implemented development code

| Area | Current behavior | Evidence boundary |
| --- | --- | --- |
| Bundles/components | `lma.model-bundle/1`, fixed revisions/sizes/SHA256, shared content objects, atomic installation, pause/resume, explicit folder import, deletion/reference protection | Byte fixtures and real host HTTP transfers, not model inference |
| User control | Declaration, browsing and planning create no transfers; downloads require a separate action; missing assets fail locally; interrupted transfers pause for manual resumption | Does not install the entire catalogue or implicitly download models |
| Settings | Per-bundle settings, editable presets, numerical clamping, joint shape checks and immutable submitted snapshots | Recipe limits and device budgets are separate; unknown maxima are not verified |
| UI | Legacy text and bundles share a flat list; text/image/video/audio filters, bundle details, task forms, queue and artifacts; Recommended stays m08 → m06 → m01 | All contains one pinned SD1.5 Q4_0 candidate; custom manifests enter through Add model; the HF multi-component recipe picker is unfinished |
| Jobs/artifacts | One heavy job, submit/cancel/retry, persistent events, private results, hashes/provenance, system export and image/WAV/MP4 inspection/ranged preview | Bounded AtomicFile JSON currently stores these records; existing chat SQLite remains; legacy text is not fully unified yet |
| Android execution | Signed-in sd.cpp ARM64 CPU worker, data-only model bundles, external user-supplied vocabularies, child lifetime bound to its host | Compiled/packaged, **no phone inference**; upstream architectures do not prove accepted recipes |
| Video path | Generated raw frames feed Android MediaCodec/MediaMuxer; repeated still images cannot masquerade as motion output | Native generation and Android encoding still need physical-device validation; no LMA video output evidence |
| Background | Foreground ownership of transfers/jobs, process cancellation, interrupted-state reconciliation without invented checkpoints, two-hour job protection limit | Screen-off, memory pressure, OEM power policies, thermals and reboot behavior remain unmeasured |

The APK contains foundation code, engines, catalogue/tag/recipe metadata and notices, **without weights or model-specific vocabulary/tokenizer/voice/language assets**. [vocab_external.cpp](../native/vocab_external.cpp) replaces upstream embedded vocabularies. Zero-model startup is valid. The user sees the complete selected components, total size and reusable assets before downloading. App updates preserve existing models/settings and do not silently replace weights.

Custom manifests gain neither device-validated status nor checked uncensored declarations. Trying an unmeasured recipe requires an explicit user choice and may still fail locally on resources/operators/components. Media jobs currently require stopping the legacy text service first; automatic coordination and the unified text adapter remain work for this release.

## Current development evidence

[verification/development](../verification/development/status.json) keeps this evidence separate from historical v0.2.0 records. **These checks do not satisfy complete release acceptance.**

| Check | Result | What it establishes |
| --- | --- | --- |
| Foundation core | 85 assertions | Component integrity, real HTTP resumption, shared references, independent settings, queue ownership/cancellation/restart, artifacts and ranged reads |
| Legacy text backend | 85 assertions | Host Android adapters exercising downloads, actual child processes, HTTP SSE and per-model settings |
| HF logic | 45 assertions | Search, pinned revisions, pagination/selection and token boundaries, not universal HF execution |
| UI | 81 assertions | Actual HTML/CSS/JS with explicit simulated native state; recommendation/tag/download/form/queue/narrow-screen regressions |
| Native package | 15 ARM64 files | Pinned hashes, resolved dependencies, Android API 28, 16 KiB ELF/APK alignment, original signing identity, asset allowlist |
| Phone inference/endurance | 0 | No actual image/audio/motion-video or sustained screen-off inference evidence |

sd.cpp is pinned to `be486498eadc29dc3cd234d944c2180ed42b1415`, ggml to `a5915eb0e47adef21c3f25b889a008925ea838c2`, built using project-local NDK 30.0.16248370 on native Windows. The added worker SHA256 is `2a84b898dfd61596c73096ec37c83c9a28127070c395ec4dad4779a242733e9c`. See [engine-lock.json](../third_party/engine-lock.json) for hashes/notices. Only actual compiled modules are registered, without empty providers counted as support.

The SD1.5 candidate combines [Second State’s pinned GGUF](https://huggingface.co/second-state/stable-diffusion-v1-5-GGUF/tree/031b5f5df991f511b3f5fa8fed6d99048ababb69) and the [original CLIP merges](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/blob/451f4fe16113bff5a5d2269ed5ad43b0592e9a14/tokenizer/merges.txt), totaling 1,567,293,035 bytes under the source CreativeML Open RAIL-M terms. Only metadata, publisher hashes and the small vocabulary were checked, without downloading weights. The vocabulary exactly matches the pinned engine’s original data. Recipe metadata ships with the App; user-selected assets do not. An unselected catalogue candidate is not a downloaded Local model. This is not accepted execution support; see [bundle-evidence.json](../catalogue/bundle-evidence.json).

## Remaining work in the same release

1. Fully unify legacy text/HF/import records with bundles, capability routing and scheduling; implement HF multi-component recipes and independent model updates.
2. Complete pinned assets, actual engines/pipelines and every subtarget for 01–14/16/17, including both SD1.5/SDXL LoRA pairings, MNN, TTS/audio, full MOSS/SoulX and older LTX Android ports. Compiling sd.cpp does not complete these targets.
3. Add authenticated async jobs/events/artifacts APIs while preserving the text API. UI jobs currently use the native bridge; `/v1/jobs` is unavailable.
4. Finish measured admission profiles, thermals, input-artifact references, stage/checkpoint capability handling, cross-modality load/unload and upgrade migration verification.
5. Obtain physical-Android offline outputs for new inputs on every frozen subtarget, quality/cancellation/cleanup checks, A7 fifteen-minute screen-off tasks and one-hour alternating service evidence. No device is available.
6. Pass all A1–A11/R-01–R-05 gates and produce complete source/APK/docs/actual feature media/Release. Development builds cannot substitute for delivery; publishing tools reject `-dev`.

## Development UI media

Every frame carries “UI FIXTURE · not a physical device · not model output”. Transfer, installation and sampling states are fixtures, with no model-weight downloads or generated artifacts.

<img src="media/development/02-local-tags.png" width="280" alt="Flat Local models and independent tags, UI fixture" /> <img src="media/development/06-queue-results.png" width="280" alt="Queue and result library, simulated state" />

[Video](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif) · [Media hashes/provenance](media/development/manifest.json)

Browser pages, contexts and processes close in `finally`. No Docker, WSL, virtual machine or Android emulator is used.
