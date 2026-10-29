# 旧 LTX 文本精度定位

[English](LTX098_PRECISION.en.md) · [完整提示词链路](LTX098_PIPELINE.md) · [本轮编号交付](releases/v0.3.0-dev.21-ltx-precision.md) · [同版完整范围](MULTIMODAL_RELEASE_PLAN.md)

旧 LTX 0.9.8 的完整原始前向对照仍是 **163 项检查中 157 通过、6 项浮点门槛失败**。本轮增加可复现的逐层诊断及隔离精度候选，保持原模型实现、原始参考前向、数值门槛和 APK 不变。诊断比较数量不表示通过了新的模型验收。

## 实际证据

| 编号 | 内容 | 范围 |
| --- | --- | --- |
| D-01 | 314 个训练中间张量对照 | embedding、24 层各 13 处观测、最终归一化；原生与原始 Transformers 各一份 |
| D-02 | 628 份原始张量哈希 | 全量核对字节数 / SHA，并独立重算 314 项最大误差与相对 RMSE；原始数组留在忽略的 `build/` |
| D-03 | 120 项同输入算子对照 | 24 层各自的两种 RMS norm、GeGLU、SDPA 和 eager attention；原始 Torch 算子使用捕获的相同原生输入 |
| D-04 | 基线身份 | 带观测的原生最终 embedding 与既有原生结果逐字节一致；原始前向最终 embedding 与既有独立参考逐字节一致 |

观测对象是提示词 A 的 53 个 token、全部 219 个训练张量、24 层 Google/community Q5 T5。原始 Transformers 实际选择 `sdpa`；前向 hook 只保存结果，不替换返回值或重写方程。分块权重装卸仍由既有参考实现负责。

最终 embedding 最大误差为 `2.3752450942993164e-5`，相对 RMSE 为 `1.5835138112703526e-6`，与上一轮失败链路的文本端完全一致。完整视频轨迹会放大这类微小差异，不能用文本端的低误差替代完整链路对照。

![主机文本数值定位，非 App 或手机验收](media/development/ltx098-text-roundoff.png)

图左比较各层原生结果与原始模型前向，包含此前层的累积差异；图右让原始算子直接消费相同原生输入，隔离该算子的局部差异。纵轴是各完整张量的相对 RMSE，对数刻度，24 个真实观测点，不是图片画质或手机性能曲线。

| 同输入局部对照 | 24 层中的最大绝对误差 |
| --- | --- |
| 注意力输入 RMS norm | `7.152557373046875e-7` |
| FFN 输入 RMS norm | `9.5367431640625e-7` |
| GeGLU | `7.62939453125e-6` |
| 注意力混合 vs 原始 SDPA | `1.049041748046875e-5` |
| 注意力混合 vs 原始 eager 算子 | `1.1444091796875e-5` |

这些数值不能单独证明某一个算子是全部偏差的根因；eager 是额外局部诊断，未被用来替换原始完整参考的 SDPA。也不证明原始未量化 Google、PixArt 权重身份、官方多尺度默认、语义或运动质量。

## 隔离精度候选

`research/ltx098_text_precision/` 是独立开发候选，不注册到 App，不进入 APK。注意力分数、稳定 softmax、value 混合使用 F64 中间计算后转回 F32；可选线性投影使用 F64 累积，仍从相同外部 Q5 权重逐矩阵转换为 F32。分词、权重、模型方程和完整链路门槛不变，候选通过独立实现标识与既有编码器区分。

`tools/experiment_ltx098_text_precision.py` 校验现有训练资产 / 独立参考，原生 Windows 编译，并执行相同真实提示词的 A/B/A 三次完整 T5 推理。它保存每次误差、资源观测、编译依赖、可执行文件及产物身份；A 的重复结果必须逐字节一致。**文本候选完成不表示完整视频精度已通过，也不表示 Android 已编译或运行。**

两种候选各完成了三次真实 T5 推理，共六次；各自 A/B/A 重复逐字节一致。这里只比较同一外部量化权重与原始前向，不是原始未量化权重验收。

| 实现 | A embedding 最大误差 | B embedding 最大误差 | A/B/A 字节重复 |
| --- | --- | --- | --- |
| 既有 F32 基线 | `2.3752450942993164e-5` | `1.430511474609375e-6` | 一致 |
| F64 注意力候选 | `6.794929504394531e-6` | `3.814697265625e-6` | 一致 |
| F64 注意力＋线性候选 | `2.86102294921875e-6` | `1.1920928955078125e-6` | 一致 |

注意力单独候选在 B 的最大误差反而更大，不能描述为所有情况都改善。组合候选改善了当前两组 embedding，但 A 的实际八步 Vulkan 轨迹仍未过固定门槛：

| A 的部分轨迹 | 最终 latent 最大误差 | 相对 RMSE | 原门槛结论 |
| --- | --- | --- | --- |
| F64 注意力 | `0.003952622413635254` | `0.00018860916780748471` | 最大误差超过 `0.003`，失败 |
| F64 注意力＋线性 | `0.0038292407989501953` | `0.00018156580439107774` | 最大误差超过 `0.003`，失败 |

两次探测的独立原始八步参考、原始噪声、候选 caption、完整训练 DiT / Vulkan、逐步文件身份均已复核。公开记录明确复用本轮实际捕获，复核命令本身不再次运行模型，仍在写证据后返回 exit 1。未运行候选的 VAE / B 视频或视频 A/B/A；这些部分结果不能关闭既有完整链路的六项失败。

候选证据：[注意力](../verification/development/ltx098-text-precision-attention.json) / [组合](../verification/development/ltx098-text-precision-linear.json)；部分轨迹：[注意力](../verification/development/ltx098-precision-sampling-attention.json) / [组合](../verification/development/ltx098-precision-sampling-linear.json)。

## 复现与公开范围

先按[完整链路指南](LTX098_PIPELINE.md)准备已锁定的本地资产、原生构建、真实提示词任务和独立参考。以下命令不会下载模型。`CAPTURE` 与 `REFERENCE` 分别替换为本轮工具输出的 `build/` 采集目录和既有 `original-reference` 目录；原始数组没有提交到仓库。

```powershell
python -B tools/diagnose_ltx098_text.py build/ltx098-pipeline-probe/red-42
python -B tools/analyze_ltx098_text.py CAPTURE
python -B tools/review_ltx098_text_diagnosis.py CAPTURE
python -B tools/export_development.py
python -B tools/plot_ltx098_text_diagnosis.py
python -B tools/experiment_ltx098_text_precision.py --reference REFERENCE
python -B tools/experiment_ltx098_text_precision.py --reference REFERENCE --linear-f64
python -B tools/compare_ltx098_precision_sampling.py --variant attention --reference REFERENCE
python -B tools/compare_ltx098_precision_sampling.py --variant linear --reference REFERENCE
python -B tools/check_repository.py --development
```

每次原始采集 / 候选使用新的目录；不会覆盖旧任务、原始编码器或既有媒体。公开的 [逐层记录](../verification/development/ltx098-text-diagnosis.json)、[同输入记录](../verification/development/ltx098-text-operators.json)、[数据重算记录](../verification/development/ltx098-text-diagnosis-review.json)与[绘图来源](media/development/ltx098-text-roundoff.json)包含误差和身份，不包含模型权重或原始中间数组。

保留中间张量会改变诊断内存；候选与检查的执行时间受主机缓存和并行审计影响，均不作为生产基准。Windows 工作集不是显存、整机或手机 RAM。没有 Android 执行、长输入 / 全语言覆盖、画质或后台耐久结论。

App 继续只更新基座，所有模型资产仍由用户显式选择 / 下载 / 导入 / 管理。本轮不新增远程推理路径、自动资产获取、ComfyUI 用户节点或 APK。`ltx098_t5_intermediate_diagnostic_executed=true` 与 `ltx098_t5_roundoff_repair_accepted=false` 分别表达已执行诊断和修复尚未验收；完整 v0.3.0 的全部冻结范围不变。

## F32 运算分步后续

[本轮后续](LTX098_STAGING.md)实现原始 F32 RMS 分组归约和 GeGLU 运算顺序，增加 72 个同输入局部对照、12 次真实 T5 和三条完整主机链路。A通过原门槛，B仍有三项浮点失败；所有门槛和原始前向保持不变，生产接入及回归仍待完成。
