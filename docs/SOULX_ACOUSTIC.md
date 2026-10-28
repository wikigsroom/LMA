# SoulX-Podcast：完整声学网络导出与原生执行

当前实现见 [dev.21 SoulX App 基座](SOULX_ENGINE.md)：共享源码已编译进生产 worker，接入用户模型包、任务与 API。以下正文保留 dev.20 研究检查点的历史范围；“未注册 / 未打包”指当时的独立研究执行器。其测试不追溯改标为 App 或手机证据。公开完整组件下载候选、语音质量与物理 Android 验收仍待完成。

[English](SOULX_ACOUSTIC.en.md) · [音频前端与 DSP](SOULX_DSP.md) · [完整版本要求](MULTIMODAL_RELEASE_PLAN.md) · [编号交付](releases/v0.3.0-dev.20-soulx-acoustic.md)

本次源码更新在 [research/soulx_acoustic](../research/soulx_acoustic/acoustic.hpp) 实现了 SoulX **声学部分**的本地执行：语义码和参考特征 → Flow → HiFT → 单声道 24kHz PCM。四份 ONNX 使用完整上游网络结构；本文244项回归使用未训练的合成夹具。[后续训练参考 /声学重建](SOULX_REFERENCE.md)另加载真实 S3 /CAMP /Flow /HiFT并记录145 /253项独立证据。它还不是从文字 / 参考 WAV 开始的完整 SoulX，也没有注册到 APK、模型目录、共用任务或 HTTP API。开发 APK 仍为 dev.20，公开 Release 仍为 v0.2.0；13 号完整模型目标仍未关闭。

## 已实现的链路

| 编号 | 阶段 / 用户资产 | 张量与执行规则 |
| --- | --- | --- |
| AC-01 | `flow-encoder.onnx` + `.data` | `tokens int64[1,N]`、`speaker float32[1,192]` → `mu[1,80,2N]`、`spks[1,80]`；保留原始 embedding、编码器、说话人投影 |
| AC-02 | `flow-estimator.onnx` + `.data` | 完整条件速度网络；batch2 的条件 / 无条件 CFG、动态帧长、余弦时间表、默认15步原生 Euler；参考 mel 写入条件前缀，全部迭代后才裁去前缀 |
| AC-03 | `hift-f0.onnx` + `.data` | 完整 F0 预测器；生成 mel `[1,80,T]` → F0 `[1,T]` |
| AC-04 | `hift-source.f32` | 原权重中的9个线性系数和1个 bias，40字节；原生九谐波 NSF → 学习到的线性合并 / tanh → 实虚 STFT，不能用固定平均替代 |
| AC-05 | `hift-spectrum.onnx` + `.data` | 完整 HiFT 卷积 / Snake 网络；mel + source STFT → 幅值 / 相位 `[1,9,120T+1]`，保留末层默认 `.01` leaky-ReLU |
| AC-06 | 原生 DSP | FFT16 / hop4 ISTFT、中心裁剪、重叠归一化、最终±.99限幅；每个生成语义码对应960个24kHz采样 |

每份 ONNX 会话单独加载 / 释放，最大同时存活1份；Flow estimator 在同一次会话内循环。CPU 使用独立 intra-op 线程数，inter-op1，不启用远程 provider。取消既检查阶段 / DSP 循环，也通过监控线程调用 ORT `RunOptions::SetTerminate()` 中断正在进行的图执行。异常路径释放会话；开发 CLI 仅在成功返回后写最终 PCM，不是 App 的服务接口。

接受上限是 **375个参考语义码 + 3000个生成语义码 = 3375个编码器 token / 6750个 Flow 帧**。后者包含参考前缀，不能误套生成 mel 的6000帧上限。编码器的确定性位置表在导出前扩展到完整接受范围。步数1–100、线程1–32、CFG0–10、seed−1或0–2147483647；严格检查语义码范围、说话人192维、参考 `[80,2P]`、有限数、输出形状。120秒生成上限是张量边界，未证明手机的速度 / 内存可承受该长度。

## 离线转换与资产归属

[转换器](../tools/export_soulx.py) 只读取明确指定的本地 `flow.pt` / `hift.pt`，`weights_only=True`，严格核对 state 字典；先加载完整原始权重，再折叠 weight norm。拒绝缺失 / 多余键、碰撞前缀、非有限参数和已有输出目录；只清理自身临时目录，成功后原子提交新目录。`soulx-acoustic.json` 记录每个资产和来源 checkpoint 的 SHA256 / 大小、固定代码修订、张量契约与上限。未指定测试标记时 `synthetic_parameters=null`，**不会由“未标记”推断为真实训练参数或认证来源**。

四份图、四个 sidecar、40字节学习参数和 manifest 都是模型资产。它们留在用户 / 开发者明确指定的目录，**不进 APK、不自动下载、不在安装 / 升级 / 浏览 / 缺组件时补齐**。未来接入 App 仍需使用现有经过校验的 bundle / lease 层管理这些资产；本研究 CLI 不是完整资产验签器。原生图加载器另验证固定 IO 契约和外部权重位置 / 范围，只接受对应的 `<graph>.data`，拒绝越界或路径逃逸。

[独立参考执行器](SOULX_REFERENCE.md)已实现 S3Tokenizer /CAMPPlus，且已用于训练声学重建。本声学模块仍不执行 Qwen3 语言主干 /tokenizer，不处理多说话人文本协议或多轮合并。不能仅凭这组声学图完成可用 TTS。App 的平级模型、功能 / 基座标签、推荐顺序和每模型参数逻辑均沿用现有实现；没有为未完成执行器添加“可运行”标签。

## 开发复现

仅使用原生 Windows MSVC / NDK r30 / CMake / Ninja，不使用 Docker、WSL、虚拟机或模拟器。先按[开发指南](DEVELOPMENT.md)准备现有原生依赖 / JSON 头和 Android ORT。主机需 Python3.13、PyTorch CPU、NumPy、SciPy、HF / transformers、safetensors 和 numba 等正常 Python 依赖。实际检查记录主机 torch / numpy 等版本；不是宣称原始上游 torch2.7.1 环境已经复现。

```powershell
# 显式联网准备开发代码 / 导出依赖，不下载任何模型。
python tools/prepare_soulx_acoustic.py --python-dependencies
# 然后离线读取开发者明确选定的本地原始 checkpoint，输出目录必须不存在。
python tools/export_soulx.py --checkpoint-dir build/user-soulx-checkpoints --output-dir build/user-soulx-acoustic
# 独立的 UNTRAINED 完整网络测试；不使用上面的用户权重。
python tools/test_soulx_acoustic.py
python tools/build_soulx_acoustic.py
python tools/test_soulx_dsp.py
python tools/build_soulx_dsp.py
python tools/export_development.py
python tools/check_repository.py --development
```

离线转换要求准备步骤已经完成，不在转换器中隐式安装依赖或拉取源码。可选 Python 包安装在 `build/soulx-python`，下载缓存 / 临时文件及所有输出在项目 `build/`。`--synthetic-fixture` 仅用于明确标记未训练测试参数。转换器的四个 ONNX 为 opset17 / float32；不要求 Android 安装 Python 或 PyTorch。ARM64 编译检查只在 `build/soulx-acoustic-arm64` 留下未注册 CLI，不复制到 `jniLibs`。

## 验证范围

[主机执行证据](../verification/development/soulx-acoustic.json)和[Android 编译回执](../verification/development/soulx-acoustic-arm64.json)分别记录输入指纹、实际进程 / 图执行、逐阶段误差、会话生存期、取消和未通过的整模型 / 手机门槛。

完整 Flow **112,549,360** 参数、HiFT **20,821,295** 参数，均为合成未训练参数；实际运行本转换器，再调用原始上游 Flow / HiFT `forward` 生成独立基准，未用缩层网络或微型常数图替代。参考 / 总语义码分别为3/9和4/17，与导出示例长度12不同；原生执行顺序0→1→0，比较 mu / spks、15步速度、mel、F0、学习源和最终 PCM。还检查非法请求、外部权重路径逃逸、阶段前取消、迭代中取消及 ORT 真正终止的运行。证据中的 PCM 是合成测试产物，不作为音色演示。

本轮 **244项限定检查、12次实际主机子进程、57次完成的 ORT 图执行、1次实际运行终止、3次声学输出**通过，63项阶段比较的最大速度误差为 `1.109e-4`，最终 PCM 最大绝对误差为 `1.733e-7`。四图和数据等9个资产合计582,584,557字节，均只在忽略的开发目录。共用ORT策略后重新编译的 Android未注册CLI为520,448字节；该尺寸不含22,249,560字节既有 ORT，更不代表整模型内存占用。

主机 ORT1.24.3 DLL 的版本和 SHA256 独立固定；Android 链接既有 ORT1.28.2 CPU 库，使用兼容 C API17，检查 ARM64 / API28 / 16KiB ELF 及导入。**Windows 执行与 Android 编译不能替代 Android 执行。本文未训练244项套件的训练checkpoint加载0；另有[训练参考 /声学重建](SOULX_REFERENCE.md)组件证据。本244项套件的完整SoulX推理0；后续[语言与完整训练主机链路](SOULX_LANGUAGE.md)已有独立输出证据；语音质量验证0、真机0。** 所有相关证据仍为 `release_ready=false`。

## 来源、许可与剩余门槛

[锁定来源](../third_party/soulx-acoustic-source-lock.json)含 SoulX、KISS FFT、ORT 和 Snake 的修订 / 文件 hash，以及导出依赖来源 hash。[归属与许可](../research/soulx_acoustic/NOTICE)保留 Apache-2.0、ORT MIT 和 Snake MIT。上游 SoulX 提到了未随其 checkout 提供的 `incl_licenses`；本仓库从独立固定的 EdwardDixon/snake 原仓库保留实际 MIT 原文，没有伪造缺失文件。模型权重与后续转换包的来源 / 许可仍需单独检查。

同一完整 v0.3.0 内继续完成：S3 /CAMP用户资产与App绑定（导出 /原生研究运行已见[参考指南](SOULX_REFERENCE.md)）、已有[语言 /窗口及完整训练主机链路](SOULX_LANGUAGE.md)的App绑定和长文本 /多说话人质量、完整显式用户模型包与任务 / API 绑定、新输入断网真实权重输出 / 质量 / 资源测试及物理 Android 验收。F-01–F-12、原有文本、01–14 / 16 / 17 全部冻结子目标、九种 MOSS、SD1.5 / SDXL LoRA、旧 LTX-Video 2B 0.9.8 distilled、A1–A11 / R-01–R-05 和完整 Release 均不缩减或自动顺延。
