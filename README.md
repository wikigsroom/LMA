# LMA · Android 本地模型工作台

[English](README.en.md) · [下载 v0.3.1](https://github.com/wikigsroom/LMA/releases/tag/v0.3.1) · [使用手册](docs/USER_GUIDE.md) · [文档目录](docs/README.md)

LMA 在 Android 手机上选择、下载、管理和运行本地模型，提供聊天、多模态任务、结果库与本机接口。App 更新提供基座，模型及其依赖始终由用户主动选择。安装包不带模型权重，不需要 ROOT、Termux、容器或其他计算设备。

**v0.3.1 已实现完整冻结范围的程序集成：F-01–F-12、既有文本及编号 01–14、16、17。按用户要求，本版仅做程序验证。** 编译、安装包、原生协议、生产任务流程、接口和页面检查与手机推理、画质、音质、速度和锁屏续航是不同结论；后几项未验证。大模型出现在目录中，不代表努比亚 Z20 能承载。

**v0.3.1 新增 14 个系列、44 个社区 checkpoint 配方（生图 30 / 生视频 14），其中 28 个有明确 NSFW 来源标记。** 区分来源声明、分级词表、文件标记、镜像声明和未核对的 HF 提示；登记目录增至 67 套配方。14 个 Wan 视频条目属于同一 1.3B 系列的训练版本。[完整来源、许可、兼容边界和操作说明](docs/COMMUNITY_MODELS.md)。

## 安装与使用顺序

1. 从 Release 下载 `LMA-0.3.1-arm64-v8a.apk`，核对同页 `SHA256SUMS`；需要 **64 位 Android 9 / API 28 或以上**。保留原签名，升级安装可继续使用已有模型和设置。
2. 打开 App，按系统提示允许通知；若要锁屏工作，可在系统中允许后台活动并取消电池限制。首次启动和升级不下载模型。
3. 在“模型”选择“推荐 / 全部 / 本地”。**推荐保留 m08 → m06 → m01**；“全部”支持 HF 关键词、仓库名、仓库链接、分页和全部格式发现；“本地”集中管理已下载、导入和未完成的传输。
4. 用“生文 / 生图 / 生视频 / 生音频”等标签筛选。打开详情核对架构、配方、后端、许可、依赖、固定版本和容量，再明确点击下载或从系统文件选择器导入。
5. 在“本地”打开所选模型的设置。参数为可编辑的选择输入框，按模型独立保存；超过模型、配方或应用约束会回填有效上限。任务中的临时改动不覆盖已保存默认值。
6. 文本模型加载后进入聊天或复制本机 API 地址。其他模型选择“使用”，按能力填写提示词、参考素材及参数，先预检再提交到共用队列。
7. 在“任务”查看进度、取消或明确重试；结果带参数、seed、来源和哈希，可预览、导出、恢复为新请求。草稿独立保存。

HF 全格式**发现**与运行适配分开。兼容文件才可进入对应文本引擎或多组件配方；不能把任意 safetensors、GGUF、Diffusers 仓库直接当成可运行包。自定义组件可以通过配方登记，缺失组件会在本机提示，不自动下载或转出手机。

## 本版模型与基座范围

所有模型平级，通过功能、能力、引擎、格式、组件、后端、许可和安装状态标签分类。Uncensored / Abliterated 是独立标签；已核对作者声明与未核对元数据线索分别显示，不代表拒答率测量。

| 编号 | 模型 / 方案 | 本地程序路线与边界 |
| --- | --- | --- |
| 既有 | 文本 GGUF | llama.cpp、聊天、SSE、逐模型上下文 / 输出约束 |
| 01、02、05 | SD 1.5、SDXL、两者 LoRA | sd.cpp；基础模型与 LoRA 独立管理并核对配对 |
| 03 | SD-Turbo、LCM checkpoint、LCM-LoRA | 独立采样配置；SD1.5 / SDXL LCM-LoRA；需要时显式本地准备和关联 |
| 04 | Sana-Sprint 0.6B、独立 Sana Edit | MNN；各自匹配编码器、转换图和采样规则；不混用变体 |
| 06–08 | Z-Image-Turbo、FLUX.2-klein-4B、Qwen-Image-2.1 | sd.cpp 多组件原生路线；编码器 / VAE / 分词资源分别管理 |
| 09 | MOSS-TTS-Nano 100M | ORT、分词与音频 codec 本机执行 |
| 10 | Kokoro-82M / Piper / Matcha | sherpa-onnx；54 个 Kokoro 音色、固定 Piper Lessac / Matcha LJSpeech 方案 |
| 11 | Qwen3-TTS 0.6B Base | 原生 GGML、参考音频与本机 codec |
| 12 | MOSS 九个冻结子目标 | TTS 1.0 / 1.5、Local 原版 / 1.5、TTSD、VoiceGenerator、SoundEffect 原版 / v2、Realtime；按架构使用 OpenMOSS、delay 或 RQ 适配器 |
| 13、14 | SoulX-Podcast 1.7B、Stable Audio Open Small | 本机语言 / 声学 / codec 与音频采样路线 |
| 16 | Wan 2.1 T2V 1.3B Q4 | sd.cpp CPU / Vulkan；显式模型组件与视频编码 |
| 17 | LTX-Video 2B 0.9.8 distilled | 原始 PixArt T5 F32 + 7 步 / 空间放大 / 3 步；Google T5 Q5 单尺度为独立变体 |

本版有 **38 个数据型配方模板、23 个目录模型包、12 类扩展引擎及原有文本引擎**。这些数量是程序集成范围，不是“所有模型真机通过”数量。完整可追溯映射见[版本实现矩阵](docs/IMPLEMENTATION_V031.md)。

## 基座如何工作

模型包以固定 revision、路径、大小和 SHA256 描述主权重及必需编码器、VAE、codec、分词或音色资源；支持暂停 / 续传、原子安装、共享引用保护、显式更新、导入与删除。运行中的资产持有使用引用，不能被清理。部分架构需要先使用 APK 内置的准备程序转换用户已有文件，再明确关联运行包；不会执行下载的程序或任意用户脚本。

内部版本化适配器实现加载、阶段进度、取消、错误和卸载；资源准入与共用调度默认只让一个大型任务占用推理资源。每个任务冻结模型身份、参数与素材，结果写入暂存区并校验后提交。中断后对账已有结果；只有存在真实 checkpoint 才能续步，否则由用户明确重试。没有 ComfyUI 连线、无限画布、用户节点或插件市场。

LTX 原始多尺度方案顺序执行 CPU T5 → Vulkan 初次采样 → CPU 学习型空间放大 / AdaIN → Vulkan 细化 → CPU VAE → 本机 AVC。原始 T5 两分片约 **17.74 GiB**，完整运行资产约 **23.86 GiB**；不适合作为 Z20 的可运行承诺。APK 仅携带放大器计算结构，72 个学习张量均引用用户另行取得的文件。[具体身份、参数与流程](docs/LTX_MULTISCALE.md)。

## 本机接口与后台

默认地址 `http://127.0.0.1:8080/v1`，使用界面提供的本地 API 密钥。保留 `/models`、`/chat/completions` 和 SSE；多模态使用异步 `/jobs`、预检、事件、取消和鉴权产物接口；UI 与 API 共用同一调度器和参数校验。接口字段见[中文 API](docs/API.md)。可选的局域网接口仍由这部手机计算；App 没有外部推理提供方。

可见前台服务、通知停止入口和按需唤醒锁支持退出界面后继续工作。系统强制停止、厂商省电策略、热量和内存压力仍会终止任务；程序恢复逻辑不等于已证明 Z20 锁屏长时间稳定输出。模型、许可、存储与运行内存需求各自独立，App 不替用户静默更换模型。

## 截图与录屏

以下为 **v0.3.1 生产页面＋明确标记的桌面交互夹具**，没有下载权重或生成模型内容；浏览器在录制后关闭。

![社区模型筛选、来源与本地管理](docs/media/development/community/community-ui.gif)

[MP4 录屏](docs/media/development/community/community-ui.mp4) · [生图目录](docs/media/development/community/01-community-images.png) · [来源详情](docs/media/development/community/02-image-source.png) · [视频目录](docs/media/development/community/03-community-video.png) · [本地管理](docs/media/development/community/05-community-local.png) · [工作台录屏](docs/media/development/release-workbench/release-workbench-ui.mp4)

## 验证、构建与文档

[本版 Release 说明](docs/releases/v0.3.1.md)列出程序检查数量、安装包身份和交付清单；[验证策略](docs/PROGRAM_VALIDATION.md)记录用户明确取消完整模型运行验收的要求。当前证据在 [verification/program](verification/program/status.json)，旧失败和旧版本记录保留在历史目录，不能被解释为本 APK 的模型测试结果。

原生 Windows 构建使用 JDK、Android SDK / NDK 和 CMake，不使用 Docker、WSL 或模拟器。签名材料仅保存在本地 `signing/`，不进入 Git 或发行附件。[构建](docs/BUILD.md) · [发布](docs/RELEASING.md) · [贡献约定](CONTRIBUTING.md)。

[完整文档目录](docs/README.md)连接模型管理、逐模型参数、工作台、后台恢复、API、全部架构方案和历史研究。代码采用 MIT；引擎和用户模型分别遵循各自许可，见 [third_party/README.md](third_party/README.md)。
