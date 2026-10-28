# SoulX trained reference models and acoustic reconstruction

[中文](SOULX_REFERENCE.md) · [Acoustic networks](SOULX_ACOUSTIC.en.md) · [Audio primitives](SOULX_DSP.en.md) · [Numbered delivery](releases/v0.3.0-dev.20-soulx-reference.md)

This implementation runs trained S3Tokenizer v2, CAMPPlus and Flow/HiFT in native research executors: **reference PCM → semantic codes / speaker embedding / mel → reconstructed PCM**. All four publisher components load trained weights. Target codes come from S3 encoding another synthetic PCM input, without text or Qwen3. Complete SoulX TTS, user bundles, App jobs/API and Android execution remain outstanding.

Sources are [research/soulx_reference](../research/soulx_reference/reference.hpp), the [shared ORT policy](../research/soulx_ort/runtime.hpp) and the existing acoustic module. They are unregistered and excluded from the APK. The development APK remains 0.3.0-dev.20/code24; the public Release remains v0.2.0. Every frozen requirement remains in the same complete v0.3.0.

## Execution contracts

| ID | Stage | Layout and bounds |
| --- | --- | --- |
| SR-01 | Decoded reference | Mono24kHz float32 PCM,24000–360000 samples/1–15seconds, finite and within±1; WAV/App input binding pending |
| SR-02 | Three frontends | Existing native DSP retains separate S3, CAMPPlus and Flow resampling/normalization/mel rules |
| SR-03 | Complete S3Tokenizer v2 | `feats float32[1,128,T]`, `feats_length int32[1]` → `indices int32[1,ceil(T/4)]`; T≤1500, at most375 raw codes, values0–6560; no invented length output |
| SR-04 | Complete CAMPPlus | `input float32[1,T,80]` → `output float32[1,192]`; preserve the original embedding without added L2 normalization |
| SR-05 | Prefix alignment | `P=min(raw_codes, Flow_frames/2)`; retain P codes and `[1,80,2P]` mel. The nonintegral input actually yields31raw→30aligned codes/60frames |
| SR-06 | Trained reconstruction | Aligned reference plus S3 target codes → complete Flow encoder/estimator → HiFT F0/learned source/spectrum →24kHz PCM;960samples/generated code, tested at1/1.2seconds |

Reference and acoustic execution share CPU ORT handling: sequential load/unload, at most one live session, intra-op1–32/inter-op1, arena and memory patterns disabled, basic graph optimization. Fixed names/dtypes/shapes, finite outputs and corresponding `<graph>.data` external locations/ranges are checked. Path escape is rejected. Stage cancellation and actual in-run `SetTerminate()` remain active; inference failures create no reference output directory; file-write errors return failure and require inspection of that new developer directory. Thread counts and tensor bounds do not establish phone performance or memory viability.

## Complete graphs and asset ownership

The [reference source lock](../third_party/soulx-reference-source-lock.json) and [acoustic asset lock](../third_party/soulx-trained-assets.json) pin publisher revisions, sizes, SHA256 and licenses. Full hashes are in those locks.

| ID | Original asset | Pinned publisher/revision | Bytes |
| --- | --- | --- | ---: |
| A-01 | `speech_tokenizer_v2.onnx` | [FunAudioLLM/CosyVoice2-0.5B](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B/tree/23778f84b1b6dd789e1b5092c3ec1145639ee1c3), `23778f84…` | 496,082,973 |
| A-02 | `campplus.onnx` | [Soul-AILab/SoulX-Podcast-1.7B](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B/tree/c2af285fc7ec68a4d3402deae7d2e215ab67fb32), `c2af285f…` | 28,303,423 |
| A-03 | `flow.pt` | Same SoulX revision | 450,575,567 |
| A-04 | `hift.pt` | Same SoulX revision | 83,390,254 |

The [offline reference converter](../tools/export_soulx_reference.py) externalizes original ONNX tensors into fixed sidecars without training or initialization. Reloaded full graphs and tensor bytes must match: S3 retains1358nodes/102initializers, CAMP3206nodes/617initializers, opsets17/14. Identity comparison only normalizes the presence of protobuf default enum fields, without altering computation or parameters. Four converted graph/data assets total524,439,313bytes, plus a manifest. Acoustic export retains [strict checkpoint loading](SOULX_ACOUSTIC.en.md); trained provenance is independently hash-matched, never inferred solely from `synthetic_parameters=null`.

Original/converted weights, manifests, embeddings and codes remain model/run assets in ignored developer directories or explicit user directories, outside Git/APK/source archives/Release. Developer downloads require explicit flags; tests do not fetch missing models. An explicitly selected HF mirror transfers fixed assets under identical hash checks and performs no inference. No real-person reference or publisher example audio was used.

End users must independently select, download/import, pause/resume, update/delete and configure models in the App; installation/upgrades update the foundation. Developer conversion commands are not intended prerequisites for eventual user operation. Complete downloadable bundles, the native phone language stage and App binding still belong in this release. Models remain peers with independent text/image/video/audio and foundation tags. Recommended order m08→m06→m01 remains; this research executor is not advertised as runnable App support.

## Evidence and numerical investigation

| ID | Checks | Actual scope |
| --- | --- | --- |
| V-01 | [145 reference assertions](../verification/development/soulx-reference.json) | 15 native host children,10 completed graphs,4 references,2 actual in-run terminations;1second/nonintegral/15second inputs and repeat lifetimes;20 stage comparisons, exact semantic codes |
| V-02 | [253 trained acoustic assertions](../verification/development/soulx-trained.json) | Two trained acoustic checkpoints and two trained reference models;3 native reconstructions,54graphs,63 stage comparisons and12 identical-input isolation comparisons; at most one session |
| V-03 | [244 untrained acoustic assertions](../verification/development/soulx-acoustic.json) | Separate full-architecture synthetic regression:12children/57graphs/one actual termination; original tighter synthetic waveform limits retained |
| V-04 | [Reference ARM64](../verification/development/soulx-reference-arm64.json) / [acoustic ARM64](../verification/development/soulx-acoustic-arm64.json) | Native Windows NDK r30/API28/16KiB ELF,504,440/520,448bytes, existing ORT1.28.2/C API17; no Android execution |

Reference baselines run original inline publisher ONNX; native children run converted graphs. Audio baselines extract pinned upstream Python function bodies. Converted graphs do not generate their own oracle. Peak errors: S3features6.3181e-6, CAMPfeatures4.1867e-4, speaker embedding4.0889e-5, Flow/reference mel2.8611e-6. Raw/aligned code lengths are independently checked.

The first trained reconstruction exceeded the old synthetic waveform peak limit5e-4. Independent isolation then called original HiFT with identical native mel/F0/source/spectra: source with identical F0 differs by≤1.491e-8, decoding with identical mel/source≤7.395e-6, ISTFT with identical spectra≤4.769e-7. End-to-end sub-millihertz FP32 F0 differences accumulate phase. Maximum waveform error is8.378e-4, maximum RMSE6.863e-5, minimum SNR58.04dB.

Trained reconstruction separately requires peak≤1e-3, RMSE≤1e-4 and SNR≥50dB plus all12 isolation checks. The244 untrained checks keep their original limits. Numerical equivalence does not establish intelligibility, voice/reference fidelity, phone memory/thermals/speed or long-text quality. **Trained component execution is not text-to-speech; Windows execution plus Android compilation is not Android execution.** Complete-model, phone and Release gates remain open.

## Developer reproduction

Use native Windows MSVC/NDK/CMake/Ninja in this project, without Docker, WSL, VMs or emulators. Follow the [development guide](DEVELOPMENT.en.md); all caches/temporary files/outputs stay in project `build/`. Run compilation/test commands sequentially to avoid concurrent SUBST builds.

```powershell
# Explicit preparation of code, export dependencies and numerical references; no models.
python tools/prepare_soulx_acoustic.py --python-dependencies
python tools/fetch_soulx_dsp.py --test-references
python tools/fetch_soulx_reference.py
# These explicit flags request the four publisher models; HF is the default origin.
python tools/fetch_soulx_reference.py --publisher-models
python tools/fetch_soulx_trained.py --download
# Optionally select --origin https://hf-mirror.com; pinned SHA256 checks still apply.
python tools/test_soulx_reference.py
python tools/test_soulx_acoustic.py
python tools/test_soulx_trained.py
python tools/build_soulx_reference.py
python tools/build_soulx_acoustic.py
python tools/export_development.py
python tools/check_repository.py --development
```

For independently selected original reference graphs: `python tools/export_soulx_reference.py --source-dir build/user-soulx-reference --output-dir build/user-soulx-reference-pack`. The output must be new. Compatible graphs from different sources do not receive a matching-publisher-hash declaration. Tests require four explicitly prepared weights and fail on missing assets without downloading them. Python/PyTorch are developer export/oracle dependencies, not Android runtime requirements.

Licensing is recorded in the [reference NOTICE](../research/soulx_reference/NOTICE), [shared ORT NOTICE](../research/soulx_ort/NOTICE), existing DSP/acoustic notices and locks. Apache-2.0, ORT MIT, KISS FFT BSD-3-Clause and Snake MIT texts are retained. Publisher cards declare Apache-2.0 for these assets; this does not imply a license for arbitrary HF models.

Still required: Qwen3/tokenizer/text-to-codes, up to four speakers/history/long text, complete explicit user bundles, App jobs/API/inputs/artifacts/admission, fresh-input offline full-model speech and quality tests, and physical Android acceptance including three load/unload cycles,15minute screen-off, one-hour alternating API and upgrade asset preservation. Existing text, F-01–F-12, every frozen01–14/16/17 subtarget, nine MOSS variants, SD1.5/SDXL LoRA, old LTX-Video2B0.9.8 distilled, A1–A11/R-01–R-05 and the final Release remain required without split scope or automatic deferral.
