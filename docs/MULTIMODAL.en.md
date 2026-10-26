# Multimodal expansion feasibility

[中文](MULTIMODAL.md) · [Workflow design](WORKFLOWS.en.md) · [Documentation](README.md)

Reviewed **2026-10-27, Asia/Taipei**, for LMA on Android without ROOT, with the nubia Z20 as the reference device and user-configured remote GPUs as an optional execution target. This is source research and an engineering assessment, **not an implementation or a device benchmark**. The v0.2.0 APK still runs compatible single-file text GGUF models only.

## Decision

LMA can expand into an image, speech, audio, video and workflow workbench. Start with **small local TTS, SD 1.5 and a remote ComfyUI adapter**. Run larger image, song and video pipelines on a user's computer/server, with model selection, workflow editing, job submission and results on the phone. Remote execution must be explicitly selected; local requests must not silently upload content.

No engine runs every HF model or every GGUF. LoRA is an adapter requiring a compatible base. Speech, songs and video need different pipelines. Being downloadable, having architecture support, having an Android backend, and working acceptably on a particular device are separate findings.

The review used publisher model cards, upstream documentation, Android samples and API documentation. No weights were downloaded, new engines built, or multimodal inference performed. No phone was available. Z20 ratings are engineering assessments pending device acceptance. Supplementary terminal access to the HF API failed, so this review supplies no download-verified file-size/hash lock. Source links track upstream revisions; implementation must pin commits, files and SHA256 values.

## Z20 baseline and ratings

The official international Z20 specification lists **Snapdragon 855+, Adreno 640, 8GB RAM, 128GB storage and a 4,000mAh battery**. Read actual device capabilities for other configurations. [nubia specifications](https://uk.nubia.com/pages/z20-specs)

CPU, GPU and Android share phone RAM. It is not equivalent to a desktop GPU with the same amount of dedicated VRAM. Drivers and operators must be checked before enabling Vulkan/OpenCL. Local Dream requires Hexagon v68 or newer for SD 1.5 NPU execution, and Snapdragon 8 Gen 3 or newer for SDXL NPU execution. This plan does **not** count the Z20 as qualified for that NPU path; start with CPU and measure GPU separately. [Local Dream requirements](https://github.com/xororz/local-dream#about-this-repo)

| Rating | Meaning |
| --- | --- |
| A: priority candidate | A relevant mobile execution path exists; worth porting and validating first, not a Z20 pass |
| B: experimental | Conversion/native foundations exist, but dependencies, RAM, drivers and latency need specific work |
| R: remote first | Remote execution is the practical product choice, not a proof that porting is mathematically impossible |

“Newer flagship” below is a **test group**, roughly 12–24GB RAM and newer ARM64 drivers, not a guaranteed minimum specification. No other device's speed is extrapolated to the Z20.

## Images and LoRA

| Model / capability | Verified upstream foundation | Z20 | Newer flagships and integration |
| --- | --- | --- | --- |
| Stable Diffusion 1.5 | Android implementation in Local Dream; MNN conversion resources; native sd.cpp inference | **A** | First local image target; start acceptance at one 256/512 image, batch 1, memory-saving mode |
| SD-Turbo, LCM / LCM-LoRA | Related distilled paths in sd.cpp; SD-Turbo is based on SD 2.1, not an SD 1.5 LoRA | **B** | Fewer steps reduce compute; match the architecture, sampler and distillation recipe |
| SDXL / SDXL-Turbo | Local Dream CPU/GPU and selected modern NPU paths | **R / B**, not a default | Dedicated modern-device trials; include both encoders and VAE in memory accounting |
| LoRA / multiple adapters | Adapter support in sd.cpp | Follows its base | Bind base family, components, quantization and strengths; not standalone generation. This proposal concerns inference, not phone training |
| Sana 600M | Publisher checkpoint and an MNN conversion/inference path | **B** | Promising experiment; the 600M label excludes other pipeline costs |
| FLUX.2-klein-4B | Publisher 4B checkpoint and sd.cpp support | **B / R** | Quantized modern-device trials; account for encoder, VAE and activations |
| Original Qwen-Image | Publisher 20B model and sd.cpp implementation | **R** | Remote first; ideal 4-bit weights for the main 20B alone are about 10GB before encoders/buffers |
| Qwen-Image-2.1 / Turbo | 2.1 has a 7B image backbone; sd.cpp also needs a Qwen3-VL-8B encoder and a dedicated VAE | **R** | **B** on modern flagships; 7B is not the entire pipeline, and licensing differs from the original |
| Z-Image-Turbo | Publisher 6B, 8-NFE model with an sd.cpp path and separate encoder/VAE | **B / R** | Quantized staged-loading trials on newer devices; desktop 4GB-VRAM recipes do not validate a Z20 |

Runtime sources: [sd.cpp capabilities](https://github.com/leejet/stable-diffusion.cpp#features), [MNN Diffusion](https://github.com/alibaba/MNN/blob/master/transformers/diffusion/README.md), [Local Dream](https://github.com/xororz/local-dream). Checkpoints: [SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5), [SD-Turbo](https://huggingface.co/stabilityai/sd-turbo), [Sana 600M](https://huggingface.co/Efficient-Large-Model/Sana_600M_1024px_diffusers), [FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), [Qwen-Image](https://huggingface.co/Qwen/Qwen-Image), [Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1), [2.1 components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/qwen_image_2.1.md), [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo).

`parameters × bits / 8` is an ideal raw-weight lower bound, with decimal GB. Quantization metadata, unquantized layers, activations, attention, VAE and Android add costs. Staged unloading can reduce simultaneous residency; memory mapping/paging does not establish usable latency. Images generally expose progress/previews and a final artifact, rather than a continuous readable token stream.

Track newer branches such as FLUX.3 Image Klein with separate recipes rather than inheriting earlier encoders, licenses or device ratings. [FLUX.3 components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/flux3.md)

## Speech, sound effects and music

| Model / capability | Verified upstream foundation | Z20 | Recommendation |
| --- | --- | --- | --- |
| **MOSS-TTS-Nano 100M** | Official ONNX and Android sample | **A** | Priority TTS / later cloning candidate; the sample uses two pre-tokenized prompts and needs a tokenizer for arbitrary text |
| **Kokoro-82M** | Small TTS model and sherpa-onnx Android TTS engine | **A** | First offline narration option; validate a particular language, voice and dictionary bundle |
| **Piper / VITS / Matcha** | Offline TTS families and Android examples in sherpa-onnx | **A** | Select explicit Chinese/English packs; engine support does not give every voice the same license/language |
| Qwen3-TTS 0.6B | Publisher multilingual/streaming TTS; dedicated audio tokenizer/decoding required | **B** | Evaluate native/ONNX adaptation; the current generic llama-server is insufficient |
| Full MOSS family | Distinct 1.7B / 4B / 8B architectures; official llama.cpp fork + ONNX codec for selected architectures | **B / R** | Prefer Nano initially; desktop 8GB-GPU claims do not establish phone viability |
| SoulX-Podcast 1.7B | Publisher podcast/multi-speaker TTS, with Linux Python reference installation | **B / R** | Remote speech first; ONNX components do not establish an end-to-end Android pipeline |
| **YuE2-3B** | Lyrics/style-to-song; reference BF16 NVIDIA 24GB GPU pipeline with an audio VAE | **R** | Remote music node, not ordinary TTS; current weights are noncommercial |
| **Stable Audio Open Small 341M** | Arm LiteRT/C++/Android deployment guidance for short audio | **B** | Local sound-effect experiment; not a replacement for long-song YuE2, with Z20 latency unknown |

Sources: [MOSS-TTS-Nano](https://github.com/OpenMOSS/MOSS-TTS-Nano), [actual Android sample scope](https://github.com/OpenMOSS/MOSS-TTS-Nano/tree/main/examples/android_onnx_runtime), [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx), [Android TTS example](https://k2-fsa.github.io/sherpa/onnx/tts/apk-engine.html), [Qwen3-TTS 0.6B](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice), [MOSS family and dedicated llama.cpp backend](https://github.com/OpenMOSS/MOSS-TTS), [SoulX-Podcast](https://github.com/Soul-AILab/SoulX-Podcast), [YuE2](https://huggingface.co/m-a-p/YuE2-3B), [Arm audio path](https://developer.arm.com/code-along/stable-audio-open-small), [Stable Audio model](https://huggingface.co/stabilityai/stable-audio-open-small).

Nano's Android sample establishes short-prompt ONNX execution and WAV output. A product still needs text processing, tokenization, matching codec, chunk delivery, cancellation and playback buffering. It is not already a complete cloning app. Measure TTS using first-audio latency, audio chunks/seconds and real-time factor; song generation also needs duration-based measurements.

## Video

| Model / version | Publisher or runtime evidence | Z20 / product route |
| --- | --- | --- |
| Wan 2.1 T2V 1.3B | Reference uses about 8.19GB GPU VRAM; unoptimized RTX 4090 example generates five seconds of 480p in about four minutes | **R**; applies to that desktop recipe, not every Wan minimum or phone speed |
| Wan 2.2 TI2V 5B / A14B | The official offloaded 5B 720p command references at least 24GB GPU VRAM; A14B has a separate resource profile | **R**; choose the exact task/model/resolution recipe |
| Older LTX-Video 2B | Smaller distilled checkpoints and a ComfyUI route exist | **R**; tiny, low-resolution experiments remain porting research, without evidence for production on Z20 |
| LTX-2.3 / 2.5 | New audio-video models with sd.cpp paths; 2.5 also requires a dedicated Gemma 4 12B encoder and video/audio VAEs | **R**; an older 2B LTX budget does not represent LTX 2.x |
| **MiniMax H3** | Open H3-Base weights; 33B backbone includes about 13B precomputable AdaLN parameters, plus Qwen3-VL-32B encoder and two VAEs; sd.cpp implementation exists | **R**; quantization/precomputation help, but do not make it a first Z20 feature |

Sources: [Wan 2.1](https://github.com/Wan-Video/Wan2.1), [Wan 2.2](https://github.com/Wan-Video/Wan2.2), [older LTX-Video](https://github.com/Lightricks/LTX-Video), [LTX-2.5 card](https://huggingface.co/Lightricks/LTX-2.5), [sd.cpp LTX components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/ltx2.md), [official H3 card](https://huggingface.co/MiniMaxAI/MiniMax-H3), [sd.cpp H3 components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/minimax_h3.md).

Separate open H3-Base from the complete hosted system: Context-IR and 2K regeneration are not all supplied as local weights in the reviewed release. Downloading Base does not reproduce the entire official offline 2K service. Video also incurs spatiotemporal activation, frame-count, decoding and encoding costs. C++ support alone does not validate every Android GPU operator.

## Business use and licenses

These are **selection signals**, not blanket commercial clearance. Check the pinned weights, adapters, dictionaries and component terms independently of runtime code.

| Exact source | Finding / business implication |
| --- | --- |
| [SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) / [SDXL base](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | OpenRAIL-M / OpenRAIL++; not unconditional MIT weights. Third-party LoRAs have their own terms |
| [Original Qwen-Image](https://huggingface.co/Qwen/Qwen-Image), [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo), [Sana 600M](https://huggingface.co/Efficient-Large-Model/Sana_600M_1024px_diffusers), [FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) | These cards declare Apache-2.0; do not generalize to future family members |
| [Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1) | **Qwen Research License**, not the original model's Apache-2.0 commercial position |
| [MOSS Nano ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX), [Nano codec](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX), [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [this Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice), [this SoulX](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B) | Cards declare Apache-2.0. Rights to voice/reference material remain separate |
| [YuE2-3B](https://huggingface.co/m-a-p/YuE2-3B) | **CC-BY-NC-4.0**; not a default commercial song-service option. Do not inherit older YuE licensing |
| [Stable Audio Open Small](https://huggingface.co/stabilityai/stable-audio-open-small) | Stability AI Community License; evaluate its specific commercial conditions |
| [H3 License](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE) | Territory and commercial conditions, including separate written authorization above US$20M yearly commercial-product/service revenue and UI attribution; not a permissive open-source license |
| [LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) | LTX-2.x Community License; includes an entity-wide US$10M annual-revenue threshold and derivative conditions; evaluate separately from older LTX |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | GPL-3.0 server; copying code, distributing components and calling a remote API are different integration choices |

Execution location, compatibility, publisher-verified uncensored versus metadata-only tags, and commercial licensing should remain independent attributes. Uncensored labels do not change resource requirements, licenses or remote-provider rules, and must not be automatically added to new models.

## Proposed delivery order

| Stage | Work and completion conditions |
| --- | --- |
| 1: common foundation | Multi-component bundles, independent providers, per-model constraints and persistent jobs/artifacts; preserve recommendations and existing text APIs. See [workflow design](WORKFLOWS.en.md) |
| 2: first local features | One explicit Chinese/English sherpa-onnx TTS bundle, a complete Nano tokenizer prototype, SD 1.5 single images and compatible LoRAs. Record model hashes, peak memory, latency, thermals, cancellation and screen-off behavior |
| 3: remote workflows | User-configured native ComfyUI/audio services; expose particular image/Wan/LTX/H3/music recipes. Start with template forms, queues, reconnection reconciliation and artifact retrieval |
| 4: advanced | Node canvas, controlled ComfyUI import, newer GPU/NPU paths, Sana/Z-Image/small-FLUX quantized recipes. Require end-to-end device evidence before a verified-compatible label |

These are proposed stages, not shipped features or delivery estimates. Acceptance includes initial/resumed downloads, missing files, offline loading, clamping, generation/cancellation, memory release, process recovery, screen-off execution and opening outputs. Remote acceptance adds duplicate submissions, reconnects and cancellation ownership. No phone timings, real-time factors or endurance results are claimed.

This change adds research/design documentation only. **The APK, curated model catalog, UI and published release assets are unchanged.** Existing screenshots/GIFs still demonstrate v0.2.0 text-model features.
