# LMA 文档 / Documentation

[项目首页 / 中文](../README.md) · [Project README / English](../README.en.md)

当前公开版本 **0.2.0**；内部开发 **0.3.0-dev**，完整版本尚未验收。文档整理日期：**2026-10-29（Asia/Taipei）**。产品行为以生产源码及对应版本的验证证据为准；历史审计保留其原始检查日期。

| 主题 / Topic | 中文 | English |
| --- | --- | --- |
| Model runtime preparation / 运行资产准备 | [MODEL_PREPARATION.md](MODEL_PREPARATION.md) | [MODEL_PREPARATION.en.md](MODEL_PREPARATION.en.md) |
| 旧LTX训练VAE / Trained decoder | [中文](LTX098_VAE.md) | [English](LTX098_VAE.en.md) |
| 安装与操作 / Installation and workflow | [USER_GUIDE.md](USER_GUIDE.md) | [USER_GUIDE.en.md](USER_GUIDE.en.md) |
| API 与 SSE / API and streaming | [API.md](API.md) | [API.en.md](API.en.md) |
| 开发实施 / Development status | [DEVELOPMENT.md](DEVELOPMENT.md) | [DEVELOPMENT.en.md](DEVELOPMENT.en.md) |
| Stable Audio 短音频 / Local short audio | [STABLE_AUDIO_ENGINE.md](STABLE_AUDIO_ENGINE.md) | [STABLE_AUDIO_ENGINE.en.md](STABLE_AUDIO_ENGINE.en.md) |
| 基座与资产需求核对 / Asset-control audit | [ASSET_CONTROL_AUDIT.md](ASSET_CONTROL_AUDIT.md) | [ASSET_CONTROL_AUDIT.en.md](ASSET_CONTROL_AUDIT.en.md) |
| Sana 移动端 / MNN 引擎 | [MNN_SANA_ENGINE.md](MNN_SANA_ENGINE.md) | [MNN_SANA_ENGINE.en.md](MNN_SANA_ENGINE.en.md) |
| 高级扩散 / 视频基座 | [ADVANCED_DIFFUSION.md](ADVANCED_DIFFUSION.md) | [ADVANCED_DIFFUSION.en.md](ADVANCED_DIFFUSION.en.md) |
| HF 组件配方 / HF component recipes | [HF_RECIPES.md](HF_RECIPES.md) | [HF_RECIPES.en.md](HF_RECIPES.en.md) |
| 模型独立更新 / Independent model versions | [MODEL_UPDATES.md](MODEL_UPDATES.md) | [MODEL_UPDATES.en.md](MODEL_UPDATES.en.md) |
| LoRA 平级配对 / Peer adapter pairing | [ADAPTERS.md](ADAPTERS.md) | [ADAPTERS.en.md](ADAPTERS.en.md) |
| 构建 / Building | [BUILD.md](BUILD.md) | [BUILD.en.md](BUILD.en.md) |
| 架构 / Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) | [ARCHITECTURE.en.md](ARCHITECTURE.en.md) |
| 多模态可行性研究 / Multimodal feasibility research | [MULTIMODAL.md](MULTIMODAL.md) | [MULTIMODAL.en.md](MULTIMODAL.en.md) |
| 可扩展多模态基座 / Extensible multimodal foundation | [FOUNDATION.md](FOUNDATION.md) | [FOUNDATION.en.md](FOUNDATION.en.md) |
| v0.3.0 完整需求 / Complete single-release requirements | [MULTIMODAL_RELEASE_PLAN.md](MULTIMODAL_RELEASE_PLAN.md) | [MULTIMODAL_RELEASE_PLAN.en.md](MULTIMODAL_RELEASE_PLAN.en.md) |
| 本机任务与内部执行 / Local jobs and internal stages | [WORKFLOWS.md](WORKFLOWS.md) | [WORKFLOWS.en.md](WORKFLOWS.en.md) |
| HF 发现与本地管理 / HF discovery and Local | [HF_MODELS.md](HF_MODELS.md) | [HF_MODELS.en.md](HF_MODELS.en.md) |
| 模型独立参数 / Per-model settings | [MODEL_SETTINGS.md](MODEL_SETTINGS.md) | [MODEL_SETTINGS.en.md](MODEL_SETTINGS.en.md) |
| 无审查模型 / Uncensored models | [UNCENSORED_MODELS.md](UNCENSORED_MODELS.md) | [UNCENSORED_MODELS.en.md](UNCENSORED_MODELS.en.md) |
| 验证 / Validation | [VALIDATION.md](VALIDATION.md) | [VALIDATION.en.md](VALIDATION.en.md) |
| 真机验收 / Physical-device acceptance | [DEVICE_ACCEPTANCE.md](DEVICE_ACCEPTANCE.md) | [DEVICE_ACCEPTANCE.en.md](DEVICE_ACCEPTANCE.en.md) |
| 截图与录屏 / Screenshots and recordings | [MEDIA.md（双语 / bilingual）](MEDIA.md) | [Provenance / 来源](media/manifest.json) |
| 后续同步与发布 / Updates and publishing | [RELEASING.md（双语 / bilingual）](RELEASING.md) | [Contributing / 贡献约定](../CONTRIBUTING.md) |
| v0.3.0 交付计划 / Delivery plan | [v0.3.0-plan.md（双语 / bilingual）](releases/v0.3.0-plan.md) | 同版基座支持、用户自选模型 / Foundation support, user-selected assets |
| 版本 / Versions | [CHANGELOG.md（双语 / bilingual）](../CHANGELOG.md) | [v0.2.0（双语 / bilingual）](releases/v0.2.0.md) |

## 阅读建议 / Reading paths

- **用户 / Users：** README → 使用手册 / User guide → API → 常见问题 / Troubleshooting in the user guide。
- **开发者 / Developers：** 构建 / Build → 架构 / Architecture → 验证 / Validation → 贡献约定 / Contributing。
- **业务扩展 / Expansion：** [现行需求 / Release plan](MULTIMODAL_RELEASE_PLAN.md) → [范围与标签 / Scope and tags](proposals/multimodal-release-scope.json) → [基座 / Foundation](FOUNDATION.md) → [本机任务 / Local tasks](WORKFLOWS.md) → [源码研究 / Source research](MULTIMODAL.md)。v0.3.0 一次性交付 01–14 / 16 / 17 与完整基座，模型平级、无画布节点生态；全部同一手机执行，尚未实现 / One complete v0.3.0 scope, flat peers, no canvas/node ecosystem, same-phone execution; unimplemented.
- **验收 / Acceptance：** [完成条件核对](COMPLETION_AUDIT.md) → 真机验收 / Device acceptance → [`verification/`](../verification/)。

## 证据和历史记录 / Evidence and audit history

- [DESIGN.md](DESIGN.md)：界面交互设计说明 / UI design rationale。
- [图片旁白草案 / Narrated-image draft](proposals/local-narrated-image.workflow.json)、[Wan 草案 / Wan draft](proposals/local-wan-video.workflow.json)：历史、不可执行示例；不属于当前导入格式或组合任务交付要求 / Historical non-executable examples, not current import formats or mandatory composed tasks.
- [local-video-evidence.json](research/local-video-evidence.json)：Wan / 旧 LTX Android 源码与作者结果记录；不属于 LMA 实测 / Wan/older LTX Android source and author reports, not LMA device results。
- [COMPLETION_AUDIT.md](COMPLETION_AUDIT.md)：逐项完成条件及真机阻塞项 / Requirement-by-requirement audit and device blocker。
- [`catalogue/`](../catalogue/)：固定模型、作者声明、GGUF 来源、哈希及架构记录 / Pinned models, publisher declarations, hashes, architecture records。
- [`third_party/README.md`](../third_party/README.md)：引擎来源、锁定版本、许可和部分上游审计源码 / Runtime provenance, locks, notices, selected audit sources。
- [`verification/README.md`](../verification/README.md)：可以公开复查的桌面及包验证记录 / Reviewable desktop and package evidence。

**界面演示不等于真机验收。UI demonstrations do not establish physical-device inference or background endurance.**

- 本地语音基座 / Local speech implementation: [中文](TTS_ENGINE.md) · [English](TTS_ENGINE.en.md)，编译与主机证据，尚无真机推理 / compiled and host evidence only, without device inference.

- Nano 本地语音执行 / Nano speech execution: [中文](MOSS_NANO_ENGINE.md) · [English](MOSS_NANO_ENGINE.en.md)，任意文本与用户资产工作区；没有实际模型 / 真机证据 / arbitrary text and user-asset workspaces, without actual model/device evidence.

文本模型与共用队列 / Text models and shared jobs: [中文](TEXT_ENGINE.md) · [English](TEXT_ENGINE.en.md)，新 HF 文本包、实际 GGUF 约束、正文 / 思考结果和当前迁移边界 / new text bundles, inspected limits, typed artifacts and migration boundaries.

- [已有模型迁移与零重复下载](MODEL_MIGRATION.md) / [Existing-model migration](MODEL_MIGRATION.en.md)：原 ID、共用资产与参数、明确续传、失败恢复和证据范围。

- [共用执行槽与文本自动切换](SCHEDULING.md) / [Shared execution slot](SCHEDULING.en.md)：回复与任务等待、取消、资源复查、真实进程回收与证据边界。

- [本地输入素材、任务引用与分块上传](LOCAL_INPUTS.md) / [Local media and uploads](LOCAL_INPUTS.en.md)：用户文件、固定 hash、签名引擎角色及引用保护；现有生产配方仍只接受文字。

新增 / Added dev.12：[扩散组件与采样](DIFFUSION_ENGINE.md) / [Diffusion components and sampling](DIFFUSION_ENGINE.en.md)；[双语检查点说明](releases/v0.3.0-dev.12.md)。

内部 dev.13：新增四条用户自选图像 / 视频组件路线，见[双语说明](releases/v0.3.0-dev.13.md)，不是完整 Release。

[Qwen3-TTS 本机语音](QWEN_TTS_ENGINE.md) / [English](QWEN_TTS_ENGINE.en.md)：0.6B Base 原生 CPU、两个自选 GGUF、内含依赖、可选参考 WAV、参数与 RTF 证据边界。

- MOSS Delay first-class 原生语音：[中文](MOSS_DELAY_ENGINE.md) / [English](MOSS_DELAY_ENGINE.en.md)；[dev.16 双语说明](releases/v0.3.0-dev.16.md)。

- MOSS Local-v1.5 / SoundEffect-v2 原生基座：[中文](OPENMOSS_ENGINE.md) / [English](OPENMOSS_ENGINE.en.md)；[dev.17 双语说明](releases/v0.3.0-dev.17.md)。

- [dev.18：MOSS delay / 双说话人与声音设计（双语）](releases/v0.3.0-dev.18.md) · [中文指南](OPENMOSS_ENGINE.md) / [English guide](OPENMOSS_ENGINE.en.md) · [固定发布者元数据核对](../catalogue/evidence/openmoss-delay-publishers.json)。


- [dev.19：旧 Local / Realtime / SoundEffect（双语编号交付）](releases/v0.3.0-dev.19.md) · [RQ 中文指南](MOSS_RQ_ENGINE.md) / [English](MOSS_RQ_ENGINE.en.md) · [固定发布者 / codec / tokenizer 核对](../catalogue/evidence/moss-rq-publishers.json)。

- SoulX完整声学网络：[中文](SOULX_ACOUSTIC.md) / [English](SOULX_ACOUSTIC.en.md)；完整结构未训练回归与原生执行。
- SoulX训练参考 /声学重建：[中文](SOULX_REFERENCE.md) / [English](SOULX_REFERENCE.en.md)；[双语编号实现与待办](releases/v0.3.0-dev.20-soulx-reference.md)，明确主机组件 /完整TTS /App /手机边界。

- SoulX语言 /完整主机链路：[中文](SOULX_LANGUAGE.md) / [English](SOULX_LANGUAGE.en.md)；[双语编号实现与待办](releases/v0.3.0-dev.20-soulx-language.md)，完整训练host输出与App /质量 /真机验收分别记录。

- dev.21 SoulX App基座：[中文](SOULX_ENGINE.md) / [English](SOULX_ENGINE.en.md)；[双语编号交付与完整待办](releases/v0.3.0-dev.21.md)。14份用户资产、配套参考原文、生产worker真实训练主机证据，与公开下载候选 /质量 /Android /Release门槛分别记录。

- 旧LTX 0.9.8原生DiT：[中文](LTX098_DIT.md) / [English](LTX098_DIT.en.md)；[编号实现与完整待办](releases/v0.3.0-dev.21-ltx-dit.md)。675检查 /80主机子进程 /48原始PyTorch比对；CPU /Vulkan、全28层小宽度未训练网络与独立ARM64编译，不是完整训练视频或Android执行。

- 旧LTX用户资产转换与原生采样：[中文](LTX098_SAMPLING.md) / [English](LTX098_SAMPLING.en.md) / [编号交付与完整待办](releases/v0.3.0-dev.21-ltx-sampling.md)。692检查 /58原生子进程 /111误差记录；完整训练28层Vulkan latent对照与ARM64采样编译分别记录，无T5 /VAE /视频 /App /手机结论。

- 旧LTX T5文本组件：[中文](LTX098_TEXT.md) / [English](LTX098_TEXT.en.md) / [本轮编号已实现与完整待办](releases/v0.3.0-dev.21-ltx-text.md)。491检查 /76原生子进程；完整训练T5主机embedding、原始外部分词配置与独立ARM64编译，完整视频 /App /手机仍待验收。


- 旧 LTX 真实提示词到主机视频：[中文](LTX098_PIPELINE.md) / [English](LTX098_PIPELINE.en.md) / [编号实现与完整待办](releases/v0.3.0-dev.21-ltx-pipeline.md)。独立单尺度 Google Q5 变体、完整训练串联与原始前向对照；[真实主机帧](media/development/ltx098-host-contact-sheet.png) / [GIF](media/development/ltx098-host-comparison.gif) / [MP4](media/development/ltx098-host-comparison.mp4)，不是 App 或手机验收。

  上述主机链路完整精度检查当前有6项失败，163项中157通过；实际出片与严格数值验收分别记录，见[具体误差](LTX098_PIPELINE.md)。

旧 LTX 文本数值定位：[中文](LTX098_PRECISION.md) / [English](LTX098_PRECISION.en.md) / [本轮编号交付及完整同版待办](releases/v0.3.0-dev.21-ltx-precision.md)。314 训练中间对照、628 文件身份 / 误差重算、120 同输入算子；[实际主机误差图](media/development/ltx098-text-roundoff.png)不表示完整数值或 Android 验收，精度候选与生产代码分开记录。

旧 LTX 原生资产准备：[中文](LTX098_PREPARE.md) / [English](LTX098_PREPARE.en.md) / [编号实现与完整待办](releases/v0.3.0-dev.21-ltx-prepare.md)。可移植分块转换、独立完整训练文件字节对照、取消 / 已有资产保护及 ARM64 编译；[实测图](media/development/ltx098-native-prepare.png)不是 App 或手机记录。No production App or model inference acceptance.

旧 VAE 原生资产准备：[中文](LTX098_VAE_PREPARE.md) / [English](LTX098_VAE_PREPARE.en.md) / [本轮编号与完整待办](releases/v0.3.0-dev.21-ltx-vae-prepare.md)。九图学习参数外置、原生完整源校验与分块数据写入、18 资产字节对照、四种尺寸真实解码；[实际主机图](media/development/ltx098-vae-prepared-decode.png)是合成 latent 的训练解码器验证，不是 App / 手机或生成质量验收。
