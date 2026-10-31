# LMA · Android 本地模型工作台

[English](README.en.md) · [下载 v0.3.4](https://github.com/wikigsroom/LMA/releases/tag/v0.3.4) · [使用手册](docs/USER_GUIDE.md) · [文档目录](docs/README.md) · [更新记录](CHANGELOG.md)

LMA（Local Model App）让用户在 Android 手机上选择、下载、管理和运行本地模型，提供聊天、生图、生视频、生音频、任务队列、结果库与本机 API。它是独立社区项目，与 LM Studio 无隶属关系；当前应用界面主要为中文，文档提供中英双语。

**App 更新提供基座，模型由用户自行选择。** APK 不附模型权重，安装、升级和浏览目录不触发模型下载。所有推理、编码、解码与媒体合成都在同一手机完成，无需 ROOT、Termux、Docker、WSL、虚拟机、其他计算设备或云推理。

**当前 APK：v0.3.4 / versionCode 54 / ARM64 / Android 9+。** 原有 F-01–F-12、生文、01–14／16／17 与 44 个社区配方保留；新增语音 / 单图 3D 11 包及四视图 3D 4 包，共 **82 套模型包**。按用户要求仅做程序验证，检查不能证明努比亚 Z20 上的速度、质量或后台耐久。

**本页已恢复详细使用场景、调用示例、历史生成案例、失败记录和测试入口。** 当前生产页面、桌面历史模型输出与实际 Android 验收分别标注；历史图片或音频不作为 v0.3.4 的模型实跑结果。[本次文档修复说明](docs/releases/v0.3.1-readme.md)

<a id="contents"></a>
## 阅读路线

| 想做什么 | 本页入口 | 详细文档 |
| --- | --- | --- |
| 安装、下载和第一次使用 | [安装](#install)、[C01–C05](#use-cases) | [使用手册](docs/USER_GUIDE.md)、[HF 与本地模型](docs/HF_MODELS.md) |
| 选择生图、生视频或生音频方案 | [支持范围](#models)、[C06–C14](#use-cases) | [完整实现矩阵](docs/IMPLEMENTATION_V034.md)、[社区模型](docs/COMMUNITY_MODELS.md) |
| 管理模型、独立参数、任务和结果 | [C03–C04、C15–C18](#use-cases) | [模型参数](docs/MODEL_SETTINGS.md)、[任务工作台](docs/TASK_WORKBENCH.md) |
| 在程序中调用手机模型 | [API 示例](#api-examples) | [API](docs/API.md)、[输入与上传](docs/LOCAL_INPUTS.md) |
| 看页面、生成案例和失败对照 | [当前页面](#ui-media)、[历史案例 H01–H18](#case-studies) | [媒体说明](docs/MEDIA.md)、[历史完整 README](docs/history/README-dev45.zh.md) |
| 查证测试范围、重建和排错 | [程序检查](#verification)、[构建](#build)、[排错](#troubleshooting) | [程序验证策略](docs/PROGRAM_VALIDATION.md)、[构建指南](docs/BUILD.md) |

<a id="models"></a>
## 模型范围与选择逻辑

所有模型平级。**生文／生图／生视频／生音频／生 3D**、能力、引擎、格式、组件、后端、许可、内容标记和安装状态是独立维度。HF 全格式发现不等于所有格式可运行；架构、配套组件与手机资源都必须满足所选路线。

| 编号 | 模型／方案 | 本机程序路线与边界 |
| --- | --- | --- |
| 既有 | 文本 GGUF | llama.cpp；聊天、SSE、逐模型上下文和输出约束 |
| 01、02、05 | SD 1.5、SDXL、两者 LoRA | sd.cpp；基础模型与 LoRA 独立管理，检查架构配对 |
| 03 | SD-Turbo、LCM checkpoint、LCM-LoRA | 独立采样配置；需要时显式本地准备与关联 |
| 04 | Sana-Sprint 0.6B、独立 Sana Edit | MNN；各自匹配编码器、转换图和采样规则，不混用变体 |
| 06–08 | Z-Image-Turbo、FLUX.2-klein-4B、Qwen-Image-2.1 | sd.cpp 多组件路线；编码器、VAE、分词资源分别管理 |
| 09 | MOSS-TTS-Nano 100M | ORT、分词与音频 codec 均在手机执行 |
| 10 | Kokoro-82M／Piper／Matcha | sherpa-onnx；54 个 Kokoro 音色、固定 Piper Lessac／Matcha LJSpeech 方案 |
| 11 | Qwen3-TTS 0.6B Base | 原生 GGML、参考音频与本机 codec |
| 12 | MOSS 九个冻结子目标 | TTS 1.0／1.5、Local 原版／1.5、TTSD、VoiceGenerator、SoundEffect 原版／v2、Realtime；OpenMOSS、delay 或 RQ 适配 |
| 13、14 | SoulX-Podcast 1.7B、Stable Audio Open Small | 本机语言、声学、codec 与音频采样路线 |
| 16 | Wan 2.1 T2V 1.3B Q4 | sd.cpp CPU／Vulkan、显式组件、本机视频编码 |
| 17 | LTX-Video 2B 0.9.8 distilled | 原始 PixArt T5 F32＋7 步／空间放大／3 步；Google T5 Q5 单尺度保留独立身份 |

当前基座有 **48 个数据型配方模板、16 类扩展引擎及原有文本引擎**；模型包为 **23 套原有＋44 套社区＋11 套语音 / 单图 3D＋4 套 MV 校验导入＝82 套**。模板、模型包、引擎和架构分别计数，不代表全部模型已在手机实测。[机器可读实现矩阵](catalogue/release-0.3.4-implementation.json)

### 语音、单图与多视图生 3D

| 编号 | 选择 | 当前接入与边界 |
| --- | --- | --- |
| S01 | Kokoro PyTorch 系列 | 新增匹配 INT8 ONNX 英文方案；原始 `.pth` 不直接执行，既有 54 音色保留 |
| S02 | MeloTTS Chinese | 中文 ONNX INT8 / FP32、phones / tones 词典与四份 FST |
| S03 | F5-TTS v1 | 原版 safetensors＋Vocos，本机 C++；参考 WAV / 文本必填，中文前端实验适配 |
| S04 | OmniVoice | Q8 GGUF / 原版两种选择，本机 C++；自动 / 克隆 / 描述音色，完整 WAV |
| D01–D02 | TRELLIS.2 / Pixal3D | 五个单图 GGUF / CPU 几何或贴图选择，本地图片 → GLB → 预览 / 导出 |

已检查指定 [3080 生 3D 测评](https://benchmark.sidcloud.cn/collections/3080-3d)的 **16 条配置**：12 条新轮次＋4 条旧轮次。本版接入两种单图架构子集及真正的 Pixal3D MV 四视图路线；另有匹配 ONNX 导出的 TripoSG / PartCrafter 形状子集；其余 7 条配置 / 6 组家族仍缺原生移植，不能以目录登记或补测冒充支持。最小 Melo 包约 61 MB，Pixal3D 贴图包约 13 GB，不能统称轻量或承诺 Z20 可运行。

[四类语音、11 套文件与许可、D01–D16 完整评估、操作 / API / 测试 / 截图](docs/SPEECH_3D_EXPANSION.md) · [来源审计](research/expansion/benchmark-audit.json)。下载由用户选择，新增模型没有推断 NSFW 标签。

### 新增多视图与可导出诊断

Pixal3D MV 新增 F16 / Q8_0 的几何 / PBR 四个选择，四张已标定的 RGBA PNG → 同一本机 CPU 多视图融合 → GLB。**当前仅提供精确哈希校验导入，尚无已核实的公开权重下载端点**；已有匹配文件可导入，其他 HF 来源可使用自选 MV 配方。不能用单图 flow 代替，也不自动下载组件。

新增阶段耗时与支持 worker 的进程峰值 RSS；任务失败后保留已收到的观察，后续测量不会抹掉后端身份。服务页显示省电、待机、后台与通知限制；主动导出的诊断对象使用字段白名单，不含提示词、参数、路径或密钥。它不表示已经验证模型质量或锁屏耐久。

[四视图、相机约定、导入、API、诊断、63 项专项与剩余移植工作](docs/MULTIVIEW_DIAGNOSTICS.md) · [本次固定源码审计](research/portability/audit-v0.3.4.json)

### 新增 RF 形状与部件几何

TripoSG / PartCrafter 物体 / PartCrafter 场景新增三个平级自选配方，通过配套 FP32 ONNX 在手机 CPU 执行图片编码、RF / 部件 DiT、SDF VAE 与网格导出。输出无贴图 GLB，部件独立节点。**当前只支持用户匹配导出后导入；没有已核实公开整套下载包，不直接执行原始 PyTorch。** 82 个目录包数量保留，模板增加到 48；用户资产不随 App 更新自动取得。

[转换、导入、参数、原生实现、API 与限制](docs/RF_SHAPE.md) · [本轮编号实现与待办](docs/IMPLEMENTATION_V034.md)。完整训练权重转换、手机内存 / 速度 / 质量未测；自动抠图、VLM 部件识别和贴图没有实现。其余未移植测评为 D04–D10，详见[当前审计](research/portability/audit-v0.3.4.json)。

### 社区生图／生视频与内容标签

v0.3.1 的 44 个可选 checkpoint 覆盖 14 个系列：**30 个生图、14 个生视频**。其中 **28 个有 NSFW 来源标记**（生图、视频各 14 个），1 个只有 HF 敏感标记，15 个没有充分内容声明。视频条目是同一 **NSFW Wan 1.3B 的 EXP E01–E14**，不是 14 种视频架构；作者建议 E14，LMA 未据此承诺效果。

| 显示依据 | 如何理解 |
| --- | --- |
| 来源声明／文件标记 | 发布者模型卡或精确文件名明确标记；不等于独立效果测试 |
| 分级词表 | 作者提供相应分级词项；与全部输出内容的保证不同 |
| 镜像声明 | 标注镜像身份、原作者和许可冲突；Pony 镜像尤其需要核对修改版条款 |
| HF 标签／名称提示 | 未逐个核对的发现线索；不冒充作者声明 |
| 敏感／内容未标注 | 不把“不适合所有受众”直接当作 NSFW 能力，也不推断未标注模型只能生成一般内容 |

Uncensored／Abliterated 与 NSFW 分别标注，不互相替代。作者声明不代表 LMA 已测拒答率。完整 44 个文件、来源、固定 revision、许可、组件与兼容边界见[社区模型指南](docs/COMMUNITY_MODELS.md)，既有文本标签依据见[作者声明核对](docs/UNCENSORED_MODELS.md)。

### 既有精选文本候选

下表是保留的精选目录，不限制用户通过 HF 搜索其他本地模型；下载体积不等于运行内存。精确文件身份以[固定清单](catalogue/verified-models.json)和 App 详情为准。

| ID | 候选 | 参考下载体积 | 用途提示 |
| --- | --- | ---: | --- |
| `m08` | Qwen 3 · 1.7B Abliterated | 1.11 GB | 中文推荐候选 |
| `m06` | LFM 2.5 · 1.2B Uncensored | 731 MB | 轻量推荐候选 |
| `m01` | Dolphin 3 · Qwen 0.5B Uncensored | 398 MB | 最小起步候选 |
| `m04` | Dolphin 3 · Llama 1B Uncensored | 808 MB | 轻量、英文 |
| `m05` | Gemma 3 · 1B Abliterated | 806 MB | 轻量、多语言 |
| `m10` | LFM 2.5 · 2.6B Uncensored | 1.67 GB | 进阶、思考模型 |
| `m11` | Dolphin 3 · Qwen 3B Uncensored | 1.93 GB | 进阶、中文 |
| `m12` | Dolphin 3 · Llama 3B Uncensored | 2.02 GB | 进阶、英文 |
| `m13` | Llama 3.2 · 3B Uncensored | 2.24 GB | 进阶、英文 |
| `m14` | Qwen 3 · 4B Instruct 2507 Abliterated | 2.50 GB | 进阶、中文 |
| `m16` | Gemma 3 · 4B Abliterated v2 | 2.49 GB | 进阶、多语言 |
| `m03` | Qwen 3.5 · 0.8B Abliterated | 528 MB | 新架构、实验候选 |
| `m09` | Qwen 3.5 · 2B Abliterated | 1.27 GB | 新架构、实验候选 |
| `m15` | Qwen 3.5 · 4B Uncensored · HauhauCS Aggressive | 2.71 GB | 新架构、实验候选 |

**推荐顺序固定为 `m08 → m06 → m01`，原有标签与来源依据保留。** HF 下载和自定义导入不会自动进入推荐，也不会因文件名含 uncensored 而变成已核对条目。

<a id="install"></a>
## 安装与首次启动

1. 从 [v0.3.4 Release](https://github.com/wikigsroom/LMA/releases/tag/v0.3.4) 下载 `LMA-0.3.4-arm64-v8a.apk`；需要 64 位 Android 9／API 28 或以上。
2. 对照同页 `SHA256SUMS` 核对安装包。Windows 示例：

   ```powershell
   Get-FileHash .\LMA-0.3.4-arm64-v8a.apk -Algorithm SHA256
   ```

3. 打开 App，按系统提示允许通知。若要退出界面或锁屏继续工作，在 Android 设置中允许后台活动并取消相关电池限制。
4. App 初次启动可零模型使用管理界面和接口；选择、下载、导入或加载模型都是独立操作。
5. 保持原签名升级安装，已有模型与设置继续保留。自行签名的 APK 不能直接覆盖另一签名的安装。

| 安装包身份 | v0.3.4 |
| --- | --- |
| 字节数 | `67424948` |
| SHA256 | `fdf2fbd72e7bf12d1f6eb4f7de71b566d1250489e5ab990c7b365c36c9cbc522` |
| 签名证书 SHA256 | `90444a717a55549e2094364d8d7d005cf8b7f4df24562da62cc1884a2f341c17` |

Release 附 APK、源码 ZIP、验证 ZIP、截图 ZIP、GIF／MP4、构建与源码清单、说明和哈希，共 22 项附件。[版本说明](docs/releases/v0.3.4.md)

<a id="use-cases"></a>
## 27 个完整使用场景

以下是操作用例及应有行为，不是新增的真机测试通过清单。当前程序检查与历史实测证据分别见下文。

### C01 · 零模型安装、启动与升级

- 打开 App，先查看“模型”“任务”“服务”和设置；不选择任何模型。
- 启动本机接口，读取健康状态；没有模型时不能产生模型输出，但管理和健康接口可使用。
- 从旧版升级后检查原文件、未完成下载和独立参数。浏览目录不创建下载任务、不替换已有权重。
- 对照：[资产控制约定](docs/ASSET_CONTROL_AUDIT.md)、[基座检查](verification/program/foundation.json)。

### C02 · 推荐、全部、HF 搜索与文件选择

- “推荐”保持 `m08 → m06 → m01`；在“全部”输入关键词、`owner/model` 或 HF 仓库链接。
- 使用排序、分页和格式筛选；选择“HF 全部格式”发现其他格式，再检查具体可用文件和架构。
- 打开量化文件详情，比较大小、固定版本与哈希后明确添加下载；任意 GGUF 或 safetensors 不能直接套用无关引擎。
- 对照：[HF 与本地模型](docs/HF_MODELS.md)、[HF 检查](verification/program/hub.json)。

### C03 · 本地下载、暂停、导入和删除

- 在“本地”搜索已下载／导入模型和未完成传输；暂停当前下载，再明确续传。
- 已有文件可通过系统文件选择器导入；导入校验与网络续传分别处理，不能用文件名代替完整身份。
- 多组件模型先展示整个下载计划；同一哈希可复用，删除一个包不会清掉仍被其他包或活动任务引用的文件。
- 对照：[模型传输](docs/MODEL_TRANSFERS.md)、[暂停检查](verification/program/bundle-pause.json)、[系统输入合约](verification/program/document-input.json)。

### C04 · 参数跟着模型走，超限自动归位

- 打开“本地 → 模型 → 设置”，在可编辑选择框中输入上下文、输出上限、线程、温度或该引擎专有参数。
- 例如为 A 保存上下文 2048，为 B 保存不同值；切换回 A 后仍读到 A 的配置。超出模型／配方／应用上限的输入回填有效边界。
- 文本输出与上下文联合约束；未知 GGUF 元数据使用明确兜底，不伪造模型最高值。任务临时参数不覆盖保存的默认值。
- 对照：[模型设置](docs/MODEL_SETTINGS.md)、[文本检查](verification/program/text.json)、[迁移检查](verification/program/migration.json)。

### C05 · 本地聊天与文本流式接口

- 完整安装并加载文本模型，在聊天中输入“用三句话解释本地模型”；观察生成、停止与错误提示。
- “服务”复制当前地址和密钥；先查 `/v1/models`，使用实际已加载模型 ID 调用聊天接口。
- SSE 按事件解析，不能把一次网络读取当作一个 token；断开、停止或达到上限后结束生成，不在空闲时自动无限输出。
- 对照：[API](docs/API.md)、[后端检查](verification/program/backend.json)、[调用示例](#api-examples)。

### C06 · SD 1.5／SDXL 文生图与 LoRA

- 选择基础模型及配套编码资源，完整取得后点击“使用”，输入“小花园中的木屋”等提示词。
- 如需风格适配，另选兼容的 SD1.5 或 SDXL LoRA，编辑强度；基础模型和 LoRA 都由用户单独管理。
- 预检拒绝架构错配、重复适配器或缺少依赖；任务冻结实际模型、适配器、强度与 seed，结果可回看来源。
- 对照：[生图选择](docs/CURATED_DIFFUSION.md)、[LoRA](docs/ADAPTERS.md)、[历史 H01–H03](#case-studies)。

### C07 · 社区 NSFW 模型筛选、来源核对与下载

- 在“模型 → 全部”组合选择“已登记”“生图／生视频”和 NSFW 内容筛选；也可通过 HF 搜索其他候选。
- 打开“来源、内容标记与兼容说明”，区分作者声明、词表、文件名、镜像和 HF 提示，核对许可及组件。
- 点击“查看并下载”并确认计划；切换到“本地”后仍保留内容标签和模型独立设置。
- 对照：[44 个完整配方与来源](docs/COMMUNITY_MODELS.md)、[社区检查](verification/program/community.json)。

### C08 · Sana-Sprint 文生图与 Sana Edit 图片转换

- 文生图选匹配的 **Sana-Sprint 0.6B MNN**，确认 14 个组件，使用该配方 1024²、1–4 步约束；资产约 6.29 GiB，不代表运行内存。
- 图片转换另选 **Sana Edit**：需要 15 个匹配组件、本地 PNG／JPEG、固定风格提示词与 512×512 输入路线。
- 不把 Edit 权重当成任意文生图模型；旧 13 组件灰图失败与后来匹配的流程分开记录。
- 对照：[Sprint](docs/SANA_SPRINT.md)、[Edit](docs/MNN_SANA_EDIT.md)、[历史 H04／H17](#case-studies)。

### C09 · Z-Image、FLUX.2-klein 与 Qwen-Image

- 选择对应多组件配方，核对主权重、文本编码器、VAE 和分词资源；不能混用同名文件。
- 在模型设置中编辑本引擎支持的步数、几何参数等，再输入提示词、预检和提交。
- 原始用户文件及 SHA 不改写；必要分词处理在内存完成。取消不发布半成品，重新运行创建新任务。
- 对照：[Z-Image](docs/ZIMAGE_TURBO.md)、[FLUX](docs/FLUX2_KLEIN.md)、[高级生图](docs/ADVANCED_DIFFUSION.md)。

### C10 · 轻量 TTS 与音色选择

- 在“全部 → 生音频”比较 MOSS Nano、Kokoro、Piper 和 Matcha，选择精确模型组合。
- Kokoro 使用本地音色名称选择框；不同模型的语言、音色和速度范围各自校验，不能把某个模型的选项复制成通用能力。
- 输入短文本，检查任务中冻结的音色和参数；结果按 WAV 预览／导出，模型删除与结果删除互相独立。
- 对照：[语音选择](docs/SPEECH_SELECTION.md)、[Nano](docs/MOSS_NANO_ENGINE.md)、[历史 H07–H08](#case-studies)。

### C11 · Qwen3-TTS、MOSS 与 SoulX 参考音频

- 只在所选架构支持时添加本地参考音频、对应原文或说话人槽位；使用有权使用的声音素材。
- Qwen3-TTS Base、MOSS 各子目标和 SoulX 的输入角色、codec 与时长预算不同，以各自表单为准。
- 若输出达到预算而未自然结束，结果和结束原因应如实显示；取消／恢复不能被写成自然完成或质量通过。
- 对照：[Qwen3-TTS](docs/QWEN_TTS_ENGINE.md)、[MOSS](docs/MOSS_TTS15.md)、[SoulX](docs/SOULX_ENGINE.md)。

### C12 · 音效与音频生成

- 按目标选择 MOSS SoundEffect 或 Stable Audio Open Small，而不是把任何 TTS 模型当成通用音乐模型。
- 检查提示词、采样与时长约束；固定长度内部计算不一定随较短输出请求等比例降成本。
- 用户明确取得所需组件后，文本编码、扩散、codec／解码都在手机执行；缺组件在本机失败。
- 对照：[Stable Audio](docs/STABLE_AUDIO_ENGINE.md)、[MOSS OpenMOSS](docs/OPENMOSS_ENGINE.md)、[RQ](docs/MOSS_RQ_ENGINE.md)。

### C13 · Wan 本地文生视频

- 选择 **Wan 2.1 T2V 1.3B** 或匹配的社区 EXP 变体，核对文本编码器、VAE、分词资源与扩散权重。
- 在模型设置中保存分辨率、帧数、步数和解码分块等；先检查资源，再提交视频任务。
- 进度分别记录编码、采样、解码与本机 MP4 合成；历史末帧伪影仍公开保留，不以改分块参数宣称修复。
- 1.3B 配方不支持直接替换为 Wan 14B／I2V、Wan 2.2 或视频 LoRA。[方案](docs/WAN_VIDEO.md) · [解码诊断](docs/WAN_DECODER.md)

### C14 · 旧 LTX 的精确变体与本地准备

- 原始 **LTX-Video 0.9.8 distilled 多尺度**使用 PixArt F32 T5、原始分词与 7 步→空间放大／AdaIN→3 步路线。
- 旧 Google T5 Q5 单尺度为独立变体，不能用它冒充原始多尺度；LTX 2.x／2.3 也不能套用旧适配器。
- 需要时先显式准备用户已有文件，再确认关联运行包；APK 不含学习张量或模型专用词表。
- 原始 T5 两分片约 17.74 GiB，完整运行资产约 23.86 GiB，不适合作为 Z20 可运行承诺。[完整路线](docs/LTX_MULTISCALE.md) · [准备](docs/MODEL_PREPARATION.md) · [关联](docs/MODEL_ASSEMBLY.md)

### C15 · 草稿、预检、共用队列与取消

- 先保存草稿，选择已安装模型和明确输入；预检显示缺失资产、有效参数和资源原因，不启动下载或推理。
- 提交后在“任务”查看阶段、进度与错误；默认单个大型任务占用推理资源，文本和多模态共用调度器。
- 取消排队／运行任务后检查引用释放；取消或失败不提交半成品。用户明确重试时创建新任务，旧记录保持不变。
- 对照：[工作台](docs/TASK_WORKBENCH.md)、[预检](docs/TASK_PREFLIGHT.md)、[调度](docs/SCHEDULING.md)。

### C16 · 中断恢复、结果来源与导出

- 重新打开 App 后查看中断状态与已提交结果；只有存在真实 checkpoint 才能续步，否则需要明确重试。
- 从结果恢复新请求，检查模型身份、有效参数、seed 和输入哈希；预览／导出期间保护正在读取的资产。
- 清理历史和结果前查看容量与确认；删除模型不自动删除已生成结果或静默重新取得同名权重。
- 对照：[恢复](docs/TASK_RECOVERY.md)、[本地输入](docs/LOCAL_INPUTS.md)、[恢复检查](verification/program/recovery.json)。

### C17 · 退出页面、锁屏与本机接口

- 通过可见前台服务、通知和按需唤醒锁维持正在进行的请求；从通知停止服务可终止工作。
- 按需允许系统后台活动。强制停止、重启限制、厂商省电、发热和内存压力仍会中断，不能保证永久存活。
- 开机恢复是用户可选项，仅恢复原先启用且文件仍在的模型；首次资产选择、系统授权和下载不能静默跳过。
- 对照：[使用手册](docs/USER_GUIDE.md)、[架构](docs/ARCHITECTURE.md)、[后台边界](#z20)。

### C18 · 独立模型更新与 HF 自选配方

- 查看模型新版本的固定 revision、文件差异和新增下载量；确认后生成独立更新计划，不改写旧版身份。
- 对支持的 HF 架构，可逐项选择主权重与配套组件、审阅建议，再登记自选配方；建议不表示已安装。
- 切换当前版本与下载是独立动作；旧任务仍引用旧身份，删除受引用保护。自选配方不冒充已核对候选。
- 对照：[模型更新](docs/MODEL_UPDATES.md)、[HF 配方](docs/HF_RECIPES.md)、[配套建议](docs/COMPONENT_SUGGESTIONS.md)。

### C19 · 中文 MeloTTS 与 Kokoro INT8

- 在“全部”搜索 MeloTTS Chinese，选择 INT8 或 FP32，核对主模型、tokens、声调词典与四份 FST 后主动下载。
- 在“本地”编辑语速、停顿、线程和时长保护，只影响此模型。Kokoro INT8 复用既有音色选择，当前包限英文前端。
- 输入文本、预检并提交；成功后试听 / 导出 WAV。[格式、许可与步骤](docs/SPEECH_3D_EXPANSION.md)

### C20 · F5-TTS v1 参考音色

- 下载原版 v1、Vocos 与词表；中文还需所列拼音字典，App 不内置这些资源。
- 导入 24 kHz 单声道、1–12 秒 WAV，填写准确参考文本和新朗读文本，编辑本模型的步数与时长保护后提交。
- 缺发音明确报错；中文分词 / 变调未验证与官方 Python 完全一致。[输入与边界](docs/SPEECH_3D_EXPANSION.md#12-输入前端与许可)

### C21 · OmniVoice 资产与音色模式

- 选择 Q8 集成 GGUF，或原版模型＋分词器 / codec，组件身份独立。
- 在此模型设置选择 auto / clone / design，编辑语言、描述和目标时长；时长随保护上限归位。
- clone 提供匹配 WAV / 文本；design 填写音色描述。本版返回完整 WAV。[完整操作](docs/SPEECH_3D_EXPANSION.md)

### C22 · 单图生 GLB、预览与再次生成

- 在“本地 → 生 3D”选择 TRELLIS.2 或 Pixal3D，导入单张 PNG / JPEG，编辑分辨率、步数、面数与贴图。
- 保存设置或草稿，预检后主动入队。512 Pixal 自动关闭贴图；缺高分辨率 / 纹理组件会报错，不补下载。
- 拖动旋转、缩放，导出 GLB 与生成记录，或恢复输入后重新提交。演示立方体是合成程序夹具。[操作与 16 项评估](docs/SPEECH_3D_EXPANSION.md)

<a id="foundation"></a>
### C23 · 四张标定视图生成 3D

- 选择 MV 的四个校验导入方案之一，检查并导入全部匹配组件；没有核实下载端点时不能点击一键下载。
- 在“本地 → 使用”分别选择正面 / 右侧 / 背面 / 左侧 RGBA PNG，确认标准转台或填写真实相机参数；编辑独立设置后预检、保存草稿或明确入队。
- 结果沿用 GLB 预览 / 导出；取消和失败清理私有侧文件。四次单图任务不等于多视图融合。
- 对照：[多视图完整方案](docs/MULTIVIEW_DIAGNOSTICS.md)、[原生专项](verification/program/multiview.json)。

### C24 · 观察后台限制与导出诊断

- 在“服务”查看当前省电、待机、后台活动和通知状态；状态不代表已完成锁屏耐久测试。
- 主动导出日志时，新增最近 64 条任务的诊断对象。支持的 worker 记录阶段耗时 / 进程 RSS，失败后已收到的信息仍持久化。
- 诊断字段白名单不含提示词 / 参数 / 路径 / 密钥；原有日志仍需自行脱敏，不会自动上传。
- 对照：[观察范围与隐私](docs/MULTIVIEW_DIAGNOSTICS.md#5-观察与诊断)、[程序检查](verification/program/expansion.json)。

### C25 · 选择本地形状模型并离线转换导入

- 自行选择 TripoSG / PartCrafter safetensors 快照，用 `tools/export_shape.py` 离线生成四张 FP32 ONNX、data、配置及带真实哈希的清单；转换不是远程推理服务。
- 将结果复制手机，明确导入清单及对应组件；缺 data 或不匹配配置不算安装完成。不提供猜测的下载地址，也不随更新下载权重。
- [完整转换与导入步骤](docs/RF_SHAPE.md#3-离线转换)。本轮只用随机小网络验证，未执行完整权重转换。

### C26 · 按模型设置部件数量并生成 GLB

- 在“本地 → 使用”选择 PartCrafter 物体 / 场景的对应导出，指定一张白底或已去背景 PNG；设置 1–16 部件、512 对齐的 tokens 和 16 对齐的 grid。
- 超限归位且设置只跟随该模型；预检不执行推理，草稿恢复后需重新选择是否尝试未测配方。TripoSG 独立保持单物体。
- 输出在一个 GLB 中保留独立 mesh / node，可预览、导出或重新请求。[程序页面演示](docs/media/development/shape/shape-ui.gif)明确为夹具，不是训练模型输出。

### C27 · 排查形状导出、曲面与资源失败

- 按清单核对同一来源的 config / image_encoder / flow / cache / query / data；原始 safetensors、FP16、其他架构图不能只改后缀使用。
- 空曲面、三角面保护超限、图片不合规或内存不足时本机报错；可明确降低参数后重新提交，不发布部分结果、不外转推理。
- [161 项专项](verification/program/shape.json)覆盖随机小图对照与 30 次实际 native 进程；不代表 Z20 内存 / 速度 / 模型质量通过。

## 基座如何工作

模型／组件／配方描述固定 revision、文件路径、大小、SHA256、能力和依赖。版本化内部引擎适配器负责加载、阶段进度、取消、错误和卸载；新增同架构变体复用描述与调度，新架构需要实际适配，不能靠目录登记冒充可运行。

| 环节 | 共用行为 |
| --- | --- |
| 取得资产 | 明确下载／导入；暂停／续传、原子安装、共享哈希、使用引用与删除保护 |
| 准备与关联 | 由 APK 内置受控程序转换用户已有资产，再明确关联；不执行下载的程序或任意用户脚本 |
| 参数与输入 | 每模型 schema、可编辑预设、超限归位；本地素材与分块上传均鉴权并固定身份 |
| 执行 | 同一手机、共用资源准入和持久队列；任务冻结模型、参数、适配器与输入 |
| 提交结果 | 暂存→校验→原子提交；保存来源，取消／失败不发布半成品 |
| 恢复与清理 | 对账已有结果、显式重试、引用保护、容量确认；不假装无 checkpoint 续步 |
| 接口与界面 | 共用生产校验器、任务存储和调度，不因入口不同绕过约束 |

不构建 ComfyUI 连线、无限画布、公共用户节点、插件市场或图导入。内部版本化引擎不是用户插件体系。[架构](docs/ARCHITECTURE.md) · [基座需求](docs/FOUNDATION.md) · [完整冻结计划](docs/MULTIMODAL_RELEASE_PLAN.md)

<a id="api-examples"></a>
## 本机 API：可复制的调用示例

默认服务为 `http://127.0.0.1:8080`，模型接口位于 `/v1`；所有公开接口包括 `/health`、事件和产物读取都需要 Bearer 密钥。App“服务”页提供当前密钥与连接示例，勿把真实密钥放进截图或提交。

以下 PowerShell 例子面向**已连接手机的客户端**。可选 USB ADB 转发只转发请求，推理仍在手机；它不是 App 用户的必装条件，也不是本项目的真机测试记录。手机上的 HTTP 客户端直接使用 `127.0.0.1:8080`。若主动开启 LAN，可改为手机地址，计算位置不变。

### A01 · 零模型健康检查和已安装模型列表

```powershell
# 可选：已连接、已授权 USB 调试的手机
adb forward tcp:18080 tcp:8080
$lmaBase = 'http://127.0.0.1:18080'
# 先在当前终端设置 LMA_API_KEY 为“服务”页的密钥
$lmaHeaders = @{ Authorization = "Bearer $env:LMA_API_KEY" }
Invoke-RestMethod "$lmaBase/health" -Headers $lmaHeaders
$lmaModels = Invoke-RestMethod "$lmaBase/v1/models" -Headers $lmaHeaders
$lmaModels.data | Select-Object id, loaded, task_tags
```

列表只包含用户已安装模型；目录不等于安装，安装不等于加载或手机验收。`/v1/engines` 可查看实际注册引擎。

### A02 · 已加载文本模型的非流式对话

```powershell
$lmaTextModel = $lmaModels.data | Where-Object { $_.loaded -eq $true -and $_.task_tags -contains 'text' } | Select-Object -First 1
if (-not $lmaTextModel) { throw '请先在 App 加载一个文本模型' }
$lmaChat = @{
    model = $lmaTextModel.id
    messages = @(@{ role = 'user'; content = '用三句话解释本地模型。' })
    max_tokens = 128
    stream = $false
} | ConvertTo-Json -Depth 8
Invoke-RestMethod "$lmaBase/v1/chat/completions" -Method Post -Headers $lmaHeaders `
    -ContentType 'application/json; charset=utf-8' -Body $lmaChat -TimeoutSec 300
```

外部客户端发送自己的消息和采样参数；LMA 不把 App 系统提示词强制注入外部请求。上下文和输出仍受所选模型的约束。切换模型后重新读取实际 ID，不从显示名称猜测。

### A03 · 流式对话的 Python 客户端

```python
import json, os, urllib.request

base = "http://127.0.0.1:18080"  # 上面的 USB 转发；手机本机为 :8080
headers = {"Authorization": "Bearer " + os.environ["LMA_API_KEY"]}
request = urllib.request.Request(base + "/v1/models", headers=headers)
with urllib.request.urlopen(request, timeout=30) as response:
    models = json.load(response)["data"]
model = next(item["id"] for item in models if item.get("loaded") is True and "text" in item.get("task_tags", []))
body = json.dumps({"model": model, "messages": [
    {"role": "user", "content": "Explain local models in three sentences."}
], "max_tokens": 128, "stream": True}).encode("utf-8")
request = urllib.request.Request(base + "/v1/chat/completions", body,
    {**headers, "Content-Type": "application/json"})
finished = False
with urllib.request.urlopen(request, timeout=300) as response:
    for raw in response:
        line = raw.decode("utf-8").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            finished = True
            break
        event = json.loads(payload)
        if "error" in event:
            raise RuntimeError(event["error"])
        for choice in event.get("choices", []):
            print(choice.get("delta", {}).get("content") or "", end="", flush=True)
if not finished:
    raise RuntimeError("Stream ended without [DONE]")
```

此例展示聊天 token 流；多模态任务事件采用不同结构。生产客户端还应处理重连、超时和不完整结束，不能把缺少结束标记的断线计为完整成功。[完整 API 与 SSE 说明](docs/API.md)

### A04 · 生图预检、持久入队、查询和取消

```powershell
# 从 /v1/models 复制一个已完整安装且支持 image.generate 的模型包 ID
$lmaBundleId = 'REPLACE_WITH_INSTALLED_BUNDLE_ID'
$lmaJob = @{
    bundleId = $lmaBundleId
    type = 'image.generate'
    input = @{ prompt = 'A small garden with a wooden house' }
    parameters = @{ seed = 123 }
    # 仅在用户明确同意尝试未测配方后设置；不会触发下载
    allowUnmeasured = $true
} | ConvertTo-Json -Depth 8
$lmaPreflight = Invoke-RestMethod "$lmaBase/v1/jobs/preflight" -Method Post `
    -Headers $lmaHeaders -ContentType 'application/json' -Body $lmaJob
$lmaPreflight
# 先审阅预检结果；仅在条件满足且用户确认执行后继续
$lmaJobHeaders = @{ Authorization = "Bearer $env:LMA_API_KEY"; 'Idempotency-Key' = 'garden-demo-001' }
$lmaAccepted = Invoke-RestMethod "$lmaBase/v1/jobs" -Method Post `
    -Headers $lmaJobHeaders -ContentType 'application/json' -Body $lmaJob
$lmaAccepted
```

提交返回 `202` 和任务标识只表示入队。按返回记录中的任务 ID 调用 `GET /v1/jobs/ID`；取消用 `POST /v1/jobs/ID/cancel`，明确重试用 `POST /v1/jobs/ID/retry`。同一幂等键＋相同请求复用原任务，改变请求产生冲突。事件连接断开不取消持久任务。

| 目标 | 接口 |
| --- | --- |
| 预检／提交／列表 | `POST /v1/jobs/preflight`、`POST /v1/jobs`、`GET /v1/jobs` |
| JSON 或 SSE 任务事件 | `GET /v1/jobs/ID/events`；SSE 发送 `Accept: text/event-stream` |
| 事件续读 | `after` 或 `Last-Event-ID`；过旧游标按 reset 重新读取任务快照 |
| 结果与原始字节 | `GET /v1/artifacts`、`GET /v1/artifacts/ID/content`；支持受控 Range |
| 媒体输入 | 显式本地导入／鉴权分块上传；角色必须由所选引擎声明 |

缺资产、缺引擎、资源不足或未授权尝试未测配方都在本机返回原因；接口不下载模型、不抓取远程素材、不转交外部推理。[预检](docs/TASK_PREFLIGHT.md) · [素材上传](docs/LOCAL_INPUTS.md) · [API 全部字段与限制](docs/API.md)

<a id="ui-media"></a>
## 当前页面、截图与录屏

以下五条为 **v0.3.4 生产页面＋明确标记的桌面交互夹具（UI FIXTURE）**，未下载权重、未产生模型输出，不是手机录像。社区流程 34 项、工作台 8 项、语音 / 3D 32 项、多视图 19 项、RF 形状 17 项交互；录制结束关闭全部测试浏览器资源。

![v0.3.4 社区筛选、来源与本地管理；UI FIXTURE](docs/media/development/community/community-ui.gif)

[社区 MP4](docs/media/development/community/community-ui.mp4) · [媒体与源码身份](docs/media/development/community/manifest.json)

| 生图目录与内容标签 | 来源、许可与组件 |
| --- | --- |
| ![当前生图目录，UI FIXTURE](docs/media/development/community/01-community-images.png) | ![当前来源详情，UI FIXTURE](docs/media/development/community/02-image-source.png) |

[视频目录](docs/media/development/community/03-community-video.png) · [视频来源与限制](docs/media/development/community/04-video-source.png) · [本地管理](docs/media/development/community/05-community-local.png)

![v0.3.4 共用工作台；UI FIXTURE，非模型推理](docs/media/development/release-workbench/release-workbench-ui.gif)

[工作台 MP4](docs/media/development/release-workbench/release-workbench-ui.mp4) · [工作台媒体身份](docs/media/development/release-workbench/manifest.json)

以下入口补回旧版演示的可发现性，**都是对应历史版本的界面夹具**：

| 场景 | 截图 | GIF／录屏 |
| --- | --- | --- |
| Sana-Sprint 组件、设置、提交和队列 | [14 组件](docs/media/development/sana/01-sana-components.png)、[独立参数](docs/media/development/sana/02-sana-settings.png) | [GIF](docs/media/development/sana/sana-ui.gif)／[MP4](docs/media/development/sana/sana-ui.mp4) |
| MOSS 组件、参数和输出上限 | [输出上限](docs/media/development/openmoss/05-output-limit.png) | [GIF](docs/media/development/openmoss/openmoss-ui.gif)／[MP4](docs/media/development/openmoss/openmoss-ui.mp4) |
| Wan 模型和参数 | [使用说明](docs/WAN_VIDEO.md) | [GIF](docs/media/development/wan/wan-ui.gif)／[MP4](docs/media/development/wan/wan-ui.mp4) |
| LTX 参数和视频队列 | [模型设置](docs/media/development/ltx/02-model-settings.png)、[队列](docs/media/development/ltx/04-video-queue.png) | [GIF](docs/media/development/ltx/ltx-ui.gif)／[MP4](docs/media/development/ltx/ltx-ui.mp4) |
| HF 配套文件确认 | [组件审阅](docs/media/development/components/02-companion-review.png)、[下载计划](docs/media/development/components/03-complete-download-plan.png) | [方案](docs/COMPONENT_SUGGESTIONS.md) |
| TTS 音色与 LoRA 配对 | [Kokoro 音色](docs/media/development/speech/02-kokoro-voices.png)、[基础模型依赖](docs/media/development/curated/01-dependency-review.png) | [配对任务](docs/media/development/curated/03-paired-task.png) |
| 运行资源与停止原因 | [资源](docs/media/development/resources/01-running.png)、[停止详情](docs/media/development/resources/02-stopped-detail.png) | [资源说明](docs/RUNTIME_RESOURCES.md) |
| 原始文本模型库、接口和深色主题 | [模型库](docs/media/01-library.png)、[接口](docs/media/05-api.png)、[深色](docs/media/07-dark.png) | [原始演示](docs/MEDIA.md) |

![v0.3.4 语音与单图生 3D；UI FIXTURE，合成立方体非模型输出](docs/media/development/expansion/expansion-ui.gif)

[语音选择](docs/media/development/expansion/01-speech-models.png) · [3D 表单](docs/media/development/expansion/03-3d-form.png) · [GLB 预览](docs/media/development/expansion/05-glb-preview.png) · [MP4](docs/media/development/expansion/expansion-ui.mp4) · [32 项页面检查](docs/media/development/expansion/manifest.json)

![v0.3.4 四视图与后台状态；UI FIXTURE，未运行训练模型](docs/media/development/multiview/multiview-ui.gif)

[四个导入选择](docs/media/development/multiview/01-multiview-models.png) · [四图表单](docs/media/development/multiview/03-four-view-form.png) · [后台观察](docs/media/development/multiview/05-background-observations.png) · [MP4](docs/media/development/multiview/multiview-ui.mp4) · [19 项页面检查](docs/media/development/multiview/manifest.json)


### RF 形状当前页面

![v0.3.4 部件设置；桌面 UI FIXTURE，非模型输出](docs/media/development/shape/03-part-settings.png)

![RF 形状流程；UI FIXTURE，无训练推理](docs/media/development/shape/shape-ui.gif)

[5 张截图 / 身份清单](docs/media/development/shape/manifest.json) · [MP4](docs/media/development/shape/shape-ui.mp4)。全部五组共 25 张截图 / 5 GIF / 5 MP4；旧版媒体和证据按原 Git 身份保留。

<a id="case-studies"></a>
## 历史案例测试与真实产物

这些是已保存的开发阶段案例，**本次文档修复没有重新下载、复制或运行完整模型**。HOST 表示原生 Windows 主机，UI FIXTURE 表示模拟桥接的页面，PROGRAM 表示程序或有界小图检查；都不能替代 Android 真机验收。旧文档中的“尚未发布”属于当时语境，当前安装包以上方 v0.3.4 为准。

| 编号 | 案例及输入／操作 | 当时观察与明确边界 | 原始说明／证据 |
| --- | --- | --- | --- |
| H01 | SD1.5：不同提示词 A／B／A、20 步采样中取消和恢复 | HOST：完整 PNG、恢复可复现；图片质量和手机性能不由哈希证明 | [实际权重与生产流程](docs/SD15_TRAINED.md) |
| H02 | SDXL、SD1.5／SDXL LoRA 强度 0／1、LCM-LoRA 组合 | HOST：基础／风格／反事实／取消恢复；低步数有主体不清问题，保留原图 | [变体验证与全部 PNG](docs/SD_VARIANTS_TRAINED.md) |
| H03 | SD-Turbo 与 LCM checkpoint 准备、完整 UNet 对照 | HOST：SD-Turbo 真实 PNG；LCM 候选诊断和错误门槛保留，不将候选称为全部通过 | [蒸馏与 LCM](docs/SD_DISTILLED_TRAINED.md)、[产品流程](docs/LCM_APP_FLOW.md) |
| H04 | Sana 原 13 组件文生图尝试→匹配 15 组件图片编辑 | HOST：旧灰图失败保留；后续必选本地图片、固定风格编辑有真实输出，不能混成同一能力 | [原失败](docs/MNN_SANA_TRAINED.md)、[图片编辑](docs/MNN_SANA_EDIT.md) |
| H05 | FLUX.2-klein：机器人与茶壶、帆船、步数变化／取消恢复 | HOST：真实 PNG；分词头导致的词项偏移已定位，151,643 基础词项等独立对照与完整模型质量分开 | [方案、原始报告与媒体](docs/FLUX2_KLEIN.md) |
| H06 | Z-Image：四组件、不同提示词与步数、生产 Java／原生取消恢复 | HOST：实际 PNG、来源和删除／重启检查；非 Android 性能结果 | [完整案例](docs/ZIMAGE_TURBO.md) |
| H07 | MOSS Nano：三语输出、错误控制及生产 Java→原生流程 | HOST：7 次 WAV 输出／7 个控制、40 项生产流程检查；音质与真机另验 | [Nano 实测与三语音频](docs/MOSS_NANO_TRAINED.md) |
| H08 | Kokoro／Piper／Matcha：音色、速度、导入、取消恢复 | HOST：68 次 WAV／13 个控制、157 项生产 Java 检查；不承诺所有文本和声音质量 | [TTS 实测与音频](docs/TTS_TRAINED.md) |
| H09 | Qwen3-TTS：十语言、参考输入、参数和取消恢复 | HOST：18 个成功 WAV／12 个控制、94 项 Java 检查；部分贪心短文本触及 30 秒预算，质量问题保留 | [Qwen3-TTS 实测](docs/QWEN_TTS_TRAINED.md) |
| H10 | MOSS-TTS 1.5：完整组合、真实进度、原生／Java 一致性 | HOST：dev.41 的 87 项／5 次运行；参考模式达到预算而未自然结束 | [1.5 案例与产物](docs/MOSS_TTS15.md) |
| H11 | MOSS 提示／排空／缓存修正与参考模式复核 | HOST：dev.43 Java 71 项／4 次运行；参考模式 375 步截断，识别 36／2 词错误仍是失败 | [修正与失败记录](docs/MOSS_DELAY_FIX.md) |
| H12 | SoulX：两／四说话人、参考原文、完整生产 worker | HOST：历史 95 项完整 worker 检查；合成参考 PCM 不等于真实人声音质或 Android 验收 | [SoulX 基座](docs/SOULX_ENGINE.md)、[语言链路](docs/SOULX_LANGUAGE.md) |
| H13 | Stable Audio：T5→DiT→解码和错误／取消 | PROGRAM：有界 LiteRT 小图与子进程；不是完整训练音频生成案例 | [音频引擎与范围](docs/STABLE_AUDIO_ENGINE.md) |
| H14 | Wan：完整视频、分块／时间解码、独立上游 VAE 对照 | HOST：末帧伪影未修复；同一 latent 在 C++／上游 CPU VAE 对照中复现，不能只展示首帧称成功 | [实际视频](docs/WAN_VIDEO.md)、[画质诊断](docs/WAN_DECODER.md) |
| H15 | 旧 LTX Google Q5 单尺度：真实提示词视频、生产 Java／原生路径 | HOST：有完整 MP4；严格浮点六项失败与画质问题保留，不是原始 PixArt 多尺度或手机证据 | [业务与产物](docs/LTX098_APP_FLOW.md)、[精度诊断](docs/LTX098_PRECISION.md) |
| H16 | 旧 LTX DiT／T5／VAE 分阶段独立对照 | HOST：组件级数值、取消与资源分别留证；组件通过不能关闭完整链路失败 | [DiT](docs/LTX098_DIT.md)、[采样](docs/LTX098_SAMPLING.md)、[T5](docs/LTX098_TEXT.md)、[VAE](docs/LTX098_VAE.md) |
| H17 | Sana-Sprint 与原始 PixArt 多尺度 LTX 后续接入 | PROGRAM：Sana 448 项；原始 LTX 路线以程序集成验收，无新增完整模型输出 | [Sana](docs/SANA_SPRINT.md)、[LTX](docs/LTX_MULTISCALE.md)、[v0.3.0](docs/releases/v0.3.0.md) |
| H18 | v0.3.1 社区内容来源、文件头、配方、下载与本地筛选 | PROGRAM／UI：814 项社区检查、564 项全页检查；不代表 44 个完整 checkpoint 实跑 | [来源清单](docs/COMMUNITY_MODELS.md)、[程序记录](verification/program/community.json) |

### 生图案例：实际主机结果

| FLUX：机器人与茶壶 | FLUX：帆船 |
| --- | --- |
| ![历史实际 CPU PNG；非手机录屏](docs/media/development/flux2-trained/01-robot.png) | ![历史实际 CPU PNG；非手机录屏](docs/media/development/flux2-trained/02-sailboat.png) |

[FLUX 原图、GIF、MP4 与来源](docs/FLUX2_KLEIN.md)；轮播不代表生成耗时。

![Z-Image 历史实际主机 PNG；未作为手机或画质验收通过](docs/media/development/zimage-trained/01-robot.png)

[Z-Image GIF](docs/media/development/zimage-trained/zimage-trained.gif) · [原始案例](docs/ZIMAGE_TURBO.md)

| Sana Edit：用户输入 | Sana Edit：实际主机输出 |
| --- | --- |
| ![NASA 公有领域输入；非生成图](docs/media/development/sana-edit-trained/source.png) | ![历史实际图片转换；非 Android 输出](docs/media/development/sana-edit-trained/01-a.png) |

输入为 NASA 公有领域样例，[素材来源](tests/fixtures/images/LICENSE.md)。这是固定图片编辑案例，不证明全面身份保持。[GIF](docs/media/development/sana-edit-trained/sana-host-outputs.gif) · [MP4](docs/media/development/sana-edit-trained/sana-host-outputs.mp4)

[SD1.5 原图联系表](docs/media/development/sd15-trained-contact-sheet.png) · [SD1.5 LoRA 对照](docs/media/development/sd-variants-sd15-contact-sheet.png) · [SDXL LoRA 对照](docs/media/development/sd-variants-sdxl-contact-sheet.png) · [实际 PNG 轮播 GIF](docs/media/development/sd-variants-trained-slideshow.gif) · [MP4](docs/media/development/sd-variants-trained-slideshow.mp4)

### 语音案例：原始 WAV、波形与失败样例

![MOSS dev.43 实际主机波形；参考模式截断失败保留](docs/media/development/openmoss-0.3.0-dev.43/openmoss-trained-waveforms.gif)

[英文 WAV](docs/media/development/openmoss-0.3.0-dev.43/openmoss-trained-en.wav) · [中文 WAV](docs/media/development/openmoss-0.3.0-dev.43/openmoss-trained-zh.wav) · [参考模式 WAV（失败保留）](docs/media/development/openmoss-0.3.0-dev.43/openmoss-trained-reference.wav) · [带实际音轨 MP4](docs/media/development/openmoss-0.3.0-dev.43/openmoss-trained-speech.mp4) · [媒体身份](docs/media/development/openmoss-0.3.0-dev.43/openmoss-trained-media.json)

[三套轻量 TTS 的 WAV 与波形](docs/TTS_TRAINED.md) · [MOSS Nano 三语音频](docs/MOSS_NANO_TRAINED.md) · [Qwen3-TTS 十语言／参考案例](docs/QWEN_TTS_TRAINED.md)。波形非空、哈希相同或输出时长都不等于语音质量通过。

### 视频案例：完整视频与未通过的画质

![Wan 历史实际主机视频；末帧伪影保留，非手机录像](docs/media/development/wan-trained/default.gif)

[完整 Wan MP4](docs/media/development/wan-trained/default.mp4) · [所有帧](docs/media/development/wan-trained/default-frames.png) · [独立 VAE 对照](docs/media/development/wan-quality/vae-comparison.png) · [失败画质 GIF](docs/media/development/wan-quality/legacy-default.gif)

![旧 LTX 生产主机链路第 0／16／32 帧；非 Android，质量未通过](docs/media/development/ltx-app-trained/frames.png)

[完整 LTX MP4](docs/media/development/ltx-app-trained/video.mp4) · [带 HOST 标签 GIF](docs/media/development/ltx-app-trained/preview.gif) · [媒体身份](docs/media/development/ltx-app-trained/manifest.json)

![旧 LTX 单尺度真实提示词帧对照；历史失败仍保留](docs/media/development/ltx098-host-contact-sheet.png)

[独立主机对照 MP4](docs/media/development/ltx098-host-comparison.mp4) · [GIF](docs/media/development/ltx098-host-comparison.gif) · [来源与时序](docs/media/development/ltx098-host-media.json)

![旧 LTX 文本精度诊断；隔离实验不是 App 质量通过](docs/media/development/ltx098-text-roundoff.png)

[精度诊断与完整失败边界](docs/LTX098_PRECISION.md)。以上原始媒体不重录、不改写为本版成功，也不将历史桌面 FFmpeg 编码当成 Android MediaCodec 验收。

<a id="verification"></a>
## 当前程序检查覆盖与复核入口

**v0.3.4 保留前版 26 组覆盖，新增 P27 RF Shape 专项，重跑受影响检查。** 当前 **27 组 / 5,306 项**。具体数量与源码指纹见[当前证据](verification/program/status.json)；完整模型、手机质量与耐久未测试。[验证策略](docs/PROGRAM_VALIDATION.md)

| 编号 | 套件／断言 | 覆盖的案例 | 记录 |
| --- | --- | --- | --- |
| P01 | community · 818 | 44 配方、内容依据、固定身份、独立参数与生产任务规划 | [JSON](verification/program/community.json) |
| P02 | foundation · 963 | 零模型启动、包管理、组件共享、下载／导入／删除与权限 | [JSON](verification/program/foundation.json) |
| P03 | backend · 138 | 文本引擎进程、代理、停止、错误与占用释放 | [JSON](verification/program/backend.json) |
| P04 | bundle-pause · 22 | 阻塞读取中暂停、关闭、后续队列释放 | [JSON](verification/program/bundle-pause.json) |
| P05 | document-input · 15 | 文档输入合约、取消、错误和资源关闭；不是手机 SAF 实跑 | [JSON](verification/program/document-input.json) |
| P06 | api · 68 | 实际本机 socket 的鉴权、路由、任务与结果保护 | [JSON](verification/program/api.json) |
| P07 | workbench · 44 | 草稿、表单、不可变任务、结果来源与重新请求 | [JSON](verification/program/workbench.json) |
| P08 | recovery · 47 | 中断对账、清理、持久状态、鉴权结果读取 | [JSON](verification/program/recovery.json) |
| P09 | inputs · 64 | 本地输入、上传、角色和完整性／引用保护 | [JSON](verification/program/inputs.json) |
| P10 | text · 66 | 文本包、逐模型默认值、上下文／输出限制 | [JSON](verification/program/text.json) |
| P11 | migration · 69 | 旧设置迁移、独立配置与原数据保留 | [JSON](verification/program/migration.json) |
| P12 | scheduler · 151 | 文本／多模态资源槽、排队、取消和释放 | [JSON](verification/program/scheduler.json) |
| P13 | preparations · 44 | 本地受控准备、取消、原文件与输出身份 | [JSON](verification/program/preparations.json) |
| P14 | assemblies · 47 | 显式关联、缺组件提示、引用与独立删除 | [JSON](verification/program/assemblies.json) |
| P15 | diffusion · 197 | 扩散任务参数、SD／SDXL／LoRA 配对与执行合约 | [JSON](verification/program/diffusion.json) |
| P16 | mnn · 101 | MNN 配方、输入约束、阶段协议和结果校验 | [JSON](verification/program/mnn.json) |
| P17 | hub · 80 | HF 搜索／仓库解析、分页、文件选择及格式边界 | [JSON](verification/program/hub.json) |
| P18 | recipe-suggestions · 73 | 配套组件建议、人工确认和精确下载计划 | [JSON](verification/program/recipe-suggestions.json) |
| P19 | speech-voices · 70 | 54 个 Kokoro 音色、模型专属参数和非法选择 | [JSON](verification/program/speech-voices.json) |
| P20 | sana-sprint · 448 | 分词、采样数学、有界小图和匹配 Sprint 路线 | [JSON](verification/program/sana-sprint.json) |
| P21 | ui · 633 | 生产页面、模型管理、组合筛选、设置、队列和结果 | [JSON](verification/program/ui.json) |
| P22 | ltx-official · 89 | 官方身份、原始 T5／分词与多尺度配置合约 | [JSON](verification/program/ltx-official.json) |
| P23 | ltx-multiscale-app · 280 | 原始 PixArt 多尺度编排、有界阶段、取消与产物提交 | [JSON](verification/program/ltx-multiscale-app.json) |
| P24 | ltx-single-scale-app · 127 | 独立单尺度路线、输入／参数／进程和取消恢复 | [JSON](verification/program/ltx-single-scale-app.json) |
| P25 | expansion · 428 | 语音 / 单图 / MV 合约、真实主机子进程夹具、GLB、清理、诊断合并持久化与微型 F5 前端 | [JSON](verification/program/expansion.json) |
| P26 | multiview · 63 | 上游真实相机 / 投影、12 个 native 进程拒绝路径与运行观察 | [JSON](verification/program/multiview.json) |
| P27 | shape · 161 | 固定源码随机小图 / RF 数学 / PNG 对照，30 次实际 native 形状流程与拒绝路径 | [JSON](verification/program/shape.json) |

另外核对 ARM64／API28、39 个原生库及依赖、16 KiB ELF／ZIP 对齐、原签名与 APK 身份；Android Lint **0 错误／16 个原有警告**。当前 25 张截图、5 GIF、5 MP4 来自五条明确标记的桌面页面流程，不是模型生视频产物。

v0.3.0 的 29 个程序文件与旧媒体[按原 Git 身份归档](verification/history/v0.3.0-program-archive.json)；更早模型失败和程序记录仍保留。`release_ready` 表示符合程序发行策略，不表示所有手机／权重／质量通过。

<a id="z20"></a>
## 努比亚 Z20 与后台运行边界

文本基线为 ARMv8 CPU，起步可用 **4 线程／2048 上下文／512 输出 tokens**，可切换的思考模式默认关闭。先用 `m01` 小模型核对自己的使用流程，再按实际资源比较 `m08`、`m06`；3B–4B 和多模态资产需要更多存储与运行内存。这是配置起点，不是手机测速结论。

当前没有可用 Z20 真机，**没有测得本机 tokens/s、峰值内存、温度或锁屏持续时长**。文件体积、参数量、头部检查、主机生成和 Android 编译都不能证明该手机能运行某个 checkpoint；大模型资源不足时本机给出原因，不转出手机执行。

“后台持续输出”指活跃请求生成期间仍可输出。EOS、输出上限、取消、系统强停、内存压力或错误都会结束请求；不是无人请求时无限生成，也不能绕过厂商省电策略。前台通知、停止入口和按需锁的实现与真实手机耐久验收分别记录。

<a id="build"></a>
## 原生 Windows 构建与开发复核

需要完整 Git 历史、JDK 21、Python 3、Android SDK Platform 35／Build Tools 35.0.1；原生引擎按锁定 NDK／CMake 构建。当前验证路径为 Windows 原生工具链，不使用 Docker、WSL、虚拟机或 Android 模拟器。Android Studio／Gradle 配置供开发参考，未将其说成已验证路径。

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
python tools/bootstrap_runtime.py
# 按 BUILD.md 取得／构建锁定的原生引擎；不是下载模型权重
python tools/build.py --sdk C:/path/to/Android/Sdk
python tools/verify_package.py
python tools/test_android_lint.py
```

已有完整原生缓存时无需重复获取；首次重建的多引擎命令、锁文件和注意事项见[构建指南](docs/BUILD.md)。源码 ZIP 不携带模型、签名、构建缓存或可重新获取的原生库；历史身份检查仍需要完整 Git 仓库，不能把 ZIP 当作已配置开发环境。

只运行与改动相关的程序检查；以下均为程序入口，不要求完整训练模型：

```powershell
python tools/test_backend.py
python tools/test_community.py
python tools/test_expansion.py
python tools/test_shape.py
python tools/test_text.py
python tools/test_scheduler.py
python tools/test_recovery.py
python tools/test_api.py
# 有 Node／Playwright／Edge 时运行，finally 关闭测试页面与浏览器
node tests/ui-smoke.cjs
# 核对现有记录及其源码指纹，不执行完整模型
python tools/program_evidence.py
```

发布前更新证据、打包和准备附件按[发布流程](docs/RELEASING.md)执行。**已发布版本后续仅修文档时，用 `python tools/check_repository.py --published` 核对当前链接与原标签源码包，不重写已发布附件。** 不运行历史指南中的完整模型、ASR 或长时耐久命令作为本次维护前置要求。

私钥与口令仅保存在本机忽略的 `signing/`，不要上传、打印或替换；升级应保留原签名。程序生成 `dist/` APK、SHA256 和构建记录，公开资料不包含权重或 API 密钥。

### 仓库地图

| 路径 | 内容 |
| --- | --- |
| `app/` | Android 应用、生产 Java 与离线页面资源 |
| `native/`、`third_party/` | 本地引擎集成、固定上游身份与许可说明 |
| `catalogue/` | 模型／组件／模板、内容依据和实现矩阵元数据 |
| `research/` | 可追溯来源与受控研究元数据，不是预装模型 |
| `tools/`、`tests/` | 原生构建、程序验证、界面及发布工具 |
| `verification/program/` | 当前程序证据；旧模型／版本记录另有历史目录 |
| `docs/media/` | 当前 UI 与明确分版的历史生成、录屏和来源清单 |
| `docs/releases/` | 版本说明、编号实现／待办和本次文档维护记录 |

<a id="troubleshooting"></a>
## 常见问题与排错

| 现象 | 检查与处理 |
| --- | --- |
| 安装失败／无法覆盖 | 是否 ARM64、Android 9+、空间足够、签名一致；不要先删除用户模型来解决签名冲突 |
| HF 搜索能看到，但无法运行 | 发现不等于适配；核对格式、精确架构、量化和全部依赖，不只看后缀 |
| 下载暂停或失败 | 在“本地”查看原因后明确续传；校验失败不能改名冒充成功，网络镜像与模型身份分开 |
| 修改上下文后自动变小 | 模型 metadata、输出联合限制或应用上限生效；在该模型设置中检查有效值 |
| 某模型没有负面提示词／音色／参考输入 | 表单按能力显示，不支持的输入不会静默当成有效参数 |
| 接口连接失败／401 | 接口是否启动、地址／端口／转发是否正确、当前 Bearer 密钥是否匹配 |
| 聊天流中断 | 检查 EOS／token 上限、取消、系统停止或引擎错误；不把部分流计为完整成功 |
| 任务一直等待或预检拒绝 | 查看当前资源槽、缺组件、参数与内存原因；不通过外部推理绕过 |
| 删除时提示正在使用 | 活动任务、共享模型或预览／导出仍持有引用；先结束相关操作 |
| 灰图、末帧伪影或语音截断 | 查对应 H 案例与原始失败；非空文件和程序通过不表示效果通过 |
| 更新 App 后没有新增模型 | 这是预期行为：基座升级不替用户下载模型；在“全部”自行选择 |
| 锁屏后停止 | 检查系统后台／电池限制、温度和内存；仍不能承诺永久存活 |

问题报告请给出手机／Android、LMA 版本、模型 ID／哈希、有效参数、复现步骤与已脱敏日志。不要附真实 API 密钥、私钥、个人参考音频或未经许可的素材。[贡献约定](CONTRIBUTING.md)

## 文档、历史与许可

[完整文档目录](docs/README.md) · [中文手册](docs/USER_GUIDE.md) · [English guide](docs/USER_GUIDE.en.md) · [模型参数](docs/MODEL_SETTINGS.md) · [共用任务](docs/TASK_WORKBENCH.md) · [输入](docs/LOCAL_INPUTS.md) · [API](docs/API.md) · [后台架构](docs/ARCHITECTURE.md)

[多模态可行性研究](docs/MULTIMODAL.md) · [基座评估](docs/FOUNDATION.md) · [冻结需求](docs/MULTIMODAL_RELEASE_PLAN.md) · [用户资产核对](docs/ASSET_CONTROL_AUDIT.md) · [当前实现](docs/IMPLEMENTATION_V034.md) · [旧验证资料](docs/VALIDATION.md) · [设备验收工具（未执行）](docs/DEVICE_ACCEPTANCE.md)

[完整历史中文 README](docs/history/README-dev45.zh.md) · [完整历史英文 README](docs/history/README-dev45.en.md) · [历史文档索引](docs/history/Documentation-dev45.md) · [本次文档修复](docs/releases/v0.3.1-readme.md)

后续授权更新同步代码、双语文档、相关媒体和更新说明，并普通推送至本仓库。文档维护不更换 APK、不覆盖历史附件；只有实际界面变化才重录相应页面。代码采用 [MIT](LICENSE)，引擎与用户模型分别遵循各自许可，见 [third_party/README.md](third_party/README.md)。
