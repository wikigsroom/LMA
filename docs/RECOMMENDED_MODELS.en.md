# Recommended models and first use · v0.3.8

[中文](RECOMMENDED_MODELS.md) · [User guide](USER_GUIDE.en.md) · [Release notes](releases/v0.3.8.md)

Models opens on Recommended with **14 choices**: three text, three image, two video, three audio and three 3D. The original text prefix `m08 → m06 → m01`, labels and provenance stay first. Eleven additions select existing entries from the 82-bundle catalogue. No weights enter the APK; Recommended, All and Local share identities and management.

## 1. Choices

Sizes use decimal MB/GB and sum all required pinned components. Verified shared assets may be reused; details show remaining transfers. Download size is not runtime RAM. Precision in a name does not imply every companion uses that precision.

| ID | Task | Model / configuration | Complete download | Foundation / backend | Reason and conditions | Content tag |
| --- | --- | --- | --- | --- | --- | --- |
| M01 | text | Qwen3 1.7B Abliterated · `m08` | 1.11 GB | llama.cpp / CPU | Existing Chinese choice | Original evidence retained |
| M02 | text | LFM2.5 1.2B Uncensored · `m06` | 731 MB | llama.cpp / CPU | Existing lightweight choice | Original evidence retained |
| M03 | text | Dolphin3 Qwen0.5B Uncensored · `m01` | About 400 MB | llama.cpp / CPU | Existing smaller choice | Original evidence retained |
| M04 | image | [SD-Turbo Q8_0](https://huggingface.co/Green-Sky/SD-Turbo-GGUF) | 2.02 GB | sd_cpp / CPU | Few-step generation, start at 512px | No new NSFW claim |
| M05 | image | [Realistic Vision 6.0 B1 FP16](https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE) | 2.47 GB | sd_cpp / CPU | SD1.5 realistic style, required VAE included | NSFW · sourced declaration |
| M06 | image | [AbyssOrangeMix2 NSFW FP16](https://huggingface.co/WarriorMama777/OrangeMixs) | 2.13 GB | sd_cpp / CPU | SD1.5 illustration style | NSFW · sourced declaration |
| M07 | video | [Wan2.1 1.3B Q4](https://huggingface.co/off-grid-ai/Wan2.1-T2V-1.3B-GGUF) | 4.74 GB | wan_sd_cpp / Vulkan | Short clips; Vulkan and substantial RAM | No new NSFW claim |
| M08 | video | [NSFW Wan EXP E14](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b) | 6.76 GB | wan_sd_cpp / Vulkan | Community checkpoint; substantial RAM | NSFW · sourced declaration |
| M09 | audio | [MeloTTS Chinese INT8](https://huggingface.co/csukuangfj/vits-melo-tts-zh_en) | 60.6 MB | sherpa_tts / CPU | Chinese/English, single female voice | No new NSFW claim |
| M10 | audio | [Kokoro82M INT8 English](https://huggingface.co/csukuangfj/kokoro-int8-multi-lang-v1_0) | 148.7 MB | sherpa_tts / CPU | Adapted English multi-voice profile | No new NSFW claim |
| M11 | audio | [OmniVoice Q8 GGUF](https://huggingface.co/audio-cpp/audio.cpp-gguf) | 1.35 GB | audio_cpp / CPU | Auto/reference/design voice controls | No new NSFW claim |
| M12 | 3D | [TRELLIS.2 geometry512](https://huggingface.co/ilintar/trellis2-gguf) | 2.63 GB | trellis_native / CPU | Single image to untextured GLB, long CPU task | No new NSFW claim |
| M13 | 3D | [TRELLIS.2 PBR512](https://huggingface.co/ilintar/trellis2-gguf) | 4.20 GB | trellis_native / CPU | Single image to PBR GLB, long CPU task | No new NSFW claim |
| M14 | 3D | [Pixal3D geometry512](https://huggingface.co/vegax87/Pixal3D) | 6.62 GB | trellis_native / CPU | Larger geometry choice; substantial RAM | No new NSFW claim |

Both video choices use Wan2.1 1.3B; E14 is a different checkpoint, not a second architecture. TRELLIS geometry/PBR are configurations of one architecture. Pixal also reuses TRELLIS encoders, with per-component provenance preserved. Kokoro accepts the adapted English profile; OmniVoice multilingual controls do not establish every language as verified.

## 2. User flow

1. Install/upgrade and open Models → Recommended. Task buttons show counts; selecting a task filters equal model cards.
2. Inspect task, architecture, engine, companions, license, pinned revision/SHA256, complete size and resource hints. NSFW is an independent sourced label, not output inspection or a quality claim.
3. Only explicit Download starts the selected bundle and disclosed required dependencies. Shared files are verified and reused. Browsing, filtering, details, installation and upgrades never download weights. Missing assets do not trigger hidden downloads.
4. Local manages transfers, pause/resume/verification/delete/import and independently saved editable settings. Recommended and Local refer to the same bundle.
5. After installation choose Use, fill the task form, attach same-phone references, review preflight and explicitly submit. Start video at low resolution/short duration. 3D needs an image; geometry and PBR profiles differ. All computation and media handling remain on the same phone.
6. Use All/HF search for other choices. All 82 registered bundles and full HF discovery remain available; discovery does not establish arbitrary architecture compatibility.

## 3. Selection and validation boundaries

Entries have complete pinned HTTPS component sources, implemented Android engines, shared management and clear use cases. Registry checks validate task, identity, count and exact size. Resource hints appear on video/3D cards. This is not a phone performance ranking or a promise that Z20, X30 or the connected device completes every model.

Checks cover original order, category counts, bundle identity, content tags, no automatic download, explicit transfer routing, All/Local, missing-metadata fallback and narrow screens. Actual Android covers category pages and the zero-model API. As requested, no complete trained weights are downloaded/copied/run; quality, duration, peak RAM, temperature and sustained screen-off inference remain unmeasured.

## 4. Media and reproduction

[Desktop category GIF](media/development/recommendations/recommendations-ui.gif) · [MP4](media/development/recommendations/recommendations-ui.mp4) · [Identity](media/development/recommendations/manifest.json) · [Actual phone image page](media/device/v0.3.8/02-recommended-image.png) · [Phone acceptance](DEVICE_ACCEPTANCE.en.md)

```powershell
python tools/recommendations.py
node tests/ui-smoke.cjs
node tools/capture_workbench.cjs recommendations
```

Desktop footage is labelled UI FIXTURE, including the simulated transfer. Actual phone footage selects no downloads and runs no model. Owned browser contexts and recording services close after use. Individual model/component licenses and [third-party notices](../THIRD_PARTY_NOTICES.md) remain applicable.
