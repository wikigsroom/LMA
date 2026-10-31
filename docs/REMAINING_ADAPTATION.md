# 后续完整适配清单

[English](REMAINING_ADAPTATION.en.md) · [F5 前端](F5_FRONTEND.md) · [本地 PBR](LOCAL_MATERIALS.md) · [原冻结需求](MULTIMODAL_RELEASE_PLAN.md)

此页跟踪 v0.3.5 之后的开发源码。下载页已发布的 v0.3.5 不包含下表新功能；不能将源码检查或目录登记写成完整模型适配。所有工作共用同一完整交付范围，不把未完成模型自动顺延到另一个工作版本。

## 1. 不变的产品约束

| 编号 | 要求 | 当前处理 |
| --- | --- | --- |
| A01 | APK 只更新基座 | 不附权重、音色、分词器或语言表；用户明确选择模型和依赖，再下载 / 导入 / 管理 |
| A02 | 所有模型平级 | 生文、生图、生视频、生音频、生 3D、能力、格式、引擎、后端、许可、内容标签和安装状态独立 |
| A03 | 推荐 / 全部 / 本地 | 保留 `m08 → m06 → m01`；HF 全部和搜索继续发现其他仓库；本地管理已选资产和未完成传输 |
| A04 | 参数跟随模型 | 可编辑预设；上限由模型和基座共同约束；过大值自动归位；不扩大未知模型上限 |
| A05 | 全部同机 | 编码、采样、解码、codec、光栅和合成都在手机；无 ROOT、远端推理、LAN fallback 或用户执行插件 |
| A06 | 保留全量原范围 | F-01–F-12、文本、01–14／16／17、九个 MOSS 子目标、SD1.5 / SDXL LoRA、全部既有社区 / 语音 / 单图 / 四图 / RF / Spatial 路线 |
| A07 | 轻量工作台 | 共用表单、预检、草稿、队列、取消、任务恢复和结果库；不建设 ComfyUI 连线、无限画布、节点或插件系统 |
| A08 | 程序验证 | 编译、实际生产协议、随机小网络、错误 / 取消 / 回收、页面、包和签名；不获取 / 运行完整训练模型，不重复要求手机 |

## 2. 此次已补齐的程序模块

| 编号 | 模块 | 实现与证据 |
| --- | --- | --- |
| B01 | F5 官方兼容中文前端 | 固定 rjieba / jieba-rs DAG＋HMM、pypinyin 多音字和变调、F5 标点 / 混合文本 / 词表 ID；2,222 组文本、6,671 项真实 C++ 对照；旧前端配方保留 |
| B02 | 前端资产由用户选择 | 新模板要求 `f5-frontend.json`，字典不进 APK；离线准备、来源锁、许可、实际字节 / SHA256；Java 导入、组件格式 / 大小、工作目录传递 |
| B03 | Hunyuan3D 2.1 Paint | 参考 PNG＋已有 GLB → 六视图条件 → DINO / VAE → 双材质 UNet / 参考和多视图注意力 / RoPE → UniPC → VAE → 可选 RealESRGAN → UV / PBR GLB；不是用形状网络替代 Paint |
| B04 | 共用本地材质几何 | 有界 CPU 光栅、遮挡、法线和位置图、xatlas、视角融合、最近可见 texel 填充；正确转换 metallic-roughness 通道并保留原始网格坐标 |
| B05 | Paint 离线资产准备 | 读取用户本地匹配 safetensors / weights-only 权重，固定源码类、五图导出、1–100 步采样程序、逐文件清单；实际 CLI 使用随机网络检查，不覆盖已有输出 |
| B06 | Paint 应用闭环 | 七个必需组件、独立参数及输入角色、本地管理、预检 / 草稿 / 防重复提交、共用子进程、取消 / 失败清理、原子结果、内嵌 PNG / UV / PBR 预览与 GPU 资源释放 |
| B07 | UltraTex 所需 BSA 基础算子 | 固定 SLA block means / smooth-K / top-k / online softmax，FP32 / BF16 与有界 CPU / ONNX bridge；它仍不是完整 UltraTex 适配 |
| B08 | 文档和演示 | 双语操作 / 资产 / 转换 / 范围说明、当前编号清单、生产页面 fixture 截图 / GIF / MP4；原 README 用例、API 示例、历史案例不删除 |

CPU 材质实现明确披露与上游 CUDA 光栅、腐蚀 / 修补和随机流的差异。BSA 对同分数采用固定索引顺序；Torch / CUDA 的 `topk(sorted=False)` 不保证跨设备同序。这些检查不构成完整训练模型、论文质量或手机资源验收。

## 3. 仍必须实施的模型流程

| 编号 | 测评项 | 必须补齐的生产路径 | 已有但不足的基础 |
| --- | --- | --- | --- |
| P01 | D04 UltraTex | FLUX.1 / FLUX.2 对应资产、LoRA、条件图、BTD mask 压缩与位置编号、匹配 VAE / 文本编码、扩散和 PBR 烘焙；用户参数与模型清单 | 通用光栅 / UV / 烘焙、BSA 算子；不能登记为已运行 UltraTex |
| P02 | D05 UniForge3D | 联合 VGGT / DiT、DINOv3、多视图 anchor 与联合特征、稀疏结构 / SLAT 采样、FDG / 材质解码及 GLB | 卷积、池化 / 细分、packed attention；不以 TRELLIS 或普通四图替代联合网络 |
| P03 | D08 SAM 3D Objects | mask、MoGe 点图、MoT 结构与布局 / pose、SLAT 与 FlexiCubes、选定输出的几何 / 外观及 GLB | 五类稀疏 CPU 算子；必须保留 SAM 的池化分母和坐标顺序 |
| P04 | D09 MV-SAM3D | D08 基础、Depth Anything 3、多相机对齐、权重融合与 MultiDiffusion、首步预热 / 回退重放 | 既有四图方案不能代替该模型；不以单图重复执行冒充多视图 |
| P05 | D10 SUPRA-Tex | 本机 Qwen 材质前端、几何 / 观察 latent、交错 completion 网络与 SCVAE、PBR 光栅 / 烘焙 | 共用 sparse 与材质基座；禁止接入外部背面图或其他远端推理服务 |

这些是实际源码缺口，用户免去完整模型验证并未免去开发。当前**没有完成全部适配**，不可仅因编译或已有冻结范围测试通过而发布成“全适配完成版”。

## 4. 其他范围与验证状态

| 编号 | 工作 | 状态 / 收口原则 |
| --- | --- | --- |
| P06 | 已披露子集之外的自动抠图、VLM 部件识别、点云输入、原始 Flash / octree 和其他新增几何模型贴图 | 缺独立实现的部分继续列明；不把 CPU 均匀网格或手动输入写成原始全流程复现 |
| P07 | 匹配完整公开导出包 | 尚未核实 Spatial / RF / MV 的完整公开下载端点；继续支持用户显式转换 / 导入，不造 URL、不默取数据 |
| P08 | 完整模型 / 手机实测 | 按用户指令不执行；记录为未测，绝不把它作为 P01–P06 没有代码的理由，也不再要求提供手机 |
| P09 | 当前代码统一验证与交付 | 每次变更更新源码指纹、独立检查、相关媒体、双语说明；原发布标签与文件不替换。正式发布条件包括对应实际范围，不只检查旧计数 |

当前详细操作见 [F5](F5_FRONTEND.md) 与 [PBR](LOCAL_MATERIALS.md)，页面演示见 [GIF](media/development/material/material-ui.gif) / [MP4](media/development/material/material-ui.mp4)。演示全部带 **UI FIXTURE** 标记，代表真实生产页面加模拟桥，不代表手机或训练模型输出。机器清单由 `tools/audit_adaptations.py` 生成，放在 `research/portability/adaptation-current.json`。
