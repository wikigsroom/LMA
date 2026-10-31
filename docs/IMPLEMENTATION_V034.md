# v0.3.4 实现与待办

[English](IMPLEMENTATION_V034.en.md) · [完整方案](RF_SHAPE.md) · [机器矩阵](../catalogue/release-0.3.4-implementation.json)

原冻结 F-01–F-12、生文、01–14／16／17、九个 MOSS 子目标、SD1.5 / SDXL LoRA、社区与语音 / 单图 / 四视图全部保留。48 模板、82 目录包、16 扩展引擎加文本；模型资产始终由用户选择。新增三个自选导出配方不冒充已核实公开下载包。

| 编号 | 本轮已实现 | 检查与边界 |
| --- | --- | --- |
| 01 | `native/rf_shape`，DINOv2 / RF 或部件 DiT / cache / SDF query / 网格 / 内部多部件 GLB | 68 项固定源码随机小图、数学及预处理对照；30 次实际主机 native 流程 |
| 02 | TripoSG、PartCrafter 物体 / 场景三条平级 CPU 配方 | 5 个必需角色及实际 data，FP32 / opset17 / 固定源码身份，无猜测 URL |
| 03 | 离线 safetensors 转换与带真实文件 SHA256 的清单 | 禁联网加载、pickle 回退、覆盖已有导出；完整训练权重转换未测 |
| 04 | 生产 Java adapter、组件导入、独立参数、PNG 输入、私有 workspace、原子结果与取消 | 共用扩展 428 项，错误 / 取消后子进程退出和目录清理 |
| 05 | 通用 3D 表单复用：本地管理、归位、预检、草稿、恢复和防重复提交 | 新增 17 页面项；完整 633 项；推荐 m08 → m06 → m01 保留 |
| 06 | Android ARM64 / API28 worker、原签名 APK、39 库、16 KiB、依赖闭合 | Lint 0 错误 / 16 既有警告；27 组 / 5,306 程序项 |
| 07 | 双语说明、27 用例、保留 H01–H18、25 截图 / 5 GIF / 5 MP4 与历史原样归档 | v0.3.3 的 36 JSON / 四组媒体保留 Git 原字节；零训练模型下载 / 复制 / 运行 |

“冻结范围完成”仍仅指原冻结需求；不是所有新增研究模型的支持承诺。D11 / D12 / D15 / D16 接入的是匹配导出的形状子集，未复现测评原始完整 workflow。

| 编号 | 剩余事项 | 性质 |
| --- | --- | --- |
| 08 | D04 UltraTex：网格 / 光栅、BTD / BSA、VAE 与烘焙 | 真实原生移植开发 |
| 09 | D05 UniForge3D：VGGT / anchor 多视图 / sparse 解码 | 真实原生移植开发 |
| 10 | D06 UltraShape：coarse mesh / voxel-query / RoPE | 真实原生移植开发 |
| 11 | D07 Hunyuan3D 2.1：flow / VAE / 曲面与独立 Paint | 真实原生移植开发 |
| 12 | D08 SAM 3D / D09 MV-SAM3D：mask / depth / sparse / pose / scene fusion | 真实原生移植开发，不把 DINO / 四图能力当成 SAM |
| 13 | D10 SUPRA-Tex：材质预测 / completion / raster；外部背面图阶段不可接入 | 需要全部本机替代路径 |
| 14 | MV / RF Shape 已匹配权重的可公开核验下载端点 | 已有显式导入 / 自选配方；未核实前不显示一键下载 |
| 15 | 自动抠图、VLM 部件识别、纹理、点云输入和原始 Flash / octree | 不在已接通形状子集内；需要额外实现，不冒充已有能力 |
| 16 | F5 中文前端与官方完整分词 / 变调的等价性 | 仍为实验适配；已有显式文本方案，不声称完整等价 |
| 17 | 完整训练权重导出 / 推理、手机性能 / 质量 / 锁屏耐久 | 按用户要求不执行，不能记录为通过；不是代码移植工作的替代 |

不用 Docker / WSL / VM / 模拟器；不增加外部推理、连线画布或用户插件体系。[审计与每项缺口](../research/portability/audit-v0.3.4.json) · [程序策略](PROGRAM_VALIDATION.md)
