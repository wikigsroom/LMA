# SoulX-Podcast: full acoustic export and native execution

Current implementation: the [dev.21 SoulX App foundation](SOULX_ENGINE.en.md) compiles the shared source into a production worker and connects user bundles, jobs and API. The body below preserves the historical dev.20 research scope; “unregistered” or “outside APK” refers to those independent research executors. Earlier tests are not relabeled as App or phone evidence. A verified complete public asset candidate, speech quality and physical-Android acceptance remain pending.

[中文](SOULX_ACOUSTIC.md) · [Audio frontends / DSP](SOULX_DSP.en.md) · [Complete release requirements](MULTIMODAL_RELEASE_PLAN.en.md) · [Numbered delivery](releases/v0.3.0-dev.20-soulx-acoustic.md)

This source update implements the **acoustic part** of SoulX in [research/soulx_acoustic](../research/soulx_acoustic/acoustic.hpp): semantic codes and reference features → Flow → HiFT → mono 24kHz PCM. Four ONNX graphs retain the full upstream architectures; this244-check suite uses UNTRAINED synthetic parameters. The [trained reference/acoustic follow-up](SOULX_REFERENCE.en.md) separately loads real S3/CAMP/Flow/HiFT and records145/253 checks. It is not complete SoulX starting from text/reference WAV, and is not registered with the APK, catalogue, shared jobs or HTTP API. The development APK remains dev.20 and the public Release v0.2.0; target13 remains open.

## Implemented chain

| ID | Stage / user assets | Contract and behavior |
| --- | --- | --- |
| AC-01 | `flow-encoder.onnx` + `.data` | `tokens int64[1,N]`, `speaker float32[1,192]` → `mu[1,80,2N]`, `spks[1,80]`; original embedding, encoder and speaker projection |
| AC-02 | `flow-estimator.onnx` + `.data` | Complete conditional velocity network; batch2 conditional/unconditional CFG, dynamic time, cosine schedule and default15 native Euler steps; reference prefix is removed only after all iterations |
| AC-03 | `hift-f0.onnx` + `.data` | Full F0 predictor: generated mel `[1,80,T]` → F0 `[1,T]` |
| AC-04 | `hift-source.f32` | Nine original learned linear weights and one bias,40 bytes; native nine-harmonic NSF → learned merge / tanh → real/imaginary STFT |
| AC-05 | `hift-spectrum.onnx` + `.data` | Full HiFT convolution/Snake network; mel and source STFT → magnitude/phase `[1,9,120T+1]`; preserve final default `.01` leaky-ReLU |
| AC-06 | Native DSP | FFT16/hop4 ISTFT, center trimming, overlap normalization and final±.99 clamp; each generated code produces960 samples at24kHz |

Sessions load/release sequentially, with at most one live; the estimator session handles the Flow loop. Execution uses CPU, configurable intra-op threads and inter-op1. Cancellation checks stage/DSP boundaries and uses an independent monitor calling ORT `RunOptions::SetTerminate()` during graph execution. Exceptions release sessions. The developer CLI writes final PCM only after success; it is not an App service endpoint.

Bounds are **375 reference +3000 generated semantic codes =3375 encoder tokens /6750 Flow frames**. The reference prefix must be included, independently of the6000-frame generated-mel bound. Export warms deterministic positional tables for the complete accepted range. Parameters accept1–100 steps,1–32 threads, CFG0–10 and seed−1 or0–2147483647. Code range,192-dimensional speaker vector, reference `[80,2P]`, finite values and output shapes are checked. A120-second generation tensor bound is not a phone speed/memory measurement.

## Offline conversion and user assets

The [converter](../tools/export_soulx.py) reads explicitly selected local `flow.pt`/`hift.pt` with `weights_only=True`, strictly loads original state dictionaries, then folds weight normalization. It rejects missing/extra/colliding keys, nonfinite parameters and existing output directories. It cleans only its own staging directory and atomically commits a new output directory. `soulx-acoustic.json` records asset/checkpoint hashes and sizes, pinned code, contracts and bounds. Without the test flag, `synthetic_parameters=null`: an absent fixture marker does **not** certify trained weights or publisher provenance.

The four graphs, four sidecars,40-byte learned source and manifest are model assets in explicitly selected user/developer directories. **None is bundled or implicitly fetched during App installation, upgrade, browsing or missing-component handling.** Future App integration must use the existing verified bundle/lease layer; this research CLI is not the complete asset-integrity verifier. Native loading additionally checks fixed graph IO and external-tensor locations/ranges, accepting only the corresponding `<graph>.data` sidecar and rejecting path escape.

The [separate reference executor](SOULX_REFERENCE.en.md) now runs S3Tokenizer/CAMPPlus and supplies trained acoustic reconstruction. This acoustic module still lacks Qwen3/tokenizer, multi-speaker text protocol and turn assembly. These acoustic graphs alone do not provide usable TTS. Flat model peers, task/foundation tags, recommendations and per-model settings remain under the existing foundation; no runnable label was added for this incomplete executor.

## Reproduction

Use native Windows MSVC / NDK r30 / CMake / Ninja, without Docker, WSL, virtual machines or emulators. Prepare existing native dependencies/JSON headers and Android ORT using the [developer guide](DEVELOPMENT.en.md). Host requirements include Python3.13, CPU PyTorch, NumPy, SciPy, normal HF/transformers dependencies, safetensors and numba. Evidence records actual torch/numpy versions; it does not claim reproduction of upstream's original torch2.7.1 environment.

```powershell
# Explicit online preparation of developer CODE/dependencies, no model downloads.
python tools/prepare_soulx_acoustic.py --python-dependencies
# Offline conversion of explicitly selected ORIGINAL local checkpoints; output must be new.
python tools/export_soulx.py --checkpoint-dir build/user-soulx-checkpoints --output-dir build/user-soulx-acoustic
# Separate UNTRAINED full-network tests, not the user checkpoints above.
python tools/test_soulx_acoustic.py
python tools/build_soulx_acoustic.py
python tools/test_soulx_dsp.py
python tools/build_soulx_dsp.py
python tools/export_development.py
python tools/check_repository.py --development
```

Offline conversion requires prior preparation; it does not implicitly install dependencies or clone code. Optional packages use `build/soulx-python`; download cache, temporary files and outputs stay in project `build/`. `--synthetic-fixture` explicitly marks UNTRAINED tests. Graphs use opset17/float32; Android needs neither Python nor PyTorch. ARM64 compilation leaves an unregistered CLI in `build/soulx-acoustic-arm64`, without copying it to `jniLibs`.

## Evidence boundaries

[Host execution evidence](../verification/development/soulx-acoustic.json) and the [Android compilation receipt](../verification/development/soulx-acoustic-arm64.json) separately record fingerprints, actual processes/graph runs, stage errors, lifetimes, cancellation and outstanding complete-model/phone gates.

Flow has **112,549,360** parameters and HiFT **20,821,295**, all synthetic and UNTRAINED. Tests execute this converter and the actual original Flow/HiFT `forward` methods for independent references, using complete networks. Reference/total code counts3/9 and4/17 differ from export length12. Native execution order0→1→0 compares mu/spks,15 velocities, mel, F0, learned source and final PCM. Invalid requests, external path escape, pre-stage/loop cancellation and actual ORT termination are checked. Synthetic PCM is not a voice demo.

This round passes **244 scoped checks,12 actual host children,57 completed ORT graph runs,one actual in-run termination and three acoustic outputs**. Across63 stage comparisons, peak velocity error is `1.109e-4` and final PCM error `1.733e-7`. Nine graph/data/source assets total582,584,557 bytes, all in ignored developer directories. After the shared ORT refactor, the rebuilt unregistered Android CLI is520,448 bytes, excluding the existing22,249,560-byte ORT runtime; this is not whole-model RAM usage.

Host ORT1.24.3 DLL version/hash are independently pinned; Android links existing ORT1.28.2 CPU using compatible C API17, with ARM64/API28/16KiB ELF/import checks. **Windows execution plus Android compilation is not Android execution. Trained checkpoints remain0 in this244-check UNTRAINED suite; [trained reference/acoustic component checks](SOULX_REFERENCE.en.md) are recorded separately. Complete SoulX inference remains0 in this244-check suite; the [separate complete trained host pipeline](SOULX_LANGUAGE.en.md) now has output evidence. Speech-quality acceptance0, physical Android0.** Evidence retains `release_ready=false`.

## Sources, licenses and remaining gates

The [source lock](../third_party/soulx-acoustic-source-lock.json) pins SoulX, KISS FFT, ORT and Snake revisions/files and export dependency hashes. [Attribution/licenses](../research/soulx_acoustic/NOTICE) retain Apache-2.0, ORT MIT and Snake MIT. Upstream SoulX references an `incl_licenses` directory absent from its checkout; the actual MIT text is preserved from independently pinned EdwardDixon/snake, without fabricating the missing directory. Checkpoint/converted-bundle provenance and licenses still need separate review.

Within the same complete v0.3.0: finish S3/CAMP user assets and App binding (native reference execution now exists in the [follow-up](SOULX_REFERENCE.en.md)); App integration of the [language/history and complete trained host pipeline](SOULX_LANGUAGE.en.md), long-form/multi-speaker quality; complete explicitly selected user bundles and task/API bindings; fresh-input offline trained outputs, quality/resources and physical Android acceptance. F-01–F-12, existing text, all frozen01–14/16/17 subtargets, nine MOSS variants, SD1.5/SDXL LoRA, old LTX-Video2B0.9.8 distilled, A1–A11/R-01–R-05 and the final Release remain required without reduction or automatic deferral.
