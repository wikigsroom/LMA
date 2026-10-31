# 本地 RF 形状与部件几何

[English](RF_SHAPE.en.md) · [v0.3.4](releases/v0.3.4.md) · [完整范围](IMPLEMENTATION_V034.md)

v0.3.4 新增 `rf_shape_ort` CPU 引擎，以及 TripoSG、PartCrafter 物体、PartCrafter 场景三个平级可选配方。输入一张明确选择的本地 PNG，生成无贴图的 GLB；PartCrafter 的部件各有独立 mesh / node，共用模型坐标系。APK 只提供程序，不含任何模型资产。

## 1. 支持的准确范围

| 配方 | 标签 | 组件与边界 |
| --- | --- | --- |
| `triposg_onnx_cpu_v1` | 生 3D、image_to_3d、sdf_geometry、rf_shape_ort、cpu | 匹配 TripoSG 的 FP32 四图导出；一个物体 |
| `partcrafter_onnx_cpu_v1` | 生 3D、image_to_3d、sdf_geometry、part_level_geometry、cpu | 匹配物体 checkpoint；用户指定 1–16 个部件 |
| `partcrafter_scene_onnx_cpu_v1` | 同上，pipeline:partcrafter_scene | 必须选择场景 checkpoint 的独立导出；不会把物体权重自动变成场景模型 |

原来的 82 个目录包、推荐 `m08 → m06 → m01`、语音 / 单图 / 四视图、F-01–F-12 和 01–14／16／17 全部保留。新增的是三个自选配方，不虚构三个已核实可下载 checkpoint；合计 48 模板、16 扩展引擎加文本、39 原生库。任务 / 能力 / 依赖 / 格式 / 内容标记独立；不从架构推断 NSFW 或 Uncensored。

当前未核实公开的整套匹配 ONNX 下载包，**支持用户本地转换后导入**，以及通过 HF 配方明确选择已经转换且匹配的组件。原始 safetensors / PyTorch 不能直接交给 Android worker。匹配组件不齐、配置不符或资源不足都会本机失败，没有外部推理回退。

## 2. 使用流程

1. 用户自行取得符合原许可的本地 TripoSG / PartCrafter safetensors 快照。保留 transformer、vae、image_encoder_dinov2、feature_extractor_dinov2、scheduler 的配置和配套文件。
2. 在自己的开发电脑上使用下面的离线资产转换工具生成配套图。此步骤只准备文件；App 不连接电脑执行推理。转换会用所选权重执行导出用的虚拟输入前向计算，不能把它称为零计算。
3. 将导出目录复制到手机。通过模型清单导入 `lma-bundle.json`，再为清单内每个组件选择对应本地文件；按字节数 / SHA256 校验，使用现有导入与共享组件机制。只导入 JSON 不等于已经安装权重。
4. 在“模型 → 本地”找到该模型，导入已去背景或白底的 8-bit RGB / RGBA PNG，点击“使用”。PNG 最多 16 MiB、4,194,304 像素；透明区域明确合成白色，不提供自动抠图。
5. 为该模型编辑部件数、步数、tokens、SDF 网格和查询块。保存只影响该模型。先预检，可保存 / 恢复草稿；明确允许尝试未测模型后加入共用本机队列。
6. 查看阶段与进度，按需取消；结果通过 GLB 校验后才提交到结果库。可旋转预览、导出 GLB / 参数来源、编辑后再次生成。取消或失败不发布半成品，等待子进程退出后清理私有目录。

新模型不会自动下载、加载或开始执行。公开 HF 文件名相同也不能证明图和模型匹配；用户必须核对转换配置及实际来源。首次尝试采用最小合法设置可减少开销，但仍不保证 Z20 内存足够。

## 3. 离线转换

开发者需要原生 Python / PyTorch、diffusers 0.35.1、transformers 4.57.6、einops 0.8.1、onnx 1.19.0、safetensors、NumPy / Pillow。本轮参考检查使用 Python 3.13、PyTorch 2.14.0、主机 ORT 1.24.3；APK 复用锁定 ORT 1.28.2 API17。依赖不是模型文件，不需要 Docker / WSL / VM / 模拟器。

```powershell
# 仅取固定源码，--fetch 不下载模型，不运行上游安装器
python tools/fetch_shape_sources.py --fetch
python tools/fetch_shape_sources.py
python tools/export_shape.py --pipeline triposg --snapshot E:/my-assets/TripoSG --output E:/my-assets/TripoSG-LMA
python tools/export_shape.py --pipeline partcrafter --snapshot E:/my-assets/PartCrafter --output E:/my-assets/PartCrafter-LMA
python tools/export_shape.py --pipeline partcrafter_scene --snapshot E:/my-assets/PartCrafter-Scene --output E:/my-assets/PartCrafter-Scene-LMA
```

路径为用户自己的示例，不会被工具自动创建模型。快照必须已有、输出目录必须全新；转换强制离线与 `use_safetensors=True`，拒绝缺配置和不匹配 scheduler，不回退加载 pickle。大权重 FP32 转换需要大量主机 RAM / 存储；本轮只验证随机小网络，**没有执行完整训练权重转换，不能据此保证任意大小权重转换成功**。

导出包括 `shape-config.json`、`image_encoder.onnx`、`flow.onnx`、`cache.onnx`、`query.onnx`、各图实际存在的同名 `.data`、`lma-bundle.json` 和 `export-receipt.json`。清单只含本次真实文件的大小 / SHA256，不含猜测 URL；数据 sidecar 不可省略。图保持 FP32 / opset17；不是任意 ONNX、INT8、FP16 或其他 exporter 格式的通用承诺。

## 4. 原生实现

固定参考为 [TripoSG fc5c409](https://github.com/VAST-AI-Research/TripoSG/tree/fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c) 和 [PartCrafter 3d773bf](https://github.com/wgsxm/PartCrafter/tree/3d773bf02fad51c7ab31a5615573fec93b287b30)。[源码锁](../third_party/rf-shape-source-lock.json)逐文件 SHA256；模型权重仍须遵循原许可，仓库根目录许可不能覆盖每个文件或模型的附加条款。

```text
用户 PNG → 白色 alpha 合成 / bicubic / center crop / normalization
  → DINOv2 image_encoder → RF / 部件 DiT flow（逐步、分开 CFG）
  → 每部件 VAE cache → 分块 SDF query
  → 有界均匀网格 marching tetrahedra → 含独立节点的内部 GLB
```

采样保留上游 `sigma_now - sigma_next` 更新方向和 shift；注意力保留发布者逐 head 的 QKV 打包，而不是改变 checkpoint 的布局。PartCrafter 保留全局 / 局部注意力、part embedding 和 U-skip；CFG 条件 / 无条件分开运行，同一组 part IDs 不跨 CFG 批次混合。VAE 返回的 SDF 符号、缓存与分块查询均和固定源码小网络对照。

PartCrafter 上游 VAE 无条件导入 `torch_cluster.fps`，此处仅用于点云 encoder。转换器从已核对源码 AST **只把这一 import 替换为明确拒绝点云编码的 guard**，解码指令不变；不伪造 FPS、不安装 CUDA 扩展，也不声称接通点云输入。

手机同一进程顺序加载各阶段，保持一个 ORT session；VAE query 复用 cache。无 Python、网络 provider、shell、远端节点或模型提供的可执行代码。固定组件文件名、仅允许披露的外置 data、尺寸 / 非有限数 / 图片 / 三角面限制和 GLB 自包含校验共同保护输入。

## 5. 参数与资源

| 参数 | 应用保护范围 / 默认 |
| --- | --- |
| CPU threads / steps / seed | 1–16 / 2；1–100 / 30；0–2,147,483,647 / 1234 |
| tokens / part | 512–4096，512 对齐；TripoSG / 场景默认 2048，物体部件默认 1024 |
| parts | TripoSG 固定 1；PartCrafter 1–16，默认 3，且不能超过导出模型上限 |
| grid | 单轴 32–256，16 对齐，默认 64；点数为 `(grid+1)^3` |
| queryChunk / guidance | 128–4096 / 512；0–15 / 7，遵循上游 guidance > 1 才启用 CFG |
| maxTriangles | 全部部件合计 1000–1,000,000，默认 300,000；超限报错，不静默裁剪 |

这些是程序上限，不是手机容量保证。部件数 × tokens 会显著增加全局注意力计算和内存；减小查询块只减小对应查询阶段开销，不减小大 DiT 权重。uniform grid 与上游 Flash / octree 提取器不同，输出几何也可能不同。

## 6. 检查、媒体与待办

| 编号 | 本轮程序检查 | 证据 |
| --- | --- | --- |
| R01 | 68 个图 / 数学 / 预处理对照，包含 1 / 2 / 3 / 16 部件与动态 tokens / 查询点 | [shape.json](../verification/program/shape.json) |
| R02 | 30 次实际 native 进程，三条 pipeline 的成功 / 配置 / 路径 / 缺件 / 空曲面 / 三角面保护 | [同一记录](../verification/program/shape.json) |
| R03 | Java 生产 adapter、存储、取消与错误回收；共用扩展合计 428 项 | [expansion.json](../verification/program/expansion.json) |
| R04 | 17 个新增页面检查；完整页面回归纳入同一版本 | [UI](../verification/program/ui.json) |

![部件设置，桌面 UI FIXTURE，非模型输出](media/development/shape/03-part-settings.png)

[五张截图与身份](media/development/shape/manifest.json) · [GIF](media/development/shape/shape-ui.gif) · [MP4](media/development/shape/shape-ui.mp4)。页面内三个模型是明确的模拟导入项；没有伪造训练输出。所有浏览器资源 finally 关闭。

本轮完整模型下载 / 复制 / 运行均为 0，无真机。完整训练权重导出、手机内存 / 速度 / 模型质量和锁屏耐久未测；按用户要求不作为后续开发前置项。自动分割 / VLM 部件识别 / 纹理 / 原始 benchmark 全流程未实现，不以编译通过冒充。

测评仍有 D04 UltraTex、D05 UniForge3D、D06 UltraShape、D07 Hunyuan3D 2.1、D08 SAM 3D、D09 MV-SAM3D、D10 SUPRA-Tex 共七条配置 / 六组架构待真正原生移植。[固定审计](../research/portability/audit-v0.3.4.json)保留这些开发缺口；D11 / D12 / D15 / D16 现为上述匹配导出形状子集，并非逐项测评复现。

另有两条真实 CLI 检查：以随机小网络保存的 safetensors 进行离线加载、位置编码插值导出、组件清单 / data / 实际 SHA256 核对。Two documented CLI checks use only tiny random safetensors; complete trained checkpoint export remains untested.
