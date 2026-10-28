# LMA extensible local multimodal foundation

[中文](FOUNDATION.md) · [Local-model assessment](MULTIMODAL.en.md) · [Task execution](WORKFLOWS.en.md) · [Current release requirements](MULTIMODAL_RELEASE_PLAN.en.md) · [Documentation](README.md)

Date: **2026-10-27 (Asia/Taipei)**. Decision: **this is buildable, and an extensible local multi-engine foundation should be the main product direction.** New models should reuse downloading, settings, jobs and artifact management instead of becoming separate application features. Every inference stage remains on the same Android phone without ROOT or off-device inference/fallbacks.

This evaluates source and upstream Android/native engines. **The complete foundation is in development and has not passed acceptance.** The public APK remains 0.2.0; internal 0.3.0-dev adds bundles, settings, persistent jobs/artifacts, UI and an ARM64 CPU diffusion worker. See [implemented progress and remaining work](DEVELOPMENT.en.md). No LMA phone-generation or endurance evidence exists. Z20 is a constrained target, not the product ceiling.

The [complete update requirements](MULTIMODAL_RELEASE_PLAN.en.md) govern one v0.3.0 delivery of all core capabilities and 01–14/16/17/frozen subtargets, equal peer models with output/dependency tags, task forms/queue/artifacts, without a ComfyUI canvas, user nodes, plugin ecosystem or graph import. Internal engine modules are application code.

## 01 · Evidence and limits

Existing C/C++ and Android execution paths support the proposal: [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp#features) implements multiple image/video families; [MNN Diffusion](https://github.com/alibaba/MNN/blob/master/transformers/diffusion/README.md) has mobile image recipes; [ONNX Runtime](https://onnxruntime.ai/docs/tutorials/mobile/), [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) and [LiteRT Android](https://developers.google.com/edge/litert/android) provide audio components or complete speech-pipeline building blocks. Pin and validate actual Android builds and coverage separately.

This supports a multi-engine engineering approach, **not execution of arbitrary HF weights**. ONNX/TFLite graph runtimes do not automatically implement a TTS tokenizer, sampling host loop and audio codec. A native engine listing an architecture does not establish operator coverage on every Android GPU.

| Addition | Main work after the foundation exists | Data-only addition possible? |
| --- | --- | --- |
| Another fine-tune/quantization of a supported architecture | Pinned sources, components, settings, compatible recipe and acceptance | **Yes**, if the installed engine supports the variant and every component |
| Matching LoRA/voice in a supported architecture | Assets and base-model constraints | **Yes**, if that adapter/voice mechanism already exists |
| Family present upstream but not enabled in LMA | Provider pipeline/parameter mapping, components and validation | Not guaranteed; an app update may be needed |
| New architecture/custom operators | Update/add engine and architecture adapter, possibly converted graphs | **Code and a signed release update required**; UI/downloads/queue should remain reusable |
| New GPU/NPU for an existing model | Backend recipe, operator probes and hardware validation | Often requires a new native build; a chip name alone is insufficient |
| New task, such as future audio editing | Task schema, interaction and adapter | Extension required, without rewriting the whole application |

Measure broad support by **continued addition of supported architecture variants, coexistence of engines and clear explanations for unknown models**. Do not invent a coverage percentage or count untested devices as supported.

## 02 · Three independent layers

1. **Architecture/pipeline:** how SD, Wan, LTX or a TTS family tokenizes, encodes, samples and decodes, with matching components.
2. **Runtime engine:** pinned executable builds such as llama.cpp, sd.cpp, MNN, ORT or LiteRT.
3. **Hardware backend:** CPU, Vulkan, OpenCL, QNN operator/shape/precision/driver constraints.

Tasks combine these layers. `video.generate` is not synonymous with Wan, `audio.generate` is not synonymous with TTS, and Vulkan is not a weight format. An LMA engine provider is an application adapter, distinct from an ONNX Runtime Execution Provider.

## 03 · Shared architecture

```mermaid
flowchart TD
    UI[Flat library / task forms / local API / artifacts] --> C[Versioned task and parameter contracts]
    C --> R[Recipe resolution / capabilities / device admission]
    R --> J[Persistent jobs / internal stages / memory and thermal scheduling]
    B[Bundles / components / verification / model settings] --> R
    J --> P[Provider pipeline adapters]
    P --> T[llama.cpp text]
    P --> D[sd.cpp / MNN images and video]
    P --> A[sherpa / ORT / LiteRT audio]
    T --> O[Local artifacts / events / preview and export]
    D --> O
    A --> O
    O --> UI
```

Pages and API use one task contract. A single image request uses the common queue; encoding/sampling/decoding dependencies stay inside pipelines without user node wiring. Capability and parameter descriptors determine forms when models change.

## 04 · Models, components and recipes

Represent model identity, weight variant, component files and execution recipes separately. One model may have multiple quantizations/backend/device recipes while keeping stable attribution and the user's model ID.

Bundles record pinned repository/revision, component role/path/bytes/SHA256, task, architecture, format/quantization, license and tags. Recipes select tokenizer, encoders, VAE/codec, pipeline adapter, engine-build requirements, hardware profile, parameter schema and resource estimate. A downloaded backbone alone never makes an incomplete pipeline runnable.

Content hashes index shared components; a dependency graph supports deletion and storage planning. Verify components and atomically commit ready status only when mandatory files are complete. Running jobs retain references so deletion/cleanup cannot remove their inputs. Unknown hashes or unpinned provenance cannot be represented as reviewed bundles.

HF search remains broad, with separate discovered, recipe-available, installed, eligible-to-try and verified-on-target states. Show required components, total downloads, reused assets and reasons. Offer prepared compatible assets as user-selected downloads: users need no attached computer for conversion, and no external conversion/inference service is invoked. Missing recipes produce an unsupported explanation.

App updates provide foundation code, engines, catalogue/tag metadata and recipes, without model weights or model-specific asset data. Users choose complete downloads/imports separately. Installation/upgrades/browsing trigger no model transfers; preserve files/settings and let users choose model updates independently. Developer coverage tests do not require users to install every target; the App remains browsable without models.

## 05 · Internal application engine modules

| Runtime route | Foundation role | Required integration |
| --- | --- | --- |
| llama.cpp | Existing text capability | Wrap the current implementation to validate migration |
| sd.cpp | General native image/video candidate | Expose only architectures in the actual build; validate one image and one small video pipeline |
| sherpa-onnx / ORT | Small TTS and ONNX audio pipelines needing dedicated host loops | Shared task contract, complete preprocessing/postprocessing per architecture |
| MNN | Packages with a demonstrated mobile-optimization benefit | Reserve an extension point; add measured recipes instead of loading every engine by default |
| LiteRT | Converted audio/other mobile pipelines | Add for specific models; .tflite alone does not establish full pipeline support |

These are complementary extension points, not a requirement to install every dependency immediately. Pipelines reference registered native operations and parameters; descriptors contain no executable scripts or arbitrary expressions. Data additions cannot bypass architecture/engine validation.

Start with **versioned modules inside the application**. Audited native engines ship in the signed APK and load on demand. Users install one app and download data for existing support. New engines arrive through ordinary APK updates; arbitrary HF `.so`, Python and custom nodes are not executable plugins. [Android dynamic-code guidance](https://developer.android.com/privacy-and-security/risks/dynamic-code-loading)

Pin engine commits, build flags, ABI, minSdk, native dependencies and licenses. The LMA provider-protocol version is separate from upstream versions. Adapters absorb upstream API/CLI changes rather than exposing CLI flags directly to the UI. Maintain compatible build tables in releases.

Heavy engines run in separate worker processes with version-negotiated IPC and controlled file handles/artifact references. They may be Android Service processes or packaged native executables like the current engine; the main process owns durable queue/state. Avoid mixing different ggml/C++ dependency versions in one process. This separates lifecycle and crashes; **it is not an additional security sandbox or immunity from OS kills**. [Android process model](https://developer.android.com/guide/components/processes-and-threads)

Start workers only when needed. Z20 defaults to one large-engine lease, not five resident model sets because five runtimes are supported. CPU is a baseline only for recipes with a compatible CPU implementation, not a universal rescue for every GPU/NPU graph.

## 06 · Common tasks, task-specific semantics

A shared request envelope contains job ID/idempotency key, task type, model/recipe references, input artifacts, parameter overrides, priority and version. Distinguish `text.generate`, `image.generate`, `video.generate`, `speech.synthesize` and `audio.generate`. Composition, image-to-image, image-to-video and editing are future extension points, not automatically included initial capabilities.

A common lifecycle is `probe → validate → plan → load → run → cancel / finish → unload`. Declare streaming, progress, preview, cancellation, pause and checkpoint support individually. Do not fabricate previews/pauses; if an engine provides no progress denominator, show stage state.

Parameters use versioned model/recipe schemas. Context, CFG, steps, voice and audio duration retain their meanings rather than fitting one global form. User defaults still follow model ID. Recipe/quantization-specific fields may have explicit subprofiles and migrations; switching backends must not overwrite other models' settings.

Editable presets clamp known hard limits; dimensions/frame counts/compiled shapes require joint validation. Separate model constraints, backend limits and resource estimates. Estimates are not rated model maxima. Snapshot requested values, effective values and adjustment reasons.

Events share job/internal-stage ID, sequence, time and type, with distinct token, diffusion-step, audio-chunk, preview and artifact payloads. Image/video tasks are not presented as continuous text tokens. Bound audio/preview queues to avoid unlimited RAM consumption when a consumer is slow.

## 07 · Resources, artifacts and internal task execution

Plan the complete pipeline, including staged encoder/backbone/VAE memory, OS/UI/driver headroom, temporary disk and outputs. Download bytes are not RAM requirements. Use measured recipes and current device state to queue, reject or offer legal lower profiles; unknown estimates cannot become guaranteed eligibility.

The scheduler owns engine leases, foreground execution, cancellation ownership, timeouts and bounded crash recovery. A failure releases its worker and records a clear state. Bind process identity to job and launch generation so cancellation cannot kill a later job. Resource failures never offload or silently substitute another model.

Artifacts are local references with provenance, hash, MIME, dimensions/duration and sample rate/fps. Large tensors stay inside providers. Latent shapes/scales/encoders/VAEs are not interchangeable across engines: exchange decoded image/audio/video artifacts in this version. Keep intermediate tensors inside matching pipelines; user tensor-node wiring is not required.

SQLite persists jobs, internal stages, settings snapshots, events and artifacts. Reuse verified completed stages after restart. Intermediate resume requires real engine checkpoints matching model hashes, engine and configuration. Cache keys also include recipes, input hashes and effective seeds to prevent invalid reuse across versions.

Use a flat model library, task forms, a common queue, previews and regeneration. Internal dependencies do not require a public DAG/canvas/node/plugin system or ComfyUI import. [Task/background details](WORKFLOWS.en.md)

## 08 · Migration from current code

| Current code | Reusable part | Foundation change |
| --- | --- | --- |
| [Store.java](../app/src/main/java/com/lma/app/Store.java), `modelFile(id)` | Stable IDs, private storage, user settings | Bundle/Component/Recipe repositories; wrap old GGUF as single-component bundles preserving files/IDs |
| [Downloads.java](../app/src/main/java/com/lma/app/Downloads.java) | HTTPS, resume, SHA256, pause/atomic install | Component transfers, bundle transactions, shared references and total-space planning |
| [EngineHost.java](../app/src/main/java/com/lma/app/EngineHost.java) | Packaged process, health checks, stop/recovery | Wrap as `llama_text`, then add engines; remove single-CLI assumptions from core |
| [LmaApp.java](../app/src/main/java/com/lma/app/LmaApp.java) / [LmaService.java](../app/src/main/java/com/lma/app/LmaService.java) | Foreground service, notification, locks, state bridge | Evolve single engineModel/Process into JobManager/WorkerSupervisor, preserving the text entry point |
| [HubClient.java](../app/src/main/java/com/lma/app/HubClient.java) | HF queries, pinned revisions, file/auth boundaries | Trusted recipe resolution beyond single `.gguf` selection; no compatibility claim based only on suffix/pipeline_tag |
| [ModelSettings.java](../app/src/main/java/com/lma/app/ModelSettings.java) | Per-model settings and clamping | Task/recipe schemas with compatible text fields/migration |
| WebView / SQLite chats / text API | Offline UI, history and established workflows | Jobs/artifact views and async task API; do not force image/video responses into text API semantics |

Preserve Recommended `m08 → m06 → m01`, broad All/search discovery, Local management and separate uncensored labels. Capability-driven expansion does not replace the existing recommendations.

## 09 · Complete foundation acceptance in one version

All items below are mandatory for the next v0.3.0, not different releases. A subset cannot stand in for the complete foundation and selected-model scope.

| Item | Required delivery | Completion |
| --- | --- | --- |
| K1 Contracts/migration | Bundle/recipe/capability/settings protocols, legacy text provider and durable jobs | Preserve models/settings/downloads/chat/text API and Recommended |
| K2 Shared cross-modality execution | Text/image/audio/real video share queue, settings, background and artifacts | At least two real engine modules; still-image MP4 is not generative video |
| K3 Every target/extensibility | All 01–14/16/17, frozen subtargets and both LoRA base families; second same-architecture weight via descriptors | Individual acceptance in this version; providers do not rewrite library/downloads/jobs |
| K4 Devices/failures | Z20-class/newer recipes, resource/background tests, crashes/cancel/missing assets/disk/recovery | Declared device/offline evidence per target, without claiming all run on Z20 |
| K5 Interaction/distribution | Flat tags, forms, queue/artifacts, full native dependencies/signed package, bilingual guides/media | F-01–F-12, A1–A11 and R-01–R-05 pass together |

Some K1 contracts/migrations allow host checks. K2–K4 device execution requires real artifacts and physical Android evidence. No device is available; completion cannot be claimed. Foreground services do not guarantee survival; see task execution limits.

Native architecture pipelines, mobile operators/quantization, resource/quality measurements and upstream maintenance are work for this version. Internal implementation follows dependencies; unresolved targets remain blockers here rather than moving to other versions.

The [asset-control audit](ASSET_CONTROL_AUDIT.en.md) confirms a consistent document baseline. dev.4 [peer-LoRA pairing](ADAPTERS.en.md) reuses model/reference/task contracts, without phone-output evidence.


Development implementation: dev.5 [HF component recipes](HF_RECIPES.en.md) use signed-App data templates and `lma.model-bundle/2`, with Git-file identity and measured SHA256 receipts while preserving schema 1. Downloads require explicit user confirmation. This remains part of the same unfinished foundation delivery.

Dev.6 adds [Nano execution and EngineWorkspace](MOSS_NANO_ENGINE.en.md): explicit user-owned graph/tokenizer/voice/external-data roles, leased filename-preserving hardlinks, cleanup/recovery and a shared runtime binary with exact dependency identity. These mechanisms extend the common foundation; they do not establish complete v0.3.0 acceptance.

dev.7 adds bundle [independent updates/rollback](MODEL_UPDATES.en.md): user-reviewed assets/profiles, separate download and activation consent, retained old files/settings and protected queued/running version references. Current preference never redirects API/existing jobs; legacy unification and device acceptance remain required in this same complete version.

dev.8 adds an actual [text module](TEXT_ENGINE.en.md) reusing the signed llama server for new bundles, shared parameters/jobs/artifacts. Complete legacy chat/API/file unification remains unfinished; full-release gates are unchanged.

Dev.9 [existing-model migration](MODEL_MIGRATION.en.md) reuses verified local hardlinks, preserves IDs/sources/profiles and exposes shared tasks/versions from original details. Incomplete transfers stay paused until explicit resume. 69 host migration and 156 UI checks pass; physical-Android A11 upgrade acceptance remains open.

Dev.10 [shared execution](SCHEDULING.en.md) unifies resident text, chat/API and jobs under the same process/cancellation boundary. 43 host assertions cover user-asset reuse, switching and retained stop intent, without model downloads or complete model/device acceptance.

Dev.11 implements local imports, authenticated chunks and immutable task references; see [input contracts](LOCAL_INPUTS.en.md). Media is separate from model components. Signed engines declare supported roles; default prompt-only recipes reject media without changing user control of model assets.
