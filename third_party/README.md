# MOSS Delay first-class CPU worker

[Pinned source lock](moss-delay-source-lock.json) records the MIT OpenMOSS fork used by the same-phone 32-channel speech pipeline. Native source only; backbone/BPE/codec files remain explicit user assets. See [中文](../docs/MOSS_DELAY_ENGINE.md) / [English](../docs/MOSS_DELAY_ENGINE.en.md). No ordinary MOSS GGUF compatibility or complete-family/device acceptance is implied.

# Native runtime provenance and notices

LMA independently implements its Android application and UI. It redistributes the CPU subset of the MIT-licensed llama.cpp runtime supplied by the [ServLlama 1.2.2 release](https://github.com/ArkaneFans/servllama/releases/tag/1.2.2).

- Asset: `llama-server-v0.4.1-android-arm64-v8a.zip`
- SHA256: `551e5be8494bd2ae9955992faaaca1a4f5cf29e3a97f90d2e04205eb460fcde6`
- Recorded llama.cpp revision: `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`
- LMA includes 14 CPU libraries, recorded individually in `runtime-lock.json`. Optional OpenCL and Hexagon libraries are excluded.

`BUILD_INFO.json`, `SHA256SUMS` and `LLAMA_CPP_LICENSE` are the upstream provider's metadata. The toolchain image mentioned in that metadata was used by the provider. **No container, WSL, emulator or virtual machine was run in this LMA build.** Native compilation was performed upstream; LMA verifies and packages the prebuilt binaries and builds its Java / resources using native Windows SDK tools.

The primary engine license is in `LLAMA_CPP_LICENSE`. `notices/` contains accompanying third-party license texts from pinned upstream sources; `notices/sources.json` records their URLs. Standard LLVM runtime notices are included conservatively because the provider's ELF bundle statically includes its C++ runtime; a separate C++ runtime source revision is not recorded by the provider. Inclusion of a notice does not assert every optional upstream feature is enabled in LMA.

`tools/collect_notices.py` can refresh these notices from the recorded revisions. The build bundles them into `assets/licenses/` and the application's About page. `upstream/` contains selected source and documentation files used to check CLI flags and supported architectures; it is not a complete source checkout. Full source for the recorded engine revision is available from the [llama.cpp repository](https://github.com/ggml-org/llama.cpp/tree/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4).

Model weights are not redistributed in the APK. Each catalogue entry links to its own model repository, whose model and base-model licenses govern the downloaded weights.

## Added development worker

0.3.0-dev adds a locally compiled ARM64 CPU sd.cpp worker, pinned with ggml in [engine-lock.json](engine-lock.json). Native Windows NDK 30.0.16248370 builds it; the temporary SUBST path alias is not virtualization. [Native sources](../native/CMakeLists.txt) replace embedded model vocabularies with externally installed user data. The 13 `sd-*` notice files come from the exact checkout and NDK, recorded in [sd-sources.json](notices/sd-sources.json). This proves compilation/packaging provenance, not phone inference or all selected-model support. Existing ServLlama binaries retain their original provenance. See [development status](../docs/DEVELOPMENT.en.md).

## MOSS Nano adapter

Pinned MOSS/SentencePiece/ORT headers and exact shared ORT bytes are recorded in [moss-nano-source-lock.json](moss-nano-source-lock.json). Seven upstream notice originals are collected from clean pinned sources. The signed worker uses external user-selected model data and shares one verified ORT file with sherpa. [中文](../docs/MOSS_NANO_ENGINE.md) · [English](../docs/MOSS_NANO_ENGINE.en.md).

The Sana mobile MNN CPU worker is pinned in [mnn-source-lock.json](mnn-source-lock.json), with six source notices in [mnn-sources.json](notices/mnn-sources.json), the shared JSON/NDK notices and the actual binary identity in [engine-lock.json](engine-lock.json). Native Windows NDK builds disable HTTP resources/Logcat. No weights/tokenizer data are distributed. Compilation and host contracts establish no phone image output. [中文](../docs/MNN_SANA_ENGINE.md) / [English](../docs/MNN_SANA_ENGINE.en.md).

Qwen speech pins both upstream and its ggml submodule in [qwen-tts-source-lock.json](qwen-tts-source-lock.json). Native source and ggml MIT notices are copied exactly and included in the App; JSON/NDK notices are shared. GGUF weights/vocabularies/speaker data are user assets, never source dependencies. See [中文](../docs/QWEN_TTS_ENGINE.md) / [English](../docs/QWEN_TTS_ENGINE.en.md).

The `openmoss_native` worker uses [openmoss-source-lock.json](openmoss-source-lock.json), its exact llama.cpp submodule and [notices/openmoss-sources.json](notices/openmoss-sources.json). Only reviewed native core sources are linked; CLI, HTTP server and upstream WAV I/O are excluded. Model/codec assets and their independent licenses remain user-selected. See the [integration guide](../docs/OPENMOSS_ENGINE.en.md).


dev.19 adds [moss-rq-source-lock.json](moss-rq-source-lock.json): `mudler/moss-tts.cpp` at `ee722b8e9205ee9b1b1c398a4e87e4e393e9be41`, GGML at `e705c5fed490514458bdd2eaddc43bd098fcce9b`. Only CPU Local/Realtime/codec source is linked; no upstream CLI/server or model assets. The pinned README declares MIT and names Ettore Di Giacinto, but that revision has no standalone LICENSE; preserve the actual README and GGML license without fabricating an upstream file. Generated copies carry LMA guards/callbacks, their hashes enter receipts, and pristine pins are revalidated. 原生编译及两个合成微型图不等于模型 / Android 验收；模型、codec、BPE 始终为用户资产。See [中文指南](../docs/MOSS_RQ_ENGINE.md) / [English](../docs/MOSS_RQ_ENGINE.en.md)。

SoulX DSP research pins are recorded in [soulx-dsp-source-lock.json](soulx-dsp-source-lock.json). The unregistered library is excluded from the APK; its [notice](../research/soulx/NOTICE), Apache-2.0 port license and KISS FFT BSD-3-Clause text stay with the source. Pinned torchaudio/librosa Python bodies and the publisher S3 mel bank are ignored host references only. No model checkpoint, filter bank, vocabulary or example audio is distributed. [中文](../docs/SOULX_DSP.md) / [English](../docs/SOULX_DSP.en.md).

SoulX trained reference/acoustic research adds [reference source/model pins](soulx-reference-source-lock.json) and [trained Flow/HiFT asset pins](soulx-trained-assets.json). Original/converted model bytes stay in ignored developer directories, outside Git/APK/source archives. The [reference NOTICE](../research/soulx_reference/NOTICE) retains source/model-card attribution; the [shared ORT NOTICE](../research/soulx_ort/NOTICE) carries Microsoft MIT. Four trained components run in scoped host checks, without Qwen3, complete text-to-speech, App registration or phone evidence. [中文](../docs/SOULX_REFERENCE.md) / [English](../docs/SOULX_REFERENCE.en.md).

SoulX language research pins the same llama.cpp revision as the existing Android text runtime and full official/earlier community model assets in [soulx-language-source-lock.json](soulx-language-source-lock.json). [NOTICE](../research/soulx_language/NOTICE) retains SoulX Apache-2.0 and llama.cpp MIT. All6561 semantic markers and distinct vocabularies are verified; full trained Qwen3/Flow/HiFT with S3/CAMP references execute on the developer host, with independent original HF/RAS/history checks. Android compilation is separate; no APK registration, phone or speech-quality acceptance. Model/tokenizer/WAV assets remain ignored, outside Git/APK. [中文](../docs/SOULX_LANGUAGE.md) / [English](../docs/SOULX_LANGUAGE.en.md).


dev.21 compiles shared SoulX DSP/reference/language/acoustic source into the actual App worker, while retaining separate research targets/evidence. [Native worker NOTICE](../native/soulx/NOTICE), exact source locks and nine complete source/runtime notices are preserved by `tools/collect_soulx_notices.py` in the engine lock. Fourteen model assets, including ten learned source coefficients, remain external user data. See [中文](../docs/SOULX_ENGINE.md) / [English](../docs/SOULX_ENGINE.en.md); host trained output is not phone/quality acceptance.

## Old LTX-Video 0.9.8 DiT research component

The [source lock](ltx098-source-lock.json) pins Apache-2.0 Lightricks architecture sources,MIT GGML/JSON,dual-licensed Vulkan headers,MIT SPIRV headers,oracle dependency hashes and the ignored Windows shaderc tool archive. Published unsigned build provenance matches that archive digest; signature verification is not claimed. Complete code notices stay in [research/ltx098](../research/ltx098/NOTICE),outside App packaging. No LLM-Hub implementation,newer LTX2 substitution,model weights,tokenizer or QNN payload is incorporated. Model open-weight terms remain separate. See [中文](../docs/LTX098_DIT.md) / [English](../docs/LTX098_DIT.en.md).

Old-LTX follow-up adds an [external trained asset identity lock](ltx098-trained-assets.json), explicit resumable retrieval, local streaming conversion, and independent publisher geometry/RF/unpatchify comparisons. The model's separate LTXV Open Weights License0.X terms still apply; model bytes, converted GGUF and oracle artifacts stay in ignored build directories, outside Git/APK/source archives. Full trained28-layer Vulkan latent checks use synthetic caption embeddings; they do not establish T5/VAE/video/App/phone support. Complete source attribution remains in [NOTICE](../research/ltx098/NOTICE). [中文](../docs/LTX098_SAMPLING.md) / [English](../docs/LTX098_SAMPLING.en.md).

## Old LTX T5 text-encoder research

The [T5 source/asset lock](ltx098-text-source-lock.json) pins MIT llama.cpp/GGML/JSON, existing Android CPU runtime identities, original Google tokenizer/config assets and the community city96 Q5_K_M encoder. Its Apache-2.0 asset declaration does not replace separate old-LTX model terms. The GGUF lacks 100 sentinel names: the original external tokenizer config is required. All learned vocabulary/scores and normalization bytes are checked against original SentencePiece. Explicit F32 GELU and temporary F32 matrix casts leave shared App libraries untouched; no weights/vocabulary or research executable enters APK. Reference Transformers files are hashed; the comparison uses the same quantized weights dequantized to F32, without unquantized-weight or prompt/video quality claims. [NOTICE](../research/ltx098_text/NOTICE) / [中文](../docs/LTX098_TEXT.md) / [English](../docs/LTX098_TEXT.en.md).
