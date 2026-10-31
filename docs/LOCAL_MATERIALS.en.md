# On-device PBR material foundation

[中文](LOCAL_MATERIALS.md) · [Shape/refinement](SPATIAL_SHAPE.en.md) · [F5 frontend](F5_FRONTEND.en.md) · [Remaining scope](REMAINING_ADAPTATION.en.md)

Development adds the equal-peer `hunyuan3d_21_paint` recipe. A selected reference image and GLB produce a self-contained GLB with new UVs and embedded albedo / metallic-roughness PNGs. This code is unreleased; the downloadable v0.3.5 APK does not include Paint.

## 1. Application flow

| ID | Action | Behavior |
| --- | --- | --- |
| M01 | Prepare/import matching assets | Configuration, sampler program, five ONNX graphs and sidecars, checked by actual SHA256; no fabricated public download package |
| M02 | Models → Local | Independent model files, parameters, deletion and restoration; installation/browsing never acquires weights |
| M03 | Import inputs | One RGB/RGBA PNG and self-contained static GLB; existing on-device shape outputs can be selected |
| M04 | Edit model settings | CPU threads, steps, seed, guidance, UV size and local RealESRGAN 4× toggle; bounds enforced |
| M05 | Preflight/draft/submit | Missing image/mesh prevents submission; drafts retain selected inputs; preflight does not generate |
| M06 | Shared background queue | Condition rendering, encoding, UniPC, decoding, optional enhancement and UV baking execute on the same phone |
| M07 | Cancel/failure | Wait for child termination, clean its workspace, publish no partial GLB, use no external fallback |
| M08 | Manage results | Validate and atomically publish GLB; preview embedded base color, metallic/roughness and UVs, rotate/zoom and export full GLB |

Capability tags: `3d / mesh_texturing / image_conditioning / multi_view_material / pbr_material / uv_baking`; foundation tags: `spatial_ort / cpu / onnx`. Content labels remain independent. This architecture is not presumed NSFW or Uncensored. Recommended `m08 → m06 → m01`, HF discovery and existing bundles remain available.

## 2. Execution components

| File | Interface/purpose |
| --- | --- |
| `material-config.json` | Pinned source, resolution, six views, DINO/VAE configuration; at most 64 KiB |
| `sampler.json` | Diffusers 0.35.1 linear UniPC coefficients for editable 1–100 steps; at most 8 MiB |
| `image_encoder.onnx` | DINOv2 1536-dimensional features; C++ preprocessing |
| `vae_encoder.onnx` | Reference/normal/position posterior mean and log variance; sampled on the phone using the selected seed |
| `flow.onnx` | Dual PBR, reference UNet, material/multiview attention, position RoPE, DINO projection and three-branch guidance |
| `vae_decoder.onnx` | Decode albedo/MR one view at a time |
| `upscale.onnx` | Matching local RealESRGAN x4plus; the complete selected bundle retains this asset even when enhancement is disabled |
| `.onnx.data` | Disclosed same-name sidecar only; no arbitrary paths, scripts, user plugins or network execution |

Source pins: Hunyuan3D 2.1 `82920d643c0dc2f7bfd7255f45f62d386edfe60c`; BasicSR `651835a1b9d38dbbdaf45750f56906be2364f01a`. Upstream Python pipeline downloaders and CUDA initialization are not executed.

The publisher inference default is **UniPC / trailing / 15 steps**. The implementation retains it and user-selected step counts. Pinned-library basis probes derive model-output conversion, history, predictor/corrector, warmup and final-order coefficients for C++ execution. A floating endpoint defect at 1000 training / 61 inference steps is corrected by retaining exactly 61 valid steps and excluding timestep `-1`.

## 3. Shared geometry and limits

- Six orthographic cameras and publisher reflection/centering/scaling, CPU depth visibility, face normals, position maps and white PNG compositing.
- xatlas UVs, view weights times cosine-to-the-fourth fusion, depth occlusion checks. Unobserved texels and seams use nearest observed texel fill; coverage is reported. This is not neural completion.
- Model MR uses metallic R / roughness G; output maps these to glTF B / G. Both PNGs are embedded; original mesh coordinates/shape are preserved.
- Fixed exports use 64–512 pixels in multiples of 64, latent size 1/8, six views and UV target 256–4096. Actual xatlas dimensions can differ from the requested target.
- PNG: at most 16 MiB / 4,194,304 pixels. Mesh: at most 300,000 triangles. Raster work, UV output, graph sizes and sidecars are bounded; stages keep one graph session resident.
- Enhanced views total at most 16,777,216 pixels. Disable 4× enhancement for 512-pixel exports. Exceeding limits fails explicitly for user correction.

This CPU raster/baker does not reproduce CUDA raster, every boundary erosion/sketch exclusion or upstream repair operation pixel-for-pixel. Native Gaussian randomness also differs from PyTorch. The executable Paint route does not establish paper-level quality, full postprocessing parity or Z20 memory feasibility. Full graphs may still exceed phone RAM.

## 4. Explicit offline asset preparation

The preparation computer only converts assets. No connection to it is needed during phone inference. Inputs are existing user files; tools fetch no weights, execute no arbitrary configuration targets and use no unrestricted pickle construction.

```powershell
python tools/fetch_spatial_sources.py
python tools/fetch_paint_sources.py
python tools/export_paint.py `
  --unet my-assets/paint/unet `
  --vae my-assets/paint/vae `
  --dino my-assets/dinov2-giant `
  --scheduler my-assets/paint/scheduler/scheduler_config.json `
  --upscaler my-assets/RealESRGAN_x4plus.pth `
  --image-size 320 --output my-assets/lma-paint
```

UNet/VAE directories each contain matching `config.json` and one safetensors or weights-only `.bin` file. DINO uses a local safetensors directory. RealESRGAN reads weights-only `params_ema` / `params`. Keys and shapes are strict; missing tensors are not replaced with random weights.

The final `lma-bundle.json` and export receipt contain real bytes, SHA256 and source identity. Copy them and the selected components to the phone for import. Conversion traces dummy forwards; that is not full-model generation acceptance.

The preview reads embedded PNGs only, with no external texture requests: at most 128 MiB GLB, eight textures / 16,777,216 combined pixels, and 4096 per edge. Base color is sRGB; metallic/roughness use B/G. Simple GGX lighting supports inspection, not professional offline rendering. Unsupported files remain exportable. Closing the result releases decoded images, textures, buffers, canvas handlers and the WebGL context.

## 5. Validation

| Program scope | Passed |
| --- | --- |
| Independent ray oracle, UV, visibility, PNG/GLB and failures | 61 |
| 100 step-count profiles, publisher networks → ONNX, actual native worker with both enhancement modes, negative requests | 227 |
| Shared Java import/settings/child process/cancel/cleanup and existing-route regression | 592 |
| Actual offline export CLI, component hashes and no-overwrite behavior | 17 |
| Production forms, drafts, queue, GPU PBR pixels/UVs and resource cleanup | 34 added checks; 687 across all UI suites |
| Native Android build | ARM64 / API28 / 16 KiB; network/external process imports absent |

Small random networks and deterministic program inputs only; no complete trained model was acquired or run. Reports: `build/material-tests/`, `build/paint-tests/`, `build/expansion-tests/`. Final delivery still requires current aggregate fingerprints, media and release artifacts; the v0.3.5 aggregate is historical evidence for that release.
