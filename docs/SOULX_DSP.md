# SoulX-Podcast：原生音频计算底层

当前实现见 [dev.21 SoulX App 基座](SOULX_ENGINE.md)：共享源码已编译进生产 worker，接入用户模型包、任务与 API。以下正文保留 dev.20 研究检查点的历史范围；“未注册 / 未打包”指当时的独立研究执行器。其测试不追溯改标为 App 或手机证据。公开完整组件下载候选、语音质量与物理 Android 验收仍待完成。

[English](SOULX_DSP.en.md) · [完整版本要求](MULTIMODAL_RELEASE_PLAN.md) · [本轮交付](releases/v0.3.0-dev.20-soulx-dsp.md)

本轮实现位于 [research/soulx](../research/soulx/dsp.hpp)，是可编译、可执行检查的 C++ 音频处理库，**尚未接入 APK、引擎注册表、任务队列或模型执行接口**。13 号 SoulX-Podcast 1.7B 仍待完成完整原生管线；本轮不新增“已支持模型”，不改变推荐、模型标签或用户下载行为。当前开发 APK 仍为 0.3.0-dev.20，公开 Release 仍为 v0.2.0。

## 完整链路与本轮边界

| 编号 | 完整 SoulX 阶段 | 本轮状态 |
| --- | --- | --- |
| S-01 | 参考 WAV → 16k S3 特征 / CAMPPlus 特征 / 24k Flow 特征 | 已实现原生计算及与上游数值比较；WAV 仍由未来工作进程接入现有输入库 |
| S-02 | S3Tokenizer → 参考语义码；CAMPPlus → 192 维说话人向量 | 已在[独立参考执行器](SOULX_REFERENCE.md)运行完整训练图；本DSP库只计算前端，用户包 /App绑定仍待完成 |
| S-03 | Qwen3 主干 → 目标语义码；多说话人、跨轮历史与 EOS | [原生语言与窗口](SOULX_LANGUAGE.md)已完成训练主机检查；App任务绑定 /完整手机验收仍待完成 |
| S-04 | Flow encoder → 条件张量；Flow estimator → 速度 | 已有[完整声学四图后续实现](SOULX_ACOUSTIC.md)及未训练完整结构 / 原生 ORT 比较；另有[训练权重重建](SOULX_REFERENCE.md)；用户组件和App绑定仍待接入 |
| S-05 | HiFT F0 / 神经谱模型 → 24k 波形 | 原生 NSF / STFT / ISTFT 已接后续 F0 / 学习 source merge / 神经谱研究执行器；[实际训练权重重建](SOULX_REFERENCE.md)已验证；完整语音质量与App绑定仍待完成 |
| S-06 | 合并多轮结果、任务产物、后台 API 与资源准入 | 待完整执行器接入共用基座；本轮未生成模型 WAV |

只下载社区的语言主干 GGUF 并不能完成语音合成。后续实际权重、tokenizer、声学图、说话人组件、codec 及其许可证仍由用户显式选择、下载 / 导入、管理；不打包进 APK，不在安装、升级、浏览或缺组件时自动获取。全部推理仍必须在同一部 Android 手机执行，无 ROOT、无其他设备推理或回退。

## 已实现的计算契约

| 编号 | 计算 | 明确布局 / 行为 |
| --- | --- | --- |
| D-01 | 音量归一化 | 按上游顺序处理：先检查低峰值，百分位仍取原始振幅，最后按实际峰值限幅；没有把三种模型前端合并成同一种 mel |
| D-02 | 重采样 | 24k→16k、Hann 窗 sinc、低通宽度 6、rolloff .99、零边界，输出长度 `ceil(N×2/3)`；S3 / CAMP 在重采样后归一化，Flow 在 24k 归一化 |
| D-03 | S3 | FFT400 / hop160、反射中心填充、周期 Hann、去最后一帧、Slaney128、功率 / log10 / 8 阶动态范围；`[128,T]` |
| D-04 | Flow | FFT1920 / hop480、两端反射720、非中心 STFT、Slaney80 / 上限8kHz、幅值 `sqrt(power+1e-9)` / 自然对数；`[80,T]` 且裁为偶数帧 |
| D-05 | CAMPPlus | Kaldi25ms / 10ms、FFT512、去直流、.97 预加重、非周期 Povey、80 mel、无 dither、log power，逐维减帧均值；`[T,80]` |
| D-06 | Flow 更新 | `1-cos(t×π/2)` 时间表；`x += dt×(1.7×条件速度−.7×无条件速度)`；非法布局、非有限值或更新溢出时拒绝，失败不改写输入状态 |
| D-07 | HiFT | 50Hz F0 → 480倍采样 / 9谐波 NSF，逐样本输出回调；显式注入噪声；FFT16 / hop4 的实虚频谱；ISTFT 重叠归一化、去中心填充、幅值上限100及最终±.99限幅 |
| D-08 | 边界与取消 | 参考入口为24k单声道、1–15秒；F0 / 谱上限为6000生成 mel帧（120秒），Flow 另含750参考前缀，最高6750帧；并非手机性能结论；逐阶段 / 帧 / 采样块检查取消、形状与数值溢出 |

NSF 对齐了上游线性插值的 float32 倒数比例、半像素坐标和先钳制边界的顺序。它在持续增长的采样偏移处会影响相位，不能只检查一秒输入。逐样本回调避免仅为谐波额外分配整段 `samples×9` 张量；未来神经阶段仍需独立做内存准入，未测量 Android 内存或速度。

## 检查与复现

原生 Windows 主机，不使用 Docker、WSL、模拟器或虚拟机：

```powershell
python tools/fetch_soulx_dsp.py --test-references
python tools/test_soulx_dsp.py
python tools/build_soulx_dsp.py
python tools/export_development.py
python tools/check_repository.py --development
```

编译前需按现有开发指南准备本项目内的 NDK r30 / CMake / Ninja，主机需 MSVC、Python、NumPy 和 PyTorch CPU。测试取锁定 wheel 中的 torchaudio 2.7.1 / librosa 0.11.0 **Python 函数体**，通过 AST 提取后在当前 PyTorch CPU 执行；不加载 torchaudio DLL，不宣称复刻上游原始 Python 环境。S3 的作者 mel bank 仅在忽略的 checkout 中作为检查基准，不进入 APK 或源码附件。

当前[数值证据](../verification/development/soulx-dsp.json)和[ARM64 编译回执](../verification/development/soulx-dsp-arm64.json)分别记录范围、误差与输入 hash。比较涵盖1秒、非整秒、15秒参考音频，以及1 / 7 / 50 / 1500 / 6000 mel帧的 NSF（含30秒 / 120秒）；另比较实际上游15步 Euler 函数、谱合成和异常输入。输入为合成 PCM、噪声、F0 与非模型 estimator。

仅此DSP套件是数值和编译证据；另有[独立训练组件检查](SOULX_REFERENCE.md)：**训练权重加载0、模型音频产物0、物理 Android0；不能证明音色、可懂度、长文本质量、真机实时率或后台耐久。** ARM64 产物是未注册的静态库，留在 `build/`，不安装新引擎或下载运行时代码。

## 来源与许可

[固定来源与文件 SHA256](../third_party/soulx-dsp-source-lock.json)：[SoulX-Podcast](https://github.com/Soul-AILab/SoulX-Podcast/tree/5ac9c0e1cfe596396200c7d38e3fd53b7b3fbf4b)、[S3Tokenizer](https://github.com/xingchensong/S3Tokenizer/tree/9bf5d845b5e043ffaf4657f4942939091c7697a2)、[KISS FFT](https://github.com/mborgerding/kissfft/tree/febd4caeed32e33ad8b2e0bb5ea77542c40f18ec)。计算移植采用 Apache-2.0，原始 LMA 接口 / 构建工具采用 MIT，KISS FFT 为 BSD-3-Clause；见[归属说明](../research/soulx/NOTICE)、[Apache 原文](../research/soulx/LICENSE-APACHE-2.0)及[KISS 原文](../research/soulx/LICENSE-KISSFFT-BSD-3-CLAUSE)。用户模型权重的来源、许可证与架构还需单独核对。

## 仍须完成

同一个完整 v0.3.0 中继续完成S-02的用户包 /App绑定及S-03–S-06的完整用户链路、最多四说话人 / 长文本协议、完整用户模型包和新输入断网语音、资源 / 质量 / 取消 / 三次装卸与真机后台测试。其他 F-01–F-12、01–14 / 16 / 17 冻结子目标、SD1.5 / SDXL 两类 LoRA、九种 MOSS、旧 LTX 2B 0.9.8 distilled、A1–A11 / R-01–R-05 及最终 Release 门槛均不缩减、不默认顺延。
