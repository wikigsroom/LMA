# v0.3.6 numbered adaptation completion

[中文](REMAINING_ADAPTATION.md) · [Complete profiles and usage](ADAPTER_PROFILES.en.md) · [Current evidence](../verification/releases/v0.3.6/status.json) · [Frozen scope](MULTIMODAL_RELEASE_PLAN.en.md)

This is the current v0.3.6 implementation inventory. The original v0.3.5 missing-adapter audit remains immutable. Required code is delivered together rather than deferred to separate releases.

| ID | Implemented | Scope / evidence |
| --- | --- | --- |
| P01 | Complete local UltraTex | FLUX.1/FLUX.2, text/tile VAE/BN, dual-LoRA materials, packing/Euler/CFG/PBR; UltraTex application and flow suites |
| P02 | Joint multiview UniForge3D | Actual VGGT/DiT, DINO, condition/anchor routing, SS/SLAT, FDG/material/GLB; component, production and router checks |
| P03 | SAM 3D Objects | MoGe, three conditioning branches, MoT/pose, occupancy/SLAT, FlexiCubes, vertex color/aux channels; actual source, native/export/depth/pose checks |
| P04 | MV-SAM3D+DA3 | Four-view joint and metric depth, camera/coordinate alignment, MultiDiffusion, SS warmup/replay, SLAT random stream; independent multiview assets |
| P05 | SUPRA-Tex | Local Qwen3-VL/VAE/dual PBR, SCVAE, interleaved completion, FDG/visibility, original-mesh material bake; actual-network and production flow checks |
| P06 | Additional same-phone preparation/material routes | DIS foreground, mtmd VLM parts, XYZ+normal VAE, original Flash/octree/Lewiner/DISO CPU, optional Paint/UltraTex; Java/native/UI contracts |
| B01 | Official-compatible F5 frontend | 6,671 segmentation/pinyin/sandhi/vocabulary checks; dictionaries remain separately selected assets |
| B02 | Hunyuan Paint and shared PBR | Local encoding/six-view dual materials/UniPC/VAE/optional enhancement, raster/xatlas/fusion/PBR; original positions retained |
| B03 | Shared application modules | Per-model editable/dependent limits, typed content-inspected JSON, role forms, drafts/preflight/queue/cancel, helper leases/hashes/effective parameters, atomic final artifacts |
| B04 | Release evidence | Current records in `verification/releases/v0.3.6/`; published `verification/program/` and history preserved; three release entrypoints reject missing code/records |

**No required P01–P06 development item remains.** These are bounded CPU program adapters, not a claim to reproduce every upstream CUDA workflow or execute every HF architecture. Inputs, export steps, parameters and differences are [documented](ADAPTER_PROFILES.en.md). `tools/audit_adaptations.py --require-complete` checks source/build/test identity; changed inputs invalidate evidence.

| ID | Unverified / unmeasured | Handling |
| --- | --- | --- |
| P07 | Complete public matched 3D export download endpoints | Not verified. Explicit user conversion/import remains supported, with no invented URLs or automatic weight retrieval. Checked catalogue downloads and other compatible HF files remain available |
| P08 | Complete trained models, phone quality/speed/peak memory/screen-off endurance | Omitted under the user's program-only policy: zero complete-model validation downloads/runs and zero phone acceptance. Not a missing-code item; no repeated phone request |
| P09 | Arbitrary other HF/CUDA architectures or every default publisher workflow | Not claimed supported. Discovery is distinct from execution; a new architecture still requires a versioned adapter |

Unchanged requirements: foundation-only APK, user-selected assets, all computation on the same phone, no ROOT/remote/virtualization, peer models and independent content labels, exact recommendations `m08 → m06 → m01`, F01–F12, text, selections 01–14/16/17, nine MOSS targets, SD1.5/SDXL LoRA and all existing community/speech/3D routes. No ComfyUI canvas/nodes/plugin ecosystem.

[UI GIF](media/development/adaptation/adaptation-ui.gif)/[MP4](media/development/adaptation/adaptation-ui.mp4) use production pages with explicit UI FIXTURE bridges, not trained-model or Android-device recordings. See [component licenses](../THIRD_PARTY_NOTICES.md), including the noncommercial DISO CPU component.
