# Community image/video models and content labels

[中文](COMMUNITY_MODELS.md) · [README](../README.en.md) · [Release v0.3.1](releases/v0.3.1.md)

v0.3.1 adds **44 optional checkpoint recipes across 14 families: 30 image variants and 14 video variants**. Of these, **28 carry sourced NSFW labels: 14 image variants and 14 video variants across 8 families**. One entry has only an HF sensitive-audience flag; 15 have insufficient content declarations. The complete registered catalogue contains 67 recipes. Counts describe selected checkpoint variants, not independent architectures.

All entries remain peers. Output task, architecture, engine, dependencies, content declaration, installation and evidence are independent. Recommended remains exactly **m08 → m06 → m01**. The APK contains program code and metadata; users explicitly obtain every checkpoint and dependency. All inference stays on the Android phone.

## Use the catalogue

1. Open Models → All. Choose **Registered recipes** to browse the signed offline catalogue, or keep All sources / HF search for arbitrary repositories. Registered recipes are independent of the HF format filter.
2. Combine Image / Video with **NSFW**, **Sensitive HF metadata**, or **Unclassified**. An exact NSFW keyword search matches the classification rather than negative statements in descriptions.
3. Open **Source, content label and compatibility**. Review the publisher or mirror, pinned revision, license, required engine, component roles and limitations. Then open the existing model manager to review the download.
4. Click Download explicitly. Only that package and its disclosed dependencies enter the normal resumable transfer manager. Matching component hashes are reused; selecting a family never downloads all its versions.
5. Use Local to inspect downloaded models and unfinished transfers, pause/resume/delete files, or edit that recipe’s independent settings. Existing numeric presets remain editable and bounded; content filters do not change settings.
6. Select Use to prepare a local task, review the parameters, and submit it to the shared queue. Cancellation, result management and the local API retain their existing behavior.

## What a label means

| Label | Evidence and boundary |
| --- | --- |
| NSFW · source declaration | An explicit statement in the pinned publisher card; not measured output quality. |
| NSFW · rating vocabulary | The publisher documents NSFW rating classes; no example outputs or prompts are bundled. |
| NSFW · file marker | The publisher’s selected weight filename explicitly contains NSFW. |
| NSFW · mirror declaration | A mirror reproduces a declaration; this is not confirmation by the original author. |
| NSFW · HF tag / name hint | Live search metadata only; no individually checked architecture, weight or publisher declaration. |
| Sensitive · HF tag | `not-for-all-audiences`; this broader flag alone does not confirm NSFW generation capability. |
| Unclassified | No sufficient declaration was found. This does not assert SFW behavior. |

The independent Uncensored / Abliterated text-model labels are preserved. An unfiltered architecture or a missing safety checker does not automatically assign an NSFW label. HF explains author-provided model-card metadata in its [official guide](https://huggingface.co/docs/hub/model-cards).

## Registered families

| # | Family | Variants | NSFW variants | Output | Route |
| --- | --- | ---: | ---: | --- | --- |
| 01 | [DreamShaper](https://huggingface.co/Lykon/DreamShaper) | 1 | 0 | Image | sd15 / cpu |
| 02 | [Realistic Vision](https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE) | 2 | 1 | Image | sd15 / cpu |
| 03 | [RealVisXL](https://huggingface.co/SG161222/RealVisXL_V3.0) | 3 | 3 | Image | sdxl / cpu |
| 04 | [Juggernaut](https://huggingface.co/RunDiffusion/Juggernaut-XL-v9) | 3 | 1 | Image | sdxl / cpu |
| 05 | [NoobAI](https://huggingface.co/Laxhar/noobai-XL-1.1) | 1 | 0 | Image | sdxl / cpu |
| 06 | [Illustrious](https://huggingface.co/OnomaAIResearch/Illustrious-xl-early-release-v0) | 4 | 0 | Image | sdxl / cpu |
| 07 | [Animagine](https://huggingface.co/cagliostrolab/animagine-xl-3.1) | 3 | 2 | Image | sdxl / cpu |
| 08 | [CyberRealistic](https://huggingface.co/cyberdelia/CyberRealistic) | 3 | 0 | Image | sd15 / cpu |
| 09 | [CyberIllustrious](https://huggingface.co/cyberdelia/CyberIllustrious) | 1 | 0 | Image | sdxl / cpu |
| 10 | [Pony Diffusion](https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL) | 1 | 1 | Image | sdxl / cpu |
| 11 | [Kohaku](https://huggingface.co/KBlueLeaf/Kohaku-XL-Zeta) | 2 | 1 | Image | sdxl / cpu |
| 12 | [OrangeMix](https://huggingface.co/WarriorMama777/OrangeMixs) | 5 | 5 | Image | sd15 / cpu |
| 13 | [Counterfeit](https://huggingface.co/gsdf/Counterfeit-V3.0) | 1 | 0 | Image | sd15 / cpu |
| 14 | [NSFW Wan 1.3B](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b) | 14 | 14 | Video | wan21 / vulkan |

## Compatibility and resource boundaries

- SD 1.5 / SDXL recipes use complete checkpoints with their required CLIP data on the existing CPU engine. Realistic Vision no-VAE variants explicitly include the separately pinned SD VAE MSE dependency. Existing SD1.5/SDXL image-LoRA pairing remains available.
- All 14 video recipes use **Wan 2.1 T2V 1.3B** with the current on-phone Vulkan engine, shared UMT5 encoder, tokenizer and Wan VAE. EXP E01–E14 are one family’s training versions. The source recommends E14; LMA has not measured their quality. The author reports degradation in legacy checkpoints; they are not pre-registered here. See the [publisher card](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b).
- Wan 14B, I2V, Wan 2.2, video LoRA and newer LTX 2.x/2.3 families are **not integrated by these recipes**. The older motion helper targets earlier Wan checkpoints and is not required by the EXP series. Their repositories can still be discovered through HF. [Survey](../research/community/compatibility-survey.json) records concrete rejected routes; discovery is not execution support.
- The current LTX engine remains the separate older 0.9.8 route. Qwen-Image / Z-Image base routes remain available, but an unrelated fine-tune or LoRA needs explicit matching architecture and component rules.
- Header checks establish checkpoint layout, cross-attention shape or Wan layer/patch geometry. They do not prove prediction semantics, output quality, peak RAM or Android driver compatibility. Model-card-specific settings may need adjustment; only the current parameter schemas are exposed.
- No physical phone was available. Full SDXL checkpoints and multi-component video packages can exceed practical resources on a Nubia Z20. Do not interpret file size as peak RAM or a running-device guarantee. The local resource checks remain in force.

## Provenance, licenses and maintenance

Review [source selection](../catalogue/community-sources.json), [bounded API/header evidence](../research/community/metadata.json), [generated packages](../catalogue/community-bundles.json), and [component proofs](../catalogue/community-bundle-evidence.json). The 27 repositories include one dependency-only VAE source. Evidence stores pinned revisions, file sizes, publisher LFS SHA256, card hashes/short markers and header hashes/architecture checks; it contains no weights, previews or copied galleries.
Pony V6 is explicitly a mirror. Its HF license field conflicts with the reproduced modified Fair AI terms; the UI highlights that conflict and points to the original author. Never treat an HF license identifier as a complete commercial grant. Juggernaut versions and other families also retain their individual license declarations; APK licensing does not replace weight licenses.
Generate offline with `python tools/community_catalogue.py` followed by `python tools/build_bundle_catalogue.py`. A deliberate metadata refresh uses `--refresh --origin https://huggingface.co` (or the disclosed HF mirror). The tool requests only API/card data and exact safetensors header ranges, rejecting a server that ignores Range. Manifest IDs include a content hash so a changed declaration cannot overwrite an immutable installed recipe. Existing weights/settings remain user-controlled.

## Program evidence and UI recording

The dedicated catalogue/production-Java suite checks all 44 optional recipes, independent parameter limits, output routes, content provenance, unsafe source URLs, and content propagation into user-created HF recipes. The UI checks filtering, explicit downloads, Local persistence, source review and narrow layouts. No complete trained model was downloaded, copied or executed; no phone, output-quality or endurance pass is claimed.

![Community image catalogue](media/development/community/01-community-images.png)
![Pinned video source and component review](media/development/community/04-video-source.png)
![UI-only interaction recording](media/development/community/community-ui.gif)
[MP4 recording](media/development/community/community-ui.mp4) · [Capture manifest](media/development/community/manifest.json)

## Exact selected files

| # | Variant | Size GiB | Content basis | Source file |
| --- | --- | ---: | --- | --- |
| 01 | DreamShaper 8 | 1.99 | none | [DreamShaper_8_pruned.safetensors](https://huggingface.co/Lykon/DreamShaper/blob/228d79cb20811466f5c5710aa91f05dabd0b8a14/DreamShaper_8_pruned.safetensors) |
| 02 | Realistic Vision 6.0 B1 FP16 | 1.99 | publisher_card | [Realistic_Vision_V6.0_NV_B1_fp16.safetensors](https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE/blob/9a857a696b9aabbf509073e0aa55ec8200b6ef7d/Realistic_Vision_V6.0_NV_B1_fp16.safetensors) |
| 03 | Realistic Vision 5.1 FP16 | 1.99 | none | [Realistic_Vision_V5.1_fp16-no-ema.safetensors](https://huggingface.co/SG161222/Realistic_Vision_V5.1_noVAE/blob/1e9f017a7b1eaefb63a1900ea6c5953d2739fd21/Realistic_Vision_V5.1_fp16-no-ema.safetensors) |
| 04 | RealVisXL 3.0 | 6.46 | publisher_card | [RealVisXL_V3.0.safetensors](https://huggingface.co/SG161222/RealVisXL_V3.0/blob/5dd66d6fe796ff7b5a31595e5d0ac2f6a39e7ad9/RealVisXL_V3.0.safetensors) |
| 05 | RealVisXL 4.0 | 6.46 | publisher_card | [RealVisXL_V4.0.safetensors](https://huggingface.co/SG161222/RealVisXL_V4.0/blob/26dfe44930964cd70d0a817b6d1cc945c130e38d/RealVisXL_V4.0.safetensors) |
| 06 | RealVisXL 5.0 | 6.46 | publisher_card | [RealVisXL_V5.0_fp16.safetensors](https://huggingface.co/SG161222/RealVisXL_V5.0/blob/ac93e0dda1f6d448cae19bbfab8c5e720a5e48bc/RealVisXL_V5.0_fp16.safetensors) |
| 07 | Juggernaut 9 | 6.62 | none | [Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors](https://huggingface.co/RunDiffusion/Juggernaut-XL-v9/blob/cf419233522daa0b9ea36c3aff98fa2cab1fb0fb/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors) |
| 08 | Juggernaut X | 6.62 | publisher_filename | [Juggernaut-X-RunDiffusion-NSFW.safetensors](https://huggingface.co/RunDiffusion/Juggernaut-X-v10/blob/35e4f3ccbe745c3e1221715d04a452aaa1ee5761/Juggernaut-X-RunDiffusion-NSFW.safetensors) |
| 09 | Juggernaut XI | 6.62 | none | [Juggernaut-XI-byRunDiffusion.safetensors](https://huggingface.co/RunDiffusion/Juggernaut-XI-v11/blob/f836518c7a75f47a9e26bc661ff9509ef2ceb7c0/Juggernaut-XI-byRunDiffusion.safetensors) |
| 10 | NoobAI XL 1.1 | 6.62 | hf_sensitive_tag | [NoobAI-XL-v1.1.safetensors](https://huggingface.co/Laxhar/noobai-XL-1.1/blob/814a274af2b8097c0828819d561ec74c7d0c6cea/NoobAI-XL-v1.1.safetensors) |
| 11 | Illustrious XL 0.1 | 6.46 | none | [Illustrious-XL-v0.1.safetensors](https://huggingface.co/OnomaAIResearch/Illustrious-xl-early-release-v0/blob/dca0dac303e6dc4b0c31d8001bc685b89b5d0204/Illustrious-XL-v0.1.safetensors) |
| 12 | Illustrious XL 1.0 | 6.46 | none | [Illustrious-XL-v1.0.safetensors](https://huggingface.co/OnomaAIResearch/Illustrious-XL-v1.0/blob/89d625482edf06d545b740265482f5c8fb2cadb0/Illustrious-XL-v1.0.safetensors) |
| 13 | Illustrious XL 1.1 | 6.46 | none | [Illustrious-XL-v1.1.safetensors](https://huggingface.co/OnomaAIResearch/Illustrious-XL-v1.1/blob/8d966ec810874502d56a22ec9130dab6ef74c5ff/Illustrious-XL-v1.1.safetensors) |
| 14 | Illustrious XL 2.0 | 6.46 | none | [Illustrious-XL-v2.0.safetensors](https://huggingface.co/OnomaAIResearch/Illustrious-XL-v2.0/blob/69459c1fe6f46db41ab31e6114f05acc0e06bcaa/Illustrious-XL-v2.0.safetensors) |
| 15 | Animagine XL 3.1 | 6.46 | none | [animagine-xl-3.1.safetensors](https://huggingface.co/cagliostrolab/animagine-xl-3.1/blob/483f0c322568ed13697ed01dd0be07204746d12b/animagine-xl-3.1.safetensors) |
| 16 | Animagine XL 4.0 | 6.46 | publisher_rating | [animagine-xl-4.0.safetensors](https://huggingface.co/cagliostrolab/animagine-xl-4.0/blob/2b7c1b397761bf5bd3cc42e5b39ec99314a75a96/animagine-xl-4.0.safetensors) |
| 17 | Animagine XL 4.0 OPT | 6.46 | publisher_rating | [animagine-xl-4.0-opt.safetensors](https://huggingface.co/cagliostrolab/animagine-xl-4.0/blob/2b7c1b397761bf5bd3cc42e5b39ec99314a75a96/animagine-xl-4.0-opt.safetensors) |
| 18 | CyberRealistic 9 FP16 | 1.99 | none | [CyberRealistic_V9_FP16.safetensors](https://huggingface.co/cyberdelia/CyberRealistic/blob/99827f96edd717dacb28c68560680c201c55df05/CyberRealistic_V9_FP16.safetensors) |
| 19 | CyberRealistic XL 10 FP16 | 6.46 | none | [CyberRealisticXLPlay_V10.0_FP16.safetensors](https://huggingface.co/cyberdelia/CyberRealisticXL/blob/c04ae13b465d19763561a834d625a3d504a4f315/CyberRealisticXLPlay_V10.0_FP16.safetensors) |
| 20 | CyberRealistic Pony 18 F16 | 6.46 | none | [CyberRealisticPony_V18.0_F16.safetensors](https://huggingface.co/cyberdelia/CyberRealisticPony/blob/bf85880a58614199d0391c93151211be2832bb8c/CyberRealisticPony_V18.0_F16.safetensors) |
| 21 | CyberIllustrious 10 FP16 | 6.46 | none | [CyberIllustrious_V10_FP16.safetensors](https://huggingface.co/cyberdelia/CyberIllustrious/blob/8a6f01bba289d7e76f3123c01f0a16ef742fd771/CyberIllustrious_V10_FP16.safetensors) |
| 22 | Pony Diffusion V6 XL | 6.46 | mirror_card | [ponyDiffusionV6XL_v6StartWithThisOne.safetensors](https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL/blob/14885f1c01d7723bcbf676773def286c1fd733bc/ponyDiffusionV6XL_v6StartWithThisOne.safetensors) |
| 23 | Kohaku XL Zeta | 6.46 | publisher_rating | [kohaku-xl-zeta.safetensors](https://huggingface.co/KBlueLeaf/Kohaku-XL-Zeta/blob/c14affd9483ac7603cfff3f06b05da22a06deaa6/kohaku-xl-zeta.safetensors) |
| 24 | Kohaku XL Epsilon rev3 | 6.46 | none | [kohaku-xl-epsilon-rev3.safetensors](https://huggingface.co/KBlueLeaf/Kohaku-XL-Epsilon-rev3/blob/680841c3ca6283b7795db608315c4472304648d4/kohaku-xl-epsilon-rev3.safetensors) |
| 25 | AbyssOrangeMix 2 NSFW FP16 | 1.99 | publisher_card | [Models/AbyssOrangeMix2/Pruned/AbyssOrangeMix2_nsfw_pruned_fp16_with_VAE.safetensors](https://huggingface.co/WarriorMama777/OrangeMixs/blob/ec9df50045e9687fd7ea8116db84c4ad5c4a4358/Models/AbyssOrangeMix2/Pruned/AbyssOrangeMix2_nsfw_pruned_fp16_with_VAE.safetensors) |
| 26 | AbyssOrangeMix 3 A1B | 1.99 | publisher_card | [Models/AbyssOrangeMix3/AOM3A1B_orangemixs.safetensors](https://huggingface.co/WarriorMama777/OrangeMixs/blob/ec9df50045e9687fd7ea8116db84c4ad5c4a4358/Models/AbyssOrangeMix3/AOM3A1B_orangemixs.safetensors) |
| 27 | AbyssOrangeMix 3 A1 | 1.99 | publisher_card | [Models/AbyssOrangeMix3/AOM3A1_orangemixs.safetensors](https://huggingface.co/WarriorMama777/OrangeMixs/blob/ec9df50045e9687fd7ea8116db84c4ad5c4a4358/Models/AbyssOrangeMix3/AOM3A1_orangemixs.safetensors) |
| 28 | AbyssOrangeMix 3 A3 | 1.99 | publisher_card | [Models/AbyssOrangeMix3/AOM3A3_orangemixs.safetensors](https://huggingface.co/WarriorMama777/OrangeMixs/blob/ec9df50045e9687fd7ea8116db84c4ad5c4a4358/Models/AbyssOrangeMix3/AOM3A3_orangemixs.safetensors) |
| 29 | VividOrangeMix NSFW | 1.99 | publisher_card | [Models/VividOrangeMix/VividOrengeMix_NSFW.safetensors](https://huggingface.co/WarriorMama777/OrangeMixs/blob/ec9df50045e9687fd7ea8116db84c4ad5c4a4358/Models/VividOrangeMix/VividOrengeMix_NSFW.safetensors) |
| 30 | Counterfeit 3 FP16 | 3.95 | none | [Counterfeit-V3.0_fp16.safetensors](https://huggingface.co/gsdf/Counterfeit-V3.0/blob/d8ce63b3eb8e9102e54b3fcc07f9cb7a28ef30fc/Counterfeit-V3.0_fp16.safetensors) |
| 31 | NSFW Wan 1.3B · EXP E01 | 2.64 | publisher_card | [wan_1.3B_exp_e1.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e1.safetensors) |
| 32 | NSFW Wan 1.3B · EXP E02 | 2.64 | publisher_card | [wan_1.3B_exp_e2.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e2.safetensors) |
| 33 | NSFW Wan 1.3B · EXP E03 | 2.64 | publisher_card | [wan_1.3B_exp_e3.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e3.safetensors) |
| 34 | NSFW Wan 1.3B · EXP E04 | 2.64 | publisher_card | [wan_1.3B_exp_e4.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e4.safetensors) |
| 35 | NSFW Wan 1.3B · EXP E05 | 2.64 | publisher_card | [wan_1.3B_exp_e5.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e5.safetensors) |
| 36 | NSFW Wan 1.3B · EXP E06 | 2.64 | publisher_card | [wan_1.3B_exp_e6.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e6.safetensors) |
| 37 | NSFW Wan 1.3B · EXP E07 | 2.64 | publisher_card | [wan_1.3B_exp_e7.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e7.safetensors) |
| 38 | NSFW Wan 1.3B · EXP E08 | 2.64 | publisher_card | [wan_1.3B_exp_e8.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e8.safetensors) |
| 39 | NSFW Wan 1.3B · EXP E09 | 2.64 | publisher_card | [wan_1.3B_exp_e9.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e9.safetensors) |
| 40 | NSFW Wan 1.3B · EXP E10 | 2.64 | publisher_card | [wan_1.3B_exp_e10.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e10.safetensors) |
| 41 | NSFW Wan 1.3B · EXP E11 | 2.64 | publisher_card | [wan_1.3B_exp_e11.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e11.safetensors) |
| 42 | NSFW Wan 1.3B · EXP E12 | 2.64 | publisher_card | [wan_1.3B_exp_e12.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e12.safetensors) |
| 43 | NSFW Wan 1.3B · EXP E13 | 2.64 | publisher_card | [wan_1.3B_exp_e13.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e13.safetensors) |
| 44 | NSFW Wan 1.3B · EXP E14 | 2.64 | publisher_card | [wan_1.3B_exp_e14.safetensors](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b/blob/4d8db25317335b4a0cfbefad9877b893f08dbc67/wan_1.3B_exp_e14.safetensors) |

## Metadata contract

The optional `content` object in a model bundle contains `classification` (`nsfw`, `sensitive`, `unclassified`), `basis` (the evidence classes above), a short `summary`, `sourceUrl`, optional pinned `sourceRevision`, `checkedAt`, and `modelQualityTested: false`. Native `ContentMetadata` checks classification/basis combinations and public-source URLs. `ModelBundle.tags().content` exposes independent `content:*` and `content_basis:*` tags. HF component selection propagates the same metadata through `RecipeCatalogue`; declaration changes contribute to its immutable recipe identity.
