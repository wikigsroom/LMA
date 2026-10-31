# Multiview 3D and local diagnostics · v0.3.3

> 此页记录 v0.3.3 的历史范围。Current v0.3.4 adds matched TripoSG / PartCrafter shape subsets; see [当前实现 / current scope](IMPLEMENTATION_V034.md), [English](IMPLEMENTATION_V034.en.md).

[中文](MULTIVIEW_DIAGNOSTICS.md) · [User guide](USER_GUIDE.en.md) · [Implementation](IMPLEMENTATION_V033.en.md) · [Release](releases/v0.3.3.md)

This update adds a real Pixal3D MV runtime, four-view input and camera validation, optional component imports, and observations retained even when a job fails. Existing single-image TRELLIS.2 / Pixal3D, the four speech additions and the complete foundation remain. The APK carries no model assets, acquires none automatically, and executes every inference stage on the same Android phone.

## 1. Implemented scope

| ID | Implementation | Boundary |
| --- | --- | --- |
| M01 | `pixal_multiview` ARM64 CPU engine invoking the actual upstream `trellis_run_mv` | Multiview feature projection and fusion, rather than combining four single-image generations |
| M02 | Four alpha PNGs; canonical turntable or explicit calibrated cameras | No automatic background removal, camera estimation or arbitrary photo alignment |
| M03 | Four equal optional choices: F16 / Q8_0 × geometry / PBR | **Verified imports**, without a verified public weight-download endpoint |
| M04 | Independent settings, drafts, preflight, explicit submission, queue and GLB results | Shared jobs and resource controls; no external execution or ComfyUI interface |
| M05 | Stage timing, supported workers' process peak RSS, persisted failure observations | Observations do not establish quality, full-model numerical parity or endurance |
| M06 | Power-save / idle / background / notification status and explicit diagnostic export | Makes restrictions visible; cannot guarantee that Android never stops a process |

There are **82 bundles, 45 data-only recipe templates, 15 extension engines plus the existing text engine**. Recommended remains `m08 → m06 → m01`. Task, foundation dependencies, content evidence, acquisition and installation are separate tags; no NSFW or Uncensored classification is inferred from a 3D architecture.

## 2. Acquiring matching weights

| ID | Bundle ID | Components |
| --- | --- | --- |
| M03a | `pixal3d_mv_f16_geometry_v1` | F16, seven required components |
| M03b | `pixal3d_mv_f16_pbr_v1` | F16, nine required components |
| M03c | `pixal3d_mv_q8_0_geometry_v1` | Q8_0, seven required components |
| M03d | `pixal3d_mv_q8_0_pbr_v1` | Q8_0, nine required components |

File names, sizes and SHA256 identities come from [pinned publisher manifest metadata](../research/multiview/model-manifests.json); see the [bundles](../catalogue/multiview-bundles.json) and [evidence](../catalogue/multiview-bundle-evidence.json). These are **publisher-declared identities**, not measurements of downloaded complete weights. Single-image flows and unrelated GGUF files are not accepted as matching MV components.

1. Find Pixal3D MV in Models → All and open its import details. Cards explicitly say verified import; no available one-click download source is advertised.
2. If you already lawfully hold the exact matching files, import each through component management. Byte counts and full hashes must match before installation completes.
3. If matching files become available on HF, the `pixal3d_mv_gguf_cpu_v1` custom recipe lets you explicitly choose them after checking architecture, layout and terms. Generic HF results do not inherit this catalogue's verified attribution.
4. Installation, upgrades, browsing and preflight never acquire missing weights. Without matching files, this route cannot perform model generation; its acquisition limitation remains visible.

Required layout: `dinov3.gguf`, `pixal3d_naf.gguf`, `ss_dec.gguf`, `shape_dec.gguf`, `pixal3d_ss_flow_mv.gguf`, `pixal3d_shape_flow_512_mv.gguf`, `pixal3d_shape_flow_1024_mv.gguf`. PBR also needs `tex_dec.gguf` and `pixal3d_tex_flow_1024_mv.gguf`. Identical decoder names across releases do not imply identical hashes; use the selected manifest.

Weights remain multiple GB. Download size is not working RAM; there is no evidence here that a 6 / 8 GB Nubia Z20 has enough memory.

## 3. Four-view workflow

1. In Local, select a completely installed MV model and choose Use. Select **front, right, back and left** inputs individually. Each must be an **8-bit RGBA PNG, ≤16 MiB and ≤4,194,304 pixels**. JPEG and RGB PNG are unsuitable. Views should already have background alpha and depict the same object.
2. Empty camera settings select a canonical turntable: four azimuths, zero elevation, horizontal FOV **20°**, distance **3.119204998**, with explicit `meshScale`. Images must actually match these cameras. Ordering handheld photos by name does not calibrate them.
3. For calibrated inputs, provide four `cameraPoses` frames in the exact input order. Matrices follow the upstream camera-to-world convention. Frames accept only `transform_matrix` and radian `camera_angle_x`; paths, URLs and extra fields are rejected.
4. Edit model-specific settings; excessive values clamp. Saving defaults changes only this model. Drafts preserve four references, camera data and effective parameters, while requiring fresh execution consent.
5. Preflight checks actual components, images, cameras, parameters and resources without running a model. Explicitly choose whether to attempt a recipe with no local measurement before enqueueing it.
6. Preview/export GLB and generation records from the shared results library. Geometry previews are bounded; full PBR resources remain embedded in the exported GLB. Temporary image links, camera JSON and sidecar meshes are cleaned after failure or cancellation.

| Parameter | Implemented application range |
| --- | --- |
| resolution | Fixed at 1024; this does not switch into the single-image 512 pipeline |
| threads / steps | 1–16 / 1–50 per stage |
| faces / atlas | Simplification target 1,000–150,000; atlas 256–2048 in steps of 256 |
| maxTokens | Sparse-token guard 1,024–49,152, default 8,192; smaller caps may constrain generated structure |
| guidance / meshScale | 0–15 / 0.1–10 |
| texture | Off by default for geometry bundles; requires the matching extra components |
| cameraPoses | ≤16,000 characters; four finite rigid 4×4 transforms, right-handed rotations, non-origin positions; FOV strictly between 0 and π |

These are application / port limits, not every model's theoretical limits. Simplification targets do not promise an exact face count for arbitrary topology.

## 4. Same-phone API

Import the four PNGs through the [input protocol](LOCAL_INPUTS.en.md) to obtain artifact IDs. Send this body to `POST /v1/jobs/preflight`, review it, then explicitly submit `POST /v1/jobs` with the current Bearer key and a new `Idempotency-Key`.

```json
{
  "bundleId": "pixal3d_mv_q8_0_geometry_v1",
  "type": "mesh.generate",
  "input": {
    "prompt": "Generate one 3D asset from four posed local views.",
    "artifacts": [
      {"role": "reference_front", "artifactId": "IMPORTED_FRONT_ID"},
      {"role": "reference_right", "artifactId": "IMPORTED_RIGHT_ID"},
      {"role": "reference_back", "artifactId": "IMPORTED_BACK_ID"},
      {"role": "reference_left", "artifactId": "IMPORTED_LEFT_ID"}
    ]
  },
  "parameters": {"resolution": 1024, "steps": 12, "maxTokens": 8192, "texture": false},
  "allowUnmeasured": true
}
```

The prompt is a fixed task description, not text-to-3D conditioning. `allowUnmeasured` reflects an explicit user choice and bypasses no missing-file, camera or resource error. Custom cameras go in a JSON **string** at `parameters.cameraPoses`; its only root field is `frames`. A frame has `{"camera_angle_x":0.34906585,"transform_matrix":[[1,0,0,0],[0,1,0,0],[0,0,1,3],[0,0,0,1]]}`. This illustrates one frame's fields, not a calibrated four-view rig; actual matrices must correspond to the four images.

## 5. Observations and privacy

The `audio_cpp`, `trellis_native` and `pixal_multiview` workers emit `lma.worker-observations/1` on completion or a caught error: elapsed time, up to 64 stage timings, and Android process peak RSS from `getrusage(RUSAGE_SELF)`. Windows checks report RSS unavailable rather than inventing a number.

**RSS covers this worker process, not the whole app, summed child processes or minimum model RAM.** Other engines retain existing shared resource monitoring; this update does not claim native RSS for every engine. An OS kill or direct cancellation may prevent the final worker observation. Previously received execution information, job timestamps and shared resource samples remain available.

Updates merge with previous execution metadata, retaining pipeline/backend identity and enforcing the 16,000-character aggregate limit. Received observations survive failure/restart. Retrying creates a fresh job without carrying previous measurements into it. Generated artifacts separately retain effective parameters and component identities.

Service displays current power-save, idle, background restriction and notification states. The existing **explicit** Export logs action now adds `lma.runtime-diagnostics/1`: a whitelist of version, device states and the latest 64 job observations. This diagnostic object excludes prompts, model settings, file paths and keys. Review/redact the existing log section separately; the entire export is not claimed to be anonymized. Nothing uploads automatically.

## 6. Program checks and rebuild

```powershell
python tools/fetch_multiview_sources.py --fetch
python tools/build_multiview.py --host
python tools/build_multiview.py
python tools/collect_expansion_notices.py
python tools/test_expansion.py
python tools/test_multiview.py
node tests/ui-smoke.cjs
node tools/capture_workbench.cjs multiview
```

Prerequisites are the [native Windows toolchain](BUILD.en.md), pinned sd.cpp JSON headers, Python, JDK and MSVC. Builders fetch fixed source code only. Temporary drive aliases use free letters and are removed in `finally`; the user's existing `S:` is preserved.

Sources: [pixal3d.cpp](https://github.com/raven38/pixal3d.cpp/tree/d1b4926452f9e09702b891db5f05acc845e153ed), [ggml](https://github.com/pwilkin/ggml/tree/737e88f25d4f62254f3b7a726fd9663036cc94da). Generated patches extract the actual MV entrypoint, connect selected steps/simplification/stages, enforce token guards and supply explicit captures for MSVC. Original/generated hashes are retained without mutating the checkout. The CPU pipeline, camera projection, sparse fusion and GLB export compile into the APK; servers, automatic downloads, CUDA/Vulkan and installers are excluded.

The new dedicated suite has **63 checks**, including actual upstream camera/projection functions and **12 real native worker rejection paths**. The shared expansion suite exercises production Java, successful/failed MV process fixtures, private-file cleanup, merged execution persistence and diagnostic whitelists. There are **19 MV UI interactions**, with 20 screenshots / four GIFs / four MP4s across the four current groups. Components and GLB fixtures are bounded and synthetic; no complete trained model, Android emulator or phone was run.

## 7. Remaining benchmark architecture work

The [pinned source audit](../research/portability/audit-v0.3.3.json) rechecks README/install dependencies for D04–D12 without installing or executing them. D03 now has a four-view subset. The other **nine configurations / eight architecture groups** still need actual Android native ports:

| ID | Model | Remaining implementation |
| --- | --- | --- |
| D04 | UltraTex | Mesh input, G-buffers, BTD/BSA attention, matching diffusion/VAE and texture baking |
| D05 | UniForge3D | VGGT poses, anchor fusion, sparse decoding; replace/port CuMesh, FlexGEMM and nvdiffrast |
| D06 | UltraShape | Coarse-mesh input, voxel-query/RoPE refinement, surface extraction |
| D07 | Hunyuan3D 2.1 | Matching shape flow/VAE/meshing; Paint needs a separate runtime |
| D08–D09 | SAM 3D / MV-SAM3D | Mask/depth conditions, sparse/layout operators; MV also needs Depth Anything 3 and scene fusion |
| D10 | SUPRA-Tex | Material prediction, completion, sparse/raster kernels; replace locally or omit optional external back-image stages |
| D11 | TripoSG | RF / SDF VAE, matched exports and surface extraction |
| D12 | PartCrafter | Part-aware generation/decoding and scene output; optional upstream VLM/stylization services are outside local execution |

These are code gaps, **not requests to repeat expensive model acceptance**. Desktop Python/CUDA installation is not an Android runtime, nor proof of permanent impossibility. This release does not claim every benchmark architecture is integrated. The complete frozen F-01–F-12, existing text and selections 01–14/16/17 remain preserved.

![Four-view local workflow; UI FIXTURE, not trained-model output](media/history/v0.3.3/multiview/multiview-ui.gif)

[Choices](media/history/v0.3.3/multiview/01-multiview-models.png) · [Import](media/history/v0.3.3/multiview/02-import-plan.png) · [Four inputs](media/history/v0.3.3/multiview/03-four-view-form.png) · [Queue](media/history/v0.3.3/multiview/04-multiview-queue.png) · [Background states](media/history/v0.3.3/multiview/05-background-observations.png) · [MP4](media/history/v0.3.3/multiview/multiview-ui.mp4) · [Media identity](media/history/v0.3.3/multiview/manifest.json)
