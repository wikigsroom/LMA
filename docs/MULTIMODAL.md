# 多模态业务扩展可行性

[English](MULTIMODAL.en.md) · [工作流方案](WORKFLOWS.md) · [文档目录](README.md)

核查日期：**2026-10-27（Asia/Taipei）**。对象是 LMA、无需 ROOT 的 Android 手机，重点参考努比亚 Z20；同时评估用户主动配置的远程 GPU。本文是资料核查与工程判断，**不是已实现功能或真机性能报告**。当前 v0.2.0 APK 仍只运行兼容的单文件 GGUF 文本模型。

## 决策

可以把 LMA 扩展为图像、语音、音频、视频和工作流工作台。建议先接入 **小型本地 TTS、SD 1.5，以及远程 ComfyUI**。大型图像、歌曲和视频生成优先放在用户自己的电脑或服务器执行；手机负责选择模型、编辑工作流、提交任务和接收结果。远程模式必须明确选择，不把本地任务静默上传。

没有一种引擎能因为文件来自 HF 或扩展名是 GGUF 就运行全部模型。LoRA 是依附基础模型的适配器；TTS、音乐、视频也不是同一种任务。下载能力、架构支持、Android 后端可用、设备实际可用，是四个不同结论。

本轮阅读官方模型卡、项目源码说明、Android 示例和 API 文档，未下载权重、编译这些新引擎或运行生成。没有可用真机，所有 Z20 判断均为待验证的工程分级；终端 HF API 的补充访问未成功，因此未制作经过下载核验的文件大小 / 哈希锁定清单。以下链接跟随上游版本，实施时须再固定 revision、文件及 SHA256。

## Z20 基线与分级

努比亚官方国际版规格为 **Snapdragon 855+、Adreno 640、8GB RAM、128GB 存储、4,000mAh 电池**。其他版本应读取实际设备信息，不能沿用 8GB 的预算。[努比亚规格](https://uk.nubia.com/pages/z20-specs)

手机的 CPU、GPU 和系统共享内存，8GB RAM 不等于桌面显卡的 8GB 独立显存；系统、WebView、模型工作缓冲都需要空间。Vulkan / OpenCL 路线要检测设备驱动及算子，不能只看芯片名称。Local Dream 的 SD 1.5 NPU 路线要求 Hexagon v68 或更新，SDXL 要求 Snapdragon 8 Gen 3 或更新；本方案**不把 Z20 计入已经满足该 NPU 路线的设备**，先评估 CPU，再实测 GPU。[Local Dream 设备要求](https://github.com/xororz/local-dream#about-this-repo)

| 分级 | 含义 |
| --- | --- |
| A：优先候选 | 已有对应移动运行路径，适合先移植和验收；不代表 Z20 已测通过 |
| B：实验 | 有转换 / 原生运行基础，但完整依赖、内存、驱动、速度仍需专项验证 |
| R：远程优先 | 为实际产品选择远程执行；不等同于数学上绝对不能移植 |

后文“较新旗舰”指约 12–24GB RAM、驱动较新的 ARM64 手机，**是测试分组，不是最低硬件保证**。没有把其他手机或桌面的速度折算成 Z20 性能。

## 生图与 LoRA

| 模型 / 能力 | 已核查的运行基础 | Z20 | 较新旗舰与接入建议 |
| --- | --- | --- | --- |
| Stable Diffusion 1.5 | Local Dream 已有 Android 实现；MNN 有 SD 1.5 转换资源；sd.cpp 有原生推理 | **A** | 首批本地生图；先测单张 256/512、batch 1、内存节省模式，数值是验收起点 |
| SD-Turbo、LCM / LCM-LoRA | sd.cpp 支持相关蒸馏路线；SD-Turbo 基于 SD 2.1，并非 SD 1.5 LoRA | **B** | 降低步数可降低计算量；仍需匹配基础架构、采样器与蒸馏配置 |
| SDXL / SDXL-Turbo | Local Dream 有 CPU/GPU 及特定新芯片 NPU 路线 | **R / B**，不作为默认 | 新旗舰专项；双编码器及 VAE 也计入内存，不只计算 UNet |
| LoRA / 多 LoRA | sd.cpp 有适配器支持 | 随基础模型 | 绑定基础模型家族、组件版本、量化和强度；不能单独“加载 LoRA 生图”，本轮讨论推理而非手机训练 |
| Sana 600M | 发布方提供 600M checkpoint；MNN 有 Sana 转换与推理说明 | **B** | 比大模型值得优先实验；600M 不包含所有运行成本，编码器仍需配套 |
| FLUX.2-klein-4B | 官方 4B checkpoint；sd.cpp 有 FLUX.2-klein 路线 | **B / R** | 新旗舰量化实验；核算文本编码器、VAE 和激活，不能只按“4B”判断 |
| Qwen-Image 原始版 | 官方 20B；sd.cpp 有实现 | **R** | 远程优先；仅 20B 主干理想 4-bit 权重已约 10GB，尚未计编码器和缓冲 |
| Qwen-Image-2.1 / Turbo | 2.1 为 7B 图像主干；sd.cpp 路线还需 Qwen3-VL-8B 编码器及专用 VAE | **R** | 新旗舰 **B**；比原版小，但不是整条管线只有 7B，许可也与原版不同 |
| Z-Image-Turbo | 官方 6B、8 次 NFE；sd.cpp 有实现，另需文本编码器和 VAE | **B / R** | 新旗舰量化、分阶段加载实验；桌面 4GB 显存优化不是 Z20 通过证据 |

运行器依据：[sd.cpp 支持列表](https://github.com/leejet/stable-diffusion.cpp#features)、[MNN Diffusion](https://github.com/alibaba/MNN/blob/master/transformers/diffusion/README.md)、[Local Dream](https://github.com/xororz/local-dream)。具体权重：[SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5)、[SD-Turbo](https://huggingface.co/stabilityai/sd-turbo)、[Sana 600M](https://huggingface.co/Efficient-Large-Model/Sana_600M_1024px_diffusers)、[FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)、[Qwen-Image](https://huggingface.co/Qwen/Qwen-Image)、[Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1)、[2.1 组件说明](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/qwen_image_2.1.md)、[Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)。

权重估算使用 `参数数 × 位数 ÷ 8`，仅为理想原始权重下界，GB 为十进制；量化元数据、未量化层、激活、注意力、VAE 和系统开销另外计算。分阶段卸载可降低同时驻留的内存，内存映射或磁盘换页不保证可接受的延迟。图像任务通常先输出进度 / 预览，再产出图片，不应承诺持续输出可读 token。

上游还出现 FLUX.3 Image Klein 等新分支；应按精确 checkpoint 建立配方，不能将前代的编码器、许可和设备结论自动继承给新模型。[FLUX.3 组件说明](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/flux3.md)

## 语音、音效与音乐

| 模型 / 能力 | 已核查的运行基础 | Z20 | 建议 |
| --- | --- | --- | --- |
| **MOSS-TTS-Nano 100M** | 官方 ONNX 与 Android 示例 | **A** | 优先 TTS / 后续克隆候选；示例只用预先分词的两个短提示，任意文本需要补 SentencePiece 等处理 |
| **Kokoro-82M** | 小型 TTS；sherpa-onnx 有 Android TTS 引擎 | **A** | 首批离线朗读；选定语言、音色与词典包后分别验收 |
| **Piper / VITS / Matcha** | sherpa-onnx 的离线 TTS 模型族及 Android 示例 | **A** | 可选中文 / 英文包；“运行器支持”不表示每个声音模型都同许可或同语言 |
| Qwen3-TTS 0.6B | 官方多语种、流式 TTS；需要专用音频 tokenizer / 解码路径 | **B** | 比较原生 / ONNX 适配，不能直接交给当前通用 llama-server |
| MOSS 完整系列 | 1.7B / 4B / 8B 等不同架构；官方另有部分架构的 llama.cpp fork + ONNX codec 路线 | **B / R** | 优先 Nano；完整系列需逐架构移植，不把桌面“8GB GPU 可运行”当手机结论 |
| SoulX-Podcast 1.7B | 官方播客 / 多说话人 TTS；参考安装是 Linux Python | **B / R** | 首批远程语音服务；部件存在 ONNX 不证明端到端 Android 已完成 |
| **YuE2-3B** | 歌词 / 风格到歌曲；官方参考配置为 BF16 NVIDIA 24GB GPU，并有音频 VAE | **R** | 远程音乐节点，不当作普通 TTS；当前权重非商业许可 |
| **Stable Audio Open Small 341M** | Arm 提供 LiteRT、C++ 与 Android 部署路线，短音频生成 | **B** | 本地音效实验，功能和长歌曲 YuE2 不同；Z20 速度未知 |

依据：[MOSS-TTS-Nano](https://github.com/OpenMOSS/MOSS-TTS-Nano)、[其 Android 示例的实际范围](https://github.com/OpenMOSS/MOSS-TTS-Nano/tree/main/examples/android_onnx_runtime)、[Kokoro](https://huggingface.co/hexgrad/Kokoro-82M)、[sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)、[Android TTS 示例](https://k2-fsa.github.io/sherpa/onnx/tts/apk-engine.html)、[Qwen3-TTS 0.6B](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)、[MOSS 系列与专用 llama.cpp 后端](https://github.com/OpenMOSS/MOSS-TTS)、[SoulX-Podcast](https://github.com/Soul-AILab/SoulX-Podcast)、[YuE2](https://huggingface.co/m-a-p/YuE2-3B)、[Arm 本地音频方案](https://developer.arm.com/code-along/stable-audio-open-small)、[Stable Audio 模型](https://huggingface.co/stabilityai/stable-audio-open-small)。

MOSS Nano Android 示例证明的是短提示的 ONNX 图执行与 WAV 输出。产品仍需完整文本前处理、tokenizer、匹配的 codec、分块输出、取消和播放缓冲，不能直接把示例描述为完整语音克隆 App。TTS 的长期输出以音频片段 / 秒数和首音延迟衡量；歌词到歌曲还应记录生成音频时长与实时率。

## 生视频

| 模型 / 版本 | 官方或运行器证据 | Z20 / 产品路径 |
| --- | --- | --- |
| Wan 2.1 T2V 1.3B | 官方参考需约 8.19GB GPU 显存；未优化的 RTX 4090 示例约 4 分钟生成 5 秒 480p | **R**；数字只对应该桌面配方，不是所有 Wan 的最低要求或手机速度 |
| Wan 2.2 TI2V 5B / A14B | 官方 5B 720p 的带卸载命令参考至少 24GB GPU；A14B 是另外的资源配置 | **R**；按任务、模型和分辨率选具体配方 |
| LTX-Video 2B 等旧版 | 有较小的蒸馏模型与 ComfyUI 路线 | **R**；低分辨率极短片可作移植研究，未找到足以承诺 Z20 生产可用的证据 |
| LTX-2.3 / 2.5 | 新一代音视频模型；sd.cpp 已有路线，2.5 还需专用 Gemma 4 12B 编码器、视 / 音频 VAE 等 | **R**；不能用旧 LTX-Video 2B 的预算代表 LTX 2.x |
| **MiniMax H3** | 已开放 H3-Base 权重，33B 主干含可预计算的约 13B AdaLN 分支，另有 Qwen3-VL-32B 编码器和两种 VAE；sd.cpp 有实现 | **R**；量化 / 预计算可降资源，仍不是 Z20 本地首批功能 |

依据：[Wan 2.1](https://github.com/Wan-Video/Wan2.1)、[Wan 2.2](https://github.com/Wan-Video/Wan2.2)、[旧 LTX-Video](https://github.com/Lightricks/LTX-Video)、[LTX-2.5 模型卡](https://huggingface.co/Lightricks/LTX-2.5)、[sd.cpp LTX 组件](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/ltx2.md)、[MiniMax H3 官方模型卡](https://huggingface.co/MiniMaxAI/MiniMax-H3)、[sd.cpp H3 组件](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/minimax_h3.md)。

H3 应区分开放的 Base 与完整托管系统：官方资料中的 Context-IR、2K 再生成能力并非本轮都已作为本地权重提供。不能宣传“下载 H3 即离线复刻全部官方 2K 服务”。视频推理还受时空激活、帧数、解码和编码成本影响；有 C++ 实现不等于已经验证 Android GPU 的全部算子。

## 业务使用与许可

以下是当前资料中的**选型信号**，上线仍按实际权重、适配器、词典和组件的固定版本条款处理；代码许可与模型许可分开。

| 具体来源 | 核查结果与业务影响 |
| --- | --- |
| [SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) / [SDXL base](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | 分别是 OpenRAIL-M / OpenRAIL++，不能标成“无条件 MIT 模型”；第三方 LoRA 另查 |
| [原版 Qwen-Image](https://huggingface.co/Qwen/Qwen-Image)、[Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)、[Sana 600M](https://huggingface.co/Efficient-Large-Model/Sana_600M_1024px_diffusers)、[FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) | 对应模型卡标注 Apache-2.0；不推及家族所有未来型号 |
| [Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1) | **Qwen Research License**，不能继承原版 Apache-2.0 的商业结论 |
| [MOSS Nano ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX)、[Nano codec](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX)、[Kokoro](https://huggingface.co/hexgrad/Kokoro-82M)、[Qwen3-TTS 此版本](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)、[SoulX 此版本](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B) | 模型卡标注 Apache-2.0；语音 / 参考素材本身的授权独立处理 |
| [YuE2-3B](https://huggingface.co/m-a-p/YuE2-3B) | **CC-BY-NC-4.0**；不能默认纳入商业歌曲服务；不要与旧 YuE 版本混为一谈 |
| [Stable Audio Open Small](https://huggingface.co/stabilityai/stable-audio-open-small) | Stability AI Community License，按具体商业条件选用 |
| [H3 License](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE) | 有地域和商业条件；年营收超过 2,000 万美元的商业产品 / 服务需要另行书面授权，并有界面署名条款；不是宽松开源许可 |
| [LTX-2.5](https://huggingface.co/Lightricks/LTX-2.5) | LTX-2.x Community License，涉及全实体年营收 1,000 万美元门槛和衍生物条款；与旧 LTX 版本分开 |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | 服务端 GPL-3.0；复用代码、分发组件和调用远程 API 是不同集成方式，应记录各自依赖 / 许可 |

“本地 / 远程”“可运行 / 实验 / 不兼容”“作者已声明无审查 / 仅元数据提示”和“商业许可”应当是独立属性。无审查标签不改变模型的硬件要求、许可或远端服务规则，也不自动赋给新模型。

## LMA 具体扩展顺序

| 阶段 | 工作与完成条件 |
| --- | --- |
| 1：共用基础 | 多组件模型包、独立 provider、每模型参数约束、持久化任务 / 产物；保留当前推荐及文本 API。规格见[工作流方案](WORKFLOWS.md) |
| 2：本地首批 | sherpa-onnx 的一个明确中文 / 英文 TTS 包；MOSS Nano 补齐 tokenizer 的端到端原型；SD 1.5 单图与兼容 LoRA。逐个记录模型哈希、峰值内存、延迟、发热、取消与锁屏行为 |
| 3：远程工作流 | 用户配置原生安装的 ComfyUI 或音频服务，按具体 workflow 暴露图像 / Wan / LTX / H3 / 音乐任务；先实现模板表单、任务列表、断网后对账和结果下载 |
| 4：进阶 | 节点画布、受控 ComfyUI 导入、新旗舰 GPU/NPU、Sana / Z-Image / 小 FLUX 的量化配方；没有端到端设备证据不进入“已验证可运行” |

阶段是建议执行顺序，不是已经交付的功能或工期承诺。任一端到端验收要覆盖：首次下载 / 续传 / 文件缺失、离线加载、超限自动归位、生成与取消、卸载释放、进程死亡恢复、锁屏持续运行与产物可打开；云端还需测重复提交、断网重连和取消归属。当前没有手机，不提供虚构的秒数、实时率或耐久结果。

本次仅新增研究与设计文档，**没有更改 APK、当前模型目录、界面或已有 Release 附件**；既有截图与 GIF 仍只演示 v0.2.0 的文本模型功能。
