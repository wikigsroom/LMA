# Old LTX 0.9.8: real-prompt host video pipeline

[中文](LTX098_PIPELINE.md) · [T5](LTX098_TEXT.en.md) · [Sampling](LTX098_SAMPLING.en.md) · [VAE](LTX098_VAE.en.md) · [One complete release scope](MULTIMODAL_RELEASE_PLAN.en.md)

This developer pipeline connects real prompts, the complete trained T5 encoder, the exact old LTX 2B 0.9.8 distilled 28-layer DiT and eight-step sampler, the trained decoder, and video frames. It is not registered as an App engine. Host execution, Android compilation, App integration, user model acquisition, quality and physical-device acceptance have separate evidence.

## Recipe and provenance

The [pipeline lock](../third_party/ltx098-pipeline-source-lock.json) fixes single-scale LinearQuadratic eight-step Euler, CFG=1, STG=0, no prompt enhancement, decode timestep=0.05, noise scale=0.025, and no tone mapping. Upstream code permits this single-scale path. **The official YAML default multi-scale, spatial-upscaler and prompt-enhancement combination is not reproduced.**

Text uses the separately validated `city96/google-t5-v1_1-xxl-encoder-Q5_K_M` and external original Google tokenizer configuration. The official old LTX default refers to PixArt's T5; matching architecture does not establish matching weights. Neither PixArt weight identity nor original unquantized T5 weights have been compared. Records and demos retain this variant identity. The DiT and decoder remain the exact old 0.9.8 distilled target, without substituting newer LTX2 or random small networks.

## Execution

1. An explicit developer command verifies four existing native executables and the complete SHA of all 21 external model/config files. Missing assets, changed bytes or stale fingerprints fail without downloading.
2. Portable C++ produces `[1,N,128]` initial Gaussian noise, then NCTHW decoder noise from the continuing stream. The frozen algorithm is SplitMix64 + Box–Muller F32 v1; identical seeds do not claim PyTorch bit parity.
3. T5 applies Unicode `strip()`, tokenization and a 256-token bound to the real prompt, returning `[1,L,4096]` token embeddings and a valid-token mask. It uses no synthetic caption or external prompt enhancement.
4. The independent native Vulkan DiT performs all 28 layers over eight steps. C++ restores NCTHW in the original `SymmetricPatchifier` order.
5. Nine native ORT CPU decoder stages load, run and unload sequentially. Noise blending precedes per-channel denormalization; original time conditioning and first-frame cropping remain intact.
6. C++ follows original Diffusers denormalization/clipping, multiplication by 255 and truncation to uint8, producing the existing `LMAFRM1` RGB24 container. Android `VideoEncoder` accepts this format but is not invoked by this developer pipeline.
7. **Host-only** native FFmpeg/libx264 creates MP4; ffprobe checks codec, dimensions, frame count and frame rate. FFmpeg is not an App dependency. Production integration must use the existing MediaCodec/MediaMuxer on the same Android phone.

Children execute sequentially, without retaining T5, DiT and VAE executors simultaneously. Process boundaries isolate the two GGML revisions; their overlapping symbols must not be naively linked together. Jobs retain immutable inputs, native stage results, asset identities and observed child timings/Windows memory. Those are not Android memory, GPU VRAM or system peaks. Failure/cancellation removes unpublished final frames/video while retaining ignored diagnostic intermediates.

The current developer profile accepts 64–256 pixels in multiples of 32, 9–33 frames of 8n+1, and 1–60 fps. This bounds the implementation under test; low-resolution execution does not establish quality acceptance or complete target 17. No real-time performance is promised.

## Independent validation

[Primitive checks](../tools/test_ltx098_tensors.py) compare RNG output with an independent scalar definition, layout with the original publisher patchifier, and complete RGB bytes with original Diffusers conversion. They cover bounds, duplicate keys, NaN/Inf, malformed byte counts, cancellation, existing-file preservation and rollback, without loading trained weights.

[Pipeline checks](../tools/test_ltx098_pipeline.py) run two distinct prompts with identical noise in A/B/A order, checking bitwise neural reproducibility, actual prompt differences, lifetimes and media structure. Non-flat/non-static statistics are diagnostics, not semantic, motion or quality acceptance.

The [independent full-chain oracle](../tools/ltx098_pipeline_oracle.py) calls no native inference executable. It runs unmodified Transformers T5EncoderModel and publisher Transformer3DModel, RectifiedFlowScheduler and Decoder forwards. It separately reconstructs equivalent quantized T5 and converted F16 DiT parameters from pinned assets. Explicit noise is shared as input; independently computed caption errors propagate through the trajectory and decoder to RGB. It does not feed native intermediate outputs into subsequent oracle stages. Frozen gates are max absolute error ≤0.003, relative RMSE ≤0.0003 and cosine ≥0.99999; RGB maximum ≤2 and mean ≤0.02 bytes. Gates cannot be relaxed to turn a failure into a pass.

## Reproduce on native Windows

First explicitly prepare the pinned developer assets, executables and decoder export using the three component guides. No command below retrieves models or invokes Docker, WSL, virtual machines or emulators. Caches, temporary files and results stay inside project `build/`.

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
python tools/build_ltx098_tensors.py
python tools/build_ltx098_tensors.py --android
python tools/test_ltx098_tensors.py
python tools/test_ltx098_pipeline.py
```

Run MSVC and Android builds sequentially with the cached project CMake/NDK. Android compilation establishes an ARM64/API28/16KiB ELF only; it neither runs a phone nor copies binaries into the APK. Full validation executes three actual trained jobs and two independent original-model references. It may take substantial time; no smaller-model or weaker-gate fallback is used. Receipts are `build/ltx098-tensors-tests/results.json` and `build/ltx098-pipeline-tests/results.json`.

## Remaining production boundaries

The APK delivers foundation code without weights, learned vocabularies, ONNX model data, channel statistics, voice or language assets. Developer conversion does not establish on-phone conversion or a public one-click candidate. Production must use shared model/component/recipe descriptors, capability tags, per-model settings and persistent jobs/artifacts. Models remain equal peers; no model-ID-specific UI/queue branch or ComfyUI canvas, nodes or plugin system is introduced.

Users explicitly select and download/import complete dependencies. Missing assets fail locally. Installation, upgrades, browsing, restored queues and failures must never initiate model downloads; restored transfers remain paused. Disk use must disclose the approximately 6.34 GB original checkpoint, 3.85 GB converted DiT, 2.21 GB VAE and 3.39 GB T5 separately. Existing files are never silently replaced/deleted; removing an original is a user decision. These are disk sizes, not runtime RAM requirements.

Component [NOTICE](../research/ltx098_pipeline/NOTICE) files and locks retain separate code/model/quantization attribution. T5's Apache-2.0 declaration does not replace old LTX model terms. Rootless execution of every stage on one Android phone, quality/resource gates, three loads/unloads per model, 15-minute screen-off execution, one-hour alternating API use, upgrade retention and A1–A11/R01–R05 remain required for complete v0.3.0; a host demo cannot close them.


## Executed host jobs and primitive checks

2026-10-29: 157 primitive checks /43 native children /31 guards passed. The independent scalar RNG comparison had zero maximum error; three original RGB comparisons were byte-identical. The host helper is 164,352 bytes; its separate Android build is 426,272 bytes, API28 /16KiB with only libc/libm/libdl dependencies, outside the APK.

| Job | Prompt | Task time including component loading | Output |
| --- | --- | --- | --- |
| 1 | A: red balloon | 1410.89 seconds | 256×256 /33 frames /24fps |
| 2 | B: blue toy car | 574.40 seconds | 256×256 /33 frames /24fps |
| 3 | A: repeat | 398.16 seconds | 256×256 /33 frames /24fps |

Task timings exclude complete preflight asset SHA verification and independent original references. They are not phone or controlled-cache benchmarks. The 21 runtime assets total 9,448,036,748 bytes. Maximum observed Windows child working sets across these jobs are T5 3,651,268,608, DiT 1,221,013,504 and VAE 1,279,008,768 bytes. DiT private committed memory is not GPU VRAM; VRAM and system peaks were not measured.

Manual frame inspection identifies the red balloon and blue toy car, with temporal changes. It does not establish requested motion direction, continuous actions, complete quality or Android acceptance. The separately exported development JSON governs final full-chain numerical conclusions. All model data stays in ignored directories.


## Frozen numerical acceptance: currently failed

The complete review records **163 checks: 157 passed and six floating-point gates failed**. Three actual trained jobs, bitwise A/B/A reproducibility, independent original forwards and outputs were executed; numerical acceptance remains false. TNC latents, their NCTHW counterparts and decoded float frames fail for both cases. Both caption comparisons and both final RGB comparisons pass.

| Metric | Red balloon A | Blue toy car B | Frozen limit |
| --- | --- | --- | --- |
| Latent maximum absolute error | 0.00830925 | 0.00499147 | 0.003, failed |
| Latent relative RMSE | 0.000394183 | 0.000305552 | 0.0003, failed |
| Decoded float maximum error | 0.00375907 | 0.00617547 | 0.003, failed |
| RGB maximum byte error | 1 | 1 | 2, passed |
| RGB mean byte error | 0.00607022 | 0.00381639 | 0.02, passed |

An additional identical-input diagnostic feeds A's independently computed T5 caption to the native Vulkan DiT. Its final eight-step latent error drops to maximum 0.00172329 and relative RMSE 0.0000833611, within the original gates. This suggests amplification of small text-encoder differences is a major contributor. The diagnostic covers same-caption latents only, without establishing complete-chain or quality acceptance. Eight steps, 12 captured file identities and actual child resources are preserved.

`test_ltx098_pipeline.py` writes all passing/failing results and returns **exit 1** for numerical failure. Gates are unchanged; generated output is not a numerical pass. `--reuse-native` / `--reference` validate existing local captures with current source fingerprints and rehash every output; records disclose reuse and newly executed job counts. The public review reuses this round's three actual jobs and two references, without rerunning inference during validation replay.

A passing development repository audit establishes consistency of source, evidence, media and the recorded failure; it cannot override the failed model check. `ltx098_complete_prompt_to_video_host_executed=true`, `ltx098_complete_prompt_to_video_host_tested=false` and `ltx098_full_chain_numeric_accepted=false`. App, physical Android, quality and complete Release remain false. Improve text-conditioning/sampling numerical stability and retest against these same gates.
