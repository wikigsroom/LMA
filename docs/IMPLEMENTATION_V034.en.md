# v0.3.4 implementation and remaining work

[中文](IMPLEMENTATION_V034.md) · [Complete design](RF_SHAPE.en.md) · [Machine matrix](../catalogue/release-0.3.4-implementation.json)

F-01–F-12, text, selections 01–14 / 16 / 17, all nine frozen MOSS targets, SD1.5 / SDXL LoRA, community, speech, single-image and four-view routes remain. There are 48 templates, 82 catalogue bundles and 16 extensions plus text. Users choose all assets. Three additional export recipes are not presented as verified public downloadable packages.

| ID | Implemented this round | Checks and boundary |
| --- | --- | --- |
| 01 | Native DINOv2 / RF or part DiT / cache / SDF query / meshing / internal multipart GLB | 68 pinned-source random graph, math and preprocessing comparisons; 30 actual native processes |
| 02 | Three equal TripoSG / PartCrafter object / scene CPU recipes | Five required roles plus actual data, FP32 / opset17 / pinned identity; no guessed URL |
| 03 | Offline safetensors export and real-file SHA256 manifests | No online loading, pickle fallback or overwrite; full trained checkpoint conversion untested |
| 04 | Production Java adapter, imports, settings, PNG inputs, private workspace, atomic result and cancellation | 428 shared expansion assertions, child exit and cleanup on error / cancellation |
| 05 | Shared form, Local management, clamping, preflight, drafts, restoration and duplicate submission protection | 17 new page checks; 633 total; preserved recommended order |
| 06 | ARM64 / API28 worker, original signer, 39 libraries / 16 KiB / dependencies | Lint zero errors / 16 retained warnings; 27 suites / 5,306 assertions |
| 07 | Bilingual guides, 27 use cases, retained H01–H18, 25 screenshots / five GIFs / five MP4s and immutable archives | Original v0.3.3 36 JSON files / four media groups; zero complete trained-model downloads / copies / runs |

Frozen-scope completion does not imply every newly researched architecture is integrated. D11 / D12 / D15 / D16 have matched-export shape subsets, not exact full benchmark reproduction.

| ID | Remaining | Meaning |
| --- | --- | --- |
| 08 | D04 UltraTex: mesh / raster, BTD / BSA, VAE and baking | Actual native port |
| 09 | D05 UniForge3D: VGGT, anchor multiview and sparse decoder | Actual native port |
| 10 | D06 UltraShape: coarse mesh, voxel queries and RoPE | Actual native port |
| 11 | D07 Hunyuan3D 2.1: flow / VAE / surface and separate Paint | Actual native port |
| 12 | D08 SAM 3D / D09 MV-SAM3D: masks, depth, sparse, pose and scene fusion | Actual native ports; DINO / four-view support is not SAM |
| 13 | D10 SUPRA-Tex: material prediction, completion and raster; external back-view stage excluded | Entirely on-phone replacement needed |
| 14 | Verified public matched MV / RF Shape weight endpoints | Import and custom recipes exist; no one-click download until verified |
| 15 | Segmentation, VLM part identification, textures, point-cloud input and original Flash / octree | Outside the integrated shape subset; additional implementation required |
| 16 | Exact official F5 Chinese segmentation / sandhi equivalence | Existing frontend remains experimental; no equivalence claim |
| 17 | Full trained checkpoint export / inference, phone performance / quality / endurance | Excluded under the user's validation policy, never marked passed; cannot replace missing development |

No Docker, WSL, VM, emulator, external inference, wiring canvas or public plugin system. [Per-architecture audit](../research/portability/audit-v0.3.4.json) · [Validation policy](PROGRAM_VALIDATION.en.md)
