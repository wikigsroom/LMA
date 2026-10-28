# Stable Audio Open Small local audio foundation

[中文](STABLE_AUDIO_ENGINE.md) · [Development](DEVELOPMENT.en.md) · [Complete requirements](MULTIMODAL_RELEASE_PLAN.en.md)

This documents source and scoped checks in **0.3.0-dev.20 / code 24**, not completed v0.3.0 support. Selection **14** still needs a complete model, fresh-input offline audio, quality/resource measurements and physical Android acceptance. There is no available phone and no full-model audio was generated.

## 1 · Pipeline and asset boundary

`stable_audio_litert` / `stable_audio_small_litert_v1` runs **LiteRT 2.2.0 CPU CompiledModel C API** entirely on the phone. T5/time conditioning, DiT sampling and audio decoding load sequentially. A stage releases its models, compiled object and tensor buffers before the next stage; the DiT stays loaded across sampling steps. Cancellation terminates the child and cleans the private hardlink workspace while leases protect user assets.

The APK contains the worker, runtime code and recipe metadata. It contains no model weights, T5 vocabulary, codec weights or voices. Installation, upgrades, browsing and missing assets initiate no transfers. This pipeline has no off-device inference, external conversion service, ROOT, Termux or installable native plugins.

| User-selected role | Format | Pinned export interface |
| --- | --- | --- |
| `conditioner` | `conditioners_float32.tflite` | int64 IDs/mask `[1,128]`, float32 seconds `[1]`; float32 cross `[1,65,768]`, mask `[1,65]`, global `[1,768]` |
| `diffusion_model` | `dit_model.tflite` | float32 latent `[1,64,256]`, time `[1]`, cross `[1,65,768]`, global `[1,768]`; same-shaped output latent |
| `audio_decoder` | `autoencoder_model.tflite` | float32 latent `[1,64,256]` → planar stereo `[1,2,524288]` |
| `tokenizer` | SentencePiece `spiece.model` | Matching T5-base 32000-piece SentencePiece model, pad 0/EOS 1. This differs from logical vocabularies including extra sentinel tokens and embedding capacity. |

Models must match the pinned Arm export. Signature/tensor counts, dtype, rank and exact shape are checked before CPU compilation. Dynamic/strided or arbitrary same-named graphs fail. Local filenames may change; roles and content constraints remain. Graph interfaces are float32/int64; compatible internal weight quantization is determined by the export. The adapter selects CPU and runtime-default XNNPACK flags, without forced FP16 or a packaged GPU accelerator. The shared runtime's system EGL/GLESv3 ELF dependencies do not mean this pipeline uses GPU execution.

## 2 · User workflow

1. Use **All/search** to find a compatible export repository you can access, inspect files and select this recipe. TFLite discovery does not make every HF architecture runnable.
2. Bind all four assets, review provenance, pinned revision, sizes and integrity, then explicitly download. Matching existing assets can use bundle import. Raw `.ckpt`/`.safetensors` files cannot replace TFLite graphs; LMA does not automatically convert them.
3. Manage components and model-specific defaults in **Local**. Select the model, enter an English sound description, acknowledge an unmeasured local attempt and enqueue. Missing/incompatible assets fail locally.
4. The same phone tokenizes, conditions, samples, decodes, crops and saves the WAV. Results enter local artifacts. The API uses `audio.generate` through the shared persistent job/artifact interfaces; see [API](API.en.md).
5. Downloads, pause/resume, independent updates, deletion and reference protection reuse the foundation. Task snapshots do not save model defaults. Restored downloads stay paused after upgrades.

No community four-file distribution is marked as verified runnable in this checkpoint. This work pins code/interfaces and official repository metadata; users still need matching assets and full-model acceptance. Records remain peers with `task:audio`, `text_to_audio`, `short_audio`, `english_prompts`, `fixed_latent_length`. Engine, pipeline, architecture, format, dependencies, device evidence, license and content labels remain independent. This model receives no automatic Uncensored label.

## 3 · Parameters, sampling and output

| Parameter | Default / range | Meaning |
| --- | --- | --- |
| Seconds | 5 / integer 1–11 | Public model duration range; crop to `44100 × seconds` frames |
| Steps | 8 / integer 1–32 | Upstream default 8; 32 is an application guard, not a theoretical model limit |
| Effective prompt tokens | 64 / 1–64 | Includes EOS. Arm accepts 128 IDs but only the first 64 reach DiT; overflow errors instead of silent truncation. |
| CPU threads | 4 / 1–32 | Application guard, not a claim of 32 phone cores |
| Seed | -1 / -1 or 0–2147483647 | Resolve -1 before execution and record the concrete seed |

Model defaults and task parameters use editable preset comboboxes with clamping. The backend revalidates snapshots. No ignored CFG, negative prompt, reference audio, voice cloning, image LoRA or incremental audio stream is exposed.

Sampling preserves Arm's ping-pong policy: `sigmoid(-linspace(-6,2,steps+1))`, exact endpoints 1/0, `denoised=x-t×velocity`, then mix with next-time noise. Initial noise uses the selected seed; per-step noise uses `seed + step + 4564`. Reproducibility is within the implementation, without cross-PyTorch/standard-library bitwise guarantees.

**One-second output still computes all 256 latent frames and 524288 decoded frames**, then crops. Shorter output does not imply proportionally lower memory. All decoded floats must be finite; planar channels become interleaved 44.1 kHz stereo PCM16. Peaks above one are attenuated; quieter signals retain their level. Receipts include actual token count, steps, fixed sizes, measured stage/pipeline times, RTF and stop reason. No full-model timing values are available to publish.

Arm's reference calls for about 8 GB RAM and discusses DotProd/i8mm optimization. Sequential loading does not establish sufficient memory. Z20 SoC, 6/8 GB variants, available RAM and thermal behavior need separate evidence. There is no claim of realtime speed, unlimited background operation or Z20 compatibility. The public model targets short English sounds/effects, without promises of full songs, reliable vocals or general TTS.

## 4 · Provenance, licensing and rebuild

- [Arm ML-examples](https://github.com/Arm-Examples/ML-examples/tree/0e453847ea28043194c32791a591d0f5a8a5ae2e/kleidiai-examples/audiogen), revision `0e453847ea28043194c32791a591d0f5a8a5ae2e`, Apache-2.0. LMA adapts its interface/sampler to C API, sequential lifetimes, strict guards, private events and PCM16 output.
- [LiteRT v2.2.0](https://github.com/google-ai-edge/LiteRT/releases/tag/v2.2.0): official Maven AAR and matching SDK; retain LICENSE and complete third-party NOTICE. ARM64 runtime: 5,508,376 bytes, SHA256 `97355a36cb8ac7628cf407773291e98da79f3ef184cc43cb0e57dedf5f0c0637`.
- SentencePiece revision `31646a467d2051eb904e0b45de3a73e91fe1c1e3`: embedded data/tests/shared library disabled, generic code only.
- [Official weights](https://huggingface.co/stabilityai/stable-audio-open-small) have separate Stability AI Community terms and gated access. Users obtain their own access. App licensing does not replace model terms or bypass gates. [Metadata evidence](../catalogue/evidence/stable-audio-publisher.json) pins model revision `dc620d91535857b72ebb59b4ca45978db6d417f5` and T5 revision `a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1`, without weights/vocabulary downloads.

Exact source/archive/notice hashes are in the [lock](../third_party/stable-audio-source-lock.json). Use native Windows NDK r30/API28, CMake/Ninja, without Docker, WSL, VMs or emulators:

```powershell
python tools/fetch_stable_audio.py
python tools/build_stable_audio.py
python tools/collect_stable_audio_notices.py
python tools/test_stable_audio.py
python tools/build.py
python tools/verify_package.py
```

Host tests also need Python `flatbuffers`, MSVC and Java. The script fetches a pinned official Windows LiteRT wheel and extracts its DLL/schema for synthetic ADD/CAST fixtures without trained weights; these are not APK contents. Caches/outputs stay under repository `build/`. Model conversion is not a build step. Temporary SUBST aliases must not race with other builds using the same mechanism.

## 5 · Numbered delivery and pending work

| ID | Implemented / checked | Evidence boundary |
| --- | --- | --- |
| SA-01 | ARM64 worker, official LiteRT 2.2.0, 16 KiB alignment | Compiled, not executed on Android |
| SA-02 | Four assets/leases, sequential stages, cancellation, WAV validation | Production code and 6 real host children; silent structural WAV fixtures |
| SA-03 | 144 assertions = Java 51 + C++ 93 | 6 actual LiteRT tiny-graph runs, three load/run/unload cycles per graph, Arm sampler equivalence; no trained checkpoint or generated model audio |
| SA-04 | Per-model parameters, clamping, peer tags and UI media | Explicit UI FIXTURE, not phone generation |

| ID | Pending | Gate |
| --- | --- | --- |
| SA-P01 | Matching four-file assets, fresh-prompt offline audio, quality/resources/cancellation | Selection 14 remains unaccepted end to end |
| SA-P02 | Physical Android load/unload, 15-minute screen-off, one-hour alternating API, upgrade asset retention | Zero physical-device tests; no new Release |
| SA-P03 | All remaining frozen scope | F-01–F-12, existing text, 01–14/16/17, every frozen subtarget and A1–A11/R-01–R-05 remain in the same complete v0.3.0, including separate nine-MOSS, SoulX, old LTX and both LoRA acceptance. |
