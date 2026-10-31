# Local RF Shape and part geometry

> v0.3.5 retains these three RF routes and adds [Hunyuan/UltraShape](SPATIAL_SHAPE.en.md). Current totals: 50 templates / 82 bundles / 17 extensions plus text. Earlier per-version numbers below describe v0.3.4. See [current work and gaps](IMPLEMENTATION_V035.en.md).

[中文](RF_SHAPE.md) · [v0.3.4](releases/v0.3.4.en.md) · [Complete scope](IMPLEMENTATION_V034.en.md)

v0.3.4 adds the native `rf_shape_ort` CPU engine and three equal optional recipes: TripoSG, PartCrafter objects and PartCrafter scenes. A selected local PNG becomes an untextured GLB. Parts have separate meshes / nodes in the model's shared coordinate system. The APK ships programs, never model assets.

## 1. Exact support

| Recipe | Independent tags | Boundary |
| --- | --- | --- |
| `triposg_onnx_cpu_v1` | 3D, image_to_3d, sdf_geometry, rf_shape_ort, cpu | Matched FP32 four-graph TripoSG export; one object |
| `partcrafter_onnx_cpu_v1` | 3D, image_to_3d, sdf_geometry, part_level_geometry, cpu | Matched object checkpoint; user selects 1–16 parts |
| `partcrafter_scene_onnx_cpu_v1` | Same, pipeline:partcrafter_scene | A separate export from a scene checkpoint is required; object weights are not silently repurposed |

All 82 catalogue bundles, original recommendations `m08 → m06 → m01`, speech / single-image / multiview routes, F-01–F-12 and selections 01–14 / 16 / 17 remain. The addition is three custom recipes, not three invented downloadable checkpoints: 48 templates, 16 extensions plus text and 39 native libraries. Task, capability, foundation dependency, format and content tags remain separate. Architecture does not imply NSFW or Uncensored status.

No public complete matched ONNX package has been verified. Users can **export locally and import** or explicitly choose already matching exports through HF recipes. Raw safetensors / PyTorch are not directly executable in the Android worker. Missing assets, incompatible configurations and resource failures remain local; there is no off-device fallback.

## 2. User workflow

1. Obtain a licensed local safetensors snapshot with matching transformer, vae, image_encoder_dinov2, feature_extractor_dinov2 and scheduler configurations and assets.
2. Prepare graphs on your own development computer using the offline tool below. This prepares files; the App never calls the computer for inference. Export tracing does execute dummy-input forwards using the selected weights.
3. Copy the export to the phone. Import `lma-bundle.json`, then select each corresponding local component through existing model import. Byte sizes and SHA256 are verified and shared assets reused. Importing the manifest alone does not install its components.
4. Open Models → Local → Use. Select a background-removed or white-background 8-bit RGB / RGBA PNG, at most 16 MiB and 4,194,304 pixels. Alpha is explicitly composited over white; there is no automatic segmentation.
5. Edit this model's part count, steps, tokens, SDF grid and query chunk. Save independent defaults, run preflight or store a draft. Restoring a draft requires a fresh choice to attempt an unmeasured recipe before queue submission.
6. Observe stages, cancel if needed and preview / rotate / export the validated GLB with provenance. Edit an artifact into a new request. Failures and cancellations publish no partial result; private workspaces are cleaned after the owned process exits.

No model is automatically downloaded, loaded or executed. Identical HF filenames do not prove matching architecture or exports. Starting with minimum legal settings can reduce work, but does not establish Z20 feasibility.

## 3. Offline asset conversion

Developer dependencies: native Python / PyTorch, diffusers 0.35.1, transformers 4.57.6, einops 0.8.1, onnx 1.19.0, safetensors, NumPy and Pillow. Reference checks used Python 3.13, PyTorch 2.14.0 and host ORT 1.24.3; Android reuses locked ORT 1.28.2 API17. Dependencies are not model files. No Docker, WSL, VM or emulator is used.

```powershell
# Source only; never downloads a checkpoint or executes upstream installers
python tools/fetch_shape_sources.py --fetch
python tools/fetch_shape_sources.py
python tools/export_shape.py --pipeline triposg --snapshot E:/my-assets/TripoSG --output E:/my-assets/TripoSG-LMA
python tools/export_shape.py --pipeline partcrafter --snapshot E:/my-assets/PartCrafter --output E:/my-assets/PartCrafter-LMA
python tools/export_shape.py --pipeline partcrafter_scene --snapshot E:/my-assets/PartCrafter-Scene --output E:/my-assets/PartCrafter-Scene-LMA
```

These are user-owned example paths. Input must already exist and output must be new. Conversion enforces offline loading and `use_safetensors=True`; missing configs, incompatible schedulers and pickle fallbacks are rejected. Large FP32 exports require substantial host memory and disk. **Complete trained checkpoint conversion was not performed in this development round**; tiny random graph checks cannot guarantee arbitrary large exports succeed.

Files are `shape-config.json`, `image_encoder.onnx`, `flow.onnx`, `cache.onnx`, `query.onnx`, each graph's actual `.data` sidecar, `lma-bundle.json` and `export-receipt.json`. The manifest hashes real files and contains no guessed URL. Referenced sidecars are mandatory. The contract is FP32 / opset17, not arbitrary ONNX, FP16, INT8 or another exporter.

## 4. Native implementation

Pinned references: [TripoSG fc5c409](https://github.com/VAST-AI-Research/TripoSG/tree/fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c) and [PartCrafter 3d773bf](https://github.com/wgsxm/PartCrafter/tree/3d773bf02fad51c7ab31a5615573fec93b287b30). The [source lock](../third_party/rf-shape-source-lock.json) hashes individual files. Original per-file and model terms apply independently of repository root licenses.

```text
Selected PNG → white alpha composite / bicubic / center crop / normalization
 → DINOv2 image_encoder → RF / part DiT flow (sequential CFG)
 → per-part VAE cache → chunked SDF query
 → bounded uniform-grid marching tetrahedra → internal multipart GLB
```

Sampling retains the publisher's `sigma_now - sigma_next` update and shift. Attention preserves per-head packed QKV checkpoint layout. PartCrafter retains global / local attention, part embeddings and U-skips. Conditional and unconditional passes run separately with identical part IDs, avoiding cross-CFG part fusion. VAE SDF signs, caches and chunked queries are checked against pinned source using tiny random networks.

The upstream PartCrafter VAE imports `torch_cluster.fps` for its point-cloud encoder. The exporter AST replaces **only that import** with a guard explicitly rejecting point-cloud encoding; decoder instructions are unchanged. It does not emulate FPS, install CUDA extensions or claim a point-cloud input path.

On-phone stages use one ORT session at a time and cache VAE latents for SDF chunks. There is no Python, network provider, shell, external execution node or model-supplied executable. Fixed component names, disclosed data references, dimension / nonfinite / image / triangle limits and self-contained GLB validation bound the accepted inputs.

## 5. Parameters and resources

| Parameter | Application bounds / default |
| --- | --- |
| CPU threads / steps / seed | 1–16 / 2; 1–100 / 30; 0–2,147,483,647 / 1234 |
| tokens per part | 512–4096, multiples of 512; 2048 for TripoSG / scene, 1024 for objects |
| parts | TripoSG exactly 1; PartCrafter 1–16 / 3, also bounded by export metadata |
| grid | 32–256 cells per axis, multiples of 16 / 64; `(grid+1)^3` query points |
| queryChunk / guidance | 128–4096 / 512; 0–15 / 7; CFG activates only above 1 as upstream |
| maxTriangles | Aggregate 1000–1,000,000 / 300,000; overflow fails instead of silently truncating |

These are program guards, not phone capacity guarantees. Parts × tokens increases global attention costs. Smaller query chunks reduce that stage's work buffer, not large DiT weights. Uniform-grid extraction differs from upstream Flash / octree extraction and can produce different geometry.

## 6. Checks, media and remaining work

| ID | Program validation | Evidence |
| --- | --- | --- |
| R01 | 68 graph / math / preprocessing comparisons, including 1 / 2 / 3 / 16 parts and dynamic tokens / query counts | [shape.json](../verification/program/shape.json) |
| R02 | 30 actual native worker processes across three pipelines: success, config, path, missing assets, empty surface and triangle guards | [Same record](../verification/program/shape.json) |
| R03 | Production Java adapter / storage / cancellation / cleanup; 428 shared expansion assertions | [expansion.json](../verification/program/expansion.json) |
| R04 | 17 added page checks in the full version's regression | [UI](../verification/program/ui.json) |

![Part settings, desktop UI FIXTURE, no trained output](media/development/shape/03-part-settings.png)

[Five screenshots and identities](media/development/shape/manifest.json) · [GIF](media/development/shape/shape-ui.gif) · [MP4](media/development/shape/shape-ui.mp4). The three illustrated models are labelled simulated imports; no trained output is fabricated. Browser resources close in finally.

Zero complete trained-model downloads / copies / runs and no phone were used. Full checkpoint export, phone memory / speed / model quality and screen-off endurance remain unmeasured under the user's program-only policy. Automatic segmentation, VLM part identification, textures and complete benchmark workflows are unimplemented extras, not inferred from compilation.

Seven benchmark configurations in six groups still require native ports: D04 UltraTex, D05 UniForge3D, D06 UltraShape, D07 Hunyuan3D 2.1, D08 SAM 3D, D09 MV-SAM3D and D10 SUPRA-Tex. The [pinned audit](../research/portability/audit-v0.3.4.json) preserves actual development gaps. D11 / D12 / D15 / D16 now map to the matched-export shape subset above, not exact benchmark reproduction.

另有两条真实 CLI 检查：以随机小网络保存的 safetensors 进行离线加载、位置编码插值导出、组件清单 / data / 实际 SHA256 核对。Two documented CLI checks use only tiny random safetensors; complete trained checkpoint export remains untested.
