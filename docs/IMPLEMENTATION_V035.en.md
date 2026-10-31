# v0.3.5 implementation and remaining work

[中文](IMPLEMENTATION_V035.md) · [Full workflow](SPATIAL_SHAPE.en.md) · [Machine matrix](../catalogue/release-0.3.5-implementation.json)

Frozen F-01–F-12, text, selections 01–14/16/17, all nine MOSS subtargets, SD1.5/SDXL LoRA, community, speech, single-image, four-view and RF/part routes remain. There are 50 templates, 82 catalogue bundles and 17 extension engines plus text. Users control all model assets; the two new recipes are not presented as verified public complete downloads.

| Number | Implemented this update | Checks and boundary |
| --- | --- | --- |
| 01 | Hunyuan3D 2.1 geometry: DINO / HunYuanDiTPlain / MoE / VAE / SDF / GLB | Matched pinned-source FP32 ONNX; separate Paint remains missing |
| 02 | UltraShape 1.0 refinement: PNG + coarse GLB, voxel RoPE / masked DINO / RefineDiT / MoE | Area + sharp-edge sampling and float16 position rounding; no automatic initial coarse mesh |
| 03 | Offline exporter and per-file manifest | safetensors/weights-only PT, fixed targets, offline, no overwrite; complete trained export untested |
| 04 | Five shared CPU sparse operations and built-in ONNX domain | Submanifold convolution, three pooling modes, two subdivision orders, spatial/channel and packed attention; 109 native ORT comparisons, not whole SAM/UniForge adapters |
| 05 | Production Java adapter, PNG/GLB roles, per-model settings and actual export limits | 533 shared expansion checks; private workspaces, atomic results, failure/cancel cleanup |
| 06 | Shared peer-model/Local pages, editable presets, preflight, drafts and duplicate-submit protection | 20 added checks, 653 complete UI checks; Recommended preserved |
| 07 | ARM64/API28, 40 libraries, 16 KiB, original signing identity and stale snapshot version fix | Package/signature/dependencies and Lint; source, Manifest and build versions agree |
| 08 | 30 suites / 5820 assertions, bilingual guides and 30 scenarios, H01–H18 retained, 30 screenshots / 6 GIF / 6 MP4 | Zero complete models downloaded/copied/run; v0.3.4's 38 JSON and 40 media files archived against original Git blobs |

“Frozen scope complete” describes the original program scope, not every later benchmark architecture. D06/D07 are disclosed geometry subsets. Existing D11/D12/D15/D16 shape subsets remain and do not reproduce complete benchmark workflows.

| Number | Pending work | Type |
| --- | --- | --- |
| 09 | D04 UltraTex: mesh G-buffer, BTD/BSA, matched diffusion/VAE and PBR baking | Actual implementation, not catalogue registration |
| 10 | D05 UniForge3D: joint VGGT/DiT, anchor routing and sparse decode | Shared kernels exist; full architecture remains missing |
| 11 | D07 Hunyuan3D Paint: separate conditioning, rasterization, multiview diffusion and baking | Shape works at program level; Paint code remains absent |
| 12 | D08 SAM / D09 MV-SAM3D: mask, MoGe/depth, MOT, pose, sparse decode, camera alignment/fusion | Actual full architectures; DINO/four-view support cannot substitute |
| 13 | D10 SUPRA-Tex: local material prediction, observed latent, completion, rasterization/baking | External back-view services are excluded; every stage must be on the phone |
| 14 | Full official F5 Chinese segmentation/polyphones/sandhi equivalence | Current longest-word dictionary frontend is experimental |
| 15 | Publicly verifiable complete matched MV/RF/Spatial download endpoints | Explicit export/import exists; no fabricated one-click download |
| 16 | Automatic background removal, VLM part detection, point-cloud inputs, original Flash/octree and added geometry-family textures | Extra implementation outside disclosed subsets |
| 17 | Complete trained export/inference, phone performance/quality/screen-off endurance | Omitted per user policy, never marked passed; separate from missing code |

The frozen scope is not reduced. No remote provider, ComfyUI wiring, infinite canvas or public plugin system is added. The actual ports above must continue; passing checks cannot be called “all adaptations complete.” [Per-target audit](../research/portability/audit-v0.3.5.json) · [Validation policy](PROGRAM_VALIDATION.en.md)
