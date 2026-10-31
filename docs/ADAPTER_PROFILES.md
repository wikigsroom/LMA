# v0.3.6 本地适配方案与操作

[English](ADAPTER_PROFILES.en.md) · [编号收口表](REMAINING_ADAPTATION.md) · [API](API.md) · [许可证](../THIRD_PARTY_NOTICES.md)

本版补齐 P01–P06 的程序集成，提供 **62 个组件配方、82 套目录模型包、18 个扩展引擎加文本引擎**。配方是可选的资产组合方式，不等于预装或下载了模型。新增 3D / 视觉配方支持用户匹配转换后导入；尚未核实完整公开导出包的下载端点，不提供占位下载链接。

所有模型平级。用户可按生文、生图、生视频、生音频、生 3D、能力、引擎、后端、组件格式、内容标签和安装状态筛选。NSFW / Uncensored 标签独立于可运行性；未分类的用户导入不自动获得已核对内容标签。推荐顺序仍为 `m08 → m06 → m01`。

## 1. 模型、输入和实际执行路径

| 编号 | 配方 / 上游配置 | 用户输入 | 手机内执行 | 输出 / 边界 |
| --- | --- | --- | --- | --- |
| P01 | D04 UltraTex · FLUX.1 / FLUX.2 | 材质描述、参考 PNG、已有静态 GLB | CLIP＋T5 或 Qwen3 分词 / 编码、六视图几何条件、tile VAE / BN、albedo / MR 独立 LoRA 流、packing、CFG / Euler、解码、UV / PBR 烘焙 | 带材质 GLB；不是只注册 FLUX 算子 |
| P02 | D05 UniForge3D | 正 / 右 / 背 / 左四张 RGBA PNG | 联合 VGGT / DiT、DINOv3、四层条件、anchor 路由、结构及 SLAT 两阶段、FDG、材质解码 / 烘焙 | 带材质 GLB；联合网络不替换成四次单图 |
| P03 | D08 SAM 3D Objects | 单张 RGBA PNG；可显式选本地抠图模型准备输入 | MoGe、三支图像条件、MoT 结构 / pose、占据、SLAT、FlexiCubes、颜色 / 辅助通道 | GLB 顶点色与 `_SAM_AUX`；不冒充完整 Gaussian 外观烘焙 |
| P04 | D09 MV-SAM3D | 四张独立 RGBA PNG | 联合 DA3 与独立度量深度、对齐、逐视图条件、MultiDiffusion 权重融合、SS 预热与状态回放、SLAT 新随机流 | 融合 GLB；不是单图模型重复四次 |
| P05 | D10 SUPRA-Tex | 已有 GLB、对齐的 1024×1024 RGBA、相机 JSON | Qwen3-VL 特征 / 双 PBR 目标、Qwen VAE、FDG / 可见性、SCVAE 编码、交错 completion、原网格材质烘焙 | 原始几何带 PBR；无外部背面图、无远端服务 |
| P06a | DIS / ISNetDIS | RGB 或 RGBA PNG | 固定源码预处理、ONNX CPU 前景预测、恢复原尺寸 alpha | RGBA PNG；恒定无效 mask 拒绝 |
| P06b | llama.cpp mtmd 视觉语言模型 | PNG、用户匹配的主 GGUF 与 mmproj | 同机分词、图像编码、模型 chat template、JSON grammar、解码 | 严格 `parts` 文本结果；1–16 个唯一部件名称 |
| P06c | TripoSG / PartCrafter 点云 VAE | 已归一化 XYZ＋单位法线 JSON | 4×token 采样、FPS、实际点编码器、mean / sample 后验、cache / query、曲面提取 | 单个整体 GLB；不运行图片扩散 |
| P06d | RF 原始曲面提取 | RF 或点云 VAE 的 SDF | `uniform`、`publisher_octree`、`publisher_flash` 可选；原版 Lewiner / DISO 前向内核的有界 CPU 移植 | GLB；后两者有独立来源对照，不以普通均匀网格冒充 |
| P06e | 固定同机准备 / 材质链 | 用户已安装且明确选择的辅助模型 | 可选抠图 → 可选 VLM 部件数 → 主几何 → 可选 Hunyuan Paint / UltraTex | 只提交最终 GLB；中途失败、取消或缺组件均清理，不回退到远端 |

原 Hunyuan3D 2.1 Shape、UltraShape 精修、Hunyuan Paint、TRELLIS / Pixal、单图 / 四图、语音和社区图像 / 视频路线继续保留。F5 的官方兼容前端及语言资产见 [F5 指南](F5_FRONTEND.md)。

## 2. 安装与使用逻辑

1. 安装 Release APK，进入“模型”。浏览推荐、全部 / HF 搜索不会下载模型。ARM64 / Android 9+ 是程序要求，不是大型模型的内存保证。
2. 选择已核对目录包并主动下载，或在配方中明确选择匹配组件、导入用户自己的导出文件。一个配方的编码器、投影、VAE、主网络、tokenizer 和外部 ONNX data 必须来自同一转换方案。原始 PyTorch 权重不能直接当作 Android 运行包。
3. 在“本地”完成下载 / 导入并检查安装状态。共享组件按哈希复用；删除一个模型不删除仍被其他模型引用的文件。缺少组件不允许开始生成。
4. 打开目标模型的独立设置。整数 / 数值采用可编辑预设输入，枚举采用选择框；大于模型或应用上限会归位。RF 的 `denseDepth` 不高于 `octreeDepth`，视觉输出 token 不高于 `context−1`。运行内存仍受单独保护。
5. 对几何模型，可选“自动前景模型”“自动部件识别模型”“几何完成后的材质模型”。只显示已完整安装的兼容模型，默认“不使用”。部件识别只用于 PartCrafter 部件数；材质不能循环调用自身。UltraTex 后续材质描述单独填写，辅助模型保留自己的设置。
6. 点击“使用”，选择表单要求的本地素材。UniForge / MV-SAM 必须选择四个视图；SUPRA 必须选择匹配的网格、相机和图像。点云配方选择后续材质时还须提供参考 PNG。
7. 先运行前检查，再按需保存草稿或加入队列。预检检查资产、类型、参数和资源，不运行模型。未测配方需要明确勾选尝试；草稿恢复后重新确认。任务运行中可取消，结束后查看 / 导出结果及来源记录。
8. 辅助模型在执行时受组件租约和完整性核验保护。记录包含每个实际阶段的模型 ID、组件哈希和生效参数；模型被删除或不匹配时任务明确失败。辅助模型保存设置在阶段执行时读取，不宣称排队前已冻结所有辅助参数。

这是固定内部流程，不提供连线、无限画布、用户节点、外部执行插件或 ComfyUI 图导入。API 客户端可以调用手机提供的接口；模型运算始终留在该手机。

## 3. 相机与点云文件

相机和点云使用 UTF-8 JSON，导入后为 `application/vnd.lma.data+json`。程序按内容识别，不依赖 Android 文档选择器提供的扩展名。任意 JSON 和生成后的文本结果不能伪装成输入；具体角色还会检查对应 schema。

SUPRA 相机最小示例（视场角为弧度；值必须与用户网格和参考图一致）：

```json
{"schema":"lma.camera/1","distance":3.0,"camera_angle_x":0.7,"mesh_scale":1.0}
```

也可提供 `extrinsic` 4×4 与 `intrinsic` 或 `projection_intrinsic` 3×3 矩阵。仅填写有效尺寸不等于校准正确，不自动推断相机。

点云格式：

```text
schema:      lma.pointcloud/1
coordinates: publisher_normalized
points:      [[x,y,z,nx,ny,nz], ...]
```

必须有 16–16,384 点、每点六个有限数、各分量在归一化范围内、法线接近单位长度。`points×tokens` 不高于 16,777,216。程序不默默截断点云，也不自动生成缺失法线。以下代码仅生成格式演示，不能作为训练模型效果验收：

```python
import json, math
points = [[.5*math.cos(i*math.tau/16), .5*math.sin(i*math.tau/16), 0,
           math.cos(i*math.tau/16), math.sin(i*math.tau/16), 0] for i in range(16)]
with open("points.json", "w", encoding="utf-8") as f:
    json.dump({"schema":"lma.pointcloud/1","coordinates":"publisher_normalized","points":points}, f)
```

## 4. 用户离线准备资产

转换工具在用户自己的准备环境运行；导出后的所有推理阶段在手机执行。工具不读取远程模型 ID、不启用 `trust_remote_code`，不运行上游安装脚本，不覆盖已有输出，不把转换后的权重放进 APK。源码和构造参数必须匹配锁定上游，safetensors 的缺键、错形状、额外键和非有限值均拒绝；SAM 只重建可证明共享存储的权重别名。

```powershell
python tools/export_uniforge.py --profile INPUTS/uniforge.json --output EXPORTS/uniforge
python tools/export_sam.py --profile INPUTS/sam.json --output EXPORTS/sam
python tools/export_sam.py --profile INPUTS/mv-sam.json --output EXPORTS/mv-sam
python tools/export_supra.py --profile INPUTS/supra.json --output EXPORTS/supra
python tools/export_pointcloud.py --pipeline triposg --snapshot INPUTS/triposg --output EXPORTS/points
python tools/export_foreground.py --weights INPUTS/isnet.safetensors --size 1024 --output EXPORTS/foreground
```

| 工具 | 用户本地 profile / 配套输入 | 生成的必需运行组件 |
| --- | --- | --- |
| UniForge | `schema:lma.uniforge-local-inputs/1`；`stages` 含 dino、joint、conditioner、shape512、shape1024、texture、structure_decoder、shape_decoder、texture_decoder；需要配置的阶段提供本地 `config`，各阶段提供本地 `weights`；joint 的 `withStage1Lora` 显式选择 | 配置＋14 个网络图；外部 data 按实际产生选择 |
| SAM / MV-SAM | `schema:lma.sam-local-inputs/1`；`target:D08|D09`；`models` 与 `runtime`，模型的参数 / 权重按所选上游配置填写；MV 额外 DA3 | 单图配置＋7 图；多图配置＋8 图；锁定辅助来源 |
| SUPRA | `schema:lma.supra-local-inputs/1`；本地 `processor`、`resolution:1024`、text / vae / pbr / shape_encoder / material_encoder / shape_decoder / material_decoder / completion 阶段本地配置和权重 | 配置＋tokenizer＋9 图 |
| 点云 VAE | 匹配 TripoSG / PartCrafter 的本地 VAE snapshot | 配置＋encoder / cache / query 三图 |
| DIS | 用户匹配的 ISNetDIS safetensors；256 / 512 / 1024 导出尺寸 | 配置＋foreground 图 |
| VLM | 支持所固定 llama.cpp mtmd 的视觉 GGUF＋同模型 mmproj | 两个独立用户选择的 GGUF，不接受任意投影混配 |

profile 中的网络构造参数是发布权重所用参数，不能用随机测试中的小维度替代。工具对正式配置执行严格检查；不匹配的 checkpoint 会明确失败。profile 字段及严格检查以相应工具的 `prepare()` 为准。

UltraTex 需要 `--family flux1|flux2`、`--flow-config`、`--flow-weights`、`--vae-config`、`--vae-weights`、`--albedo-lora`、`--mr-lora`、`--mr-decoder`、`--output`；FLUX.1 另外给 `--clip` 与 `--t5`，FLUX.2 给 `--qwen`。这些路径全部是用户本地配置 / 权重 / tokenizer 目录。可用 `--image-size` 和显式 `--lora-scale`；不要把 FLUX.1、FLUX.2、Klein guidance 配置混用。完整生成的运行清单包含逐文件大小和 SHA256，须按清单选择配置、所有图及实际外部 data 文件。更多网络细节见 [UltraTex](ULTRATEX_FLOW.md)。

## 5. 资源、数值与许可证边界

- CPU profile 使用 FP32 网络及有界稀疏 / 光栅处理，不能承诺复现上游 CUDA / BF16 / FP16 的数值、速度或质量。固定 tie 顺序、MT19937 与上游 NumPy PCG64 / Torch CUDA 随机流不同。
- UniForge 稀疏阶段最多 20,000 行，几何 / 材质辅助坐标上限 262,144；SAM 最多 4,096 行；SUPRA 使用固定 1024 观察条件。超预算明确失败，不通过截断伪造成功。
- 原始 RF 提取目标深度 5–8、初始深度 3–目标深度、分块不超过 4,096。Flash 的上游最终 SDF 正比例缩放与 CPU profile 不同，零等值面相同；测试按恢复后的原始场比较，保留披露。
- SAM 输出顶点色与源辅助通道；需要 PBR 可显式再选择已安装的 Paint / UltraTex。UniForge 不执行上游 CUDA 重网格 / 补洞 / 减面；本地材质光栅与视图融合的差异单独保留。
- 主应用代码 MIT 不改变依赖许可证。DISO 前向 CPU 移植适用 **CC BY-NC 4.0（非商业）**；其余完整许可随 APK 和源码附带。模型、LoRA、DINO、深度、tokenizer 等仍须遵守各自权重条款。
- 本版只做程序验证：源码定义和形式配置、随机小网络 / 实际 ORT、生产任务 / 取消 / 清理、页面、APK、签名和 Lint。没有下载 / 运行完整训练模型，没有手机推理、质量、速度、峰值内存或锁屏耐久结论。努比亚 Z20 的 ARM64/API 条件不等于能运行这些大型 3D 模型。

## 6. 程序验证与页面证据

[当前机器证据](../verification/releases/v0.3.6/status.json) · [适配审计](../research/portability/adaptation-current.json) · [新页面 GIF](media/development/adaptation/adaptation-ui.gif) · [MP4](media/development/adaptation/adaptation-ui.mp4)。页面使用真实生产资源和明确标注的 UI FIXTURE 桥，展示选择 / 参数 / 任务逻辑，不展示伪造的模型生成结果。历史版本证据继续保留在 `verification/program/` 与 `verification/history/`。
