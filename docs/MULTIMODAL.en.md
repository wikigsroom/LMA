# Fully local Android multimodal feasibility

[中文](MULTIMODAL.md) · [Local workflow proposal](WORKFLOWS.en.md) · [Documentation](README.md)

Reviewed **2026-10-27 (Asia/Taipei)** under the user's revised requirement: **every inference stage runs on the same Android phone, without ROOT, another computer, a LAN inference server, cloud inference, or an off-device fallback.** HF access may download assets. Once installed, tokenization, text encoding, sampling, VAE / codec, composition and export must work offline.

This is source review and engineering assessment, **not shipped functionality or an LMA phone benchmark**. The v0.2.0 APK still executes compatible single-file text GGUF only. No new weights were downloaded, new engines compiled, or phone generation run. No physical device is available.

## Revised decision

Start with **SD 1.5 and matching LoRA, small offline TTS, a native job queue and a local workflow executor**. Investigate Stable Audio Open Small for short sounds. Full songs, large image pipelines and large video models are outside the currently supportable local product scope.

**Video generation cannot be dismissed as a whole.** Community implementations include an ARM64 / Vulkan Android pipeline for Wan 2.1 1.3B, plus Android Vulkan and device-specific QNN paths for the older LTX-Video 2B. They are worthwhile local experiments, not evidence that Z20 passed or LMA already supports them.

HF visibility, downloadability, a native architecture implementation, Android backend execution and practical operation on a specific phone are separate claims. GGUF is not a universal cross-task interface; LoRA cannot generate images on its own.

## Device baseline and evidence

The international Z20 specification lists **Snapdragon 855+, Adreno 640, 8GB RAM, 128GB storage and 4,000mAh**. Read the actual device variant before budgeting. CPU and GPU share RAM; it is not equivalent to 8GB dedicated VRAM. Retain a CPU path, probe GPU drivers/operators, and do not reuse newer NPU binaries indiscriminately. [Z20 specifications](https://uk.nubia.com/pages/z20-specs)

| Grade | Meaning here |
| --- | --- |
| A: initial candidate | A relevant mobile implementation makes it a priority to port and validate; no LMA or Z20 pass is implied |
| B: experimental | Native, conversion or Android evidence exists, but full components, drivers, memory, speed and quality need validation |
| C: excluded for now | Insufficient evidence for current local product support; not a claim that future quantization or hardware can never enable it |

“Newer phones” is an ARM64 test group with roughly 12–24GB RAM and newer drivers, **not a universal minimum specification**. QNN additionally needs the exact SoC, Hexagon target, SDK and compiled shapes. All grades describe candidates; current APK multimodal support remains zero.

Keep publisher Android samples, implementation authors' phone results, native/desktop recipes and LMA measurements distinct. The first three cannot be presented as the fourth. Download size is not peak RAM; desktop VRAM is not directly interchangeable with phone shared memory.

## Images and LoRA

| Model / feature | Local implementation basis | Z20 | Newer phones / integration |
| --- | --- | --- | --- |
| **Stable Diffusion 1.5** | Local Dream Android, MNN Diffusion, sd.cpp | **A** | **A**; single image, batch 1; begin validation at 256 / 512 |
| **Matching LoRA** | sd.cpp adapters | Follows base | Validate family, components, quantization and strength; no on-phone training is proposed |
| SD-Turbo / LCM / LCM-LoRA | Corresponding sd.cpp distillation paths | **B** | **A/B**; SD-Turbo is based on SD 2.1, not an SD 1.5 LoRA; use matching sampling settings |
| SDXL / SDXL-Turbo | Local Dream CPU/GPU and selected newer NPU targets | **B**, high risk, not default | **B**; budget both encoders, UNet and VAE |
| Sana 600M / MNN mobile variants | Publisher checkpoint; MNN Android/conversion paths | **B** | **A/B**; MNN mobile recipes can use Qwen3-0.6B encoding; do not mix them with original Sana assets |
| FLUX.2-klein-4B | Publisher 4B checkpoint, sd.cpp | **B/C**, not default | **B**; quantize and load encoder/backbone/VAE sequentially |
| Original Qwen-Image 20B | Publisher weights, sd.cpp | **C** | **C**, later port research; ideal raw 4-bit backbone alone is about 10GB before other components |
| Qwen-Image-2.1 / Turbo | 7B image backbone, Qwen3-VL-8B encoder, dedicated VAE | **C** | **B**, high-memory experiment; the full pipeline is not just 7B and its license differs from the original |
| Z-Image-Turbo 6B | sd.cpp, plus Qwen3-4B encoder and VAE | **B/C**, not default | **B**; 8-NFE distillation, quantization and staged unloading; a desktop 4GB-VRAM recipe does not establish 4GB-phone support |

Runtime sources: [Local Dream](https://github.com/xororz/local-dream#about-this-repo), [MNN Diffusion](https://github.com/alibaba/MNN/blob/master/transformers/diffusion/README.md), [sd.cpp](https://github.com/leejet/stable-diffusion.cpp#features). Local Dream's SD 1.5 NPU route requires Hexagon v68+, and its SDXL NPU route Snapdragon 8 Gen 3+. **Z20 is outside those listed NPU targets**; CPU/GPU paths need separate validation.

Exact checkpoints/components: [SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5), [SD-Turbo](https://huggingface.co/stabilityai/sd-turbo), [Sana 600M](https://huggingface.co/Efficient-Large-Model/Sana_600M_1024px_diffusers), [FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), [Qwen-Image](https://huggingface.co/Qwen/Qwen-Image), [Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1), [2.1 components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/qwen_image_2.1.md), [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo), [Z-Image components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/z_image.md). New versions require new recipes rather than inheriting encoders or device conclusions.

`parameters × bits / 8` is only an ideal raw-weight lower bound; GB is decimal. Quantization overhead, unquantized layers, activations, attention, VAE, driver and OS are additional. mmap/disk streaming can reduce residency without guaranteeing latency or avoiding memory kills. Lower settings still have to obey shape and distillation constraints.

## Speech, sound and music

| Model / feature | Complete local route and boundary | Z20 | Newer phones |
| --- | --- | --- | --- |
| **MOSS-TTS-Nano 100M** | Official ONNX/Android sample; add arbitrary-text tokenizer and codec | **A** | **A** |
| **Kokoro-82M** | sherpa-onnx Android; complete language, voice and dictionary packages | **A** | **A** |
| **Piper / VITS / Matcha** | sherpa-onnx offline TTS and Android samples | **A** | **A**; check each voice/language package |
| **Qwen3-TTS 0.6B Base** | Google LiteRT Kotlin CPU sample; community qwen3-tts.cpp JNI app | **B**, API 28 port and performance unverified | **A/B**, end-to-end Android code exists, realtime is not promised |
| Full MOSS family | Different architectures; selected dedicated llama.cpp forks plus ONNX codec | **B/C** | **B**; validate the complete architecture, not only LLM weight size |
| SoulX-Podcast 1.7B | Official reference uses Linux/Python; convertible parts are not an Android pipeline | **B/C** | **B**, native-port research, outside initial features |
| **Stable Audio Open Small 341M** | Arm LiteRT/C++/Android route for short sounds/music | **B** | **A/B**; not full-song generation |
| **YuE2-3B** | Lyrics-to-song with multiple stages and audio VAE; no reviewed complete Android recipe | **C** | **C**, retained only for future local-port research |

Sources: [MOSS Nano official Android sample](https://github.com/OpenMOSS/MOSS-TTS-Nano/tree/main/examples/android_onnx_runtime), [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx), [Android TTS examples](https://k2-fsa.github.io/sherpa/onnx/tts/apk-engine.html), [MOSS family](https://github.com/OpenMOSS/MOSS-TTS), [SoulX-Podcast](https://github.com/Soul-AILab/SoulX-Podcast), [YuE2](https://huggingface.co/m-a-p/YuE2-3B), [Arm deployment](https://developer.arm.com/code-along/stable-audio-open-small), [Stable Audio checkpoint](https://huggingface.co/stabilityai/stable-audio-open-small).

MOSS Nano's official Android smoke test uses two pre-tokenized prompts. It is not a complete arbitrary-input voice-cloning product. SentencePiece, matching audio tokenizer/codec, chunking, cancellation and playback buffering remain necessary. Use bounded short-sentence queues; sustained playback depends on measured realtime factor.

**New Qwen3-TTS evidence:** the [Google LiteRT sample](https://github.com/google-ai-edge/litert-samples/tree/main/samples/litert/text_to_speech_lm) includes a Kotlin CPU host loop with tokenizer, Talker, MTP, codec and playback. The publisher reports 4.16 seconds of audio in 28 seconds on Pixel 8a, about RTF 6.7. **That is another phone's upstream result, not a Z20 measurement or realtime operation.** The [community Android app](https://github.com/Danmoreng/qwen3-tts-android) uses quantized GGUF and JNI, but requires Android 12/API 31. Its APK cannot simply be assumed installable on stock Android 9 Z20; an API 28 backend port needs validation.

Stable Audio Open Small targets short audio up to about 11 seconds, not YuE2's complete-song structure. YuE2's official BF16 NVIDIA 24GB reference is not a physical minimum for every quantized implementation. Its C rating reflects the lack of a complete, verifiable Android pipeline, rather than an assertion that 3B weights cannot fit.

## Video: actual local experiments

| Exact version | Local evidence | Z20 | Newer phones |
| --- | --- | --- | --- |
| **Wan 2.1 T2V 1.3B Q4** | Saient native Android process/Vulkan; author reports SM-S921B execution | **B**, high risk | **B**, priority video-port experiment |
| **LTX-Video 2B 0.9.8 distilled** | Android Vulkan/QNN implementation, converted bundles, author phone results | **B/C**; its QNN packages do not target Z20, Vulkan needs separate testing | **B**, exact-chip QNN or independently validated Vulkan recipe |
| Wan 2.2 TI2V 5B / A14B | Official pipeline and native bases such as sd.cpp | **C** | **B/C**, later native quantization research; 1.3B evidence does not cover them |
| LTX-2.3 / LTX-2.5 | New audio/video paths in sd.cpp; 2.5 also needs components such as Gemma 4 12B | **C** | **C**, later research; not the old 2B budget |
| **MiniMax H3-Base** | Released weights and sd.cpp; 33B backbone including about 13B precomputable branches, plus Qwen3-VL-32B and audio/video VAEs | **C** | **C**, outside current phone support; unreleased hosted-system features are not promised |

### Wan 1.3B evidence and portable recipe

[Saient's pipeline](https://github.com/SaientAI/saient/blob/main/docs/VIDEO_PIPELINE.md) and [Android invocation](https://github.com/SaientAI/saient/blob/main/modules/saient-diffusion/android/src/main/java/expo/modules/saientdiffusion/SaientDiffusionModule.kt) show a local `ProcessBuilder`. Diffusion uses Vulkan, UMT5/VAE use CPU, with disk-backed parameters, VAE tiling and chat-model unloading before video.

Its reference settings are **416×240, 5–41 frames constrained to `4n+1`, 8fps and 8–20 steps**, CFG 6 and flow shift 8. These are not Z20-approved settings. Begin with extremely short clips and measure memory, drivers and an actual playable output; do not arbitrarily reduce a non-distilled recipe to 1–4 steps.

The [upstream model lock](https://github.com/SaientAI/saient/blob/main/engine/wan/MODEL_PACK_LOCK.json) totals **4,725,021,654 bytes** across UMT5 (about 3.66GB), backbone (0.82GB) and VAE (0.25GB). **Download bytes are not peak RAM.** Its `hostSmoke.elapsedSeconds = 14.9` is explicitly a desktop CUDA A/B result, not phone speed. The Android report concerns Galaxy S24 SM-S921B and was not reproduced here. Review its [backend revision and patches](https://github.com/SaientAI/saient/blob/main/engine/wan/BACKEND_LOCK.json) separately.

### Older LTX 2B evidence and hardware limits

The [QNN conversion model card](https://huggingface.co/timmyboy26/LTX-Video-2B-0.9.8-distilled-QNN) describes split transformer graphs, fixed-shape VAE, a CPU T5 encoder and QAIRT versions. Listed targets include v69 Snapdragon 8 Gen 1/8+ Gen 1, v73 8 Gen 2, v75 8 Gen 3 and newer chips; **none is Z20**. Shapes such as 512×320×25 and 768×512×25 are separate compiled packages, not freely editable dimensions. Some v73-int exports were not tested on every claimed target.

The reported Snapdragon 8 Elite result, **768×512×25, eight steps, 25.9 seconds**, belongs to the conversion author, not LMA/Z20, and is not universal phone speed. A separate Vulkan route exists. Its GGUF/T5/VAE [source listing](https://github.com/timmyy123/LLM-Hub/blob/main/android/app/src/main/java/com/llmhub/llmhub/data/ModelData.kt) totals **6,653,719,052 bytes**; that is neither RAM nor the QNN bundle size.

The [native QNN runner](https://github.com/timmyy123/LLM-Hub/blob/main/android/stable-diffusion.cpp/src/model/diffusion/ltxv_qnn.hpp) is implementation evidence, but its LLM-Hub repository uses **PolyForm Noncommercial 1.0.0**. It cannot be copied wholesale into a commercially distributed MIT LMA. Prefer auditing permissively licensed native upstreams; resolve licenses separately for code derived from this implementation. Source visibility is not a permissive license. [Project license](https://github.com/timmyy123/LLM-Hub/blob/main/LICENSE)

Other sources: [Wan 2.1](https://github.com/Wan-Video/Wan2.1), [Wan 2.2](https://github.com/Wan-Video/Wan2.2), [experimental MNN Wan entry](https://github.com/alibaba/MNN/blob/master/transformers/diffusion/README.md), [older LTX-Video](https://github.com/Lightricks/LTX-Video), [LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5), [LTX components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/ltx2.md), [H3 model card](https://huggingface.co/MiniMaxAI/MiniMax-H3), [H3 components](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/minimax_h3.md). MNN labels Wan as experimental bring-up, not phone acceptance. Official desktop 8.19GB/24GB GPU configurations describe their recipes, not every native quantized minimum.

## Licenses and model labels

Check all components at their actual pinned revision. Model, code, runtime SDK, voice and reference-material terms are separate. These selection conditions do not transfer across family versions.

| Exact source | Current integration condition |
| --- | --- |
| [SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) / [SDXL](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | OpenRAIL-M / OpenRAIL++; check third-party LoRA independently |
| Original Qwen-Image, Z-Image-Turbo, Sana 600M and FLUX.2-klein-4B above | Their cards specify Apache-2.0; Qwen-Image-2.1 uses **Qwen Research License**, not the original commercial terms |
| [MOSS Nano ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX), [codec](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX), Kokoro, [Qwen3-TTS Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base), [SoulX](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B) | Their cards specify Apache-2.0; inspect language packages and reference material separately |
| YuE2-3B / Stable Audio Open Small | **CC-BY-NC-4.0** / Stability AI Community License respectively; not unconditional commercial components |
| Older LTX-Video 2B / LTX-2.5 | Separate old Open Weights and new LTX-2.x Community licenses; cards include conditions concerning entity-wide annual revenue of USD 10M |
| [H3 license](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE) | Territory, attribution and commercial conditions, including written permission for relevant commercial products/services above USD 20M annual revenue |
| sd.cpp / MNN / [LLM-Hub](https://github.com/timmyy123/LLM-Hub/blob/main/LICENSE) | MIT / Apache-2.0 / PolyForm Noncommercial respectively; inspect QNN SDK terms independently |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | GPL-3.0; independently implementing a local DAG does not reuse all code/Python nodes or imply compatibility |

Preserve local-model positioning, the existing Recommended entries and separate Uncensored/Abliterated tags. New models do not inherit those tags. Compatibility, evidence and commercial terms remain separate attributes.

## Local product roadmap and acceptance

| Stage | Deliverables and acceptance |
| --- | --- |
| 1: shared foundation | Multi-component bundles, native providers, per-model settings, persistent jobs/artifacts, offline validation, one large-engine lease |
| 2: initial working chains | One explicit-language small TTS, SD 1.5 plus matching LoRA; templates and actual execution before a canvas |
| 3: mobile expansion | Qwen3-TTS Base, MNN Sana, short sounds; validate complete local chains on API 28 and newer devices |
| 4: on-phone video experiments | Wan 1.3B prototype first; separate Vulkan and exact-chip QNN recipes for old LTX 2B; retain experimental labels until measured |
| 5: advanced models | Quantization/staged loading on high-memory phones; C-rated candidates never appear as verified/default recommendations |

Acceptance includes full download/resume/missing-file handling, revision/hashes, **new arbitrary inputs generated with networking disabled**, playable outputs, model-settings isolation, clamping and joint shape limits, generation/cancellation/unloading, peak RAM, time/quality, screen-off/thermal behavior and honest recovery after process death. Foreground work needs no ROOT but cannot guarantee survival or 24/7 full-load execution.

See [WORKFLOWS.en.md](WORKFLOWS.en.md) for the framework and two **design-only, non-executable** local JSON examples; [local-video-evidence.json](research/local-video-evidence.json) records source evidence. This update changes documentation only, adds no phone passes, and does not rebuild APKs or replace published assets. Existing screenshots/GIFs still demonstrate v0.2.0 text features.
