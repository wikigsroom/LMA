# Old LTX-Video 0.9.8: native DiT component

[中文](LTX098_DIT.md) · [Documentation](README.md) · [Numbered delivery and pending work](releases/v0.3.0-dev.21-ltx-dit.md)

This implements part of frozen target **17: LTX-Video 2B 0.9.8 distilled**. It is an unregistered native DiT research component outside the App. It does not provide complete video generation. The development APK remains **0.3.0-dev.21 / code 25**, and the public Release remains **v0.2.0**. All F-01–F-12, targets 01–14 / 16 / 17 and frozen subtargets remain in one complete v0.3.0.

## 1. Architecture and provenance

| Item | Pinned identity |
| --- | --- |
| Publisher code | [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video/tree/4b2d053057623ddd4d0a1d3e9cd28890e9ef487f), Apache-2.0 |
| Checkpoint | [ltxv-2b-0.9.8-distilled.safetensors](https://huggingface.co/Lightricks/LTX-Video/blob/8984fa25007f376c1a299016d0957a37a2f797bb/ltxv-2b-0.9.8-distilled.safetensors); only its pinned header was read, without trained tensor data |
| DiT | 28 layers, hidden size 2048, 32 heads of size 64, 128 input/output channels, caption width 4096; 715 tensors / 1,923,385,472 parameters |
| Native execution | GGML `a5915eb0e47adef21c3f25b889a008925ea838c2`; independent C++ graph; explicit CPU or Vulkan with no automatic CPU fallback |
| Asset format | Dedicated GGUF architecture `lma-ltx-video-098`; F32 or F16 dense weights with F32 remaining parameters; no production model converter yet |
| Build | Native Windows MSVC / NDK r30, project-local CMake / Ninja, Vulkan / SPIRV headers and recent shaderc; no virtualization |

The [source lock](../third_party/ltx098-source-lock.json) records source/dependency hashes, checkpoint header and layout hashes, oracle versions and the Windows compiler origin. Google's published unsigned SLSA statement matches the downloaded ZIP digest and source revision; signature verification is not claimed. Compiler binaries remain in the ignored developer cache.

No LLM-Hub implementation is incorporated; its license was reviewed separately. The newer LTX2 implementation in [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) is not substituted for old 0.9.8. Source licenses and the checkpoint's LTXV Open Weights License 0.X are separate. See [NOTICE](../research/ltx098/NOTICE) and the accompanying complete license texts.

## 2. Implemented component

`research/ltx098/` loads local weights, builds the graph and writes raw velocity:

1. Validate architecture, old-version constants, every tensor name/shape/encoding and file byte range. Non-publisher sizes require explicit `--fixture` mode.
2. Execute input/caption projections, 256-dimensional time embeddings and six-way AdaLN modulation with global or per-token sigma.
3. Execute all 28 self-attention/cross-attention/FFN blocks, QK RMSNorm, three-axis RoPE, masking, residuals and final LayerNorm/projection. RoPE acts on the full hidden dimension before head splitting and retains old position constants/layout.
4. Use explicit float32 tanh GELU instead of CPU half lookup; materialize contiguous attention matrices and require float32 accumulation. Vulkan uses float32 shaders with process-local cooperative/F16 arithmetic paths disabled because those paths reduce input precision in the pinned backend. F16 dense weight storage still executes on GPU. Performance remains unmeasured.
5. Release backend, weights, graph and compute buffers through RAII. Bound tokens/text/threads/sigma/masks and reject non-finite inputs, overwritten outputs and uncompiled Vulkan requests.

The standalone worker accepts only local paths and JSON, with no network or shell execution. Inputs are already encoded caption/latent/coordinate/sigma arrays. Output is **raw float32 velocity**, not sampled latents, images or video.

## 3. Independent verification and limits

`tools/ltx098_fixture.py` imports the pinned publisher `Transformer3DModel` implementation. It first instantiates the complete architecture on the meta device and verifies all 715 tensor shapes / 1,923,385,472 parameters against the actual checkpoint header. Fixed-seed untrained reduced-width networks then provide executable references.

| Check | Actual coverage | Not established |
| --- | --- | --- |
| Publisher forward parity | 2 / 3 / 28 layers at widths 24 / 32; global/per-token time, text masks and changed masked padding | No full-width trained checkpoint execution |
| Two weight precisions | F32 and F16 dense weights against the original float32 forward; F16 reference rounds/dequantizes the same weights | No arbitrary quantization compatibility |
| Two backends | Real CPU and NVIDIA RTX 3060 Vulkan child processes, explicit device and precision policy | No Android GPU or Z20 execution |
| Fixed gates | F32 max error `1e-4`, RMSE `3e-5`; F16 max error `.005`, RMSE `.001` | No video quality, speed, thermal or peak-RSS measurements |
| Guards | Missing/extra tensors, wrong config, truncation, shape/sigma/mask/thread limits, fixture opt-in, fallback and output overwrite | Not complete production parsing/security qualification |
| Android build | Separate ARM64 / API28 / 16 KiB ELF/dependency evidence | Compilation does not prove phone execution, background operation or complete video |

The pinned GGML Vulkan backend requires **Vulkan 1.2**; its cm2 shaders use a separate 1.3 route that this component disables. Android API28 is only the compilation minimum and does not establish old-phone driver compatibility. Nubia Z20 driver capabilities, available memory and complete-pipeline resources remain untested; no handset support claim is made.

See [native parity evidence](../verification/development/ltx098-transformer.json), [Android build evidence](../verification/development/ltx098-transformer-arm64.json) and the [numbered handoff](releases/v0.3.0-dev.21-ltx-dit.md) for counts, errors and scope. `trained_weights_loaded / video_outputs / engine_registered / physical_android / complete_video_pipeline` remain false.

## 4. Reproduction

Use native Windows PowerShell from the repository root with the existing project toolchain and pinned CPU torch/numpy versions. All dependency caches, compiler files and temporary files remain under this project's `build/`. Explicit developer preparation fetches source/tools; it is not an App model download.

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:TEMP=Join-Path $PWD 'build/tmp'
$env:TMP=$env:TEMP
python tools/fetch_native.py
python tools/fetch_ltx098.py --python-dependencies
python tools/test_ltx098.py
python tools/build_ltx098.py --android --vulkan
python tools/export_development.py
python tools/check_repository.py --development
```

The test builds/reuses fingerprinted host executables sequentially, then runs actual native children and the original oracle. Failure removes the passing report. Fixtures/raw outputs/logs stay in `build/ltx098-tests/`. Builds use a temporary ASCII SUBST alias, removed in `finally`; never run these builds concurrently. `--cpu-only` is diagnostic and cannot satisfy the dual-backend repository checks.

## 5. Product requirements and remaining work

The APK updates the foundation. Users choose, download, import, update, roll back and remove model assets in the flat model catalogue. Installation/upgrades/browsing/missing components do not initiate downloads. Settings follow each model and jobs retain immutable snapshots. Recommended m08 → m06 → m01 stays unchanged.

Target17 retains **video** and **ltx_video_098** tags, with independent **ltx_vulkan_port / ltx_qnn_port** routes and format/device/license/evidence/content tags. Neither QNN packages nor host Vulkan evidence automatically enables another route. This research component has not registered App execution support.

| ID | Pending work | Acceptance |
| --- | --- | --- |
| P-01 | Complete user assets/conversion | Exact old DiT, T5/tokenizer and matching VAE with fixed origins/formats/checksums/licenses; explicit user downloads/imports, no model data in APK |
| P-02 | Complete same-phone video | Text encoding, actual latent coordinates/time, distilled sampling, VAE decoding, frames/MP4, sequential lifetimes, budgets and cancellation |
| P-03 | Trained models/quality | Full-size trained checkpoint comparisons, fresh-input videos, quality/resources/device scope; reduced-width parity is insufficient |
| P-04 | App integration | Per-model settings, dependency/compatibility tags, shared jobs/API/artifacts/cancellation/migration; no canvas or plugin ecosystem |
| P-05 | Device/Release | Every pipeline on physical Android, three load/unloads, 15-minute screen-off, one-hour alternating API, upgrade retention, A1–A11 / R01–R05 and every frozen target/subtarget in the same version |

No Android phone is available, as already established. Host output, compilation and UI FIXTURE media remain separate from phone acceptance. This source-only update changes no App page, retains the dev.21 screenshot/recording/GIF fixtures, and provides no fabricated video-generation demonstration.
