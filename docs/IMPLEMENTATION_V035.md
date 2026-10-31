# v0.3.5 实现与待办

[English](IMPLEMENTATION_V035.en.md) · [完整操作方案](SPATIAL_SHAPE.md) · [机器矩阵](../catalogue/release-0.3.5-implementation.json)

原冻结 F-01–F-12、生文、01–14／16／17、九个 MOSS 子目标、SD1.5 / SDXL LoRA、社区、语音、单图、四视图和 RF / 部件全部保留。当前为 50 模板、82 目录包、17 扩展引擎加文本。模型资产仍由用户选择；两个新增配方没有冒充可公开下载的完整模型包。

| 编号 | 本轮已实现 | 检查与边界 |
| --- | --- | --- |
| 01 | Hunyuan3D 2.1 形状：DINO / HunYuanDiTPlain / MoE / VAE / SDF / GLB | 匹配固定源码 FP32 ONNX，独立 Paint 尚未实现 |
| 02 | UltraShape 1.0 精修：PNG＋粗 GLB、voxel RoPE / masked DINO / RefineDiT / MoE | 面积＋锐边采样、FP16 坐标舍入；不自动制作粗网格 |
| 03 | 离线导出器与逐文件清单 | safetensors / weights-only PT；固定 target，强制离线，不覆盖既有输出；完整训练权重导出未测 |
| 04 | 五个共用 CPU 稀疏运算及编译在引擎内的 ONNX domain | submanifold convolution、三种池化、两种细分顺序、spatial/channel、packed attention；109 项实际 native ORT 对照；不等于完整 SAM / UniForge 等适配 |
| 05 | 生产 Java adapter、PNG / GLB 素材角色、独立参数和实际模型上限 | 共用扩展 533 项；私有目录、原子提交、失败 / 取消回收 |
| 06 | 共用页面：平级模型、本地管理、可编辑预设、预检、草稿与防重复提交 | 新增 20 项，完整 UI 653 项；推荐顺序保留 |
| 07 | 原生 ARM64 / API28、40 库、16 KiB、原签名 APK，修正应用快照的旧版本号 | 包 / 签名 / 依赖与 Lint 检查；源码、Manifest、构建版本一致 |
| 08 | 30 组 / 5820 程序项、双语指南与 30 用例、保留 H01–H18、30 截图 / 6 GIF / 6 MP4 | 零完整模型下载 / 复制 / 运行；v0.3.4 的 38 JSON 与 40 媒体文件按原 Git blob 归档 |

“原冻结范围完成”仅指原需求的程序接入，不表示此次追加测评中的所有架构都已适配。D06 / D07 新接的是明确披露的几何子集；D11 / D12 / D15 / D16 的既有形状子集继续保留，均不冒充原 benchmark 全流程复现。

| 编号 | 待处理 / 待完成 | 性质 |
| --- | --- | --- |
| 09 | D04 UltraTex：网格 G-buffer、BTD / BSA、匹配扩散 / VAE 与 PBR 烘焙 | 真实代码适配，不能仅登记目录 |
| 10 | D05 UniForge3D：联合 VGGT / DiT、多视图 anchor 路由与 sparse 解码 | 已有共用算子，完整模型流程仍未实现 |
| 11 | D07 Hunyuan3D Paint：独立条件网络、光栅、多视图扩散与贴图烘焙 | 形状已接通，Paint 仍缺代码 |
| 12 | D08 SAM / D09 MV-SAM3D：mask、MoGe / depth、MOT、pose、sparse decoder、相机对齐与融合 | 完整架构适配；DINO 或四图模型不能替代 |
| 13 | D10 SUPRA-Tex：本机材质预测、观察 latent、completion、光栅与烘焙 | 外部背面图服务不能接入，所有阶段须同机 |
| 14 | F5 中文完整官方分词 / 多音字 / 变调等价性 | 现有最长词字典前端仍为实验适配 |
| 15 | MV / RF / Spatial 可公开核验的匹配完整下载端点 | 已有显式转换 / 导入；未核实前不伪造一键下载 |
| 16 | 自动抠图、VLM 部件识别、点云输入、原始 Flash / octree 与新增几何模型贴图 | 已披露子集之外的实现，不与现有功能混计 |
| 17 | 完整训练权重导出 / 推理，手机性能 / 质量 / 锁屏耐久 | 按用户要求不执行；不能写成通过，也不是上述代码缺口的原因 |

原冻结范围不缩减；没有远端 provider、ComfyUI 连线 / 无限画布 / 用户插件体系。下一步仍应继续上表的实际移植，不以程序测试通过宣称“所有适配完成”。[逐项审计](../research/portability/audit-v0.3.5.json) · [程序验证政策](PROGRAM_VALIDATION.md)
