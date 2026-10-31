# UltraTex 网络组件转换

[English](ULTRATEX_FLOW.en.md) · [完整待办](REMAINING_ADAPTATION.md) · [本地材质](LOCAL_MATERIALS.md)

**当前是网络组件转换工具，UltraTex 尚不能作为完整 App 配方运行。** 它补齐实际 FLUX.1 dev / FLUX.2 网络、LoRA、前景压缩与位置编号的导出，未将模型登记成可下载或可运行项。文本编码、匹配 VAE、UltraTex 条件准备、采样与 App 编排仍需完成。

| 编号 | 已实现 | 边界 |
| --- | --- | --- |
| U01 | 固定源码中的 FLUX.1 dev | 双流 / 单流块、调制、RoPE、文本 pooled vector、蒸馏 guidance 和 BSA；不转换为其他 FLUX 架构 |
| U02 | 固定源码中的 FLUX.2 | 支持 guidance / Klein 无 guidance 两种构造；使用训练时的普通联合参考序列，不误用 causal KV-cache 路径 |
| U03 | 动态前景 | 目标与法线分别压缩，保留原始坐标及单图参考；输出预测和原目标索引，支持批量 1–2 |
| U04 | LoRA | FLUX.1 processor 两因子、FLUX.2 固定 PEFT 格式；维度、目标、因子、有限值全部检查通过后才修改权重 |
| U05 | 精确旋转查找表 | FLUX.1 原始双精度三角函数转 float32，导出为 0–8191 整数位置表，避免 Android ORT 缺少双精度 Cos；逐值对照上游，表随用户资产走 |
| U06 | 本机 CPU / ORT | 共用已编译内置 BSA，FP32 / BF16 注意力；没有 Triton、CUDA 安装器或下载式执行插件 |
| U07 | 离线转换与回执 | 显式本地 safetensors、严格基础权重匹配、SHA256、来源修订、完整缺口；已有输出目录立即拒绝覆盖 |

源码固定为 `yiboz2001/UltraTex@a726678f3f3631fe2c5e3d1fb4597114784c7a8b`，8 个文件的逐文件哈希见 [来源锁](../third_party/ultratex-flow-source-lock.json)。只加载已列明的类和函数，不导入上游训练或推理脚本，不执行 caption 缓存、安装器或下载帮助函数。Apache 许可与 SLA 条款见应用已有 notices；实际模型权重另遵各自许可。

## 转换逻辑

这是开发者离线准备程序，需原生 Python、CPU PyTorch、ONNX、einops、safetensors 及锁定源码。若本机尚无源码，使用项目已有 `tools/fetch_spatial_sources.py` 获取固定修订的源码；该脚本不获取权重。

```powershell
python tools/export_ultratex_flow.py --family flux1 `
  --config E:/models/ultratex/flux1-parameters.json `
  --weights E:/models/ultratex/flux1-base.safetensors `
  --lora E:/models/ultratex/flux1-lora.safetensors `
  --output E:/models/ultratex/flow-export-new
```

`--config` 为固定源码对应 `FluxParams` / `Flux2Params` 的构造参数 JSON；必须与用户基础权重的尺寸一致。`--family flux2` 接受匹配 FLUX.2 构造和 PEFT 权重。`--lora` 可省略；`--lora-scale` 默认为 1，允许 -4 到 4。默认保留 BF16 注意力概率转换，`--float-attention` 显式选择 FP32。完整模型转换可能需要大量桌面内存；程序检查仅使用小型随机架构。

输出包含 `flow.onnx`、需要时的外部 tensor 数据及 `export-receipt.json`。回执明确 `complete_adapter=false`、`app_recipe_registered=false`，**不会生成冒充完整模型的 `lma-bundle.json`**。路径和本地文件名不写入回执；记录来源、角色、尺寸和哈希。

FLUX.1 输入位置编号是 int64、0–8191，FLUX.2 为源码的 float32 位置。mask 是与批量共用的一维 int64 0/1，目标至少一个前景 token；输入必须为有限值。输出索引供未来同机采样恢复目标位置。单个 ONNX 文件不承担完整任务预检；这些范围是组件调用者必须满足的契约。BSA 工作量上限与同分数排序遵循已有实现和披露。

## 程序证据与未完成部分

101 项检查实际执行固定源码的随机双流 / 单流网络、导出的动态 ONNX 和生产 C++ ORT / BSA：不同目标 / 法线 / 参考 / 文本长度、批量、无背景注意力、原位置影响、参考影响、FP32 / BF16、精确上游 RoPE、未合并上游 LoRA processor 对照、缺因子 / 非有限值的原子拒绝、两种真实转换 CLI 与不覆盖旧目录。没有下载或运行完整训练模型、没有手机或虚拟化运行。

[检查记录](../verification/adaptation/ultratex-flows.json) · [测试入口](../tools/test_ultratex_flows.py)

完整 UltraTex 仍缺同一手机上的 CLIP / T5 或 Qwen3 分词与编码、各自 tile VAE / BN 及材质解码器、规范几何条件 / token packing、Euler / CFG 与黑背景恢复、albedo / MR 两次流程、模型资产 / 参数 / 子进程 / PBR 烘焙编排。这些继续属于原完整交付范围，不能因网络图检查通过就标成已完成。
