# Old LTX 0.9.8: trained VAE decoding

[中文](LTX098_VAE.md) · [Text encoding](LTX098_TEXT.en.md) · [Sampling](LTX098_SAMPLING.en.md) · [Complete release scope](MULTIMODAL_RELEASE_PLAN.en.md)

Frozen target17 remains **LTX-Video 2B 0.9.8 distilled**. This component converts denoised latents into raw RGB float frames. Text encoding, DiT, VAE, media encoding, App integration, output quality and phone acceptance are separate claims. Developer-host execution does not replace the requirement that every production stage runs on the same Android phone.

## 1. Assets and licenses

The original `Lightricks/LTX-Video` checkpoint is pinned at revision `8984fa25007f376c1a299016d0957a37a2f797bb`: `ltxv-2b-0.9.8-distilled.safetensors`, 6,340,744,492 bytes, SHA-256 `76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f`. Only 132 decoder tensors / 552,814,641 parameters and two channel statistics are loaded. Original BF16 parameters are cast to F32. The VAE encoder is not instantiated, and trained parameters are not replaced with random weights.

The original Lightricks implementation is pinned at `4b2d053057623ddd4d0a1d3e9cd28890e9ef487f`, Apache-2.0. Weights have the separate **LTX-Video Open Weights License 0.x**. See the [configuration, full layout, identities and numerical gates](../third_party/ltx098-vae-source-lock.json).

Exported ONNX graphs and external data are model assets, excluded from Git and the APK. The current offline developer exporter does not establish a complete public one-click download candidate or on-phone conversion. App releases update the foundation; users independently select, download, import, update and delete model assets.

## 2. Exact order

1. Blend explicit noise **in normalized latent space**: `mixed = latent * (1 - noise_scale) + noise * noise_scale`.
2. Denormalize using the original `std-of-means` and `mean-of-means`. Substituting `mean-of-stds` or denormalizing before blending changes the pipeline.
3. Noncausal Conv3D repeats temporal edge frames and uses spatial zero padding. PixelNorm reduces over channels. Conditioned residual blocks use the learned timestep multiplier, embeddings and scale/shift tables.
4. Each of three temporal/spatial upsamplers removes its first frame: `T → 2*T-1`. Final spatial unpatchify scales by 4. `[1,128,T,H,W] → [1,3,8*(T-1)+1,32*H,32*W]`; the small video probe produces17×64×64 frames from a3×2×2 latent.
5. Output remains raw NCTHW F32, without tone mapping, clipping or media encoding. The frozen recipe defaults to timestep `.05`, noise scale `.025` and tone-map compression `0`. The caller supplies noise; this CLI does not claim the complete pipeline's RNG convention.

## 3. Nine sequential CPU graphs

| No. | Stage | Work |
| --- | --- | --- |
| V-01 | stage00 | Noise blend, channel denormalization and conv_in |
| V-02 | stage01 | Five conditioned residual units,1024 channels; largest block 300,980,224 parameters plus shared scalar |
| V-03 | stage02 | Temporal/spatial upsampling,1024→512 |
| V-04 | stage03 |512-channel conditioned residual block |
| V-05 | stage04 | Temporal/spatial upsampling,512→256 |
| V-06 | stage05 |256-channel conditioned residual block |
| V-07 | stage06 | Temporal/spatial upsampling,256→128 |
| V-08 | stage07 |128-channel conditioned residual block |
| V-09 | stage08 | PixelNorm, time conditioning, SiLU, conv_out and unpatchify |

Only one session is live at a time; weights unload before loading the next stage. This reuses the read-only MIT [research ORT helper](../research/soulx_ort/runtime.hpp), not SoulX audio networks. CPU sessions use C API 17, disabled CPU arena/memory pattern and an actual execution-cancellation path. Host ORT 1.24.3 and Android ORT 1.28.2 have separate pinned identities. Android compilation reuses the existing shared ORT runtime.

Nine graphs plus nine sidecars form 18 external assets. The CLI checks the fixed profile, sizes, paths and IO; external references are confined to the declared sidecar. **The research CLI does not calculate asset SHA itself.** Offline tests verify every full digest before execution. App integration still needs the existing asset-integrity manager; size checks must not be described as content verification.

## 4. Reproduction

Use native Windows tools in the repository, with temporary files below `build/tmp`. No Docker, WSL, emulator or off-device inference is used. Explicitly obtain the pinned original checkpoint using the [sampling guide](LTX098_SAMPLING.en.md) first. These commands download no models:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
python tools/ltx098_vae.py export
python tools/ltx098_vae.py references
python tools/build_ltx098_vae.py
python tools/build_ltx098_vae.py --android
python tools/test_ltx098_vae.py
```

The exporter refuses to overwrite existing graph directories. Use a fresh explicit `--output` and manage only your own developer assets when rebuilding. The independent oracle executes **unmodified upstream Decoder.forward**; hooks capture conv_in and seven up blocks, with final frames saved separately. Export wrappers are not the reference implementation.

CLI: `lma_ltx098_vae BUNDLE REQUEST.json OUTPUT.f32`. Requests provide `operation:decode`, local `latents/noise` binaries, `latent_shape`, timestep, noise scale, threads, optional cancellation file and a fresh trace directory. Research bounds are batch 1, 128 channels, T 1…5, H/W1…8 and 1…32 threads. These limits are not phone performance claims. Existing output is preserved; cancellation/failure leaves no final artifact.

Precision gates are frozen before trained decoder inference: maximum absolute error≤0.002, relative RMSE≤0.0002, cosine≥0.999999 and finite values. Different geometries, timestep values and noise scales are compared per stage and at final frames. Windows child-process memory observations exclude GPU and system totals and are not Nubia Z20 measurements.

## 5. Delivery boundaries

| No. | Layer | Component scope | Remaining acceptance |
| --- | --- | --- | --- |
| P-01 | Source | Nine-stage F32 export, native CPU worker, original-forward reference and checks | Report actual validation records separately |
| P-02 | Model | Exact trained VAE/statistics | Complete prompt-to-video chain, RNG/postprocessing, representative quality and resource gates |
| P-03 | Android | ARM64/API28 compilation and ELF checks | Native chain, App binding, public user asset candidate and independent download lifecycle |
| P-04 | Phone | No device evidence | Three load/unload cycles per model,15-minute screen-off, one-hour alternating API and upgrade retention |
| P-05 | Release | No new APK or Release | Complete F-01–F-12, existing text,01–14/16/17, every frozen subtarget and A1–A11/R01–R05 |

Models remain peers. Video generation is an output-task tag; T5/DiT/VAE/ONNX Runtime/CPU/F32/ARM64 describe dependencies and execution conditions. Host validation, Android compilation and phone acceptance are distinct evidence tags. Uncensored status requires its own source-backed content tag and cannot be inferred from modality or model name.


## 6. Validation results

**355 checks /36 actual native children /31 guards pass.** Four trained decoder geometries produce17×64×64,1×32×32,17×32×64 and9×64×32 frames. All 40 stage/final comparison records pass the frozen gates, including separate final-file/stage08-trace checks. Maximum intermediate absolute error is `1.1444091796875e-4`; maximum final-frame error is `2.1457672119140625e-6`; maximum relative RMSE is `2.4708418913210748e-6`, minimum cosine `0.9999999999969488`. All 44 reference files and 18 model assets have their sizes and complete digests verified before execution.

Five complete native decodes, including one repeat, execute 45 graphs. Actual trained execution cancellation completes one stage and interrupts the next, giving 46 successful graph runs in total. Every reported session lifecycle balances, with at most one live session; one real ORT termination is recorded. A larger 5×4×4 latent and one CPU thread make cancellation occur inside Run; a preexisting marker does not satisfy this gate.

| Item | Observation | Limits |
| --- | --- | --- |
| Native CPU time | Four CLIs take approximately 7.40…15.46s including nine loads/unloads and trace writes | Prior SHA reads warm caches; not cold-start or phone performance |
| Windows process |1402 samples at 20ms; maximum observed peak working set 1,238,388,736 bytes, sampled peak private 92,758,016 bytes | Mapped weights and private memory are different measures; no GPU/system/phone total, possible final-interval omissions |
| Host CLI |217,088 bytes, SHA `abfa7108963be7a2be1d91b7c81b7643f783be913885ee8741e5573fdc10e550` | Developer host only |
| ARM64 CLI |504,400 bytes, SHA `da89cbac98b1e7feba625b9c2f425a507a5f898f0f1542570999c0b1b22e15a1` | API28/16KiB compilation with ORT/system dependencies; not in APK or phone-executed |

[Numerical/lifecycle record](../verification/development/ltx098-vae.json) / [host compilation](../verification/development/ltx098-vae-host.json) / [Android compilation](../verification/development/ltx098-vae-arm64.json) / [numbered complete handoff](releases/v0.3.0-dev.21-ltx-vae.md). No prompt-to-video, quality, App or phone acceptance is added.
