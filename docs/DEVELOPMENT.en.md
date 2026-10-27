# v0.3.0 development status and evidence

[中文](DEVELOPMENT.md) · [Full scope](MULTIMODAL_RELEASE_PLAN.en.md) · [Build](BUILD.en.md) · [English home](../README.en.md)

The current public release remains **v0.2.0**. This branch is **0.3.0-dev.9 / versionCode 13**, not the complete v0.3.0, and has no new Release. All F-01–F-12 requirements, selections 01–14/16/17 and frozen subtargets still belong to one delivery. This is implementation progress within that release, not a split roadmap.

## Implemented development code

| Area | Current behavior | Evidence boundary |
| --- | --- | --- |
| Bundles/components | `lma.model-bundle/1` and `/2`, pinned revisions/sizes/SHA256 or Git blob identity with measured SHA256, shared content objects, atomic installation, pause/resume, explicit folder import, deletion/reference protection | Byte fixtures and real host HTTP transfers, not model inference |
| Independent model versions | User-selected pinned target, component/profile review, separate transfer/activation, retained old files, rollback, last 64 switches and queued-reference protection | 62 real host storage/failure/transfer checks; Android upgrades remain unverified; see [version guide](MODEL_UPDATES.en.md) |
| User control | Declaration, browsing and planning create no transfers; downloads require a separate action; missing assets fail locally; interrupted transfers pause for manual resumption | Does not install the entire catalogue or implicitly download models |
| Settings | Per-bundle settings, editable presets, numerical clamping, joint shape checks and immutable submitted snapshots | Recipe limits and device budgets are separate; unknown maxima are not verified |
| UI | Legacy text and bundles share a flat list; text/image/video/audio filters, bundle details, task forms, queue and artifacts; Recommended stays m08 → m06 → m01 | All contains pinned SD1.5 and three TTS candidates; custom manifests enter through Add model; dev.8 offers nine explicit HF component templates without universal architecture support |
| Jobs/artifacts | One heavy job, submit/cancel/retry, persistent events, private results, hashes/provenance, system export and image/WAV/MP4 inspection/ranged preview | Bounded AtomicFile JSON currently stores these records; existing chat SQLite remains; legacy text is not fully unified yet |
| Unified gateway | Start with zero models; authenticated model/engine/job/event/artifact Range routes; public text proxy applies profile bounds and tracks leases; native text stays on a separate loopback port/secret | Production HTTP/stores use real host sockets and explicit execution fixtures; no model downloads or inference redirects |
| Android execution | Signed-in sd.cpp ARM64 CPU worker, data-only model bundles, external user-supplied vocabularies, child lifetime bound to its host | Compiled/packaged, **no phone inference**; upstream architectures do not prove accepted recipes |
| Video path | Generated raw frames feed Android MediaCodec/MediaMuxer; repeated still images cannot masquerade as motion output | Native generation and Android encoding still need physical-device validation; no LMA video output evidence |
| Background | Foreground ownership of transfers/jobs, process cancellation, interrupted-state reconciliation without invented checkpoints, two-hour job protection limit | Screen-off, memory pressure, OEM power policies, thermals and reboot behavior remain unmeasured |

The APK contains foundation code, engines, catalogue/tag/recipe metadata and notices, **without weights or model-specific vocabulary/tokenizer/voice/language assets**. [vocab_external.cpp](../native/vocab_external.cpp) replaces upstream embedded vocabularies. Zero-model startup is valid. The user sees the complete selected components, total size and reusable assets before downloading. App updates preserve existing models/settings and do not silently replace weights.

Custom manifests gain neither device-validated status nor checked uncensored declarations. Trying an unmeasured recipe requires an explicit user choice and may still fail locally on resources/operators/components. Media jobs currently require stopping the legacy text service first; new text bundles use shared jobs, with local legacy adoption now implemented; physical upgrade acceptance and complete automatic coordination remain work for this release.

## Current development evidence

[verification/development](../verification/development/status.json) keeps this evidence separate from historical v0.2.0 records. **These checks do not satisfy complete release acceptance.**

| Check | Result | What it establishes |
| --- | --- | --- |
| Foundation core | 310 assertions | Component integrity, real HTTP resumption, shared references, independent settings, queue ownership/cancellation/restart, artifacts and ranged reads |
| API/transport | 67 assertions | Auth, zero-model state, JSON/framing limits, idempotency/cancel/events, exact artifacts/Range/leases and text policy; actual host sockets, not Android inference |
| Legacy backend/proxy | 98 assertions | Host Android adapters exercising downloads, actual child processes, HTTP SSE and per-model settings |
| HF logic | 76 assertions | Search, pinned revisions, pagination/selection and token boundaries, not universal HF execution |
| UI | 156 assertions | Actual HTML/CSS/JS with explicit simulated native state; recommendation/tag/download/form/queue/narrow-screen regressions |
| Native package | 19 ARM64 files | Pinned hashes, resolved dependencies, Android API 28, 16 KiB ELF/APK alignment, original signing identity, asset allowlist |
| Phone inference/endurance | 0 | No actual image/audio/motion-video or sustained screen-off inference evidence |

sd.cpp is pinned to `be486498eadc29dc3cd234d944c2180ed42b1415`, ggml to `a5915eb0e47adef21c3f25b889a008925ea838c2`, built using project-local NDK 30.0.16248370 on native Windows. The added worker SHA256 is `2a84b898dfd61596c73096ec37c83c9a28127070c395ec4dad4779a242733e9c`. See [engine-lock.json](../third_party/engine-lock.json) for hashes/notices. Only actual compiled modules are registered, without empty providers counted as support.

The SD1.5 candidate combines [Second State’s pinned GGUF](https://huggingface.co/second-state/stable-diffusion-v1-5-GGUF/tree/031b5f5df991f511b3f5fa8fed6d99048ababb69) and the [original CLIP merges](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/blob/451f4fe16113bff5a5d2269ed5ad43b0592e9a14/tokenizer/merges.txt), totaling 1,567,293,035 bytes under the source CreativeML Open RAIL-M terms. Only metadata, publisher hashes and the small vocabulary were checked, without downloading weights. The vocabulary exactly matches the pinned engine’s original data. Recipe metadata ships with the App; user-selected assets do not. An unselected catalogue candidate is not a downloaded Local model. This is not accepted execution support; see [bundle-evidence.json](../catalogue/bundle-evidence.json).

## Remaining work in the same release

1. Finish automatic scheduling between legacy chat/synchronous APIs and shared jobs, plus physical-Android migration/upgrade acceptance. Dev.9 implements existing complete text/HF/import GGUF adoption, shared defaults, version management and task entry points; existing version protocols and nine HF templates remain shared.
2. Complete pinned assets, actual engines/pipelines and every subtarget for 01–14/16/17, including both SD1.5/SDXL LoRA pairings, MNN, remaining audio, full MOSS/SoulX and older LTX Android ports. Some TTS paths are integrated but not device-accepted. Compiling sd.cpp does not complete these targets.
3. Extend the implemented async/text API to every engine, input-artifact reference and physical-device validation. Full text scheduling unification, per-modality compatibility surfaces and lifecycle coverage remain in this release. See [API behavior/limits](API.en.md#030-dev2-independent-gateway-jobs-and-artifacts).
4. Finish measured admission profiles, thermals, input-artifact references, stage/checkpoint capability handling, cross-modality load/unload and upgrade migration verification.
5. Obtain physical-Android offline outputs for new inputs on every frozen subtarget, quality/cancellation/cleanup checks, A7 fifteen-minute screen-off tasks and one-hour alternating service evidence. No device is available.
6. Pass all A1–A11/R-01–R-05 gates and produce complete source/APK/docs/actual feature media/Release. Development builds cannot substitute for delivery; publishing tools reject `-dev`.

## Development UI media

Every frame carries “UI FIXTURE · not a physical device · not model output”. Transfer, installation and sampling states are fixtures, with no model-weight downloads or generated artifacts.

<img src="media/development/02-local-tags.png" width="280" alt="Flat Local models and independent tags, UI fixture" /> <img src="media/development/06-queue-results.png" width="280" alt="Queue and result library, simulated state" />

<img src="media/development/08-zero-model-api.png" width="280" alt="Zero-model gateway controls, UI fixture" />

[Video](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif) · [Media hashes/provenance](media/development/manifest.json)

Browser pages, contexts and processes close in `finally`. No Docker, WSL, virtual machine or Android emulator is used.

## dev.3 speech integration

Add a compiled sherpa_tts ARM64 worker and Kokoro / Piper / Matcha adapters. Three complete candidate recipes remain explicit user-selected audio / TTS / CPU assets. NativeWorker shares process ownership, speech parameters, duration protection, PCM WAV and effective-parameter / waveform provenance. Code dependencies come from the pinned official release, never model downloads. Package checks include 23 new notice originals and exact dependency closure; some model-data licenses still require review.

**62 new TTS contract / actual host child-process assertions** cover components, bounds, cancellation, exits, completion protocol and private request cleanup; output is arbitrary fixture bytes, not speech. 89 UI checks pass. Waveforms, pronunciation, actual RAM / speed / heat, Android log binding and endurance have no device evidence. Selection 10 remains unaccepted. All other selected models/recipes, unified scheduling and physical-device gates remain mandatory for the same v0.3.0. See [speech foundation](TTS_ENGINE.en.md).

<img src="media/development/09-tts-form.png" width="280" alt="Speech-specific form, explicit UI fixture without generated audio" />


## dev.4 explicit peer-adapter pairing

Add data-only `lma.adapter/1` declarations with SD 1.5/SDXL architecture, pipeline and optional model-ID restrictions. LoRAs remain image-library peers. Explicitly select an installed base or up to eight compatible adapters in a base task form, with independent saved strengths and bounded task edits. Missing bases never trigger model selection/download.

Tasks/API freeze IDs, scales and adjustments; execution atomically leases the complete base/adapter group, protects in-use assets and resolves private component paths into the existing native `loras` array. Provenance retains adapter manifests. 45 new host checks bring the foundation total to 130, with 97 UI checks. These are arbitrary-byte/UI fixtures, not LoRA output.

No checked LoRA download candidate is added. Real SD 1.5/SDXL/LCM recipes, quantized compatibility and effect acceptance remain open. See [pairing](ADAPTERS.en.md) and the [foundation/user-asset audit](ASSET_CONTROL_AUDIT.en.md). This is `0.3.0-dev.4 / code 8`; complete v0.3.0 remains unfinished and unpublished.

![Explicit adapter pairing, UI fixture](media/development/10-lora-pairing.png)
![Independent adapter strength, UI fixture](media/development/11-lora-form.png)


## dev.5: user-selected HF components and integrity

Seven signed-App data templates cover complete SD 1.5/SDXL checkpoints, respective LoRAs, and English Kokoro/Piper/Matcha recipes. Users explicitly choose every component, including files from separate frozen HF repositories; fixed dependencies are disclosed. Registration only saves a manifest; downloading requires a separate confirmation. Flat peers retain image/audio and independent engine tags, without App-triggered model downloads.

Schema 2 adds Git blob identity, measured SHA256 receipts, task component provenance and role-separated import paths; schema 1 remains compatible. 87 additional recipe/integrity assertions bring foundation checks to 217; HF has 74 and UI 112. These are scoped host/UI checks, not phone or universal-HF acceptance. See [workflow and limitations](HF_RECIPES.en.md) and [checkpoint notes](releases/v0.3.0-dev.5.md).

![HF recipe UI fixture](media/development/12-hf-components.png)
![HF component-file UI fixture](media/development/13-hf-component-files.png)

## dev.6: MOSS Nano execution and private asset workspaces

Add a compiled ARM64 SentencePiece/ONNX/codec speech worker, an eighth HF component template, explicit external-data selection, private leased hardlinks and shared ORT conflict checks. 190 new host checks cover Java contracts/real child processes and hardlinks, executed C++ reference validation and dependency identity. All tokenizer, voice and weight data stays user-selected. See [complete route, bounds, sources and limitations](MOSS_NANO_ENGINE.en.md) and [checkpoint notes](releases/v0.3.0-dev.6.md). No actual MOSS speech or device evidence exists; 09 and every complete-v0.3.0 target remain mandatory.

## dev.7: user-controlled model versions

Bundles gain a native version index, component/license/profile review, explicit download/folder import, separate activation and rollback. Old settings and immutable task provenance remain intact; stale consent is rejected. App installation/upgrades still start no model transfers; only foundation code is added. Queued/running base and LoRA references prevent deletion.

302 foundation checks include 62 version assertions; 132 UI checks pass. Screenshots 17–21 and refreshed [recording](media/development/foundation-ui.mp4)/[GIF](media/development/foundation-ui.gif) retain UI FIXTURE labels. See [workflow/failure rules](MODEL_UPDATES.en.md) and [checkpoint notes](releases/v0.3.0-dev.7.md). Legacy unification, every selected target and device gates still block complete v0.3.0; no new Release is created.

## dev.8: text bundles join shared execution

The ninth HF recipe accepts an explicitly selected complete text GGUF. The existing signed llama runtime implements `LocalEngine`, sharing profiles, leases, jobs, cancellation, artifacts and provenance through a private authenticated loopback endpoint per task. Saving/execution inspect GGUF context and UI/native code jointly clamp output limits. Effective schemas stay separate from immutable manifests; an incompatible record does not disable the library.

66 added checks execute actual host files/children/HTTP with literal test output, without model inference. Foundation checks total 310 and UI 147; Lint has zero errors and ten warnings. The APK has 50 production Java sources and the same 19 native files, without new model assets. Typed local JSON preserves response/reasoning and supports safe text preview, copy and export. See the [guide](TEXT_ENGINE.en.md), [receipt](../verification/development/text.json) and [notes](releases/v0.3.0-dev.8.md).

Screenshots 22–24 and the updated recording/GIF retain UI FIXTURE labels. Complete legacy migration, chat/API scheduling, every selected model and physical Android acceptance remain open. All queued jobs still require stopping the legacy persistent text service first. No new Release.

## dev.9: existing models share assets and profiles

Existing complete GGUF files are locally adopted with hardlinks, measured receipts and an atomic original-ID binding; no network transfer or implicit model load is involved. Original model details open shared tasks/version management, and duplicate library/API rows are suppressed. Legacy and bundle editors share defaults; loaded-context changes reload through the engine-owned lease. Restored unfinished downloads require explicit resume.

69 added host migration checks and 156 UI checks pass. Text 66, TTS 62, Nano 190, API 67, backend 98, HF 76 and foundation 310 remain scoped host/UI evidence. See the [migration guide](MODEL_MIGRATION.en.md), [receipt](../verification/development/migration.json) and [notes](releases/v0.3.0-dev.9.md). Screenshots 25–26 and refreshed recording/GIF retain UI FIXTURE labels. Full automatic scheduling, every selected pipeline and physical-Android installation/upgrade/output/endurance still block the same complete v0.3.0; no new Release.
