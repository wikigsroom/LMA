# SoulX：训练参考模型与声学重建

当前后续进展见[语言与完整训练主机链路](SOULX_LANGUAGE.md)：已在开发主机运行Qwen3文字到语义码并接Flow /HiFT。本页保留原检查点的限定套件范围；App绑定、语音质量与物理Android仍待完成，旧套件不追溯改标为完整TTS证据。

[English](SOULX_REFERENCE.en.md) · [声学网络](SOULX_ACOUSTIC.md) · [音频计算](SOULX_DSP.md) · [本轮编号交付](releases/v0.3.0-dev.20-soulx-reference.md)

本页记录的前一检查点把已训练的 S3Tokenizer v2、CAMPPlus 和 Flow / HiFT 接入可执行的原生研究链路：**参考 PCM → 语义码 / 说话人向量 / mel → 声学重建 PCM**。四个发布者组件均实际加载训练权重；目标语义码来自另一段合成 PCM 的 S3 编码，尚未来自文字或 Qwen3。因此这是参考提取与声学重建证据，完整 SoulX Android TTS、App 下载包 / 任务 / API 绑定和 Android 执行仍待完成。

代码位于 [research/soulx_reference](../research/soulx_reference/reference.hpp)、[共享 ORT 策略](../research/soulx_ort/runtime.hpp)及现有声学模块。它们尚未注册或打包进 APK；开发 APK 仍为 0.3.0-dev.20 / code24，公开 Release 仍为 v0.2.0。所有冻结目标继续属于同一个完整 v0.3.0。

## 执行契约

| 编号 | 阶段 | 布局与限制 |
| --- | --- | --- |
| SR-01 | 已解码参考输入 | 单声道24kHz float32 PCM，24000–360000采样，即1–15秒；有限数且幅值在±1内；尚未绑定 WAV 解码 / App 输入 |
| SR-02 | 三种独立前端 | 现有原生 DSP 分别计算 S3、CAMPPlus 和 Flow 特征，保留各自重采样 / 归一化 / mel 规则 |
| SR-03 | 完整 S3Tokenizer v2 | `feats float32[1,128,T]`、`feats_length int32[1]` → `indices int32[1,ceil(T/4)]`；T≤1500、原始码≤375、码值0–6560；不虚构模型没有的长度输出 |
| SR-04 | 完整 CAMPPlus | `input float32[1,T,80]` → `output float32[1,192]`；保留原始向量，不擅自 L2 归一化 |
| SR-05 | 参考前缀对齐 | `P=min(原始码数, Flow帧数/2)`，裁取 P 个码和 `[1,80,2P]` mel；非整秒检查确实出现31个原始码→30个对齐码 /60帧 |
| SR-06 | 训练声学重建 | 对齐参考 + S3目标码 → 完整 Flow encoder / estimator → HiFT F0 / 学习源 / spectrum →24kHz PCM；每个生成码960采样，测试生成1秒或1.2秒 |

参考与声学执行共用 CPU ORT 策略：顺序加载 / 释放，最多一个存活会话；intra-op线程1–32，inter-op1，禁用 arena / memory pattern，basic 图优化。固定 IO 名称 / dtype / 形状、实际输出有限性和对应 `<graph>.data` 外部权重位置 / 范围均检查；路径逃逸被拒绝。阶段取消和实际图运行的 `SetTerminate()` 均保留；推理未完成不会创建参考输出目录；文件写入异常会返回失败，开发者需检查该新目录。CPU 线程数和理论张量上限不等于手机可承受的速度 / 内存。

## 完整模型与资产归属

[参考来源锁](../third_party/soulx-reference-source-lock.json)与[声学资产锁](../third_party/soulx-trained-assets.json)固定发布者修订、字节数、SHA256和许可。原始资产如下；精确完整 hash 以锁文件为准。

| 编号 | 原始资产 | 固定来源 / 修订 | 字节数 |
| --- | --- | --- | ---: |
| A-01 | `speech_tokenizer_v2.onnx` | [FunAudioLLM/CosyVoice2-0.5B](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B/tree/23778f84b1b6dd789e1b5092c3ec1145639ee1c3) · `23778f84…` | 496,082,973 |
| A-02 | `campplus.onnx` | [Soul-AILab/SoulX-Podcast-1.7B](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B/tree/c2af285fc7ec68a4d3402deae7d2e215ab67fb32) · `c2af285f…` | 28,303,423 |
| A-03 | `flow.pt` | 同一 SoulX 修订 | 450,575,567 |
| A-04 | `hift.pt` | 同一 SoulX 修订 | 83,390,254 |

[离线参考转换器](../tools/export_soulx_reference.py)将两个原始 ONNX 的权重移到固定 sidecar，不重新训练或初始化。回读后核对完整 graph 与所有 tensor 字节身份：S3保留1358个节点 /102个 initializer，CAMP保留3206个节点 /617个 initializer；opset分别17 /14。仅规范化 protobuf 默认枚举字段的“显式存在”状态，不改图计算或参数。转换后四个图 / 数据文件共524,439,313字节，另有 manifest。声学转换仍使用[严格 checkpoint 加载](SOULX_ACOUSTIC.md)，实际训练源的 hash 单独匹配；不能仅由 `synthetic_parameters=null` 推断来源认证。

原始 / 转换权重、manifest、说话人向量和语义码都是模型或运行资产，留在忽略的开发目录或用户指定目录，不进入 Git、APK、源码附件或 Release。开发者必须显式请求模型下载；不带下载开关的检查不会补齐权重。可显式选择 HF 镜像下载固定资产，仍校验同一来源 hash；镜像只传输文件，不参与推理。本轮没有真人声音或上游示例音频。

最终用户仍应在 App 中自行选择、下载 / 导入、暂停 / 续传、更新 / 删除和设置模型，安装或升级只更新基座。这里的开发转换命令不作为未来用户使用 SoulX 的前置步骤；完整可下载用户 bundle、手机原生语言阶段和 App 绑定仍须在同一个版本内完成。模型平级，生文 / 生图 / 生视频 / 生音频与基座标签独立；推荐顺序 m08→m06→m01 保留，未把本研究模块标成 App“可运行”。

## 检查证据与误差定位

| 编号 | 检查 | 实际范围 |
| --- | --- | --- |
| V-01 | [参考模型145项](../verification/development/soulx-reference.json) | 15次原生主机子进程、10次完成图执行、4次参考提取、2次真实运行终止；1秒 / 非整秒 /15秒和重复装卸；20组阶段比较，语义码逐项完全相同 |
| V-02 | [训练声学253项](../verification/development/soulx-trained.json) | 2份真实声学 checkpoint、2个真实参考模型；3次原生重建、54次图执行、63组阶段比较及12组相同中间输入隔离比较；最多一个会话 |
| V-03 | [未训练声学244项](../verification/development/soulx-acoustic.json) | 完整结构合成参数回归，另计12次子进程 /57次图执行 /1次真实终止；保留原有更紧的合成参数波形阈值 |
| V-04 | [参考 ARM64](../verification/development/soulx-reference-arm64.json) / [声学 ARM64](../verification/development/soulx-acoustic-arm64.json) | Windows 原生 NDK r30，API28 /16KiB ELF，分别504,440 /520,448字节，链接既有 ORT1.28.2 / C API17；未在 Android 执行 |

参考基准使用原始发布者内联 ONNX，原生子进程运行转换后的图；音频基准提取固定上游 Python 数学函数体，未用待测转换图生成自己的基准。S3特征峰值误差6.3181e-6、CAMP特征4.1867e-4、说话人向量4.0889e-5、Flow /参考 mel 2.8611e-6；原始语义码与对齐码均按实际长度检查。

训练权重的首轮重建超过了未训练夹具原有的波形峰值阈值5e-4，因此增加独立定位：用完全相同的原生 mel / F0 / source /谱分别调用原始 HiFT。相同 F0 的声源峰值差≤1.491e-8，相同 mel /声源的解码差≤7.395e-6，相同谱的 ISTFT差≤4.769e-7。端到端亚毫赫兹的 F0 浮点差会累积相位，最终波形峰值差最高8.378e-4，RMSE最高6.863e-5，最低SNR58.04dB。

训练重建独立要求峰值≤1e-3、RMSE≤1e-4、SNR≥50dB，并继续要求上述12组隔离检查；未训练244项的阈值不变。这些是数值一致性门槛，尚未测量可懂度、音色、参考一致性、端侧内存 / 热量 / 实时率或长文本质量。**训练组件运行不等于文字生语音；Windows 执行与 Android 编译不等于 Android 执行。** 所有整模型 / 手机 / Release 门槛继续未通过。

## 开发复现

在本项目目录执行，使用原生 Windows MSVC / NDK / CMake / Ninja，不使用 Docker、WSL、虚拟机或模拟器。依赖沿用[开发指南](DEVELOPMENT.md)；所有缓存 / 临时文件 / 输出留在项目 `build/`。顺序执行构建和测试，避免并发 SUBST 编译。

```powershell
# 显式准备源码、Python导出依赖和上游数值参考，不下载模型。
python tools/prepare_soulx_acoustic.py --python-dependencies
python tools/fetch_soulx_dsp.py --test-references
python tools/fetch_soulx_reference.py
# 仅这两个显式开关请求四份发布者模型；默认来源 HF。
python tools/fetch_soulx_reference.py --publisher-models
python tools/fetch_soulx_trained.py --download
# 如需镜像，显式附加 --origin https://hf-mirror.com，仍核对固定SHA256。
python tools/test_soulx_reference.py
python tools/test_soulx_acoustic.py
python tools/test_soulx_trained.py
python tools/build_soulx_reference.py
python tools/build_soulx_acoustic.py
python tools/export_development.py
python tools/check_repository.py --development
```

如仅转换自选原始参考 ONNX，可运行 `python tools/export_soulx_reference.py --source-dir build/user-soulx-reference --output-dir build/user-soulx-reference-pack`，输出目录须不存在。不同来源即使契约兼容，也不会获得“固定发布者 hash 已匹配”标记。测试需四份已明确准备的权重，缺失时失败，不自动下载。Python / PyTorch 仅用于开发导出和基准，Android 执行器不依赖它们。

许可见[参考模块 NOTICE](../research/soulx_reference/NOTICE)、[共享 ORT NOTICE](../research/soulx_ort/NOTICE)、现有 DSP /声学 NOTICE 和来源锁。保留 Apache-2.0、ORT MIT、KISS FFT BSD-3-Clause及 Snake MIT；发布者模型卡声明 Apache-2.0，不将代码许可推断成任意 HF 模型的许可。

[语言及完整训练主机链路](SOULX_LANGUAGE.md)已另获证据；仍须完成其App绑定、长文本 /多说话人质量、完整显式用户模型包、App队列 / API /输入输出 /资源准入、全模型新输入断网语音和质量测试，以及物理 Android 三次装卸、15分钟锁屏、1小时交替 API 和升级保留资产。原有文本、F-01–F-12、01–14 /16 /17全部冻结子目标、九种 MOSS、SD1.5 /SDXL LoRA、旧 LTX-Video 2B 0.9.8 distilled、A1–A11 /R-01–R-05及最终 Release 均保留，不拆版本或默认顺延。
