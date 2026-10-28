# SoulX-Podcast native audio primitives

Current follow-up: [language and complete trained host pipeline](SOULX_LANGUAGE.en.md) now executes Qwen3 text-to-codes through Flow/HiFT. This page retains its original scoped suite; App integration, speech quality and physical Android remain pending. The complete host evidence does not retroactively change these earlier tests.

[中文](SOULX_DSP.md) · [Complete requirements](MULTIMODAL_RELEASE_PLAN.md) · [Numbered delivery](releases/v0.3.0-dev.20-soulx-dsp.md)

The implementation in [research/soulx](../research/soulx/dsp.hpp) is a compilable C++ audio library with executable checks. **It is not registered in the APK, engine registry, job queue or inference API.** Target 13, SoulX-Podcast 1.7B, still needs its complete native pipeline. No model is newly advertised as supported; recommendations, tags and user downloads are unchanged. The development APK remains 0.3.0-dev.20; the public Release remains v0.2.0.

## Complete pipeline and current boundary

| ID | SoulX stage | Current state |
| --- | --- | --- |
| S-01 | Reference WAV → 16k S3 / CAMPPlus features and 24k Flow features | Native computation and upstream numerical comparisons implemented; the future worker must connect WAV decoding to the existing input library |
| S-02 | S3Tokenizer → semantic codes; CAMPPlus → 192-dimensional speaker embedding | [Separate reference execution](SOULX_REFERENCE.en.md) now runs complete trained graphs; DSP alone only computes features, with user bundles/App binding still pending |
| S-03 | Qwen3 → target codes, multiple speakers, turn history and EOS | [Native language/windows](SOULX_LANGUAGE.en.md) pass trained host checks; App task integration and complete phone acceptance remain pending |
| S-04 | Flow encoder → conditions; estimator → velocities | [Full acoustic four-graph follow-up](SOULX_ACOUSTIC.en.md) implements native ORT comparisons with complete UNTRAINED architectures; [trained reconstruction](SOULX_REFERENCE.en.md) is also checked; user components and App binding remain pending |
| S-05 | HiFT F0 / neural spectra → 24k waveform | Native NSF/STFT/ISTFT now feed the research F0/learned-source/neural-spectrum executor; [trained reconstruction](SOULX_REFERENCE.en.md) is now checked; complete speech quality and App binding remain pending |
| S-06 | Turn concatenation, artifacts, background API and resource admission | Complete executor must join the shared foundation; no model WAV produced in this update |

A community language-backbone GGUF alone cannot synthesize speech. Users must explicitly select, download/import and manage the eventual weights, tokenizers, acoustic graphs, speaker components, codecs and their licenses. They are not APK contents; installation, upgrades, browsing and missing components initiate no model transfer. Every inference stage must run on the same Android phone without ROOT or off-device inference/fallbacks.

## Implemented computation contracts

| ID | Operation | Layout / behavior |
| --- | --- | --- |
| D-01 | Volume normalization | Preserve upstream order: quiet-peak handling, percentile from ORIGINAL amplitudes, then actual-peak limiting; retain three distinct feature frontends |
| D-02 | Resampling | 24k→16k Hann-window sinc, lowpass width6, rolloff .99, zero boundaries, `ceil(N×2/3)` output; normalize AFTER resampling for S3/CAMP, at 24k for Flow |
| D-03 | S3 | FFT400/hop160, reflected centered padding, periodic Hann, final frame dropped, Slaney128, log10 power and 8-order dynamic range; `[128,T]` |
| D-04 | Flow | FFT1920/hop480, reflect720 each side, uncentered STFT, Slaney80/8kHz, `sqrt(power+1e-9)` magnitude and natural log; `[80,T]`, cropped to even frames |
| D-05 | CAMPPlus | Kaldi25ms/10ms, FFT512, DC removal, .97 preemphasis, nonperiodic Povey, 80 mel, no dither, log power and per-feature mean subtraction; `[T,80]` |
| D-06 | Flow update | `1-cos(t×π/2)` schedule; `x += dt×(1.7×conditional−.7×unconditional)`; invalid shapes, nonfinite values or overflow fail without mutating the input state |
| D-07 | HiFT | 50Hz F0 → 480× samples / nine NSF harmonics, per-sample callback and explicitly injected noise; FFT16/hop4 real/imaginary spectra; overlap-normalized ISTFT, centered trimming, magnitude cap100 and final±.99 clamp |
| D-08 | Bounds / cancellation | Reference entry:24k mono,1–15seconds. F0/spectra:6000 generated mel frames (120seconds); Flow additionally includes up to750 reference frames,6750 total. These are not phone capacity claims. Stage/frame/sample cancellation and shape/numeric overflow guards |

NSF matches upstream float32 reciprocal scaling, half-pixel coordinates and boundary clamping BEFORE interpolation weights. These details affect phase as global sample offsets grow, requiring more than a one-second check. Per-sample callbacks avoid a separate full `samples×9` harmonic allocation. Eventual neural stages still require their own memory admission; Android memory, speed and quality remain unmeasured.

## Verification and reproduction

Use native Windows tools, without Docker, WSL, emulators or virtual machines:

```powershell
python tools/fetch_soulx_dsp.py --test-references
python tools/test_soulx_dsp.py
python tools/build_soulx_dsp.py
python tools/export_development.py
python tools/check_repository.py --development
```

Prepare the existing project-local NDK r30/CMake/Ninja toolchain; host checks need MSVC, Python, NumPy and CPU PyTorch. Tests AST-extract unchanged **Python function bodies** from pinned torchaudio 2.7.1 / librosa 0.11.0 wheels, then execute them on the current host CPU PyTorch. No torchaudio DLL is loaded; this is not a reproduction of upstream's original Python environment. The publisher S3 mel bank is a test reference in the ignored checkout, excluded from APK and source artifacts.

[Numerical evidence](../verification/development/soulx-dsp.json) and the [ARM64 compilation receipt](../verification/development/soulx-dsp-arm64.json) record scope, errors and input hashes separately. Comparisons cover one-second, nonintegral-duration and 15-second references; 1/7/50/1500/6000 mel-frame NSF inputs include 30/120seconds. Additional checks execute the actual upstream 15-step Euler body, spectral synthesis and invalid-input guards. Inputs are synthetic PCM, noise, F0 and a non-model estimator.

This DSP suite alone is numerical/compilation evidence; [trained component checks](SOULX_REFERENCE.en.md) are recorded separately: **zero trained checkpoints loaded, zero model audio outputs, zero physical Android tests.** It establishes no voice quality, intelligibility, long-form model quality, phone throughput or background endurance. The ARM64 artifact is an unregistered static library retained in `build/`; it installs no engine or downloaded runtime code.

## Sources and licenses

[Pinned revisions and file SHA256s](../third_party/soulx-dsp-source-lock.json): [SoulX-Podcast](https://github.com/Soul-AILab/SoulX-Podcast/tree/5ac9c0e1cfe596396200c7d38e3fd53b7b3fbf4b), [S3Tokenizer](https://github.com/xingchensong/S3Tokenizer/tree/9bf5d845b5e043ffaf4657f4942939091c7697a2), [KISS FFT](https://github.com/mborgerding/kissfft/tree/febd4caeed32e33ad8b2e0bb5ea77542c40f18ec). Computation ports are Apache-2.0; original LMA interfaces/tools are MIT; KISS FFT is BSD-3-Clause. See [attribution](../research/soulx/NOTICE), [Apache text](../research/soulx/LICENSE-APACHE-2.0) and [KISS text](../research/soulx/LICENSE-KISSFFT-BSD-3-CLAUSE). User model provenance, licenses and architecture still require separate review.

## Remaining gates

Complete S-02 user bundles/App binding and the full S-03–S-06 user pipeline, up-to-four-speaker/long-form protocols, complete user model packages, fresh offline speech, resource/quality/cancellation/three-load-cycle evidence and phone background acceptance within the same complete v0.3.0. F-01–F-12, every frozen 01–14/16/17 subtarget, SD1.5/SDXL LoRA, nine MOSS variants, old LTX 2B 0.9.8 distilled, A1–A11/R-01–R-05 and final Release gates remain intact without automatic deferral.
