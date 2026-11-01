# LMA 文档 / Documentation

**v0.3.12 / code62 · 当前 / Current:** [本地多模态 API](LOCAL_API_V0312.md) / [English](LOCAL_API_V0312.en.md) · [实机测评](DEVICE_BENCHMARK_V0312.md) / [Benchmark](DEVICE_BENCHMARK_V0312.en.md) · [协议](SUB2API_OPENAI.md) / [Contract](SUB2API_OPENAI.en.md) · [Release](releases/v0.3.12.md)。自动模型列表、标准图片／语音、统一异步任务与 Sub2API 源码扩展；生成无固定时间上限，视频实机验收大于 5 秒。旧版记录保留原身份。

**v0.3.11 / code61：** [手机模型修复与真实输出](ON_DEVICE_MODEL_REPAIR.md) / [English](ON_DEVICE_MODEL_REPAIR.en.md) · [完整实现](IMPLEMENTATION_V0311.md) / [English](IMPLEMENTATION_V0311.en.md) · [Release](releases/v0.3.11.md)。

[空闲卡顿原因与真机对比](PERFORMANCE.md) / [Idle UI performance and measurements](PERFORMANCE.en.md) · [v0.3.9](releases/v0.3.9.md)。

**v0.3.10 / code60 · 当前 / Current:** [14 个推荐模型 / fourteen recommended choices](RECOMMENDED_MODELS.md)：text 3 / image 3 / video 2 / audio 3 / 3D 3. Default Recommended preserves the original text prefix, adds optional multimodal choices and never downloads automatically. [Release](releases/v0.3.10.md) · [当前实现 / implementation](IMPLEMENTATION_V0310.md). Earlier version callouts below retain their historical context.

**v0.3.7 / code57:** [真机零模型启动修复与 19 项程序检查](DEVICE_ACCEPTANCE.md) / [Physical program acceptance](DEVICE_ACCEPTANCE.en.md). Includes short screen-off API health and separate real phone media; no complete model or endurance claim.

**v0.3.7 历史适配检查点 / Historical adaptation checkpoint.** 完成 P01–P06 的有界 CPU 程序适配：UltraTex、UniForge、SAM / MV-SAM＋DA3、SUPRA、抠图 / VLM / 点云 / 原始提取与可选材质链。62 recipes / 82 bundles / 18 extension engines plus text。只更新基座，资产仍由用户选择；没有完整模型或手机效果验收。

- [本版完整方案 / Full adapter profiles](ADAPTER_PROFILES.md) · [English](ADAPTER_PROFILES.en.md)：输入、离线转换、独立参数、同机可选阶段、相机 / 点云示例、CPU / 许可边界。
- [编号收口 / Numbered completion](REMAINING_ADAPTATION.md) · [English](REMAINING_ADAPTATION.en.md)：P01–P06 已实现；公开整包端点未核实、完整模型和手机实测按要求不执行。
- [当前程序证据 / Current evidence](../verification/releases/v0.3.10/status.json) · [v0.3.10 Release notes](releases/v0.3.10.md) · [依赖条款 / Component terms](../THIRD_PARTY_NOTICES.md)。
- [F5 官方兼容前端](F5_FRONTEND.md) / [English](F5_FRONTEND.en.md)、[本机 Paint / PBR](LOCAL_MATERIALS.md) / [English](LOCAL_MATERIALS.en.md)、[UltraTex 网络工具详解](ULTRATEX_FLOW.md) / [English](ULTRATEX_FLOW.en.md)。

- [Hunyuan3D 形状 / UltraShape 精修](SPATIAL_SHAPE.md) · [English](SPATIAL_SHAPE.en.md)：用户自选导出 / 导入，PNG＋可选粗 GLB，8 / 10 个独立参数，任务与 sparse CPU 基座。
- [v0.3.5 全部已实现 / 待完成](IMPLEMENTATION_V035.md) · [English](IMPLEMENTATION_V035.en.md)：原冻结范围保留，六项测评配置仍缺完整代码；不把共用算子当作整个模型。

历史版本 **v0.3.5**：原冻结范围的程序集成记录，保留原身份。Historical frozen-scope evidence; current v0.3.10 records are linked above. [中文 README](../README.md) · [English README](../README.en.md) · [Release notes](releases/v0.3.5.md)

- [社区生图 / 生视频与 NSFW 标记](COMMUNITY_MODELS.md) · [English](COMMUNITY_MODELS.en.md)：44 个新增版本、来源 / 许可 / 兼容边界、操作及截图。
- README 已恢复详细正文：[48 个使用场景](../README.md#use-cases)、[4 组 API 示例](../README.md#api-examples)、[18 组案例与失败](../README.md#case-studies)、[当前及历史测试覆盖](../README.md#verification)；[English scenarios](../README.en.md#use-cases) / [cases](../README.en.md#case-studies)。[本次完整性修复 / Repair notes](releases/v0.3.1-readme.md)。

**本地目录自动发布 / Automatic local publication (design):** [R17–R24](SUB2API_OPENAI.md#41-本地模型自动加入广播目录) · [English](SUB2API_OPENAI.en.md#41-automatically-publish-existing-local-models) · [六类模型示例 / Six-modality example](proposals/sub2api-local-models.example.json)。已下载、有效配置、未加载可见；手机与 Sub2API 同步仍待开发。

## 使用与基座 / Usage and foundation

| 主题 / Topic | 中文 | English |
| --- | --- | --- |
| 完整实现与范围 / Implementation | [实现矩阵](IMPLEMENTATION_V035.md) | [Matrix](IMPLEMENTATION_V035.en.md) |
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

- [RF 形状与部件几何](RF_SHAPE.md) · [English](RF_SHAPE.en.md)：三个自选导出配方、全部本机 CPU、完整导入 / 参数 / 任务 / GLB 流程、161 项专项、5 张新截图与 GIF / MP4；D04、D05、D07 Paint、D08–D10 仍待完整适配；D06 精修和 D07 形状见上方 Spatial 指南。

完整配方与 59 组程序检查：[中文矩阵](IMPLEMENTATION_V037.md) / [English inventory](IMPLEMENTATION_V037.en.md)。原 [v0.3.5 矩阵](IMPLEMENTATION_V035.md) 保留历史范围。
