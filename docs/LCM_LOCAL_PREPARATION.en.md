# Small local LCM preparation component

**Historical scope:** This page preserves the original dev.24 experiment. Dev.28 connects preparation, the condition role, explicit association and generation to the App; see the [current flow](LCM_APP_FLOW.en.md). Statements about missing integration or unchanged APK describe the original commit. The maximum pixel difference failure 8 > 5, quality and Android gates remain open.

[中文](LCM_LOCAL_PREPARATION.md) · [Previous trained checks](SD_DISTILLED_TRAINED.en.md) · [Numbered delivery and complete pending scope](releases/v0.3.0-dev.24-lcm-preparation.md)

This round implements a native preparation program without learned parameters. It verifies the separately acquired original LCM UNet and creates a small conditioning component, avoiding an additional 2.13 GB patched checkpoint. Actual Windows execution and Android compilation have separate receipts. The current dev.24 APK does not yet include this program, a derived-component recipe or the corresponding user flow.

## Sources and computation

The [preparation contract](../research/lcm_prepare/contract.json) pins the 3,438,495,328-byte original F32 UNet from `SimianLuo/LCM_Dreamshaper_v7` and the matching 2,134,675,232-byte complete checkpoint from `Steward/lcm-dreamshaper-v7-gguf`. Repository revisions, files, byte counts and complete SHAs are independent identities. This is not a general repair for files sharing a model name. Previous comparison found all 686 converted tensors equal to the original cast values, with the conditioning projection omitted.

The computation is `b0′ = b0 + W0 × Wcond × guidance_embedding(8.5 − 1)`. `W0` receives the matching F16 rounding; the original condition projection remains F32. Sequential F64 dot products return to F32 after each linear result, with FMA disabled. Output need not be bit identical to PyTorch's parallel FP32 dot products; explicit numerical gates apply. Complete official UNet equivalence for this new C++ implementation remains unproved. Previous full-UNet checks used a different folded bias and do not transfer automatically.

The 256 embedded guidance values are unlearned sine/cosine constants. The [generator](../tools/generate_lcm_condition_contract.py) recomputes them from pinned official diffusers v0.22.0 source without reading model parameters. These 1,024 mathematical bytes have SHA `54d6aabf1d7a3082cbf26313138517135674c6216bd9c2a2636e1f8809ea8250`.

**Fixed distilled guidance 8.5 and sampler CFG 1 are different parameters.** This component supports the fixed value 8.5. Changing task CFG cannot change that conditioning, and this receipt does not cover arbitrary guidance, quantization or base models.

## Native boundary

[prepare.cpp](../research/lcm_prepare/prepare.cpp) reuses local preparation I/O. It bounds and validates the Safetensors header, tensor shapes, contiguous ranges and total file length, then streams the complete SHA. It retains three calculation tensors totaling 1,971,200 parameter bytes and a 4 MiB input block. It never loads the entire checkpoint or modifies the source.

`lcm-condition-bias.gguf` is 5,696 bytes: one 1,280-element F32 bias, 5,120 learned bytes and source metadata. Metadata binds the source SHA, base SHA, algorithm, fixed guidance and sampler CFG. Derived learned data remains in ignored developer storage or future explicitly selected user storage, never Git or the APK.

Preparation uses an exclusive staging directory, file synchronization and read-back verification before committing. Invalid sources, non-finite parameters, budgets, unknown/duplicate fields, unsafe names and cancellation fail while retaining the source and cleaning owned temporary files. Existing destinations cannot be overwritten. The Android program inherits the preparation foundation's parent-death guard. ARM64/API28/16 KiB compilation and absence of network/child-process imports do not test Android execution, power-loss durability or background lifetime.

## Actual checks and media

[Core checks](../verification/development/lcm-preparation-core.json) execute 24 native children and 105 assertions covering repetition, identity/format/parameter errors, cancellation and recovery. Every one of the 1,280 synthetic output scalars matches an independent fixed-order oracle bit for bit. Maximum deviation from the FP32 PyTorch equation is `5.960464477539063e-08`.

[Trained checks](../verification/development/lcm-preparation-trained.json) actually verify the complete 3.44 GB source. Output SHA is `213f8a346cf0a70b2cfbb6460f2c9e990b3c45c6fdd435002a82c906e2d3c66c`. Every output scalar matches the independent calculation. Maximum bias deviation from the FP32 equation is `1.4901161193847656e-07`; the nonlinear first time-projection stage at six deterministic inputs differs by at most `1.430511474609375e-06`. That is not a complete UNet or quality result. Observed preparation takes 214.327 seconds with a 12.46 MiB host peak working set; this is not phone performance.

[Actual native image captures](../verification/development/lcm-overlay-trained.json) retain raw logs, images, time and host memory observations for an original-bias control, native-prepared component, invalid CFG, actual sampler-step termination and recovery. The [independent audit](../verification/development/lcm-preparation-capture-audit.json) rereads153 raw files,31 native process records, complete source objects, derived data and four actual PNGs. It preserves a strict observer's historical failure on one empty stdout line: that process completed and its PNG exactly matched the earlier full patched checkpoint. The new capture permits only whitespace-only extra lines while retaining the original observer error list. All five execution checks complete and recovery PNGs match exactly. However, the new C++ result differs from the previous PyTorch-folded image by mean RGB 0.083892822265625 (limit0.1) and maximum8 (limit5). **The preset pixel-equivalence gate fails. The candidate remains rejected; thresholds and App support are unchanged.**

![Actual host outputs, not Android screenshots](media/development/lcm-preparation-contact-sheet.png)

The [GIF](media/development/lcm-preparation-slideshow.gif) and [MP4](media/development/lcm-preparation-slideshow.mp4) are labelled still slideshows of actual host PNGs, **not App/Android recordings**. Fox/teapot details remain visibly defective. Image quality and complete official-pipeline equivalence remain unaccepted.

## User assets and remaining product integration

The intended product flow reuses Local management, shared preparation jobs, derived assets and explicit association: select source → review required files/storage → explicitly download or import → explicitly prepare → select matching base and vocabulary → explicitly associate → independently manage/run in Local. Installation, upgrades, browsing and paused-job restoration must never trigger model downloads. Source, runtime base, vocabulary and derived component remain independent assets; deletion/update must respect job references and active leases.

For a user explicitly selecting this particular recipe, source UNet, base checkpoint and CLIP merges total 5,573,695,179 bytes, plus a 5,696-byte derived file and staging space. The small component saves a patched duplicate; it does not reduce the runtime base's memory requirement or establish Nubia Z20 readiness. These are optional recipe assets, not mandatory LMA installations.

Current Java `SdSpec` still requires either a complete checkpoint or independent diffusion components. Host experiments invoke the lower-level two-file loader directly, so they do not establish App recipe support. Product integration needs a distinct condition-component role, exactly one validated tensor, source/base binding, fixed guidance, preparation receipts and immutable snapshots before mapping to the underlying override path. Missing, corrupt or mismatched components must fail before engine launch; the product cannot rely on a loader that might continue with the original bias after an override error.

Existing user models/settings, Recommended `m08 → m06 → m01`, HF All/search and Local management retain their requirements. Only foundation capability is updated. All models remain peers, with separate task, format, backend, dependency, device, evidence, license and content tags; uncensored remains an independently attributed content tag.

## Developer reproduction

These commands are explicit developer actions without asset downloads. They require previously acquired pinned files and native Windows tools. No Docker/WSL/VM/emulator is used.

```powershell
python tools/generate_lcm_condition_contract.py
python tools/build_lcm_prepare.py
python tools/build_lcm_prepare.py --android
python tools/test_lcm_prepare.py
python tools/test_lcm_preparation_trained.py
python tools/test_lcm_overlay_trained.py
python tools/check_lcm_preparation_evidence.py --capture-audit
python tools/render_lcm_preparation.py
python tools/export_development.py
python tools/check_repository.py --development
```

The first busy-host compilation reached the 300-second observation timeout. Its failure log is retained; after checking owned compiler processes have ended, continue the same build directory without duplicating a live producer. Compilation is not device execution. F-01–F-12, existing text, selections 01–14/16/17 and every frozen subtarget still share one complete v0.3.0 gate. No complete Release has been published.
