# LCM: user assets through local generation

[中文](LCM_APP_FLOW.md) · [Numbered delivery and complete pending scope](releases/v0.3.0-dev.28.md) · [Original preparation experiment](LCM_LOCAL_PREPARATION.en.md) · [Complete release requirements](MULTIMODAL_RELEASE_PLAN.en.md)

Dev.28 connects the small preparation program to the production asset, queue, model and generation modules. The APK contains runtime and preparation code. Users independently acquire the source, base and vocabulary and explicitly prepare derived condition data. The two entries are peers in the flat model library, tagged for images with separate source-asset, runtime and fixed-condition capabilities. Recommendations m08→m06→m01 remain.

This is a product-flow integration. The earlier maximum pixel difference **8 > 5** remains a failed gate. Image quality and Android acceptance remain open; producing a file does not complete target 03 or the full v0.3.0 release.

## 1. User actions

| ID | Action | Behavior |
|---|---|---|
| U01 | Select the LCM Dreamshaper v7 preparation-source entry; download or import the complete file | Transfer requires a click. Repository, revision, size and full SHA256 are pinned |
| U02 | In Local, open runtime assets, review source/output/storage, then start preparation | An explicit `model.prepare` enters the shared queue. Leave the page, cancel or explicitly retry; the original source stays intact |
| U03 | Review and explicitly associate the prepared component with the runtime model | A separate `model.assemble` links verified local data. It downloads no base or vocabulary |
| U04 | Choose to download or import the missing complete base and CLIP merges | Partial models remain paused and cannot generate. Complete file verification is required |
| U05 | Edit that runtime model's settings, open generation, enter a prompt and consent to a local trial | The request owns its parameter snapshot. Production Java verifies the condition contract before starting the bundled native worker |
| U06 | Inspect results, cancel, explicitly retry or reuse a result | Existing background execution, drafts, output recovery, capacity and provenance apply. There is no external inference or implicit dependency download |

The source entry cannot generate directly. Source, prepared assets and runtime have independent records and deletion. Finishing preparation starts no association; association starts no download; installation starts no generation.

## 2. Fixed data and storage

The [model catalogue](../catalogue/model-bundles.json), [preparation plans](../catalogue/asset-preparations.json), [association plans](../catalogue/model-assemblies.json) and [calculation contract](../research/lcm_prepare/contract.json) are authoritative. A model manifest cannot select executable code or another preparation algorithm.

| Asset | Pinned source / revision | Bytes | Purpose |
|---|---|---:|---|
| Original F32 UNet | `SimianLuo/LCM_Dreamshaper_v7` / `a85df6a8bd976cdd08b4fd8f3b73f229c9e54df5` | 3,438,495,328 | Explicit user preparation source, verified with a complete streaming hash |
| Complete GGUF base | `Steward/lcm-dreamshaper-v7-gguf` / `ae3fa73e105d5f848a4ef122e2ce14c92123bf1a` | 2,134,675,232 | Complete matching base; another file with the same name is insufficient |
| CLIP merges | Separately pinned catalogue vocabulary | 524,619 | User download/import; no vocabulary embedded in the APK |
| Derived condition GGUF | Explicit preparation from the original UNet | 5,696 | One F32 bias tensor with source binding; user model data, excluded from APK and Git |

Keeping the original, base and vocabulary requires about **5.57 GB**. Existing verified objects can be reused. Preparation admission also reserves output bytes plus **128 MiB**; the native stage output budget is exactly **5,696 bytes**, separate from this disk margin. Shared admission and execution check resources again. File size is not peak inference memory.

Association uses verified local files with independent hardlink ownership, avoiding a second complete weight copy. Deleting prepared data preserves the runtime's link; deleting the runtime preserves the source. Android filesystem behavior still requires device acceptance. Source retention is a user decision, never automatic cleanup.

## 3. Model settings

| Setting | This recipe |
|---|---|
| Distilled training guidance | Fixed **8.5**, bound to the preparation contract and metadata; distinct from sampler CFG |
| Sampler CFG | Fixed **1**; excessive values clamp to this model's limit |
| Steps | Default **4**, range **1–8**, editable presets |
| Sampler / scheduler | `lcm` / `lcm`, checked when queuing and by native execution |
| Dimensions, threads, seed | Fields and limits belong to this runtime model; default dimensions 512×512; catalogue contains the complete specification |
| Negative conditioning | Disabled; direct requests containing a nonempty negative prompt fail |
| LoRA | This fixed condition does not accept additional LoRA that could change the folded time embedding. Select an independent base for LoRA. Existing SD1.5/SDXL LoRA paths remain |

Settings belong to the model record. Clamping and sampler adjustments produce an immutable `diffusionPlan`, rechecked before execution and recorded in provenance. They do not overwrite peer settings. Restoring a task or draft requires explicit submission.

## 4. Foundation implementation

1. `ModelPreparations` reads only bundled, source-bound plans. `NativePreparation` reads a private leased source and starts registered, verified App programs. Stage output limits and disk reserves are separate.
2. The native preparer hashes the whole source using a 4 MiB buffer and reads three required tensors to calculate the fixed condition bias. Its 256 mathematical constants contain no learned parameters. The derived 1,280 bias values are user model data.
3. `PreparedAssets` verifies output bytes, SHA, complete-source receipt and identity before committing. Cancellation, missing files or mismatches publish no successful preparation.
4. `PreparedModelAssembly` applies only an explicitly confirmed role mapping. Its fingerprint binds the preparation plan, source record and runtime manifest. Missing dependencies remain paused without calling the downloader.
5. Java and C++ `LcmCondition` validation require exactly one GGUFv3 tensor, six exact metadata fields, matching source/base SHA, 1,280 finite F32 values, zero padding and exact end of file. Extra tensors, unknown bindings, truncation, wrong types and NaN fail.
6. `SdEngine` verifies full component leases and the sampling snapshot, then supplies a separate `condition_bias`. Native loading failures stop generation instead of silently continuing with the original bias. Other adapters continue using the shared foundation.

Preparation does not connect to a network, execute user scripts or install plugins. Model manifests describe data, never programs. Product execution requires no ROOT, Termux, virtualization or ComfyUI and is designed to run all stages on the same Android phone. Development checks use native Windows production sources with explicitly identified Android system ports.

## 5. Validation and media

See the [current evidence index](../verification/development/status.json) and [delivery record](releases/v0.3.0-dev.28.md). Parser rejection controls, complete-source preparation, actual Java/native generation and Android compilation have separate scopes. Equality with the earlier native-prepared PNG does not repair the failed official-reference pixel comparison.

| Preparation review (UI fixture) | Association review (UI fixture) |
|---|---|
| ![Preparation](media/development/lcm/01-prepare.png) | ![Association](media/development/lcm/02-associate.png) |

[Dependencies](media/development/lcm/03-dependencies.png) · [Generation settings](media/development/lcm/04-generate.png) · [Recording](media/development/lcm/lcm-ui.mp4) · [GIF](media/development/lcm/lcm-ui.gif) · [Media hashes and source](media/development/lcm/manifest.json). These are explicitly labelled UI FIXTURE interactions, not Android inference recordings. Historical trained imagery remains separately archived in the [original experiment](LCM_LOCAL_PREPARATION.en.md).

The following actual 512×512 PNG comes from this turn's production Java → native Windows worker, using four steps, seed 42 and CFG 1. Preparation, association, dependency installation and inference use production modules. An explicit retry after cancellation produces identical PNG bytes. The [two original PNGs and source manifest](media/development/lcm-app-trained/manifest.json) are separate from UI fixtures. The fox's face is blurred; quality evaluation and the failed reference pixel gate remain open. This is not Android acceptance.

![Actual current Java/native Windows LCM output; not Android](media/development/lcm-app-trained/native-prepared.png)

```powershell
python tools/test_lcm_app_host.py
python tools/render_lcm_app_host.py
python tools/test_preparations.py
python tools/test_assemblies.py
python tools/test_diffusion.py
node tests/ui-smoke.cjs
node tools/capture_workbench.cjs lcm
python tools/build.py
python tools/verify_package.py
python tools/test_android_lint.py
```

The full model test uses existing, explicitly acquired fixed files in development storage. It never downloads missing data. Native JDK, Windows C++ tools, Android SDK/NDK, Playwright and FFmpeg setup is described in [Build](BUILD.en.md) and [Media](MEDIA.md). Owned browser contexts, processes and drive aliases are closed in cleanup.

## 6. Remaining gates

Numerical/pixel differences from the original full pipeline, image quality, Android generation, memory, thermal behavior, screen-off operation and long-running API acceptance remain required. Source license fields are declarations, not completed legal review of every component. Every frozen target and the full release gate stay in the same required scope; see the [complete pending table](releases/v0.3.0-dev.28.md#完整同版待完成--remaining-in-the-same-complete-release).
