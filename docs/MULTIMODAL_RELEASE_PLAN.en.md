# LMA multimodal requirements, release scope and feasibility

[中文](MULTIMODAL_RELEASE_PLAN.md) · [Foundation](FOUNDATION.en.md) · [Task execution](WORKFLOWS.en.md) · [Structured scope and tags](proposals/multimodal-release-scope.json)

Date: **2026-10-27 (Asia/Taipei)**. Status: **requirements and release proposal, not implemented in the current APK; none of the versions proposed below has been published.** The public APK remains 0.2.0. This scope supersedes earlier ComfyUI canvas/node proposals.

## 01 · Decision and scope

**A complete shared local foundation is buildable; integrate the selected 16 groups across releases.** Removing canvas, wiring, user nodes and a plugin marketplace reduces UI and distribution work. The remaining risks are native model pipelines, operators, shared memory and hardware compatibility. Simpler interaction cannot establish that every family will run.

- Include original selections **01–14, 16, 17**, without renumbering. Preserve existing text models and text generation.
- Exclude original 15 YuE2, 18 large Wan, 19 newer LTX, 20 H3 and 21 ComfyUI infrastructure. Model/LoRA training is outside scope.
- All model records are equal peers. Use capability, runtime-dependency, format, device, installation and evidence tags/filters rather than model hierarchies or engine folders.
- Every generation stage executes on the same Android phone, without ROOT, Termux, an external inference server or a conversion service. HF access downloads explicitly selected assets; after installation, fresh inputs must work offline.
- Internal engine adapters and fixed pipelines are necessary implementation modules. Do not build a user node/plugin system or import ComfyUI graphs.

**Supported means a complete pinned bundle, a compatible packaged engine, valid parameters, fresh-input offline phone output, openable artifacts, cancellation/unloading, background ownership and reviewable device evidence.** Listing/tagging a repository, downloading weights or declaring a nonfunctional provider does not meet this definition. Experimental support also requires actual output.

These are 16 requirement groups, not 16 weight files. In particular, 03, 10 and 12 contain multiple subtargets. Overall completion requires every frozen subtarget; Nano in 09 does not substitute for 12, and a still-image MP4 does not substitute for 16/17.

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
| F-04 Internal engines | Lifecycle protocol, worker processes, version/dependency locks and crash isolation | Native code updates through signed APKs; model downloads contain data |
| F-05 Model settings | Per-model/recipe schema, editable presets, hard-limit correction and joint constraints | Text context, image steps/dimensions, video frames and audio settings remain independent; record effective values/reasons |
| F-06 Jobs/queue | Async submission, queueing, cancellation, ordered events, progress and bounded retries | Durable inputs/state; cancellation binds job and process launch generation |
| F-07 Admission/resources | Staged memory, shared RAM, disk, threads/GPU profiles and thermal policy | Default one heavy engine; distinguish measurements from estimates; no silent offloading/substitution |
| F-08 Background/recovery | Foreground service, visible notification/stop, scoped locks and restart reconciliation | UI closure does not cancel explicitly started jobs; resume only genuine engine checkpoints, otherwise rerun the stage |
| F-09 Artifacts | Image/WAV/video preview, settings/seed/provenance, save/export | Hashes and complete effective snapshots; distinguish still-image encoding from generative motion |
| F-10 API | Preserve text API; add local async jobs/events/cancel/authenticated artifacts | UI/API share scheduling and validation; video is not a text-token stream |
| F-11 Releases/migration | Native Windows NDK/CMake, ABI/SDK/dependencies, signing, migrations and regressions | No Docker/WSL/emulators; preserve old models/history/settings; consistent source/APK/evidence |
| F-12 Evidence/maintenance | Exact model/engine/device matrix, errors/resources, bilingual docs and feature media | Desktop fixtures, upstream reports and LMA phone results remain distinct |

No infinite canvas, wiring editor, user nodes, plugin marketplace, third-party Python nodes or ComfyUI JSON import. Internal encoding/sampling/decoding stages may have dependencies without exposing a general DAG. Earlier graph drafts are not current execution-interface commitments.

## 04 · Selected models and foundation requirements

These are target routes and engineering assessments. **Every new entry is currently unimplemented/unverified in LMA.** Engine names are proposed alternatives or architecture-specific choices, not installed capabilities. Full component tags and acceptance details are in the [scope JSON](proposals/multimodal-release-scope.json).

| Original ID | Model/route | Output tags | Engine route | Main gate | Proposed first version |
| --- | --- | --- | --- | --- | --- |
| 01 | Stable Diffusion 1.5 | image | `sd_cpp / mnn_diffusion` | Established mobile route; Z20 candidate | 0.3.0 |
| 02 | LoRA loading and management | image | `sd_cpp` | Requires a matching base; not standalone | 0.3.0 |
| 03 | SD-Turbo / LCM / LCM-LoRA | image | `sd_cpp` | Sampler/distillation-specific validation | 0.4.0 |
| 04 | Sana | image | `mnn_diffusion` | Match converted package and encoder | 0.4.0 |
| 05 | SDXL | image | `sd_cpp / mnn_diffusion` | Dual encoders and memory validation | 0.4.0 |
| 06 | Z-Image-Turbo | image | `sd_cpp` | High-memory quantized/staged experiment | 0.5.0 |
| 07 | FLUX.2-klein-4B | image | `sd_cpp` | Quantized full-pipeline experiment | 0.5.0 |
| 08 | Qwen-Image-2.1 | image | `sd_cpp` | High-memory and license gates | 0.5.0 |
| 09 | MOSS-TTS-Nano 100M | audio | `moss_nano_ort` | Complete arbitrary-input tokenizer/codec | 0.3.0 |
| 10 | Kokoro / Piper / Matcha | audio | `sherpa_tts` | Accept all three subroutes separately | 0.3.0 |
| 11 | Qwen3-TTS 0.6B Base | audio | `qwen_tts_litert / qwen_tts_native` | Android references; speed/API validation | 0.4.0 |
| 12 | Full MOSS family | audio | `moss_architecture_specific` | Multiple architecture research gates; no family-wide guarantee | 0.6.0 |
| 13 | SoulX-Podcast 1.7B | audio | `soulx_native_port` | Complete native Android port unproven | 0.6.0 |
| 14 | Stable Audio Open Small | audio | `stable_audio_litert` | Short sounds/music, not full songs | 0.4.0 |
| 16 | Wan 2.1 T2V 1.3B Q4 | video | `wan_sd_cpp` | Author Android evidence; local experiment | 0.3.0 |
| 17 | LTX-Video 2B 0.9.8 distilled | video | `ltx_vulkan_port / ltx_qnn_port` | Separate Vulkan/QNN and code-license gates | 0.5.0 |

Preserve the 14 existing built-in text records with text-generation tags, `llama_text`, single-component text GGUF recipes and existing independent settings. Migrate HF/imported records too, without changing their evidence. Derive runtime tags from recipes, not repository names.

## 05 · Subtargets and practical feasibility

**03:** Accept separate SD-Turbo (SD 2.1), LCM checkpoint and LCM-LoRA routes with matching bases. One working route does not establish all three. **10:** Pin and validate a distributable language/voice package for each of Kokoro, Piper and Matcha; this does not promise all languages or third-party voices.

**12:** Freeze nine current publisher subtargets: MOSS-TTS 1.0, v1.5, Local-Transformer, Local-Transformer-v1.5, TTSD-v1.0, VoiceGenerator, SoundEffect, SoundEffect-v2.0 and Realtime. Nano belongs to 09. These span Delay, Local, Realtime and a separate DiT pipeline. The upstream fully native Delay fork includes audio encoding/decoding and provides a porting starting point; it does not prove Android support for every architecture. [Publisher family list](https://github.com/OpenMOSS/MOSS-TTS#released-models), [native Delay pipeline](https://github.com/OpenMOSS/llama.cpp/blob/moss-tts-firstclass/docs/moss-tts-firstclass-e2e.md)

**13:** SoulX's official Linux/Python pipeline and partial ONNX files do not establish a complete Android host loop, tokenization, reference encoding, codec and multi-speaker timing. [SoulX model card](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B) Both 12 and 13 remain explicit requirements with native prototype gates. Phone resources/quality are unproven; failure must remain visible rather than being counted as completion or silently removed.

**06/07/08:** Account for encoders, VAE, activations and OS memory in addition to the quantized backbone. Start with newer high-memory devices. Qwen-Image-2.1's full chain cannot be budgeted as only 7B, and its Qwen Research License cannot inherit an earlier model's Apache terms. [Qwen components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/qwen_image_2.1.md), [model/license](https://huggingface.co/Qwen/Qwen-Image-2.1)

**11:** LiteRT Kotlin and native Android references exist; validate API requirements and speed separately. An upstream Pixel 8a example is not realtime, and does not promise realtime Z20 speech. **14:** The LiteRT route generates short sounds/music, not full songs. [Android Qwen TTS](https://github.com/google-ai-edge/litert-samples/tree/main/samples/litert/text_to_speech_lm), [Arm audio deployment](https://developer.arm.com/code-along/stable-audio-open-small)

**16/17:** Implementation-author Android routes justify actual on-phone video experiments. Port Wan's disk parameters, CPU text/VAE and Vulkan diffusion; desktop CUDA timing is not a phone benchmark. The old LTX 2B QNN bundle excludes Z20; validate Vulkan separately. Resolve LLM-Hub's noncommercial code terms and independent QNN/model redistribution terms before integration; do not absorb the whole project into MIT LMA. [Wan implementation](https://github.com/SaientAI/saient/blob/main/docs/VIDEO_PIPELINE.md), [LTX conversion](https://huggingface.co/timmyboy26/LTX-Video-2B-0.9.8-distilled-QNN), [code license](https://github.com/timmyy123/LLM-Hub/blob/main/LICENSE)

See [broader source research](MULTIMODAL.en.md). License gates apply to every selected component; an open-model description is not a redistribution/commercial-use determination.

## 06 · User flow

1. Install/upgrade LMA and open one model library. Keep Recommended and filter by text/image/video/audio, name, installation or compatibility.
2. Open details for capabilities, foundation dependencies, total component download and device state. Select a compatible quantization/device recipe and download. Missing engine support identifies a required app version; downloading model data does not install execution code.
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

## 08 · Proposed releases

These are **proposed versions, not published Releases or Manifest changes**. Later releases extend accepted earlier scope. Phases express engineering dependencies, not model ranks.

| Version | Required scope | Release gate |
| --- | --- | --- |
| **0.3.0: complete core and first cross-modality execution** | F-01–F-12; existing text; 01/02/09/10/16 | Common bundles/queue/settings/artifacts/API execute text, image, audio and real generative video; Wan may be device-limited experimental but must produce output; legacy migration passes |
| **0.4.0: mobile images/audio** | 03/04/05/11/14; SDXL LoRA | Each subroute, full components, devices/backends, quality/resources; 10's three packages cannot be replaced by one |
| **0.5.0: high-memory images and second video architecture** | 06/07/08/17 | Complete pipelines/quantization; Qwen license; explicit Vulkan or distributable QNN LTX coverage, without requiring both backends to pass |
| **0.6.0: research-gated speech families** | Nine frozen 12 subtargets; 13 | Prototypes followed by complete Android/codec/host-loop acceptance; any failed target leaves overall 16-group scope incomplete, not catalogue-only complete |

Each may have alpha/beta previews. Only real device evidence permits experimentally tested/device-validated states. Without devices, explicitly scoped developer previews are possible but do not meet final acceptance. Current evidence cannot guarantee one fully tested release containing all 16 groups, especially 12/13.

## 09 · Work breakdown and estimation

| Package | Difficulty/uncertainty | Dependency and output |
| --- | --- | --- |
| W1 Scope/tags/components/migration | Medium, defined boundaries | Existing text mapping, flat filters, schemas and compatible migration |
| W2 Native build/engine protocol/processes | High, upstream risk | Repeatable Windows builds, ABI/SDK/native dependencies/signing |
| W3 Installation/recipes/settings | High, state consistency | Shared components, resume, space plans and joint model/backend constraints |
| W4 Jobs/resources/background/API | High, lifecycle risk | Single heavy engine, durable queue, cancel/timeouts, recovery/events |
| W5 Cross-modality/all pipelines | Very high, main continuing cost | Validate 01/09/10/16 on the shared chain, then expand via the four-release map |
| W6 Devices/media/releases | High, physical evidence required | Compatibility matrix, quality/memory/timing/screen-off, upgrades and release notes |

Run risky prototypes early: native Android Wan build/output; MOSS native Delay and differences for Local/Realtime/DiT; complete SoulX native portability; and 08 full-bundle memory/license. Do not wait until after 0.5.0 to discover missing 0.6.0 architecture support.

No physical device is available, and complete 12/13 Android paths remain unproven. Do not invent fixed person-days or calendar promises. Module boundaries, release order and dependencies can be fixed now; prototype/device results determine performance, peak RAM and uncertain porting estimates. Removing canvas/plugins reduces UI/compatibility/distribution work, not generation compute.

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
- **A10 Whole scope:** all 16 groups and frozen subtargets pass individually. Entries/downloads do not count. Failed targets remain tracked; scope changes require an explicit record.

A1–A4 rules and some migrations permit desktop checks. A5–A8 require physical Android evidence, currently zero. `multimodal-release-scope.json` is a reviewable requirements snapshot, not the production catalogue, a download lock or a test report.

## 11 · This update

This update delivers requirements, numbering, tags, feasibility, four-release scope, risks/acceptance and revised design boundaries, with synchronized bilingual READMEs, index, changelog and maintenance notes. It implements no new engine, changes no APK, adds no phone evidence and publishes no proposed version. Earlier canvas/node work is withdrawn from current requirements. The current target interaction is **flat library → task form → on-phone queue → artifact library**.
