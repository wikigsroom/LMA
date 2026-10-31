# Hunyuan3D shape and UltraShape refinement

[中文](SPATIAL_SHAPE.md) · [Numbered implementation and gaps](IMPLEMENTATION_V035.en.md) · [v0.3.5](releases/v0.3.5.md)

LMA v0.3.5 adds two equal, optional phone-local CPU routes: Hunyuan3D 2.1 image-conditioned geometry and UltraShape 1.0 refinement of an existing coarse mesh. Both use `spatial_ort` with matched FP32 ONNX exports and produce untextured GLB. App updates deliver code; users select every model and input asset.

## 1. Exact support

| Recipe | Inputs | Task and foundation tags | Excluded stages |
| --- | --- | --- | --- |
| `hunyuan3d_21_shape_onnx_cpu_v1` | One RGB / RGBA PNG | 3D, image_to_3d, image_conditioning, sdf_geometry, spatial_ort, cpu | Separate Hunyuan3D Paint, automatic background removal |
| `ultrashape_1_refine_onnx_cpu_v1` | Reference PNG + static, self-contained coarse GLB | 3D, mesh_refinement, coarse_mesh_conditioning, image_conditioning, sdf_geometry, spatial_ort, cpu | Automatic initial mesh generation, texture |

No public complete matched ONNX package has been verified. These are **explicit export/import recipes**, not invented one-click downloads. The existing 82 catalogue bundles remain. Raw PT / CKPT / safetensors are not Android executables. HF discovery stays open to other repositories; execution depends on architecture, format, complete components and resources.

Recommended remains `m08 → m06 → m01`. Existing text, F-01–F-12, selections 01–14/16/17, community, speech, single-image and four-view routes are retained. Content labels, functional tags, dependencies and installation state are independent; architecture names do not imply NSFW or Uncensored status.

## 2. User workflow

1. Obtain local checkpoints and configs under their applicable terms. Convert them using the offline tool below. The conversion computer prepares files only; it does not participate in inference on the phone.
2. Copy the export to the phone. Import `lma-bundle.json`, then select each component file. Actual sizes and SHA256 are checked; importing a JSON manifest alone does not install weights.
3. Find the model in Models → Local. Imports, pause/resume, deletion and settings follow the shared manager. Installing/upgrading LMA or browsing never starts a model download.
4. Import a background-removed or white-background reference PNG. UltraShape additionally requires a coarse GLB, supplied by the user or chosen from existing local results. This recipe does not silently run another model to create it.
5. Select Use and edit this model's steps, tokens, SDF grid and query chunk. Editable presets share the per-model schema and clamp excessive input; the installed export's `maxTokens` further limits that model.
6. Preflight or save a draft. Explicitly opt to try an unmeasured model before submitting to the shared queue. Missing inputs block submission. Preflight does not run inference.
7. Follow image encoding, shape sampling, SDF and export stages, or cancel. A validated GLB is committed to the artifact library only on success. Preview, export or reuse it as a local input. Failure/cancellation publishes no partial result and cleans the private workspace after the child exits.

Background execution uses the existing Android foreground service, notification and recovery mechanisms. Android can still restrict the process; phone performance, quality, memory and screen-off endurance have not been measured.

## 3. Offline asset conversion

Tools use native Windows Python/PyTorch, without Docker, WSL, VMs or an emulator. Program checks used Python 3.13, PyTorch 2.14.0 CPU, transformers 4.57.6, diffusers 0.35.1, einops 0.8.1, ONNX 1.19.0, safetensors, PyYAML, NumPy/Pillow and host ORT 1.24.3. Preprocessing comparisons additionally use OpenCV 4.12.0.88 and trimesh 4.8.3. These dependencies are code, not model assets.

```powershell
# Fixed source/config/license files only; no weights or upstream installers
python tools/fetch_spatial_sources.py --fetch
python tools/fetch_spatial_sources.py

# Example paths to assets explicitly prepared by their owner
python tools/export_spatial.py --pipeline hunyuan3d_21_shape --config E:/my-assets/hy3d/config.yaml --checkpoint E:/my-assets/hy3d/model.safetensors --output E:/my-assets/hy3d-lma
python tools/export_spatial.py --pipeline ultrashape_1_refine --config E:/my-assets/ultra/infer_dit_refine.yaml --checkpoint E:/my-assets/ultra/model.pt --image-config E:/my-assets/dino/config.json --image-snapshot E:/my-assets/dino --output E:/my-assets/ultra-lma
```

The output directory must be new. `--image-config` is unnecessary when the YAML contains the DINO configuration. `--image-snapshot` is unnecessary when the checkpoint contains the full conditioner; otherwise it must select an existing local safetensors snapshot. Implicit network loading and pickle fallback are disabled. PT/CKPT loading uses `torch.load(weights_only=True)` and accepts only tensor dictionaries or one nested dictionary level, not arbitrary training objects.

The exporter checks fixed model targets instead of dynamically importing model-supplied code. It retains all expert weights and emits FP32/opset17 graphs; it does not promise arbitrary ONNX, quantized or unrelated architecture support. Export tracing executes dummy forwards. **Only tiny random models were used here, with no complete trained checkpoint export or inference.** Full conversion can exceed host RAM, storage or graph-size limits.

| Required role | File |
| --- | --- |
| config | `spatial-config.json` |
| image_encoder | `image_encoder.onnx` |
| flow | `flow.onnx` |
| cache | `cache.onnx` |
| query | `query.onnx` |

Include every `.onnx.data` sidecar actually emitted, under its matching `_data` role. `lma-bundle.json` and `export-receipt.json` record real sizes/hashes and empty URLs. Same-name components from another export are not interchangeable.

## 4. Execution and numerical boundaries

Fixed references: [Hunyuan3D 2.1 82920d6](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/tree/82920d643c0dc2f7bfd7255f45f62d386edfe60c) and [UltraShape 5e8dcef](https://github.com/PKU-YuanGroup/UltraShape-1.0/tree/5e8dcef05df101ab00ab6cd5fdd0ed0c74fbca66). The [per-file lock](../third_party/spatial-shape-source-lock.json) also pins UniForge/SAM sparse reference rules. Original source, per-file and model terms apply separately.

```text
Reference PNG -> alpha bounds / area resize / centering / white matte -> DINOv2
UltraShape: coarse GLB -> scene transforms -> normalize -> area + sharp-edge samples
  -> float16 positions -> occupied voxels
  -> HunYuanDiTPlain or RefineDiT (voxel RoPE, MoE, stepwise CFG)
  -> rescale / post_kl / VAE transformer cache -> chunked SDF query
  -> bounded uniform-grid marching tetrahedra -> self-contained GLB
```

- Hunyuan uses the released configuration's `HunYuanDiTPlain`, not the neighboring alternative DiT class. UltraShape uses `dit_mask.RefineDiT`, including voxel conditioning and masked image tokens.
- MoE preserves top-k **unnormalized** routing probabilities and the shared expert. CPU evaluation computes experts sequentially and combines their original routed outputs. All expert weights remain required, so this can be slow and memory-intensive.
- The source schedule ascends from 0 to 1 with shift; updates use `(sigma_next - sigma_now) * velocity`. RF Shape's opposite direction must not be reused. Conditional and unconditional predictions run separately, preserving steps even at guidance 0/1.
- UltraShape preserves the publisher's unusual cross-attention KV packing, nearest/max-pooled mask and valid-token selection. Tiny FP32 graphs are compared with the pinned classes.
- Coarse surface sampling uses half area-weighted triangles and half length-weighted sharp edges, including repeated directed edges. Positions round through float16 before voxelization. Direct sampling avoids the large intermediate publisher pools while retaining their distribution; RNG streams are not NumPy/Torch bit-identical.
- Sharp-edge detection uses angle-weighted shared-vertex normals. Supply a correctly connected triangle mesh. LMA does not automatically weld disconnected duplicate vertices, retopologize or repair it. No usable sharp edges is a local error, not an implicit alternative refinement algorithm.
- One ORT stage session is resident at a time; query reuses the VAE cache. Uniform-grid extraction differs from the upstream Flash/octree route and does not reproduce the original benchmark workflow.

## 5. Parameters, inputs and resources

| Field | Default / range |
| --- | --- |
| threads / steps / seed | 2 / 1–16; 30 / 1–100; 1234 / 0–2,147,483,647 |
| tokens | Hunyuan 4096, Ultra 8192; multiples of 512; constrained by installed `maxTokens`, application ceiling 32768 and decoder memory guard |
| grid / queryChunk | 64 / 32–256 in multiples of 16; 512 / 128–4096 |
| guidance / maxTriangles | 5 / 0–15; 300000 / 1000–1000000 |
| meshScale, Ultra only | .99 / .1–1 normalized half extent |
| surfaceSamples, Ultra only | 65536 / 1024–409600 total area/edge samples; odd totals allocate one more area sample |

Reference inputs must be 8-bit RGB/RGBA PNG, at most 16 MiB and 4,194,304 pixels; background removal is explicit. Coarse GLB is limited to 256 MiB, one million triangles and three million vertices. Static, self-contained scene transforms and mirrored winding are supported. External buffers, skins, animations, morphs, compression, sparse accessors, cycles and out-of-bounds data are rejected.

The grid has `(grid+1)^3` points; tokens × queryChunk is limited to 33,554,432. These are program guards, not a Nubia Z20 capacity guarantee. A smaller chunk does not reduce DiT/expert weight memory. Limits produce errors rather than silently truncating geometry.

## 6. Shared job API

Upload PNG/GLB using the existing artifact API and use an actually installed bundle ID. Authentication, idempotency, events, cancellation and results remain shared. Arbitrary filesystem paths and remote execution URLs are not accepted.

```json
{
  "bundleId": "your_installed_ultrashape_export",
  "type": "mesh.generate",
  "input": {
    "prompt": "Generate local 3D geometry from the explicitly selected inputs.",
    "artifacts": [
      {"role": "reference_image", "artifactId": "your_imported_png"},
      {"role": "coarse_mesh", "artifactId": "your_imported_glb"}
    ]
  },
  "parameters": {"steps": 10, "tokens": 512, "grid": 32, "queryChunk": 256},
  "allowUnmeasured": true
}
```

Submit to `POST /v1/jobs`, inspect `GET /v1/jobs/ID`. Hunyuan uses its own bundle and only `reference_image`. The prompt is a fixed operation description, not arbitrary text conditioning; negative prompts are unavailable. `allowUnmeasured` records user intent and does not waive model/input/resource checks. [Uploads](LOCAL_INPUTS.md) · [API](API.md)

## 7. Program evidence, media and remaining work

| Number | Check | Record |
| --- | --- | --- |
| SP01 | Pinned publisher tiny random graphs: dynamic latent/image tokens, cache/query, MoE and schedule; 60 checks | [spatial-graphs.json](../verification/program/spatial-graphs.json) |
| SP02 | PNG/OpenCV/Torch preprocessing, GLB, sharp-edge/float16, actual native success/failure and offline CLI; 188 checks | [spatial.json](../verification/program/spatial.json) |
| SP03 | Five built-in CPU sparse custom operators, exported ONNX executed through native ORT; 109 checks | [spatial-sparse.json](../verification/program/spatial-sparse.json) |
| SP04 | Production Java adapter, storage, roles, schema, cancellation and cleanup; 533 shared expansion checks | [expansion.json](../verification/program/expansion.json) |
| SP05 | 20 added production UI checks for filters, per-model settings, preflight, drafts and duplicate submission | [UI](../verification/program/ui.json) |
| SP06 | ARM64/API28/16 KiB, original signing identity, dependencies and no embedded model data | [spatial-android.json](../verification/program/spatial-android.json) |

![UltraShape inputs and settings: UI FIXTURE, not model output](media/development/spatial/04-ultrashape-inputs.png)

[Five screenshots and identity](media/development/spatial/manifest.json) · [GIF](media/development/spatial/spatial-ui.gif) · [MP4](media/development/spatial/spatial-ui.mp4). These are production pages with an explicit simulated bridge, not phone/model recordings. Owned browser resources close in finally blocks.

Sparse operations preserve different UniForge/SAM pooling denominators, subdivision order, spatial/channel layout and packed attention. They **do not complete** UniForge, SAM, MV-SAM or SUPRA adapters. D04 UltraTex, D05 UniForge, D07 Paint, D08 SAM, D09 MV-SAM and D10 SUPRA still require actual implementation. F5's Chinese frontend is not equivalent to the full official segmentation/sandhi pipeline. See [remaining work](IMPLEMENTATION_V035.en.md) and the [audit](../research/portability/audit-v0.3.5.json).

Per the user's policy, no complete trained model was downloaded/copied/run and no phone or endurance acceptance was attempted. Missing implementation is distinct from omitted runtime validation and remains unfinished work.
