# Curated diffusion selection, dependencies and task flow

FLUX.2-klein 4B now has an optional complete four-component catalogue flow and matching HF suggestions. [User flow, parameters and evidence](FLUX2_KLEIN.en.md). The App ships foundation code only; downloads remain explicit.

[中文](CURATED_DIFFUSION.md) · [User guide](USER_GUIDE.en.md) · [Numbered delivery and full pending scope](releases/v0.3.0-dev.32.md)

**0.3.0-dev.32 / code 36** brings six exact asset sets with existing complete trained-host records into Models → All and adds generic LoRA base-model review. App installation and upgrades deliver foundation code and metadata. They include no weights or learned tokenizer data and start no model downloads. This is an internal checkpoint; the complete v0.3.0 scope remains required.

## 1. Optional profiles

Every profile is a peer, with independent image/task, architecture, engine, LoRA and base-dependency tags. Recommended remains **m08 → m06 → m01**. HF All/search and custom recipe selection remain available. This does not declare every HF model runnable on Android.

| ID | Profile in All | Complete package bytes | Additional dependency |
|---|---|---:|---|
| C01 | [SDXL Base 1.0 Q4_0 / genai-archive](https://huggingface.co/genai-archive/stable-diffusion-xl-base-1.0-gguf) | 2,598,564,107 | Complete checkpoint and separately disclosed CLIP merges |
| C02 | [PixelArtRedmond SD 1.5](https://huggingface.co/artificialguybr/pixelartredmond-1-5v-pixel-art-loras-for-sd-1-5) | 27,216,848 | Choose an SD 1.5 base separately; publisher prompt guidance includes `pixel art, PixArFK` |
| C03 | [Pixel Art XL / nerijs](https://huggingface.co/nerijs/pixel-art-xl) | 170,543,052 | Choose an SDXL base separately; publisher requires no special trigger |
| C04 | [LCM-LoRA SD 1.5](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5) | 134,621,556 | Choose an SD 1.5 base separately and use the explicit LCM job policy |
| C05 | [LCM-LoRA SDXL](https://huggingface.co/latent-consistency/lcm-lora-sdxl) | 393,855,224 | Choose an SDXL base separately and use the explicit LCM job policy |
| C06 | [SD-Turbo Q8_0 / Green-Sky](https://huggingface.co/Green-Sky/SD-Turbo-GGUF) | 2,024,269,995 | Complete checkpoint and separately disclosed CLIP merges |

These are file totals; **LoRA rows exclude the separately selected base**. Existing fully hash-verified identical objects can be reused. Details show remaining transfer bytes. File size is not peak runtime memory: phone peak resources remain unknown for all six profiles, with no Nubia Z20 fit claim.

## 2. User flow

1. Open Models → All and filter by image generation. Review a profile's license, complete components, storage and reusable files. Browsing only reads metadata.
2. For a base or standalone SD-Turbo, explicitly choose Download selected package or import a complete folder. Only disclosed package components are requested.
3. A LoRA detail shows compatible bases already known to the library and their missing, incomplete-transfer, installed or in-use state. View base model opens its full details; Return to LoRA goes back. **Downloading a LoRA does not download its base.** Choose that base's download or import separately.
4. Local manages downloaded models and unfinished transfers. If the LoRA is installed but its base is missing, pairing blocks submission and links directly to base review. Once installed, select a compatible base. Architecture, recipe, backend and declared model identity constraints exclude incompatible peers.
5. Save defaults in each local model's settings. The task form allows editable LoRA strength and returns excessive values to that profile's ceiling. Task edits preserve saved defaults. Style and LCM adapters retain their individual schemas.
6. Enter a prompt, review parameters and submit explicitly. The shared local queue freezes the base, adapters, individual strengths and sampling parameters. LCM-LoRA uses 1–8 steps, CFG 1 and an empty negative prompt. SD-Turbo uses 1–4 steps, CFG 1, an empty negative prompt and Euler ancestral. Saved base settings remain independent.
7. Use existing task details, cancellation, explicit retry, resource protection and artifacts. Generation, decoding and media processing execute on the same phone. Missing assets neither trigger downloads nor move execution elsewhere. This checkpoint's UI recording demonstrates request queuing; actual trained images retain their separate historical host scope.

## 3. Upgrades, asset identities and terms

The six profiles use fresh immutable bundle/model IDs in the [shipped catalogue](../catalogue/model-bundles.json). Previously imported research manifests keep their original identities, settings and task records. New descriptions do not overwrite old IDs. New SD 1.5 adapters explicitly allow the existing App base `sd15_ss_q4_0_r031b5f5` and its older imported identity. New SDXL adapters allow the new curated SDXL base and the old research identity. Production Java/native pairing still enforces the declared constraints.

Publisher card metadata declares CreativeML OpenRAIL-M for the SDXL quantization, while upstream SDXL declares Open RAIL++; bespoke LoRA terms for PixelArtRedmond; CreativeML OpenRAIL-M for Pixel Art XL; Open RAIL++ for both LCM adapters; and the Stability AI Community License Agreement for the SD-Turbo quantization. See each publisher link above, the [SDXL/LoRA terms record](SD_VARIANTS_TRAINED.en.md) and [SD-Turbo terms record](SD_DISTILLED_TRAINED.en.md). These separate declarations do not replace per-component/upstream review or grant blanket redistribution rights. No original model data enters the APK, Git or source archives.

Accessible public publisher cards were rechecked on 2026-10-30. Direct pinned-revision API requests timed out; this update did not download trained weights or freshly verify pinned file availability. [Component evidence](../catalogue/bundle-evidence.json) binds exact URLs, revisions, sizes and SHA values to the original locks and host records, with that limitation explicit. The builder verifies those historical files' hashes without presenting their trained results as current execution.

## 4. Evidence and media

| ID | Current check | Scope |
|---|---|---|
| V01 | 55 added production storage checks | Old imports coexist with 16 catalogue entries; settings survive reopening; exact components; zero automatic transfers; compatible and incompatible SD 1.5/SDXL pairing |
| V02 | 40 UI checks | All four LoRAs: dependencies, explicit download intent, installed-state fixtures, pairing, clamping and frozen queued requests; no actual download or inference |
| V03 | Original-signed arm64 APK and current regressions | Android compilation/package audit, source business controls and UI evidence; no physical-device acceptance |
| V04 | Separately retained complete trained-host records | [SDXL, both style/LCM adapter architectures](SD_VARIANTS_TRAINED.en.md) and [SD-Turbo](SD_DISTILLED_TRAINED.en.md); model math was not rerun for this metadata/UI change |

| LoRA dependency review — desktop UI fixture | Paired task — desktop UI fixture |
|---|---|
| ![SDXL LoRA dependencies](media/development/curated/01-dependency-review.png) | ![Paired task and individual strength](media/development/curated/03-paired-task.png) |

[Base details](media/development/curated/02-base-review.png) · [Task queue](media/development/curated/04-queued-task.png) · [MP4](media/development/curated/curated-ui.mp4) · [GIF](media/development/curated/curated-ui.gif) · [Original media receipt](media/development/curated/manifest.json). Every recording is labelled UI FIXTURE, closes its browser and downloads/packages no model data.

The complete version still requires F01–F12, existing text, every frozen subtarget in 01–14/16/17, trained quality/resources and same-phone Android acceptance. The original LCM maximum pixel error 8 > 5 and six old-LTX numerical failures remain failed. See the [full numbered pending scope](releases/v0.3.0-dev.32.md).
