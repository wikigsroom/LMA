# v0.3.3 程序实现与剩余范围

> 此页记录 v0.3.3 的历史范围。Current v0.3.4 adds matched TripoSG / PartCrafter shape subsets; see [当前实现 / current scope](IMPLEMENTATION_V034.md), [English](IMPLEMENTATION_V034.en.md).

[English](IMPLEMENTATION_V033.en.md) · [完整方案](MULTIVIEW_DIAGNOSTICS.md) · [机器矩阵](../catalogue/release-0.3.3-implementation.json)

F-01–F-12、既有文本、01–14 / 16 / 17 和九个 MOSS 冻结子目标继续完整保留。[v0.3.0 基座](IMPLEMENTATION_V030.md)、[社区扩展](IMPLEMENTATION_V031.md)、[语音 / 单图 3D](IMPLEMENTATION_V032.md)不因本轮新增功能而削减。模板 45、模型包 82、扩展引擎 15＋文本，模型由用户独立选择与管理。

| 编号 | 本轮生产实现 | 对应检查 |
| --- | --- | --- |
| 01 | `MultiViewSpec / ExpansionEngine / native/multiview`，真正 Pixal3D MV CPU 与 ARM64 | 四图、相机、组件、硬约束、上游投影与 native 拒绝路径 |
| 02 | F16 / Q8_0 几何 / PBR 四个校验导入包与通用 MV 配方 | 固定清单、7 / 9 角色、无未核实下载 URL、导入与独立设置 |
| 03 | `expansion.js / community.js`，四图输入、相机编辑、草稿、预检、明确提交 | 19 项新增界面检查，保留原推荐与零自动下载 |
| 04 | `runtime_metrics / JobStore / LocalJobs`，阶段耗时、支持 worker 的 RSS、合并持久化 | 失败 / 重启、元数据身份保留、累计大小和引用隔离 |
| 05 | `RuntimeDiagnostics / LmaApp / MainActivity`，系统限制与主动导出 | 最近 64 条、字段白名单、无提示词 / 密钥泄漏夹具 |
| 06 | 当前程序、包签名与依赖、双语文档、4 组媒体、不可变历史 | 原签名、38 ELF / 16 KiB、旧 v0.3.2 按 Git 身份归档 |

原冻结矩阵中的“完整”只针对 F-01–F-12、文本与原所选编号，不代表后续研究的所有新架构均已接入。当前证据明确另列 `all_benchmark_architectures_integrated=false` 和 D04–D12。

| 编号 | 尚未完成的事项 | 性质 |
| --- | --- | --- |
| 07 | UltraTex、UniForge3D、UltraShape、Hunyuan3D 2.1、SAM 3D / MV-SAM3D、SUPRA-Tex、TripoSG、PartCrafter | 9 条配置 / 8 组家族仍需 Android 原生移植；[具体开发缺口](MULTIVIEW_DIAGNOSTICS.md#7-其余测评模型仍需什么) |
| 08 | 对应 MV 完整权重的可公开下载端点 | 已做校验导入与自选配方，不伪造一键下载来源 |
| 09 | 完整模型质量、F5 官方完整中文分词 / 变调等价、手机性能与锁屏耐久 | 按用户指令本轮不执行完整模型 / 实机验证，不能写成通过 |

所有实际推理仍限同一手机，不增远程后端、ComfyUI 连线 / 画布 / 用户插件。程序验证减少验收耗时，不豁免未移植架构的开发。
