# Complete adaptation work list

[中文](REMAINING_ADAPTATION.md) · [F5 frontend](F5_FRONTEND.en.md) · [Local PBR](LOCAL_MATERIALS.en.md) · [Frozen requirements](MULTIMODAL_RELEASE_PLAN.en.md)

This page tracks development after v0.3.5. The published v0.3.5 APK does not contain these additions. Source checks and catalogue registration do not establish complete model integration. Every outstanding item belongs to the same complete delivery scope; unfinished models are not silently deferred to another release track.

## 1. Product requirements

| ID | Requirement | Handling |
| --- | --- | --- |
| A01 | App updates deliver the foundation | No weights, voices, tokenizers or linguistic tables in the APK; users explicitly select, download / import and manage assets |
| A02 | Equal model peers | Text, image, video, audio, 3D, capabilities, format, engine, backend, licence, content labels and installation are independent dimensions |
| A03 | Recommended / All / Local | Preserve `m08 → m06 → m01`; other HF repositories remain discoverable through All / search; Local manages selected files and incomplete transfers |
| A04 | Per-model settings | Editable presets, actual model and application limits, excessive values return to the upper bound; no invented limits for unknown models |
| A05 | Entirely on the same phone | Encoding, sampling, decoding, codec, rasterization and composition stay local; no ROOT, remote inference, LAN fallback or user execution plugins |
| A06 | Preserve the complete original scope | F-01–F-12, text, selections 01–14 / 16 / 17, all nine MOSS subtargets, SD1.5 / SDXL LoRA, community / speech / single-image / four-view / RF / Spatial routes |
| A07 | Compact workbench | Shared forms, preflight, drafts, queue, cancellation, recovery and artifacts; no ComfyUI wiring, infinite canvas, nodes or plugin ecosystem |
| A08 | Program-only validation | Compilation, production contracts, small random networks, error / cancellation / cleanup, UI, package and signature checks; no complete trained models or repeated phone requests |

## 2. Implemented in this development work

| ID | Module | Implementation and evidence |
| --- | --- | --- |
| B01 | Official-compatible F5 Chinese frontend | Pinned rjieba / jieba-rs DAG + HMM, pypinyin pronunciation / sandhi and F5 punctuation, mixed text and vocabulary IDs; 2,222 texts / 6,671 native comparisons; legacy recipe retained |
| B02 | User-selected linguistic asset | New template requires `f5-frontend.json`; offline preparation, source pins, licences, real size / SHA256, Java import, role / size checks and workspace staging; no dictionary in APK |
| B03 | Hunyuan3D 2.1 Paint | Selected PNG + existing GLB → six-view conditions → DINO / VAE → dual-material UNet, reference / multiview attention and RoPE → UniPC → VAE → optional RealESRGAN → UV / PBR GLB; actual Paint network |
| B04 | Shared local material geometry | Bounded CPU raster, visibility, normal / position maps, xatlas, weighted fusion and nearest-observed texel fill; correct metallic-roughness channels and original mesh coordinates |
| B05 | Offline Paint preparation | Explicit local safetensors / weights-only files, fixed source classes, five graphs, sampling programs for 1–100 steps and file manifest; real CLI exercised with random architecture fixtures; existing exports preserved |
| B06 | Application workflow | Seven required components, independent settings / typed inputs, Local, preflight, drafts, idempotent submission, shared child process, cancellation / failure cleanup, atomic artifacts and embedded PNG / UV / PBR preview with GPU cleanup |
| B07 | BSA building block for UltraTex | Pinned SLA block means, smooth-K selection, top-k and online softmax, FP32 / BF16 bounded CPU / ONNX bridge; still not a complete UltraTex adapter |
| B08 | Documentation and media | Bilingual asset / conversion / usage / limits, numbered status and production UI fixture screenshots / GIF / MP4; previous README scenarios, API examples and historical cases retained |
| B09 | Actual UltraTex network conversion components | Pinned FLUX.1 dev / FLUX.2, dynamic foreground / original IDs, exact rotary tables, strict LoRA merge and both offline CLIs; 101 actual network / native ORT checks; [usage and gaps](ULTRATEX_FLOW.en.md); no app recipe registered |

CPU materials disclose differences from upstream CUDA raster, erosion / repair and random streams. BSA uses deterministic index ordering for ties; Torch / CUDA `topk(sorted=False)` does not guarantee identical ordering across devices. These checks establish neither trained-model quality nor phone resource acceptance.

## 3. Required model workflows still missing

| ID | Benchmark | Required production path | Existing but insufficient foundation |
| --- | --- | --- | --- |
| P01 | D04 UltraTex | Same-phone text encoders, tile VAE / BN / material decoders, canonical conditions / packing, Euler / CFG / black-background restoration, albedo / MR and complete app orchestration | Actual flow conversion / LoRA / foreground / IDs, shared raster / UV / baking and BSA; still not integrated UltraTex |
| P02 | D05 UniForge3D | Joint VGGT / DiT, DINOv3, multiview anchors / features, sparse structure / SLAT sampling, FDG / material decoders and GLB | Sparse convolution, pooling / subdivision and packed attention; TRELLIS or ordinary four-view inference cannot replace the joint network |
| P03 | D08 SAM 3D Objects | Mask, MoGe pointmap, MoT structure / layout / pose, SLAT / FlexiCubes and selected geometry / appearance output | Five sparse operation families; preserve SAM pooling denominator and coordinate ordering |
| P04 | D09 MV-SAM3D | D08 plus Depth Anything 3, camera alignment, weighted MultiDiffusion and first-step warmup / reset / replay | Existing four-view generation or repeated single-image inference cannot substitute for this architecture |
| P05 | D10 SUPRA-Tex | On-phone Qwen material frontend, geometry / observation latents, interleaved completion and SCVAE, PBR raster / bake | Shared sparse and material foundation; no off-device back-view service or inference provider |

These are actual implementation gaps. Waiving complete-model runs did not waive development. **All requested adaptations are not complete.** Compilation or passing the earlier frozen scope cannot justify a release claiming otherwise.

## 4. Other scope and validation

| ID | Work | Status / completion rule |
| --- | --- | --- |
| P06 | Automatic segmentation, VLM part identification, pointcloud input, original Flash / octree and textures beyond disclosed subsets | Missing code remains explicit; CPU uniform-grid extraction and manual input are not complete benchmark reproduction |
| P07 | Public matched complete export packages | No verified complete Spatial / RF / MV endpoints yet; retain explicit conversion / import, never fabricate URLs or silently acquire data |
| P08 | Complete trained models / physical phone | Not run under the user's policy; neither a pass nor a justification for P01–P06 code gaps; do not request a phone again |
| P09 | Current-code verification and delivery | Refresh input fingerprints, relevant checks / media and bilingual guides; preserve published files / tags; release gates must assess actual current scope, not only old counts |

Detailed usage: [F5](F5_FRONTEND.en.md), [PBR](LOCAL_MATERIALS.en.md). UI media: [GIF](media/development/material/material-ui.gif) / [MP4](media/development/material/material-ui.mp4). All demonstrations carry **UI FIXTURE** labels and use production pages with a simulated bridge; no phone or trained-model output is depicted. `tools/audit_adaptations.py` generates the machine-readable `research/portability/adaptation-current.json`.
