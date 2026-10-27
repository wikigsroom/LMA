# LMA v0.3.0 complete update requirements and acceptance

[中文](MULTIMODAL_RELEASE_PLAN.md) · [Foundation](FOUNDATION.en.md) · [Task execution](WORKFLOWS.en.md) · [Structured scope and tags](proposals/multimodal-release-scope.json)

Date: **2026-10-27 (Asia/Taipei)**. Status: **complete requirements baseline for the next version, v0.3.0; unimplemented and unpublished.** The public APK remains 0.2.0. This consolidates all previously planned work and supersedes the split-release roadmap and ComfyUI canvas/node proposal. See the [v0.3.0 delivery summary](releases/v0.3.0-plan.md).

## 01 · Decision and scope

**The next version, v0.3.0, must deliver the complete shared local foundation and runtime/recipe support for all 16 selected groups together. No release splitting or automatic deferral.** Native pipelines, operators, shared memory, devices and licenses are work to resolve within this release. Open risks remain blockers for this version, rather than later-release assignments. Inclusion in requirements is not an implementation claim.

- Include original selections **01–14, 16, 17** and every frozen subtarget in v0.3.0, without renumbering. Preserve existing text models and text generation. Both SD 1.5 and SDXL LoRA pass acceptance in this release.
- Exclude original 15 YuE2, 18 large Wan, 19 newer LTX, 20 H3 and 21 ComfyUI infrastructure. Model/LoRA training is outside scope.
- All model records are equal peers. Use capability, runtime-dependency, format, device, installation and evidence tags/filters rather than model hierarchies or engine folders.
- Every generation stage executes on the same Android phone, without ROOT, Termux, an external inference server or a conversion service. HF access downloads explicitly selected assets; after installation, fresh inputs must work offline.
- Internal engine adapters and fixed pipelines are necessary implementation modules. Do not build a user node/plugin system or import ComfyUI graphs.

**Supported means a complete pinned bundle, a compatible packaged engine, valid parameters, fresh-input offline phone output, openable artifacts, cancellation/unloading, background ownership and reviewable device evidence.** Listing/tagging a repository, downloading weights or declaring a nonfunctional provider does not meet this definition. Experimental support also requires actual output.

These are 16 requirement groups, not 16 weight files. In particular, 03, 10 and 12 contain multiple subtargets. Overall completion requires every frozen subtarget; Nano in 09 does not substitute for 12, and a still-image MP4 does not substitute for 16/17.

### App updates and user-owned model assets

**App updates deliver the foundation. Users independently choose, download, import, manage and delete model assets.** Supporting every target means its architecture, engine, recipe and management path are functional; it does not bundle/preinstall all models or require users to download them all.

| Object | Delivery/management rule |
| --- | --- |
| APK foundation | UI, engine/backend code, jobs/background/API, generic resources, tag rules, catalogue metadata, recipes and notices; no model weights |
| Model-specific data | Backbone, LoRA, encoder/VAE/audio-codec weights and model-specific tokenizers/voices/language packs are separate user-selected downloads/imports |
| Install/app upgrade | No automatic model selection or asset download triggered by installation/upgrade. Preserve existing files, settings and user-authorized preferences without silently replacing weights |
| User downloads | Show the selected model/quantization/recipe's required components, total size, reusable assets and device requirements; only an explicit download action creates that bundle's job, without adding recommendations/sibling models |
| Independent management | Install one model or any needed combination; pause/resume/update/import/delete independently. Deleting models retains the foundation and protects shared references |
| No-model state | App/catalogue/tags/settings remain usable; generation and model APIs need a compatible user-installed model. Missing assets prompt selection/download, without implicit download or off-device execution |

Capability tags and actual installation state are independent. Recommended is a candidate view, not an auto-download list. The 14 built-ins mean catalogue metadata, not bundled weights. App upgrades do not force model updates; compatible weights on supported architectures can download separately, while new architectures/operators may require a foundation update.

Developer acceptance may download test models to validate the 16 groups. Those assets never enter the release APK or become user installation prerequisites. Coverage, single-release scope and real execution evidence remain required.

## 02 · Flat models and tag semantics

Text, image, video and audio models share one `ModelRecord`: stable ID, name, source/revision, task capabilities, available recipes, component dependencies, independent settings, installation and compatibility status. Forms depend on the selected model's actual capabilities.

| Dimension | Examples | Rule |
| --- | --- | --- |
| Output task | `task:text`, `task:image`, `task:video`, `task:audio` | Multiple values allowed; a TTS input being text does not confer text-generation capability |
| Specific capability | `text_to_image`, `text_to_speech`, `text_to_sound`, `text_to_video`, `image_adapter` | Recipe-specific; cloning, editing and image-to-video are not inherited automatically |
| Engine requirement | `engine:sd_cpp`, `engine:mnn_diffusion`, `engine:sherpa_tts` | Alternative engines mean OR, not simultaneous mandatory installation |
| Pipeline, format, components | `pipeline:wan21_13b`, `format:gguf`, `dependency:audio_codec`, `dependency:vae` | Derived from a pinned recipe; GGUF/safetensors do not imply universal execution, and components may use mixed formats |
| Hardware/runtime | `backend:vulkan`, `backend:cpu`, QNN SoC/QAIRT/compiled shapes | Separate requirements, detection and measurements; show the selected route's requirements |
| State | Needs adapter/components, installed, unverified, experimentally tested, device-validated, incompatible | Architecture, installation and device evidence are independent fields |
| License, content, evidence | Exact license; Uncensored/Abliterated; checked declaration or metadata hint | Independent of function and device support; new models do not inherit uncensored labels |

All/search/Local are views over the same flat pool. Preserve Recommended **m08 → m06 → m01**, including existing labels and evidence. It is a curated view, not a higher model tier. Task filters do not create four different model managers or downloaders.

LoRAs also have flat records, labeled image adapters requiring a compatible base. Selecting one prompts for a matching base; it cannot generate independently. Technical dependency relationships do not create UI ranks. Encoders, VAEs and codecs primarily remain component resources; separately imported components have explicit roles, not false generation capabilities.

Family planning records may summarize capabilities; each published checkpoint receives its own tags. MOSS SoundEffect does not automatically become TTS. Unknown HF records remain capability-unresolved/without a recipe; metadata hints are not verified capabilities.

For example, Wan gets video/text-to-video tags plus a Wan pipeline, UMT5/VAE and backend requirements. Nano gets audio/TTS plus tokenizer/codec requirements. Both remain peers of existing Qwen text records. Tags in the proposal JSON are requirements only; they do not alter the production catalogue or imply installed engines.

## 03 · Complete foundation requirements

| ID | Required delivery | Completion condition |
| --- | --- | --- |
| F-01 Flat library | Shared records, tags/filters, details, HF provenance and Local management | Common IDs/search/download entry points; preserve Recommended |
| F-02 Bundles | Multiple components, pinned revision/SHA256, shared references, resume, atomic install and deletion protection | Missing mandatory files prevent execution; active inputs cannot be cleaned |
| F-03 Recipes/capabilities | Separate architecture, engine and backend with compiled/versioned support | Explain unavailability; unknown operators/devices do not pass admission automatically |
| F-04 Internal engines | Lifecycle protocol, worker processes, version/dependency locks and crash isolation | Every module required by selected recipes executes; empty adapters do not qualify. Native code updates through signed APKs; model downloads contain data |
| F-05 Model settings | Per-model/recipe schema, editable presets, hard-limit correction and joint constraints | Text context, image steps/dimensions, video frames and audio settings remain independent; record effective values/reasons |
| F-06 Jobs/queue | Async submission, queueing, cancellation, ordered events, progress and bounded retries | Durable inputs/state; cancellation binds job and process launch generation |
| F-07 Admission/resources | Staged memory, shared RAM, disk, threads/GPU profiles and thermal policy | Default one heavy engine; distinguish measurements from estimates; no silent offloading/substitution |
| F-08 Background/recovery | Foreground service, visible notification/stop, scoped locks and restart reconciliation | UI closure does not cancel explicitly started jobs; resume only genuine engine checkpoints, otherwise rerun the stage |
| F-09 Artifacts | Image/WAV/video preview, settings/seed/provenance, save/export | Hashes and complete effective snapshots; distinguish still-image encoding from generative motion |
| F-10 API | Preserve text API; add local async jobs/events/cancel/authenticated artifacts | UI/API share scheduling and validation; video is not a text-token stream |
| F-11 Releases/migration | Native Windows NDK/CMake, ABI/SDK/dependencies, signing, migrations and regressions | No Docker/WSL/emulators; preserve old models/history/settings; consistent source/APK/evidence |
| F-12 Evidence/maintenance | Exact model/engine/device matrix, errors/resources, bilingual docs and feature media | Desktop fixtures, upstream reports and LMA phone results remain distinct |

No infinite canvas, wiring editor, user nodes, plugin marketplace, third-party Python nodes or ComfyUI JSON import. Internal encoding/sampling/decoding stages may have dependencies without exposing a general DAG. Earlier graph drafts are not current execution-interface commitments.

## 04 · Foundation coverage, model tags and adaptation requirements

These are target routes and engineering assessments. **Every new entry is currently unimplemented/unverified in LMA.** Engine names are proposed alternatives or architecture-specific choices, not installed capabilities. Full component tags and acceptance details are in the [scope JSON](proposals/multimodal-release-scope.json).

| Original ID | Model/route | Output tags | Engine route | Required resolution | Single target version |
| --- | --- | --- | --- | --- | --- |
| 01 | Stable Diffusion 1.5 | image | `sd_cpp / mnn_diffusion` | Established mobile route; Z20 candidate | 0.3.0 |
| 02 | LoRA loading and management | image | `sd_cpp` | Requires a matching base; not standalone | 0.3.0 |
| 03 | SD-Turbo / LCM / LCM-LoRA | image | `sd_cpp` | Sampler/distillation-specific validation | 0.3.0 |
| 04 | Sana | image | `mnn_diffusion` | Match converted package and encoder | 0.3.0 |
| 05 | SDXL | image | `sd_cpp / mnn_diffusion` | Dual encoders and memory validation | 0.3.0 |
| 06 | Z-Image-Turbo | image | `sd_cpp` | High-memory quantized/staged experiment | 0.3.0 |
| 07 | FLUX.2-klein-4B | image | `sd_cpp` | Quantized full-pipeline experiment | 0.3.0 |
| 08 | Qwen-Image-2.1 | image | `sd_cpp` | High-memory and license gates | 0.3.0 |
| 09 | MOSS-TTS-Nano 100M | audio | `moss_nano_ort` | Complete arbitrary-input tokenizer/codec | 0.3.0 |
| 10 | Kokoro / Piper / Matcha | audio | `sherpa_tts` | Accept all three subroutes separately | 0.3.0 |
| 11 | Qwen3-TTS 0.6B Base | audio | `qwen_tts_litert / qwen_tts_native` | Android references; speed/API validation | 0.3.0 |
| 12 | Full MOSS family | audio | `moss_architecture_specific` | Native adaptation/acceptance of all nine subtargets | 0.3.0 |
| 13 | SoulX-Podcast 1.7B | audio | `soulx_native_port` | Complete native Android port unproven | 0.3.0 |
| 14 | Stable Audio Open Small | audio | `stable_audio_litert` | Short sounds/music, not full songs | 0.3.0 |
| 16 | Wan 2.1 T2V 1.3B Q4 | video | `wan_sd_cpp` | Author Android evidence; local experiment | 0.3.0 |
| 17 | LTX-Video 2B 0.9.8 distilled | video | `ltx_vulkan_port / ltx_qnn_port` | Separate Vulkan/QNN and code-license gates | 0.3.0 |

Preserve the 14 existing built-in text records with text-generation tags, `llama_text`, single-component text GGUF recipes and existing independent settings. Migrate HF/imported records too, without changing their evidence. Derive runtime tags from recipes, not repository names.

## 05 · Family subtargets and release risks

**03:** Accept separate SD-Turbo (SD 2.1), LCM checkpoint and LCM-LoRA routes with matching bases. One working route does not establish all three. **10:** Pin and validate a distributable language/voice package for each of Kokoro, Piper and Matcha; this does not promise all languages or third-party voices.

**12:** Freeze nine required publisher subtargets for this version: MOSS-TTS 1.0, v1.5, Local-Transformer, Local-Transformer-v1.5, TTSD-v1.0, VoiceGenerator, SoundEffect, SoundEffect-v2.0 and Realtime. Nano belongs to 09. These span Delay, Local, Realtime and a separate DiT pipeline. The upstream fully native Delay fork includes audio encoding/decoding and provides a porting starting point; it does not prove Android support for every architecture. [Publisher family list](https://github.com/OpenMOSS/MOSS-TTS#released-models), [native Delay pipeline](https://github.com/OpenMOSS/llama.cpp/blob/moss-tts-firstclass/docs/moss-tts-firstclass-e2e.md)

**13:** SoulX's official Linux/Python pipeline and partial ONNX files do not establish a complete Android host loop, tokenization, reference encoding, codec and multi-speaker timing. [SoulX model card](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B) Both 12 and 13 remain explicit requirements with native prototype gates. Phone resources/quality are unproven; failure must remain visible rather than being counted as completion or silently removed.

**06/07/08:** Account for encoders, VAE, activations and OS memory in addition to the quantized backbone. Start with newer high-memory devices. Qwen-Image-2.1's full chain cannot be budgeted as only 7B, and its Qwen Research License cannot inherit an earlier model's Apache terms. [Qwen components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/qwen_image_2.1.md), [model/license](https://huggingface.co/Qwen/Qwen-Image-2.1)

**11:** LiteRT Kotlin and native Android references exist; validate API requirements and speed separately. An upstream Pixel 8a example is not realtime, and does not promise realtime Z20 speech. **14:** The LiteRT route generates short sounds/music, not full songs. [Android Qwen TTS](https://github.com/google-ai-edge/litert-samples/tree/main/samples/litert/text_to_speech_lm), [Arm audio deployment](https://developer.arm.com/code-along/stable-audio-open-small)

**16/17:** Implementation-author Android routes justify actual on-phone video experiments. Port Wan's disk parameters, CPU text/VAE and Vulkan diffusion; desktop CUDA timing is not a phone benchmark. The old LTX 2B QNN bundle excludes Z20; validate Vulkan separately. Resolve LLM-Hub's noncommercial code terms and independent QNN/model redistribution terms before integration; do not absorb the whole project into MIT LMA. [Wan implementation](https://github.com/SaientAI/saient/blob/main/docs/VIDEO_PIPELINE.md), [LTX conversion](https://huggingface.co/timmyboy26/LTX-Video-2B-0.9.8-distilled-QNN), [code license](https://github.com/timmyy123/LLM-Hub/blob/main/LICENSE)

See [broader source research](MULTIMODAL.en.md). License gates apply to every selected component; an open-model description is not a redistribution/commercial-use determination.

## 06 · User flow

1. Install/upgrade only the foundation, preserving user models/settings and creating no model downloads. Open the flat library, keep Recommended and filter by output/name/installation/compatibility. The App remains browsable without installed models.
2. Choose a model/quantization/recipe; inspect capabilities, complete components, total download, reusable assets and device state. Only clicking Download creates the selected bundle job. Browsing/recommendations never trigger downloads. Missing engine support identifies a required foundation version; weights do not supply execution code.
3. Manage all models/transfers under Local and edit independent settings. LoRA remains a peer record using a compatible-base selector.
4. Select Use to open the task form: prompt/text, required files, supported voices/speakers, dimensions/frames/duration. Only show fields supported by that recipe and explain missing inputs.
5. Validate natively, return corrected effective values with reasons, and submit to the common queue. Report stages, real progress/previews and cancellation; do not invent percentages.
6. Preview/play/export artifacts, copy effective configuration or regenerate. The foreground service owns screen-off work; reopening restores durable records, with interruption behavior matching real engine capabilities.

No free-form automation editor is required. Any future narrated-image composition would use a fixed form/internal sequence, not become mandatory because of an old graph draft.

## 07 · Distribution and devices

Android 9/API 28, ARM64 remains the application baseline. A new engine/hardware package may require a higher API; declare that per recipe and disable incompatible routes. Prioritize Z20 checks for 01/02/09/10. Other targets require specific or newer devices; no claim that all 16 groups run on Z20. Newer high-memory phones and chip-specific QNN are test groups, not invented universal RAM minima.

With networking disabled, tokenization, text/reference encoding, sampling, VAE/codec, playback and export must complete a fresh task. Report failures locally. Internal loopback and serving API clients do not change the computation location.

Foreground services need no ROOT, but vendor battery policy, low memory, OS termination and heat can interrupt work. Background API/queue acceptance is separate from generation quality; neither 24/7 full load nor immunity from Android timeouts is promised. Select service types according to actual work and Android version. [Background limits](WORKFLOWS.en.md)

The current build repackages prebuilt text libraries. New engines need native Windows NDK/CMake/dependencies, ABI/page-size checks and license packaging. Old build success does not validate a new engine. Tie engine/model support to the signed APK; do not put executable scripts in model data.

## 08 · One complete release and release gates

The only target is **v0.3.0**; the public APK remains v0.2.0. This requirements update does not change the Manifest or publish a Release. Every package, model and frozen subtarget belongs to the same acceptance scope, without later-release assignments.

| Delivery scope | Required completion |
| --- | --- |
| Complete shared foundation | Implement F-01–F-12 for all four output tasks and reusable supported-architecture variants |
| Existing text support | Migrate 14 catalogue records, user-selected HF/imported records, chat, text API, recommendations and settings compatibly; no bundled weights |
| Image/adapter support | All 01–08; both SD 1.5/SDXL LoRA for 02; all three 03 subtargets |
| Audio support | All 09–14; Kokoro/Piper/Matcha individually and all nine frozen 12 subtargets |
| Video support | Both 16 Wan 1.3B and 17 older LTX 2B produce actual motion video using declared lawful device recipes |
| Product flow | One flat library, tags, complete downloads, Local settings, forms, queue, background, artifacts, API, recovery/export |
| Release package | Upgrade-compatible signed APK, matching source/dependency locks/hashes, phone evidence, bilingual guides and screenshots/recording/GIFs |

| Gate | Full v0.3.0 delivery condition |
| --- | --- |
| R-01 Complete scope | F-01–F-12, all 16 groups and frozen subtargets have implementation and acceptance; both base families for 02 pass |
| R-02 Actual execution | Each generation target has at least one pinned complete recipe producing fresh-input offline output on a declared physical Android device; adapters run with matching bases; device restrictions do not remove models |
| R-03 Resolved risks | Native host loops/operators/codecs, selected code/model licenses, memory and parameter constraints are deliverable; failed targets remain blockers, not empty adapters/catalogue entries/experimental labels |
| R-04 Lifecycle/regression | A1–A11 pass, including upgrade, background, cancellation, unloading, interruptions and resource release; no unresolved severe runtime/data issues |
| R-05 Reviewable release | Version, signature, APK/source, engine/component locks, device matrix, feature media and bilingual guides agree, with exact device limits |

Internal development builds validate this same scope. A reduced preview cannot substitute for completion. A particular phone may disable incompatible recipes; a selected target that runs on no declared device leaves the whole version incomplete. Missing devices and unfinished ports remain explicit blockers without changing the target version. Only a new user instruction revises scope.

## 09 · Work packages and blockers within this release

These are work packages within the same v0.3.0, not a version roadmap or partial deliveries. Implementation follows technical dependencies; every package shares the release gates in section 08.

| Package | Required work/output | Acceptance dependencies |
| --- | --- | --- |
| W1 Records/tags/migration | Flat ModelRecord, task/dependency tags, component/recipe schemas, legacy text and user-record migration | F-01/F-02/F-03/F-05; A1/A2/A4 |
| W2 Native builds/all required engines | Windows NDK/CMake, adapters/protocol, worker isolation, ABI/API/page size, full dependencies/licenses of selected recipes | F-04/F-11; actual execution modules for all targets |
| W3 Downloads/settings/admission | Atomic bundles, shared references, resume/space plans, compiled capabilities, independent editable settings/joint constraints | F-02/F-03/F-05; A2–A4 |
| W4 Jobs/resources/background/API | One heavy-engine lease, durable jobs/events, cancel/timeouts, background ownership, real recovery, authenticated APIs/artifacts | F-06–F-10; A5–A8 |
| W5 Every model pipeline | All 01–14/16/17, frozen 03/10/12 subtargets and both SD 1.5/SDXL LoRA; preserve existing text | R-01–R-03; one cross-modality example is insufficient |
| W6 Acceptance/media/release | Physical offline output, resources/quality/screen-off/endurance, upgrades, bilingual guides/media and signed package | F-11/F-12; A1–A11; R-04/R-05 |

Validate risky work early within this version: native Wan output, MOSS Delay/Local/Realtime/DiT, complete SoulX, and 08 full-bundle memory/licenses. Prototypes are implementation tools, not final product integration. Resolve problems here, select lawful compatible recipes or track explicit blockers; do not defer automatically.

Track each model/subtarget's implementation, asset binding, engine build, device, evidence, blockers and completion against v0.3.0. States progress from unimplemented/adapting through awaiting device verification to accepted. Experimental evidence is labeled accurately without bypassing complete acceptance. Define resource/quality budgets per device recipe before testing and publish them, rather than counting unacceptable latency as usable support.

No physical device is available; complete Android ports for 12/13 remain unproven. Do not invent person-days, dates, speed or peak RAM. The scope and single-release rule are fixed; update estimates using prototypes/device results within this version.

## 10 · Acceptance and completion

- **A1 Flat library:** one pool for four task filters; unchanged recommendations/order/labels; peer LoRAs with dependencies; unknown HF models do not become runnable automatically.
- **A2 Tags:** output and foundation tags on every target/subtarget; correct OR alternatives, mixed formats, backend/version constraints; tags do not replace measured status.
- **A3 Installation:** missing files, bad SHA, resume/pause, disk exhaustion, shared deletion, active references and interrupted upgrades have truthful states.
- **A4 Settings:** independent values, migrations, editable presets, hard-limit correction, unknown limits, joint dimensions/frames/fixed shapes and effective snapshots.
- **A5 Execution:** fresh offline inputs produce openable non-placeholder images, non-prerecorded audio and generative motion video; at least three short consecutive tasks verify reload/release.
- **A6 Lifecycle:** queueing, model switching, cancel/unload, worker crash, UI recreation, screen-off, power/thermal policy and interrupted recovery; no fake checkpoint resume.
- **A7 Background:** at least one task/queue spanning 15 minutes screen-off, plus one hour of idle/request-alternating service. Record longer tests separately; do not infer permanent survival.
- **A8 Resources/quality:** per recipe record SoC/RAM/Android/driver, component hashes, engine build, effective settings, peak shared memory, timing, audio RTF/first audio, video frames/fps and acceptable artifacts. Another device is not Z20 evidence.
- **A9 Regression/release:** preserve old text API/chat/recommendations/settings/downloads; consistent native package/signing/version/SHA/bilingual docs/screens/recordings. Desktop fixtures cannot stand in for feature demonstrations.
- **A10 Complete single release:** v0.3.0 includes F-01–F-12, existing text, all 16 groups/frozen subtargets and both SD 1.5/SDXL adapter pairings. Entries/downloads do not count. Any missing requirement leaves overall completion open, without automatic release splitting, removal or deferral.

- **A11 Foundation/asset separation:** zero-model installation/app upgrade creates no model downloads; browsing/filtering never starts transfers; only selected bundles and disclosed dependencies download; one-model use works; upgrades do not silently replace/force-update weights; deletion retains the foundation with explicit settings/shared-reference handling.

A1–A4 rules and some migrations permit desktop checks. A5–A8 require physical Android evidence, currently zero. `multimodal-release-scope.json` is a reviewable requirements snapshot, not the production catalogue, a download lock or a test report.

## 11 · Documentation baseline and current state

This update consolidates the previous multi-release plan into one complete next-version baseline, v0.3.0. It synchronizes the model matrix, structured scope, foundation/task/research guides, bilingual READMEs, index, changelog and version plan. All 12 core requirements and support for the 16 groups/frozen subtargets belong to this version. Model data remains an independent user choice and is not shipped with the App.

The public APK remains v0.2.0. See [implementation status](DEVELOPMENT.en.md) for partial foundation code, native compilation and development UI media in 0.3.0-dev. Complete model/API/device acceptance is unfinished; no v0.3.0 tag/Release exists. Outstanding work remains blocking in this release. The product target stays **flat library → task form → on-phone queue → artifact library**; old canvas/node JSON remains historical and non-executable.
