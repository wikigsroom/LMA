# Old LTX 0.9.8: external assets and native sampling

[中文](LTX098_SAMPLING.md) · [DiT architecture](LTX098_DIT.en.md) · [Documentation](README.md) · [Numbered handoff](releases/v0.3.0-dev.21-ltx-sampling.md)

This extends the unregistered research component for frozen target **17, LTX-Video 2B 0.9.8 distilled**, with explicit checkpoint acquisition, streaming local GGUF conversion, old-version coordinates/layout and eight-step sampling. **It is not complete video generation**: T5/tokenizer and VAE have not executed, no video was produced, and there is no Android execution. APK remains **0.3.0-dev.21 / code 25**; public Release remains **v0.2.0**.

## 1. Foundation and user assets

The APK contains none of these weights, GGUFs, vocabulary, text encoder or VAE. Acquisition/conversion commands below are explicit developer actions. Installation, upgrades, browsing, missing components and test startup do not download models. Future App support must preserve user selection, downloading, import and management; a developer cache is not a complete public asset candidate.

| Item | Pinned identity |
| --- | --- |
| Original checkpoint | [Publisher file](https://huggingface.co/Lightricks/LTX-Video/blob/8984fa25007f376c1a299016d0957a37a2f797bb/ltxv-2b-0.9.8-distilled.safetensors), revision `8984fa25007f376c1a299016d0957a37a2f797bb` |
| Size / SHA256 | `6,340,744,492` bytes; `76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f` |
| Contents | BF16 DiT, matching VAE encoder/decoder and channel statistics; **no T5 or tokenizer** |
| Converted subset | DiT only: 715 tensors / 1,923,385,472 parameters; F16 two-dimensional dense weights, F32 other parameters; standard GGUF v3 with `lma-ltx-video-098` architecture |
| GGUF size / SHA256 | `3,849,516,416` bytes; `ef29c886b36f8a1dbc6693002256049407e512da7a61bf2cc750f1d4d2277ebf` |
| License | Separate LTXV Open Weights License 0.X model terms; source/GGML notices in [NOTICE](../research/ltx098/NOTICE) |

The [asset identity lock](../third_party/ltx098-trained-assets.json) is metadata, not an installed model. The downloader verifies local files by default; only explicit `--download` retrieves assets. It checks every range/total length, resumes only the same pinned identity and publishes the final file after the whole SHA256 passes. A mirror changes the asset transport only; it never performs inference.

The converter reads one tensor at a time rather than copying the entire multi-GB checkpoint. It validates exact-old config/layout, offsets, overlaps, truncation, finite values, F16 overflow and source identity during conversion. Output directories must be new. It writes into a sibling staging directory, checks the result and atomically renames it; failures preserve input/existing assets and remove its own staging directory. It never downloads and is not yet an App import path.

## 2. Native behavior and bounds

1. Latent dimensions are `F=(frames-1)/8+1`, `H=height/32`, `W=width/32`; tokens flatten `F,H,W`, with channels inside each token. Unpatchify restores `B,C,F,H,W`.
2. This old checkpoint has `causal_temporal_positioning=False`. Coordinates scale by `[8,32,32]`; time multiplies by float32 `1/fps`. The newer first-frame causal fix is not applied.
3. Publisher `LinearQuadratic(8,.025)` uses actual times `1, .99375, .9875, .98125, .975, .909375, .725, .421875`. Four-decimal checkpoint metadata checks allowed steps; it must not replace those actual times.
4. Deterministic RF selects the closest schedule time strictly below `time-1e-6`, then computes `sample-dt*velocity`. The single-step operation distinguishes scalar/global and per-token time. Global zero fails; per-token zero preserves its sample.
5. The eight-step loop retains one DiT instance, emits actual stage events and graph allocations, and optionally writes raw latent traces. Cancellation is checked around each forward, with no final artifact after cancellation. This boundary is between forwards; production Android interruption remains unfinished.
6. Research bounds are width/height `32..2048` in multiples of 32, `1..257` frames in `8n+1` form, fps `1..240`, at most 4096 latent tokens and 256 text tokens. They are not phone resource guarantees. Custom CFG/STG, replacement schedulers, image-to-video, production initial-noise generation and batching are not exposed; unknown settings fail explicitly.

The worker has no network or shell calls. Missing/incompatible assets fail locally; CPU/Vulkan selection is explicit, without a remote fallback. Pinned GGML Vulkan requires **Vulkan 1.2**. Current F32 shader arithmetic verifies F16 weight storage; it does not establish Z20 driver compatibility or performance.

## 3. Verification scope

Full new results are in the [sampling receipt](../verification/development/ltx098-sampling.json). The previous 675 checks / 80 actual children / 48 comparisons remain in the [separate DiT receipt](../verification/development/ltx098-transformer.json). Check counts are not video quality measurements.

| Result | Measured scope |
| --- | --- |
| 692 checks / 58 actual native children / 33 guards | 22 math cases, ten untrained eight-step trajectories, full trained Vulkan forward/sampling; 111 error records |
| Coordinates / unpatchify / RF | All 22 cases exactly match publisher outputs |
| Untrained CPU/Vulkan eight-step trajectories | CPU F16 max `3.45827e-4` / RMSE `1.36672e-4`; Vulkan max `6.55651e-7` / RMSE `2.96737e-7`, within frozen gates |
| Full trained DiT velocity | Max `6.91414e-6`, RMSE `1.63089e-6` |
| Full trained eighth-step latent | Max `3.57628e-6`, RMSE `8.72783e-7` |
| Host resources / time | RTX3060 Vulkan; eight-step CLI including loading about `21.26s`; weight buffer `3,849,462,272` bytes, per-step GGML graph buffer `1,874,992` bytes; observed Windows peak working set `1,216,548,864`, sampled peak private `4,021,002,240` bytes |

Timing describes one host run with this tiny latent input, not phone speed or video FPS. Tests read the complete GGUF to verify its hash first; file-cache state can affect loading time. Cold-start timing remains unmeasured. Process counters are sampled every 20ms and exclude GPU VRAM, the final sampling interval and total system use. A GGML graph buffer is not the full-pipeline peak. Full trained checks currently cover Vulkan only; full trained CPU and Android execution remain unverified.

The untrained suite executes publisher `SymmetricPatchifier`, coordinate conversion, `RectifiedFlowScheduler` and original 2/28-layer PyTorch forwards. It checks math, F32/F16 and converted BF16-to-GGUF CPU/Vulkan trajectories, invalid geometry/times/settings, existing-file protection, malformed checkpoint cleanup, and cancellation after an actual neural forward starts.

The trained suite uses the complete pinned BF16 checkpoint and unmodified official 28-layer `forward`. Module pre/post hooks page one module's F32 parameters into CPU and return it to meta after computation. The largest scheduled parameter allocation is `268,623,872` bytes, **not peak RSS**. All 715 trained tensors execute across eight steps. Native execution loads the independent F16/F32 GGUF and records step errors, graph allocations and backend identity.

Each publisher-reference directory records every artifact size/SHA256. Tests verify all inputs, expected outputs and fixture GGUF files first; missing, extra or changed reference files fail.

Inputs are limited to **64×64 / 17-frame / 24fps latent geometry, 12 latent tokens and 5 synthetic caption-embedding tokens**. T5 does not run. This is not a video from a new prompt and cannot establish image quality, prompt adherence, playable frame rate, phone memory or background endurance. Frozen trained-velocity gates are max `2e-3` / RMSE `5e-4`; eight-step latent gates are `1e-2` / `2e-3`. Failed comparisons must not be relabeled by widening gates.

The [Android build receipt](../verification/development/ltx098-transformer-arm64.json) separately checks probe and sampler ARM64/API28/16KiB ELF identity/dependencies. Neither executable is in the APK; compilation does not prove device execution. Legacy `model_inference=false` denotes complete Android acceptance. Separate trained-DiT host flags cannot enable a complete-video claim.

## 4. Reproduction

Use native Windows PowerShell from the repository root, without Docker, WSL or emulators. Prepare code/oracle dependencies as in [BUILD](BUILD.en.md) and the [DiT guide](LTX098_DIT.en.md). Developer assets stay in ignored `build/`; none of these commands performs remote inference.

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:TEMP=Join-Path $PWD 'build/tmp'
$env:TMP=$env:TEMP
python tools/test_ltx098.py
python tools/fetch_ltx098_trained.py --download
# Explicit mirror alternative: --origin https://hf-mirror.com
python tools/export_ltx098.py --checkpoint build/ltx098-trained/originals/ltxv-2b-0.9.8-distilled.safetensors --output-dir build/ltx098-trained/converted
python tools/ltx098_sampling_oracle.py --output build/ltx098-sampling-oracle
python tools/ltx098_sampling_oracle.py --output build/ltx098-trained/oracle --checkpoint build/ltx098-trained/originals/ltxv-2b-0.9.8-distilled.safetensors
python tools/test_ltx098_sampling.py --trained --skip-build
python tools/build_ltx098.py --android --vulkan
python tools/export_development.py
python tools/check_repository.py --development
```

Conversion/oracle output directories must be fresh. Preserve old records independently before a rerun, or select new developer directories and adjust test paths accordingly. Native builds use a temporary ASCII SUBST removed in `finally`; execute builds sequentially. Sampling tests never download missing assets, recompute an oracle implicitly or relabel untrained results. Missing/mismatched files or fingerprints fail.

Developer CLI: `lma_ltx098_sample MODEL.gguf|- REQUEST.json OUTPUT.f32 cpu|vulkan THREADS [--fixture]`. `--info` lists geometry/rf_step/unpatchify/sample. Sampling requires externally supplied latents, caption embeddings and mask. Only reduced test networks use explicit `--fixture`; this CLI is not a finished user text-to-video feature.

## 5. Required work in the same release

| Number | Pending work | Required evidence |
| --- | --- | --- |
| P-01 | Complete target-17 user assets | Pinned T5/tokenizer, matching VAE, download/import/update/rollback and licensing; a developer conversion is not a complete downloadable candidate |
| P-02 | Complete same-phone pipeline | Actual prompt encoding, production noise/settings, VAE/frames/MP4, sequential lifetimes, resource budgets and production cancellation; at least one compatible declared Vulkan/QNN route; QNN is an optional alternative, with independent evidence required if exposed |
| P-03 | App integration | Equal model peers; task/foundation/backend/format/device/evidence/license/content tags; per-model snapshots and shared jobs/API/artifacts, without a ComfyUI canvas or user plugin ecosystem |
| P-04 | Entire frozen scope | F-01–F-12, existing text, 01–14/16/17, all nine MOSS variants, SD1.5/SDXL LoRA and every frozen subtarget, with real trained output/quality/resources; no deferral |
| P-05 | Android and Release | Each model: three load/unloads, 15-minute screen-off, one-hour alternating API, upgrade retention, A1–A11/R01–R05; publish one complete v0.3.0 only after all gates pass |

No physical phone is available; this is already known. There is no App UI change in this follow-up, so accurately labeled dev.21 fixture screenshots/recording/GIF remain applicable. No video-generation demo is fabricated. Recommended m08→m06→m01, All/search/Local, user-controlled assets and per-model settings remain required.
