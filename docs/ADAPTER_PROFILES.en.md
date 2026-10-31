# v0.3.6 local adapters and usage

[中文](ADAPTER_PROFILES.md) · [Numbered completion](REMAINING_ADAPTATION.en.md) · [API](API.en.md) · [Licenses](../THIRD_PARTY_NOTICES.md)

This release completes program integration for P01–P06: **62 component recipes, 82 catalogue bundles and 18 extension engines plus text**. A recipe describes an optional asset combination; it neither installs nor downloads a model. New 3D/vision routes accept explicitly selected matching exports. Complete public download packages have not been verified, so no placeholder download endpoints are supplied.

Every model is an equal peer. Text/image/video/audio/3D, capabilities, engines, backends, component formats, content labels and installation states are independent tags. NSFW/Uncensored labels do not establish executable compatibility; custom imports do not inherit checked content labels. Recommended remains `m08 → m06 → m01`.

## 1. Actual execution paths

| ID | Recipe / source configuration | User input | Execution on the same phone | Output / limit |
| --- | --- | --- | --- | --- |
| P01 | D04 UltraTex, FLUX.1 / FLUX.2 | Material prompt, reference PNG, existing static GLB | CLIP+T5 or Qwen3 tokenization/encoding, six-view geometry, tile VAE/BN, separate albedo/MR LoRA flows, packing, CFG/Euler, decoding, UV/PBR bake | Textured GLB; includes application orchestration |
| P02 | D05 UniForge3D | Front/right/back/left RGBA PNGs | Joint VGGT/DiT, DINOv3, four-layer conditions, anchor routing, structure and two-stage SLAT, FDG, material decoding/bake | Textured GLB; joint processing is retained |
| P03 | D08 SAM 3D Objects | One RGBA PNG; optional explicitly selected foreground model | MoGe, three image-condition branches, MoT structure/pose, occupancy, SLAT, FlexiCubes and color/auxiliary channels | GLB vertex colors and `_SAM_AUX`; no claim of complete Gaussian appearance baking |
| P04 | D09 MV-SAM3D | Four independent RGBA views | Joint DA3 plus separate metric depth, alignment, per-view conditions, MultiDiffusion fusion, SS warmup/state replay, fresh SLAT random stream | Fused GLB; not four independent single-image runs |
| P05 | D10 SUPRA-Tex | Existing GLB, aligned 1024×1024 RGBA, camera JSON | Qwen3-VL features/two PBR targets, Qwen VAE, FDG/visibility, SCVAE encoders, interleaved completion, original-mesh material bake | PBR on original geometry; no external back-image service |
| P06a | DIS / ISNetDIS | RGB or RGBA PNG | Pinned preprocessing, ONNX CPU mask prediction, original-size alpha reconstruction | RGBA PNG; invalid constant masks fail |
| P06b | llama.cpp mtmd VLM | PNG, matched user-selected main GGUF and mmproj | Local tokenizer, image encoding, publisher chat template, JSON grammar and decoding | Strict `parts` text result with 1–16 unique names |
| P06c | TripoSG / PartCrafter point-cloud VAE | Normalized XYZ+unit-normal JSON | 4×token sampling, FPS, actual point encoder, mean/sample posterior, cache/query, extraction | One whole GLB; no image diffusion |
| P06d | Original RF surface extraction | RF or point-cloud VAE SDF | Selectable `uniform`, `publisher_octree`, `publisher_flash`; bounded CPU ports of original Lewiner/DISO forward kernels | GLB; separate source comparisons cover the original extraction routes |
| P06e | Fixed local preparation/material stages | Explicitly selected installed helper models | Optional foreground → optional VLM part count → geometry → optional Hunyuan Paint/UltraTex | One final GLB; failure/cancel removes intermediate outputs, with no remote fallback |

Existing Hunyuan Shape, UltraShape refinement, Paint, TRELLIS/Pixal, single/four-view, speech and community image/video routes remain. The official-compatible F5 frontend and separately selected linguistic assets are documented in [F5](F5_FRONTEND.en.md).

## 2. Install and operate

1. Install the Release APK and open Models. Browsing Recommended, All or HF search downloads no model. ARM64/Android 9+ describes application compatibility, not the memory required by a large model.
2. Explicitly download a checked catalogue bundle, or choose a recipe and import matching user-owned exported components. Encoders, projectors, VAEs, main networks, tokenizers and external ONNX data must belong to the same export. Raw PyTorch weights are not Android runtime bundles.
3. Complete installation in Local. Shared assets reuse verified hashes. Deleting a model preserves components still referenced by others. Missing components prevent execution.
4. Edit the selected model's settings. Numeric values use editable presets; enumerations use selectors. Values above model/application bounds clamp. RF `denseDepth` cannot exceed `octreeDepth`; VLM output tokens cannot exceed `context−1`. Separate runtime resource guards still apply.
5. Geometry models can explicitly select installed foreground, part-identification and follow-up material models. All default to None. VLM part counts apply to PartCrafter; material stages cannot recurse into themselves. A follow-up UltraTex material prompt is separate, and helpers retain their own model settings.
6. Choose Use and the required local artifacts. UniForge/MV-SAM require four views; SUPRA requires matching geometry, camera and image. Point-cloud requests with follow-up materials also need a reference PNG.
7. Run preflight, optionally save a draft, then enqueue. Preflight validates assets, roles, parameters and resources without inference. Trying an unmeasured recipe requires an explicit choice, renewed after restoring a draft. Tasks support cancel and explicit retry; results retain provenance and can be exported.
8. Execution holds helper-model leases and checks component integrity. Actual stage IDs, hashes and effective parameters are recorded. Removed/incompatible helpers fail explicitly. Helper saved settings are read when a stage executes; they are not all claimed to be frozen before queueing.

This is an internal fixed sequence, with no public nodes, wiring canvas, external execution plugins or ComfyUI graph import. API clients may call the phone's interface; computation remains on that phone.

## 3. Camera and point-cloud documents

Both use UTF-8 JSON and become `application/vnd.lma.data+json` after content inspection. Detection works even when Android stages the file without its original extension. Arbitrary JSON and generated text envelopes cannot masquerade as these inputs; each role additionally validates its schema.

Minimal SUPRA camera example, using radians and values matched to the actual mesh/image:

```json
{"schema":"lma.camera/1","distance":3.0,"camera_angle_x":0.7,"mesh_scale":1.0}
```

Alternatively provide a 4×4 `extrinsic` and 3×3 `intrinsic` or `projection_intrinsic`. Matrix dimensions alone do not establish correct calibration. No camera is silently inferred.

Point clouds require `schema: lma.pointcloud/1`, `coordinates: publisher_normalized` and `points: [[x,y,z,nx,ny,nz], ...]`: 16–16,384 points, six finite bounded components per point, and approximately unit normals. `points×tokens` must not exceed 16,777,216. The program does not silently truncate points or fabricate missing normals. This creates a format example, not a model-quality test:

```python
import json, math
points = [[.5*math.cos(i*math.tau/16), .5*math.sin(i*math.tau/16), 0,
           math.cos(i*math.tau/16), math.sin(i*math.tau/16), 0] for i in range(16)]
with open("points.json", "w", encoding="utf-8") as f:
    json.dump({"schema":"lma.pointcloud/1","coordinates":"publisher_normalized","points":points}, f)
```

## 4. Explicit offline asset preparation

Users run conversion in their preparation environment; every exported inference stage runs on the Android phone. Exporters accept local configurations and weights, do not resolve remote model IDs or run upstream installers, never enable `trust_remote_code`, and refuse existing output folders. Weights do not enter the APK. Missing/unexpected keys, wrong shapes and nonfinite safetensors fail. SAM reconstructs only aliases proven to share storage in the actual source model.

```powershell
python tools/export_uniforge.py --profile INPUTS/uniforge.json --output EXPORTS/uniforge
python tools/export_sam.py --profile INPUTS/sam.json --output EXPORTS/sam
python tools/export_sam.py --profile INPUTS/mv-sam.json --output EXPORTS/mv-sam
python tools/export_supra.py --profile INPUTS/supra.json --output EXPORTS/supra
python tools/export_pointcloud.py --pipeline triposg --snapshot INPUTS/triposg --output EXPORTS/points
python tools/export_foreground.py --weights INPUTS/isnet.safetensors --size 1024 --output EXPORTS/foreground
```

| Exporter | Selected local profile / inputs | Required runtime outputs |
| --- | --- | --- |
| UniForge | `schema:lma.uniforge-local-inputs/1`; `stages`: dino, joint, conditioner, shape512, shape1024, texture, structure_decoder, shape_decoder, texture_decoder. Supply local `config` where required and local `weights` for each stage; explicitly choose joint `withStage1Lora` | Config +14 graphs and external data where produced |
| SAM/MV-SAM | `schema:lma.sam-local-inputs/1`; `target:D08|D09`; source-matched `models` and `runtime`, with local constructor settings and weights; MV adds DA3 | Single-view config+7 graphs, multiview config+8 graphs; auxiliary source pins checked |
| SUPRA | `schema:lma.supra-local-inputs/1`; local `processor`, `resolution:1024`; local config/weights for text, vae, pbr, shape_encoder, material_encoder, shape_decoder, material_decoder, completion | Config + tokenizer +9 graphs |
| Point-cloud VAE | Matched local TripoSG/PartCrafter VAE snapshot | Config + encoder/cache/query |
| DIS | User-selected ISNetDIS safetensors; export size 256, 512 or 1024 | Config + foreground graph |
| VLM | Visual GGUF and matching mmproj supported by the pinned llama.cpp mtmd | Two separate selected GGUF files; arbitrary projector mixing is unsupported |

Constructor settings must match the actual published weights. Tiny random test dimensions are not model profiles. Formal architecture checks reject mismatches; exact profile fields and checks are implemented by each exporter's `prepare()`.

UltraTex requires `--family flux1|flux2`, `--flow-config`, `--flow-weights`, `--vae-config`, `--vae-weights`, `--albedo-lora`, `--mr-lora`, `--mr-decoder`, and `--output`. FLUX.1 additionally uses `--clip` and `--t5`; FLUX.2 uses `--qwen`. All paths identify local configs/weights/tokenizer directories. `--image-size` and explicit `--lora-scale` are available. Do not mix FLUX.1/FLUX.2/Klein guidance configurations. The resulting manifest includes sizes and SHA256 for every required config, graph and actual external-data file. See [UltraTex](ULTRATEX_FLOW.en.md).

## 5. Resources, numerical profiles and licenses

- Networks use FP32 and bounded CPU sparse/raster processing. This does not establish equivalence to publisher CUDA/BF16/FP16 numbers, speed or quality. Deterministic tie order and MT19937 differ from NumPy PCG64/Torch CUDA random streams.
- UniForge allows at most 20,000 sparse rows and 262,144 auxiliary geometry/material coordinates; SAM allows 4,096 rows; SUPRA fixes 1024 observation conditions. Exceeding budgets fails instead of silently truncating work.
- RF original extraction uses target depths 5–8, initial depth 3–target, and query chunks up to 4,096. Upstream Flash and the CPU profile apply different positive final SDF scales; the zero isosurface is unchanged. Comparisons restore raw fields and disclose the difference.
- SAM produces vertex colors and source auxiliary channels. Explicit Paint/UltraTex can add PBR. UniForge omits publisher CUDA remeshing/hole-fill/decimation; local material raster/view-fusion differences remain documented.
- LMA-authored code is MIT, while the DISO CPU forward port is **CC BY-NC 4.0, noncommercial**. Complete component notices ship with source and APK. Selected model/LoRA/DINO/depth/tokenizer weight terms remain separate.
- Validation is program-only: source definitions/formal configs, random tiny networks/actual ORT, production jobs/cancel/cleanup, UI, APK/signature and Lint. No complete trained model was downloaded/run, and no phone inference, quality, speed, peak-memory or screen-off endurance was measured. Nubia Z20 ARM64/API compatibility does not establish that these large 3D models fit.

## 6. Evidence and UI recordings

[Current machine evidence](../verification/releases/v0.3.6/status.json) · [Adapter audit](../research/portability/adaptation-current.json) · [UI GIF](media/development/adaptation/adaptation-ui.gif) · [MP4](media/development/adaptation/adaptation-ui.mp4). Recordings use production assets and an explicit UI FIXTURE bridge. They demonstrate selections, settings and queue logic, with no fabricated trained-model results. Published evidence remains in `verification/program/` and `verification/history/`.
