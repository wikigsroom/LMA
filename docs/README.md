# LMA 文档 / Documentation

当前版本 **v0.3.4**：完整冻结范围的程序集成，按用户指令只做程序验证。Current release: complete frozen program scope; phone/model quality and endurance remain untested. [中文 README](../README.md) · [English README](../README.en.md) · [Release notes](releases/v0.3.4.md)

- [社区生图 / 生视频与 NSFW 标记](COMMUNITY_MODELS.md) · [English](COMMUNITY_MODELS.en.md)：44 个新增版本、来源 / 许可 / 兼容边界、操作及截图。
- README 已恢复详细正文：[27 个使用场景](../README.md#use-cases)、[4 组 API 示例](../README.md#api-examples)、[18 组案例与失败](../README.md#case-studies)、[27 组测试覆盖](../README.md#verification)；[English scenarios](../README.en.md#use-cases) / [cases](../README.en.md#case-studies)。[本次完整性修复 / Repair notes](releases/v0.3.1-readme.md)。

## 使用与基座 / Usage and foundation

| 主题 / Topic | 中文 | English |
| --- | --- | --- |
| 完整实现与范围 / Implementation | [实现矩阵](IMPLEMENTATION_V034.md) | [Matrix](IMPLEMENTATION_V034.en.md) |
| 安装、模型和使用 / User guide | [使用手册](USER_GUIDE.md) | [Guide](USER_GUIDE.en.md) |
| HF 全部 / 本地 / Discovery | [HF 模型](HF_MODELS.md) | [HF models](HF_MODELS.en.md) |
| 模型包与共享组件 / Bundles | [模型包](MODEL_TRANSFERS.md) | [Bundles](MODEL_TRANSFERS.en.md) |
| 逐模型设置 / Settings | [参数设置](MODEL_SETTINGS.md) | [Settings](MODEL_SETTINGS.en.md) |
| 更新与迁移 / Updates | [独立更新](MODEL_UPDATES.md) | [Updates](MODEL_UPDATES.en.md) |
| 原始模型准备 / Preparation | [本地准备](MODEL_PREPARATION.md) | [Preparation](MODEL_PREPARATION.en.md) |
| 显式关联 / Association | [运行包关联](MODEL_ASSEMBLY.md) | [Association](MODEL_ASSEMBLY.en.md) |
| HF 配方 / Recipes | [配方](HF_RECIPES.md) | [Recipes](HF_RECIPES.en.md) |
| 共用工作台 / Workbench | [草稿、任务与结果](TASK_WORKBENCH.md) | [Workbench](TASK_WORKBENCH.en.md) |
| 预检、资源与恢复 / Preflight | [预检](TASK_PREFLIGHT.md)、[资源](RUNTIME_RESOURCES.md)、[恢复](TASK_RECOVERY.md) | [Preflight](TASK_PREFLIGHT.en.md), [resources](RUNTIME_RESOURCES.en.md), [recovery](TASK_RECOVERY.en.md) |
| 本机接口 / API | [API](API.md) | [API](API.en.md) |
| 内部适配器 / Adapters | [架构](ARCHITECTURE.md)、[适配器](ADAPTERS.md) | [Architecture](ARCHITECTURE.en.md), [adapters](ADAPTERS.en.md) |

- [四视图 3D 与诊断](MULTIVIEW_DIAGNOSTICS.md) · [English](MULTIVIEW_DIAGNOSTICS.en.md)：4 个校验导入包、相机 / API / 观察隐私 / 63 项原生专项；该 v0.3.3 记录按历史保留，当前剩余见下一项。

## 模型路线 / Model routes

- [新增语音与本地生 3D](SPEECH_3D_EXPANSION.md) · [English](SPEECH_3D_EXPANSION.en.md)：四类语音 / 11 包、16 条测评评估、单图 GLB / 独立参数 / API / 程序检查 / 新演示。

| 范围 / Scope | 中文 | English |
| --- | --- | --- |
| 01/02/03/05 SD、SDXL、LoRA、LCM | [生图选择](CURATED_DIFFUSION.md)、[LCM 流程](LCM_APP_FLOW.md) | [Image selection](CURATED_DIFFUSION.en.md), [LCM](LCM_APP_FLOW.en.md) |
| 04 Sana-Sprint / 独立 Edit | [Sprint](SANA_SPRINT.md)、[Edit](MNN_SANA_EDIT.md) | [Sprint](SANA_SPRINT.en.md), [Edit](MNN_SANA_EDIT.en.md) |
| 06 Z-Image-Turbo | [方案](ZIMAGE_TURBO.md) | [Route](ZIMAGE_TURBO.en.md) |
| 07 FLUX.2-klein-4B | [方案](FLUX2_KLEIN.md) | [Route](FLUX2_KLEIN.en.md) |
| 08 Qwen-Image-2.1 | [高级生图](ADVANCED_DIFFUSION.md) | [Advanced image](ADVANCED_DIFFUSION.en.md) |
| 09 Nano / 10 Kokoro、Piper、Matcha | [音色与选择](SPEECH_SELECTION.md)、[Nano](MOSS_NANO_ENGINE.md) | [Selection](SPEECH_SELECTION.en.md), [Nano](MOSS_NANO_ENGINE.en.md) |
| 11 Qwen3-TTS 0.6B | [引擎](QWEN_TTS_ENGINE.md) | [Engine](QWEN_TTS_ENGINE.en.md) |
| 12 MOSS 九子目标 | [OpenMOSS](OPENMOSS_ENGINE.md)、[Delay](MOSS_DELAY_ENGINE.md)、[RQ](MOSS_RQ_ENGINE.md) | [OpenMOSS](OPENMOSS_ENGINE.en.md), [delay](MOSS_DELAY_ENGINE.en.md), [RQ](MOSS_RQ_ENGINE.en.md) |
| 13 SoulX | [引擎](SOULX_ENGINE.md) | [Engine](SOULX_ENGINE.en.md) |
| 14 Stable Audio | [引擎](STABLE_AUDIO_ENGINE.md) | [Engine](STABLE_AUDIO_ENGINE.en.md) |
| 16 Wan | [视频](WAN_VIDEO.md) | [Video](WAN_VIDEO.en.md) |
| 17 原始 PixArt 多尺度 LTX | [完整路线](LTX_MULTISCALE.md) | [Complete route](LTX_MULTISCALE.en.md) |
| 既有 Google Q5 单尺度 LTX | [独立历史路线](LTX098_APP_FLOW.md) | [Independent legacy route](LTX098_APP_FLOW.en.md) |

## 交付与历史 / Delivery and history

[程序验证 / Program policy](PROGRAM_VALIDATION.md) · [English policy](PROGRAM_VALIDATION.en.md) · [当前证据 / Evidence](../verification/program/status.json) · [构建 / Build](BUILD.md) · [English build](BUILD.en.md) · [发布流程 / Release workflow](RELEASING.md) · [贡献 / Contributing](../CONTRIBUTING.md)

[冻结需求 / Frozen plan](MULTIMODAL_RELEASE_PLAN.md) 与其旧模型运行门槛保留为需求历史；当前验证规则以上述用户指令为准。[历史文档索引 / Historical research index](history/Documentation-dev45.md) · [历史 README](history/README-dev45.zh.md) · [English historical README](history/README-dev45.en.md)。旧模型失败、旧桌面录制和旧版本证据不改写为本版测试通过。

- [RF 形状与部件几何](RF_SHAPE.md) · [English](RF_SHAPE.en.md)：三个自选导出配方、全部本机 CPU、完整导入 / 参数 / 任务 / GLB 流程、161 项专项、5 张新截图与 GIF / MP4；D04–D10 仍为开发待办。
