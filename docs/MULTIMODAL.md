# Android 纯本地多模态可行性

[English](MULTIMODAL.en.md) · [共用基座评估](FOUNDATION.md) · [本机任务方案](WORKFLOWS.md) · [现行需求](MULTIMODAL_RELEASE_PLAN.md) · [文档目录](README.md)

核查日期：**2026-10-27（Asia/Taipei）**。按用户最新要求重新评估：**所有模型推理均在同一台 Android 手机上完成，无需 ROOT，不采用其他设备、局域网服务器或云端推理，也不设置此类回退。** 下载权重可以访问 HF；下载完成后，分词、文本编码、采样、VAE / codec、合成和导出均应能离线执行。

这是源码与资料核查及工程分级，**不是已实现功能或 LMA 真机性能报告**。当前 v0.2.0 APK 仍只运行兼容的单文件文本 GGUF。本轮没有下载新权重、编译新引擎或执行手机生成；没有可用真机。

本页保留较宽的模型研究；当前交付范围以[需求与发版计划](MULTIMODAL_RELEASE_PLAN.md)为准：01–14 / 16 / 17、平级模型与功能 / 基座标签、表单 / 队列 / 结果。本文中的 YuE2、H3、新 LTX 和 ComfyUI 仅属背景，未纳入本次需求；早期画布 / 节点计划已撤回。

## 重新评估的结论

纯本地扩展可行，优先交付 **SD 1.5 + 匹配 LoRA、小型离线 TTS、原生任务队列与本机执行器**。音效可继续实验 Stable Audio Open Small。完整歌曲、大规格图像和大型视频模型暂不列为本地产品已支持项。

**生视频不能整体判为手机不可行。** 社区已有 Wan 2.1 1.3B 的 ARM64 / Vulkan Android 管线，以及旧版 LTX-Video 2B 的 Android Vulkan / 特定芯片 QNN 管线。它们是值得移植的本机实验候选；这些证据不等于 Z20 已通过，也不代表当前 LMA 已集成。

HF 可发现、文件可下载、架构有 C++ 实现、Android 后端能运行、某一手机实际可用，分别是不同结论。GGUF 不是跨任务的通用加载协议；LoRA 也不能独立生图。

## 设备基线与证据等级

国际版 Z20 官方规格为 **Snapdragon 855+、Adreno 640、8GB RAM、128GB 存储、4,000mAh**；实际设备版本仍需读取确认。CPU / GPU 共用内存，不能把它当作 8GB 独立显存。先保留 CPU 路线，GPU 按驱动 / 算子探测；不把新芯片 NPU 包套用于 Z20。[Z20 规格](https://uk.nubia.com/pages/z20-specs)

| 等级 | 本文含义 |
| --- | --- |
| A：首批候选 | 已有适合移动端的对应实现，优先移植与验收；不代表 LMA 或 Z20 已测通过 |
| B：实验 | 有原生实现、转换或 Android 证据，仍需核验完整组件、驱动、内存、速度及质量 |
| C：暂不纳入 | 当前没有足够证据纳入本地产品支持；不是永远无法通过量化或新硬件实现 |

“较新手机”是约 12–24GB RAM、较新驱动的 ARM64 测试组，**不是统一最低配置**；QNN 还须精确匹配 SoC、Hexagon、SDK 和图形状。以下分级都是候选评估，当前 APK 的多模态支持仍为零。

证据分别标记为：发布方 Android 示例、实现作者的手机结果、原生引擎 / 桌面配方，以及 LMA 实测。前三者不能写成第四者。文件大小不是峰值 RAM；桌面 GPU 显存与手机共享 RAM 不能直接换算。

## 生图与 LoRA

| 模型 / 能力 | 本地实现依据 | Z20 | 较新手机 / 接入方式 |
| --- | --- | --- | --- |
| **Stable Diffusion 1.5** | Local Dream Android；MNN Diffusion；sd.cpp | **A** | **A**；首批单图、batch 1，先测 256 / 512 档位 |
| **匹配的 LoRA** | sd.cpp 适配器 | 随基础模型 | 校验基础家族、组件、量化和强度；本轮不包括 LoRA 训练 |
| SD-Turbo / LCM / LCM-LoRA | sd.cpp 的相应蒸馏路线 | **B** | **A/B**；SD-Turbo 基于 SD 2.1，不能当作 SD 1.5 LoRA；只用对应采样配置 |
| SDXL / SDXL-Turbo | Local Dream CPU/GPU 与特定新芯片 NPU | **B**，高风险、非默认 | **B**；双编码器、UNet、VAE 完整预算 |
| Sana 600M / MNN Sana 移动变体 | 官方 checkpoint；MNN Android / 转换路径 | **B** | **A/B**；MNN 移动配方可用 Qwen3-0.6B 编码器，不能与原版 Sana 包混配 |
| FLUX.2-klein-4B | 官方 4B；sd.cpp | **B/C**，非默认 | **B**；量化、顺序加载编码器 / 主干 / VAE |
| 原始 Qwen-Image 20B | 官方权重；sd.cpp | **C** | **C**，仅后续移植研究；20B 主干理想 4-bit 原始权重已约 10GB，其他组件另计 |
| Qwen-Image-2.1 / Turbo | 7B 图像主干 + Qwen3-VL-8B 编码器 + 专用 VAE | **C** | **B**，高内存实验；不能按整条管线 7B 估算，也不能继承原版许可 |
| Z-Image-Turbo 6B | sd.cpp；另需 Qwen3-4B 编码器及 VAE | **B/C**，非默认 | **B**；8 NFE 蒸馏、量化和阶段卸载；桌面 4GB 显存配方不是手机 4GB RAM 证明 |

实现来源：[Local Dream](https://github.com/xororz/local-dream#about-this-repo)、[MNN Diffusion](https://github.com/alibaba/MNN/blob/master/transformers/diffusion/README.md)、[sd.cpp](https://github.com/leejet/stable-diffusion.cpp#features)。Local Dream 的 SD 1.5 NPU 要求 Hexagon v68+，SDXL NPU 要求 Snapdragon 8 Gen 3+；**Z20 不在这两条已列出的 NPU 适配范围内**，CPU / GPU 必须另测。

精确模型与组件：[SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5)、[SD-Turbo](https://huggingface.co/stabilityai/sd-turbo)、[Sana 600M](https://huggingface.co/Efficient-Large-Model/Sana_600M_1024px_diffusers)、[FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)、[Qwen-Image](https://huggingface.co/Qwen/Qwen-Image)、[Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1)、[2.1 组件](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/qwen_image_2.1.md)、[Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)、[Z-Image 组件](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/z_image.md)。新家族或新版本重新建立配方，不自动继承前代编码器和设备结论。

`参数数 × 位数 ÷ 8` 只是理想原始权重下界，GB 为十进制。量化附加数据、未量化层、激活、注意力、VAE、驱动和系统另计。mmap / 磁盘流式读取可减常驻内存，但不保证延迟或避免低内存杀进程。参数降档也不能越过模型形状或蒸馏约束。

## 语音、音效与音乐

| 模型 / 能力 | 端到端本地路线与边界 | Z20 | 较新手机 |
| --- | --- | --- | --- |
| **MOSS-TTS-Nano 100M** | 官方 ONNX / Android 示例；补任意文本 tokenizer 与 codec | **A** | **A** |
| **Kokoro-82M** | sherpa-onnx Android；完整语言 / 音色 / 词典包 | **A** | **A** |
| **Piper / VITS / Matcha** | sherpa-onnx 离线 TTS 与 Android 示例 | **A** | **A**；具体声音和语言逐包核查 |
| **Qwen3-TTS 0.6B Base** | Google LiteRT Kotlin CPU 示例；社区 qwen3-tts.cpp JNI App | **B**，性能及 API 28 适配待验 | **A/B**；已有 Android 端到端代码，不承诺实时 |
| MOSS 完整系列 | 多架构；Delay 有含 codec 的原生 fork，其他路线分别移植 | **B/C** | **B**；逐架构核验整条链，不能只看 LLM 权重大小 |
| SoulX-Podcast 1.7B | 官方参考为 Linux Python；部件可转换不等于完整 Android 管线 | **B/C** | **B**，原生移植研究，暂不当首批功能 |
| **Stable Audio Open Small 341M** | Arm LiteRT / C++ / Android 路线；短音效 / 音乐片段 | **B** | **A/B**；不代表完整歌曲生成能力 |
| **YuE2-3B** | 歌词到歌曲，含多阶段生成及音频 VAE；缺少已核查的完整 Android 方案 | **C** | **C**；仅保留后续本地移植研究 |

主要依据：[MOSS Nano 官方 Android 示例](https://github.com/OpenMOSS/MOSS-TTS-Nano/tree/main/examples/android_onnx_runtime)、[Kokoro](https://huggingface.co/hexgrad/Kokoro-82M)、[sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)、[Android TTS 示例](https://k2-fsa.github.io/sherpa/onnx/tts/apk-engine.html)、[MOSS 系列](https://github.com/OpenMOSS/MOSS-TTS)、[SoulX-Podcast](https://github.com/Soul-AILab/SoulX-Podcast)、[YuE2](https://huggingface.co/m-a-p/YuE2-3B)、[Arm 本地音频部署](https://developer.arm.com/code-along/stable-audio-open-small)、[Stable Audio 模型](https://huggingface.co/stabilityai/stable-audio-open-small)。

全 MOSS 的 [Delay 原生分支](https://github.com/OpenMOSS/llama.cpp/blob/moss-tts-firstclass/docs/moss-tts-firstclass-e2e.md)已提供原生 backbone / 音频编码 / 解码路线；不再一律假设需要 Python 或 ONNX codec。但这不证明 Local / Realtime / DiT 或 Android 全家族支持；冻结子目标见现行发版需求。

MOSS Nano 官方 Android smoke 示例使用预先分词的两个提示，不能直接宣传为任意输入的完整语音克隆产品。还需 SentencePiece、匹配的音频 tokenizer / codec、分块、取消和播放缓冲。TTS 优先短句有界队列；是否能持续播放取决于实际实时率。

**Qwen3-TTS 的新增证据：** [Google LiteRT 示例](https://github.com/google-ai-edge/litert-samples/tree/main/samples/litert/text_to_speech_lm) 有 Kotlin CPU host loop，覆盖 tokenizer、Talker、MTP、codec 与播放。发布方记录 Pixel 8a 生成 4.16 秒音频耗时 28 秒，约 RTF 6.7；**这是上游在另一手机的结果，不是 Z20 测量，也没有达到实时**。[社区 Android App](https://github.com/Danmoreng/qwen3-tts-android) 使用量化 GGUF + JNI，但其 App 最低 Android 12 / API 31；不能直接认定可安装到原生 Android 9 的 Z20，后端向 API 28 移植需单独验证。

Stable Audio Open Small 面向至多约 11 秒短音频，不能替代 YuE2 的整曲结构。YuE2 官方 BF16 NVIDIA 24GB 参考配置不是所有量化实现的物理下限；本文将其列 C，依据是当前缺乏完整、可验收的 Android 本机管线，而不是“3B 一定放不下”。

## 生视频：本机实验方案

| 精确版本 | 本地证据 | Z20 | 较新手机 |
| --- | --- | --- | --- |
| **Wan 2.1 T2V 1.3B Q4** | Saient Android 原生进程 + Vulkan；作者报告 SM-S921B 运行 | **B**，高风险 | **B**，优先移植的生视频实验 |
| **LTX-Video 2B 0.9.8 distilled** | Android Vulkan / QNN 实现与转换模型包，作者有手机结果 | **B/C**；QNN 包不适配 Z20，Vulkan 另验 | **B**；优先精确匹配芯片的 QNN 或独立 Vulkan 配方 |
| Wan 2.2 TI2V 5B / A14B | 官方管线、sd.cpp 等原生基础 | **C** | **B/C**，后续原生量化研究；1.3B 的成功不覆盖这些型号 |
| LTX-2.3 / LTX-2.5 | sd.cpp 有新一代音视频路线；2.5 另含 Gemma 4 12B 等组件 | **C** | **C**，后续研究；不是旧 2B 的同等资源预算 |
| **MiniMax H3-Base** | 官方开放权重与 sd.cpp；33B 主干含约 13B 可预计算分支，另需 Qwen3-VL-32B 及音视频 VAE | **C** | **C**，暂不纳入手机产品支持；不承诺复现未开放的完整托管系统 |

### Wan 1.3B 的证据及可移植配方

[Saient 管线说明](https://github.com/SaientAI/saient/blob/main/docs/VIDEO_PIPELINE.md) 与 [Android 调用源码](https://github.com/SaientAI/saient/blob/main/modules/saient-diffusion/android/src/main/java/expo/modules/saientdiffusion/SaientDiffusionModule.kt) 展示本机 `ProcessBuilder`，不是把提示词发送出去。Diffusion 用 Vulkan，UMT5 编码器 / VAE 用 CPU，磁盘参数后端、VAE tiling，并在视频前卸载聊天模型。

上游配方为 **416×240、5–41 帧且 `4n+1`、8fps、8–20 步**，CFG 6、flow shift 8；这是参考范围，不是已经批准的 Z20 参数。先用极短片验证内存、驱动和可打开的实际视频，不将“少步”任意降到未蒸馏模型的 1–4 步。

[上游模型包锁](https://github.com/SaientAI/saient/blob/main/engine/wan/MODEL_PACK_LOCK.json) 列三组件合计 **4,725,021,654 字节**，其中 UMT5 编码器约 3.66GB，主干约 0.82GB，VAE 约 0.25GB。**这是下载大小，不是峰值 RAM。** 其中 `hostSmoke.elapsedSeconds = 14.9` 明确来自桌面 CUDA A/B，不能写成手机速度。Android 声明涉及 Galaxy S24 SM-S921B，本文未复现。[后端固定版本与补丁](https://github.com/SaientAI/saient/blob/main/engine/wan/BACKEND_LOCK.json) 也需单独审计。

### 旧 LTX 2B 的证据及设备限制

[QNN 转换包模型卡](https://huggingface.co/timmyboy26/LTX-Video-2B-0.9.8-distilled-QNN) 给出分片 transformer、固定形状 VAE、CPU T5 编码器及 QAIRT 版本。作者列出 v69 的 Snapdragon 8 Gen 1 / 8+ Gen 1，v73 的 8 Gen 2，v75 的 8 Gen 3，以及更新芯片包；**没有 Z20 的芯片包**。例如 512×320×25 与 768×512×25 是不同编译形状，不能任意编辑尺寸；部分 v73-int 目标只是导出支持，未在每个目标手机实测。

模型卡中的 Snapdragon 8 Elite **768×512×25、8 步、25.9 秒**是作者结果，不是 LMA / Z20 结果，也不能推广为所有手机速度。QNN 之外还有独立 Vulkan 路径；其 GGUF + T5 + VAE [源码清单](https://github.com/timmyy123/LLM-Hub/blob/main/android/app/src/main/java/com/llmhub/llmhub/data/ModelData.kt) 合计 **6,653,719,052 字节**，同样不等于 RAM，也不是 QNN 包的总大小。

[QNN 原生执行器](https://github.com/timmyy123/LLM-Hub/blob/main/android/stable-diffusion.cpp/src/model/diffusion/ltxv_qnn.hpp) 证明有实现可研究，但其所属 LLM-Hub 仓库采用 **PolyForm Noncommercial 1.0.0**，不能整包复制后按 LMA MIT 商用分发。优先审计宽松许可的上游原生引擎；涉及该实现的代码另行解决许可，不把“源码可见”当作宽松开源。[项目许可](https://github.com/timmyy123/LLM-Hub/blob/main/LICENSE)

其他依据：[Wan 2.1](https://github.com/Wan-Video/Wan2.1)、[Wan 2.2](https://github.com/Wan-Video/Wan2.2)、[MNN Wan 实验入口](https://github.com/alibaba/MNN/blob/master/transformers/diffusion/README.md)、[旧 LTX-Video](https://github.com/Lightricks/LTX-Video)、[LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5)、[LTX 组件](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/ltx2.md)、[H3 模型卡](https://huggingface.co/MiniMaxAI/MiniMax-H3)、[H3 组件](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/minimax_h3.md)。MNN Wan 文档仍定位为实验 bring-up，不能单独视为手机验收。官方桌面 8.19GB / 24GB GPU 配置只描述相应配方，不构成所有原生量化方案的下限。

## 许可与模型标签

按实际固定 revision 的所有组件核查；模型许可、代码许可、运行 SDK 和音色 / 参考素材分别处理。这是集成条件梳理，不把同家族许可推广到其他版本。

| 具体来源 | 当前选型条件 |
| --- | --- |
| [SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) / [SDXL](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | OpenRAIL-M / OpenRAIL++；第三方 LoRA 另查 |
| 上表原版 Qwen-Image、Z-Image-Turbo、Sana 600M、FLUX.2-klein-4B | 对应模型卡 Apache-2.0；Qwen-Image-2.1 是 **Qwen Research License**，不得继承原版商业结论 |
| [MOSS Nano ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX)、[codec](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX)、Kokoro、[Qwen3-TTS Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base)、[SoulX](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B) | 对应模型卡 Apache-2.0，语言包 / 参考素材独立核查 |
| YuE2-3B / Stable Audio Open Small | 分别为 **CC-BY-NC-4.0** / Stability AI Community License；不可默认当作无条件商业组件 |
| 旧 LTX-Video 2B / LTX-2.5 | 旧版 Open Weights License 与新版 LTX-2.x Community License 分开；模型卡存在全实体年营收 1,000 万美元相关条件 |
| [H3 License](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE) | 地域、署名及商业条件；年营收超过 2,000 万美元的相关商业产品 / 服务需书面授权 |
| sd.cpp / MNN / [LLM-Hub](https://github.com/timmyy123/LLM-Hub/blob/main/LICENSE) | 前两者 MIT / Apache-2.0；后者 PolyForm Noncommercial，不能混同；QNN SDK 条款另查 |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | GPL-3.0；自行实现本地 DAG 不等于复用其全部代码 / Python 节点，也不自动兼容 |

保留“本地模型”定位、“推荐”现有内容和独立的 Uncensored / Abliterated 标签；不把其他新模型自动贴无审查标签。兼容性、证据等级和商业许可是不同属性。

## 本地产品路线与完成条件

| 阶段 | 交付内容与验收目标 |
| --- | --- |
| 1：共用基础 | 多组件模型包、原生 provider、模型独立参数、任务 / 产物持久化、离线资源校验、单大型引擎调度 |
| 2：首批可用链 | 一套明确语言的小型 TTS、SD 1.5 + 匹配 LoRA；任务表单 / 队列与真实生成，不增加画布 |
| 3：移动扩展 | Qwen3-TTS Base、MNN Sana、短音效；按完整本地链逐个测 API 28 和较新手机 |
| 4：本机生视频实验 | Wan 1.3B 优先原型；旧 LTX 2B 分 Vulkan / 芯片特定 QNN 配方；未测通过保留实验标签 |
| 5：进阶模型 | 高内存手机量化 / 分阶段加载；C 类不出现在“已验证可运行”或默认下载推荐中 |

具体验收必须包含：完整下载 / 续传 / 缺失文件、revision 与哈希、**关闭网络后的任意新输入生成**、实际可打开的产物、模型间设置独立、超限回填与联合形状约束、生成 / 取消 / 卸载、峰值内存、耗时和质量、锁屏 / 发热、进程死亡后的真实恢复行为。后台服务无需 ROOT，但没有永不被杀或 24/7 连续满载保证。

本机任务与两份**历史、不可执行，非当前交付要求**的 JSON 见 [WORKFLOWS.md](WORKFLOWS.md)；视频来源的结构化记录见 [local-video-evidence.json](research/local-video-evidence.json)。本轮仅更新设计文档，没有新增手机测试结论，也不重建 APK 或替换公开 Release 附件。已有截图 / GIF 仍只演示 v0.2.0 的文本功能。
