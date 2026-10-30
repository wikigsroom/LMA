# Sana Edit: local fixed-style image conversion

[中文](MNN_SANA_EDIT.md) · [Documentation](README.md) · [dev.36 numbered delivery and full pending scope](releases/v0.3.0-dev.36.md)

## 1. Corrected capability

The matched application uses `taobao-mnn/MNN-Sana-Edit-V2` for **fixed cartoon-style conversion of an input image**. Its earlier dev.35 classification as a thirteen-component text-to-image variant was incorrect. The gray outputs and failed quality observations remain in the [historical experiment](MNN_SANA_TRAINED.en.md); they are not successful image-edit evidence.

Primary references: [pinned official Sana documentation](https://github.com/alibaba/MNN/blob/35a20ca0995bb7e4a549b7def42c4acb30559a94/apps/sana/README.md) and [matched Android prompt defaults](https://github.com/alibaba/MNN/blob/35a20ca0995bb7e4a549b7def42c4acb30559a94/apps/Android/MnnLlmChat/app/src/main/java/com/alibaba/mnnllm/android/chat/SanaDefaults.kt). Generic HF metadata is not proof of runnable capabilities.

The production recipe is `sana_edit_mnn_cpu_v1`, using `mnn_diffusion` / CPU, architecture `sana_mobile_edit`, pipeline `sana_edit_mnn_v1`. It is a peer model with image, `image_to_image`, `fixed_style` and foundation tags. **Frozen target 04 remains text-to-image and is still pending. Image editing does not replace it.**

## 2. User flow

1. Open the chosen repository through All or HF search, inspect files and pin the intended revision. Recommended and Local model management remain available.
2. Select “Sana Edit · 本地图片卡通转换.” Review and explicitly confirm companion suggestions. Filename matching does not establish architecture compatibility.
3. Explicitly register the model, inspect the complete fifteen-file plan, then choose download or import your selected files. Installing/updating the App, searching and registering do not download weights.
4. Manage the model and its independent settings in Local. Open its shared generation form, import a local PNG/JPEG and select it in the required source-image field.
5. The form displays the read-only matched prompt and omits negative conditioning and CFG. Start with a square source, 512×512 output and ten steps. Run preflight, then explicitly submit.
6. Monitor progress, cancel or retry through the shared job list. Successful images enter the shared artifact manager for preview, retrieval and export. Retry creates a new job; historical snapshots remain immutable.

Downloading, importing media and inference are distinct actions. Execution needs no network, ROOT, Termux or another inference device. Optional API clients submit requests to this App; computation must remain on the same Android phone. Android and vendor power management still constrain background operation. No untested phone is claimed to sustain screen-off generation.

## 3. Complete user-selected assets

Developer verification pins repository `taobao-mnn/MNN-Sana-Edit-V2`, revision `dd5955b4e63359b5822fa29a3b3711a112212046`. Total: **1,661,730,284 bytes**, approximately 1.55 GiB, plus temporary installation space. [The metadata-only identity lock](../research/mnn_edit_trained/assets.json) records every path, size and SHA-256.

| Roles | Files | Count |
|---|---|---:|
| diffusion / diffusion_data | transformer.mnn / transformer.mnn.weight | 2 |
| connector / connector_data | connector.mnn / connector.mnn.weight | 2 |
| projector / projector_data | projector.mnn / projector.mnn.weight | 2 |
| vae / vae_data | vae_decoder.mnn / vae_decoder.mnn.weight | 2 |
| vae_encoder / vae_encoder_data | vae_encoder.mnn / vae_encoder.mnn.weight | 2 |
| llm / llm_data | llm.mnn / llm.mnn.weight | 2 |
| llm_config | llm_config.json | 1 |
| tokenizer | tokenizer.txt | 1 |
| meta_queries | meta_queries.mnn | 1 |

Old thirteen-component declarations, files, settings and jobs remain intact. There is no silent migration, identifier replacement or historical job rewrite. Trying the legacy text-to-image declaration produces an explicit incompatibility error. Users must choose the new recipe and missing image encoder themselves. Content-addressed storage can reuse identical installed objects, while registration and download-plan confirmation remain explicit.

## 4. Input, settings and API contract

| Item | Supported contract |
|---|---|
| source_image | Required imported PNG/JPEG; up to 16 MiB and 4,194,304 pixels |
| Output dimensions | Width and height fixed at 512; edits clamp to recipe bounds |
| Prompt | Matched fixed prompt; read-only in UI, arbitrary API instructions rejected |
| Negative conditioning / CFG / LoRA | Unsupported by this recipe; submitted conditions are not silently discarded |
| steps | 1–50, default 10; one-step execution is a boundary check, not accepted quality |
| threads | 1–32, default 4; device-specific speed and memory remain unverified |
| maxInputTokens | 1–1792, default 512; includes formatting prefixes; insufficient budget fails explicitly |
| seed | -1 for random, or 0–2,147,483,647; actual seed recorded in execution metadata |

Non-square sources use the matched upstream padding/resizing path and still produce square output. Camera EXIF orientations, color profiles and all large-image variants have not been validated. Export a correctly oriented, suitably sized PNG/JPEG first. This recipe does not claim general instruction editing, arbitrary styles or original Sana checkpoint compatibility.

The [shared API](API.en.md) uses `POST /v1/jobs/preflight` and `POST /v1/jobs` with type `image.generate`. `input.artifacts` must include `{ "role": "source_image", "artifactId": "an imported artifact ID" }`; `input.prompt` must equal the engine input schema's `fixedPrompt`. Filesystem paths cannot substitute for artifact IDs. The service freezes hashes, metadata and parameters, revalidates the selected file and leases it during execution. In-use sources cannot be deleted.

Only the App resolves an internal path for its signed built-in worker. Before neural allocation, the worker checks actual PNG/JPEG headers, byte size and pixel bounds, and also checks real decode results. It executes no arbitrary model configuration, Python, external program or network inference. Failure publishes no result; cancellation ends the real child and releases its workspace. Successful artifacts preserve source and parameter provenance.

## 5. Evidence and reproduction

![Required local image and fixed prompt (UI fixture, not phone footage)](media/development/sana-edit-required-source.png)

![Local sources and actual native host outputs](media/development/sana-edit-trained/00-contact-sheet.png)

[Actual-output MP4](media/development/sana-edit-trained/sana-host-outputs.mp4) · [GIF](media/development/sana-edit-trained/sana-host-outputs.gif) · [Original output PNG](media/development/sana-edit-trained/01-a.png). These are actual native Windows CPU outputs and a labelled artifact slideshow, **not Android footage**. The source is NASA's public-domain astronaut sample; see [attribution](../tests/fixtures/images/LICENSE.md). The inspected edit retains the subject, clothing and scene while changing appearance details. This does not establish general identity preservation or final quality.

Native execution checks cover PNG/JPEG, non-square sources, fixed conditioning, steps, missing/corrupt/oversized images, incorrect pipelines, missing image encoder, token budget and recovery. Production Java checks cover full selected-component import, independent clamped/restarted settings, source import/leasing, immutable jobs, real sampling cancellation, recovery, result publication/restart/provenance and source deletion. UI checks use explicitly labelled fixtures and remain separate from trained-model execution.

With the existing native Windows toolchain, explicitly run the following from the project directory. Developer model assets stay in ignored build storage and never enter the APK:

```powershell
python tools/fetch_mnn_edit_trained.py --download --origin https://huggingface.co
python tools/build_mnn.py
python tools/test_mnn.py
python tools/test_mnn_edit_trained.py
python tools/test_mnn_edit_app_host.py
python tools/export_mnn_evidence.py
python tools/render_mnn_edit_trained.py
```

Review the selected model's license and origin before download. A supported public mirror can be selected explicitly; the tools do not download by default. Matching generated Android/host sources do not establish Android execution, independent reference numerics, quality, resources, screen-off operation or sustained API acceptance. All frozen scope and original failed gates remain in the [full pending table](releases/v0.3.0-dev.36.md).
