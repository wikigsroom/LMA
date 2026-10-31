# v0.3.6 编号适配收口

[English](REMAINING_ADAPTATION.en.md) · [完整方案与操作](ADAPTER_PROFILES.md) · [当前证据](../verification/releases/v0.3.6/status.json) · [原冻结需求](MULTIMODAL_RELEASE_PLAN.md)

此页是 v0.3.6 当前实现清单。原 v0.3.5 未适配结论保留在其发布审计；本版补齐对应代码，不回写原发布证据。开发采用一次完整交付，不把必需适配拆到后续版本。

| 编号 | 本轮实现 | 当前范围 / 证据入口 |
| --- | --- | --- |
| P01 | UltraTex 完整本地流程 | FLUX.1 / FLUX.2、文本 / tile VAE / BN、双 LoRA 材质、packing / Euler / CFG / PBR；`ultratex-tests`、`ultratex-flow-tests` |
| P02 | UniForge3D 联合多视图 | 实际 VGGT / DiT、DINO、条件 / anchor 路由、SS / SLAT、FDG / 材质 / GLB；`uniforge-tests`、`uniforge-component-tests`、`view-router-tests` |
| P03 | SAM 3D Objects | MoGe、三支条件、MoT / pose、占据 / SLAT、FlexiCubes、顶点色 / 辅助通道；SAM、depth、pose、FlexiCubes 生产对照与导出检查 |
| P04 | MV-SAM3D＋DA3 | 四图联合深度、度量分支、相机 / 坐标对齐、MultiDiffusion、SS 预热 / 回放和 SLAT 随机流；独立四视图配置和资产核验 |
| P05 | SUPRA-Tex | 本地 Qwen3-VL / VAE / 双 PBR、SCVAE、交错 completion、FDG / 可见性与原网格烘焙；SUPRA 实际网络和生产流程检查 |
| P06 | 子集之外的同机准备和材质链 | DIS 抠图、mtmd VLM 部件识别、XYZ＋法线点云 VAE、原始 Flash / octree / Lewiner / DISO CPU、可选 Paint / UltraTex 后处理；Java / native / UI 检查 |
| B01 | F5 官方兼容前端 | 6,671 项分词 / 拼音 / 变调 / 词表 ID 检查；语言表为独立用户资产 |
| B02 | Hunyuan Paint 与通用 PBR | 本机编码 / 六视图双材质 / UniPC / VAE / 可选增强、光栅 / xatlas / 融合 / PBR；保留原网格坐标 |
| B03 | 共用应用模块 | 参数跟模型走、可编辑 / 联动归位、输入角色、内容识别 JSON、草稿 / 预检 / 队列 / 取消、阶段租约 / 哈希 / 生效参数、原子最终结果 |
| B04 | 发版体系 | 当前证据放 `verification/releases/v0.3.6/`；原 `verification/program/` / history 保持；实际缺代码 / 缺记录时三个发布入口拒绝 |

**P01–P06 没有剩余必需开发项。** 本版是明确有界 CPU 方案的程序集成；不会称为复现全部上游 CUDA 流程或所有 HF 架构。完整参数、输入、导出与差异见 [方案](ADAPTER_PROFILES.md)，机器核对由 `tools/audit_adaptations.py --require-complete` 执行，来源与检查变更会使证据失效。

| 编号 | 未核实 / 未测事项 | 处理方式 |
| --- | --- | --- |
| P07 | 匹配完整公开 3D 导出包的下载端点 | 未核实。保留用户明确转换 / 导入；不伪造 URL，不自动取权重。已核对目录包和 HF 其他可兼容模型的显式下载继续可用 |
| P08 | 完整训练模型、手机效果 / 速度 / 峰值内存 / 锁屏耐久 | 按用户指令不执行；零完整模型下载 / 运行、零手机验收。不是开发缺口，也不向用户反复要求手机 |
| P09 | 任意其他 HF / CUDA 架构或所有论文默认流程 | 不在“已适配”声明中。HF 发现与执行兼容分开；后续新架构仍需要版本化适配器 |

不变的约束：APK 只更新基座，所有资产用户自选；全同一手机，无 ROOT / 远端 / 虚拟化；模型平级、内容标签独立；推荐 `m08 → m06 → m01`；保留 F01–F12、文本、01–14／16／17、九个 MOSS、SD1.5 / SDXL LoRA 与既有所有社区 / 语音 / 3D 路线；不建设 ComfyUI 画布、节点或插件系统。

[页面 GIF](media/development/adaptation/adaptation-ui.gif) / [MP4](media/development/adaptation/adaptation-ui.mp4) 是生产页面＋明确 UI FIXTURE，非训练模型或 Android 真机录像。完整依赖条款见[许可证](../THIRD_PARTY_NOTICES.md)，DISO CPU 组件含非商业限制。
