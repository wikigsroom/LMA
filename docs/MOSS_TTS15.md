# MOSS-TTS 1.5 本地语音

[English](MOSS_TTS15.en.md) · [MOSS 引擎与格式边界](OPENMOSS_ENGINE.md) · [完整版本范围](proposals/multimodal-release-scope.json)

## 使用方式

1. 安装 LMA，进入「模型 → 全部」，搜索 MOSS。保留原有「推荐」栏目；新增候选不会自动下载或替换用户模型。
2. 选择 `MOSS-TTS 1.5 · Q8 / BF16 · CPU`，先查看许可证、两个组件的大小及运行状态，再由用户点击下载。也可在组件页面分别选择已下载的对应文件导入。
3. 下载完整并校验后，在「本地」管理该模型，编辑它自己的参数；预设选择框可直接输入数值，超出约束时自动归位。设置随模型保存，不影响其他模型。
4. 点击使用，选择语音任务，输入待朗读文字。可选语言和声音描述；参考音频由用户显式选择，须为 1–10 秒、24 kHz、单声道、PCM16 或 float32 WAV，最多 1 MiB。App 不自动重采样或获取参考声音。
5. 提交后参数成为独立任务快照。加载、参考编码、实际采样、音频解码和保存均在同一台 Android 设备执行；任务结束后在结果中试听、保存或分享 WAV。
6. 下载、暂停、继续、导入、更新、回滚与删除仍由用户选择。更新 App 只更新基座，不更新、重新下载或替换这些资产。

该候选包含 **13,430,589,376 字节**文件：9,339,597,248 字节主干与 4,090,992,128 字节 extras。下载大小不是峰值内存；运行时还需要上下文缓存与中间计算空间。目前没有 Z20 或其他 Android 真机通过记录，不据此承诺手机能够加载。所有模型平级，分别标记生音频、语音合成、CPU、GGUF 和实际验证状态；没有对该模型作 Uncensored 声明。

## 匹配的组件与基座

资产固定为 [ilintar/moss-tts-gguf](https://huggingface.co/ilintar/moss-tts-gguf/tree/66bc8249cc3bae20547d312123f502332158c1d0) 的完整 Q8_0/BF16 配对。模型卡标注 Apache-2.0，来源为官方 MOSS-TTS-v1.5 与 MOSS-Audio-Tokenizer。精确修订、文件大小、SHA-256 与来源见 [资产清单](../research/openmoss_trained/assets.json)；App 使用的可选组合见 [模型清单](../research/openmoss_trained/catalogue-bundle.json)。

此格式使用固定 `pwilkin/openmoss` 引擎及它对应的 llama 版本；由已审查读取器保留 BF16 codec 与 FP32 量化统计。不能混用 first-class MOSS、旧 Local、Local-v1.5、Nano、Realtime 或任意同名 GGUF。运行工作目录仅为已取得租约的两个文件创建私有硬链接，不转换或改写用户权重；worker 退出后清理链接与请求文件。APK 不含权重、词表、音色或参考声音。

## 参数与真实进度

| 参数 | 可编辑范围与含义 |
|---|---|
| 输入预算 | 1–2048；包含格式化提示与参考编码所占位置 |
| 单次生成步数 | 1–1500；包含 Delay 排空与停止步骤，不等于字符数或音频秒数 |
| 文本 / 音频温度 | 各 0–3 |
| 音频 Top P / Top K | 0.01–1 / 1–1024 |
| 重复惩罚 | 1–2 |
| 线程 | 1–32；更高线程数不保证更快 |
| 种子 | -1 自动选择，或 0–2147483647；结果保存实际选择值 |
| 声音描述 / 语言 | 普通文本，分别最多 1000 / 64 字符；不允许模板标记 |

格式化输入、生成上限及保留位置合计还须满足实际 4096 上下文约束。验证发生在 prefill 前，避免界面数值合法而实际提示超限后仍开始采样。

CPU 权重加载使用私有文件映射：只映射该组件实际需要的权重区间，保留原始 Q8_0、BF16 与 FP32 数据，避免将 codec 和重复的文本嵌入整份复制到堆内存。计算仍在设备 CPU 执行，未改变分词、采样、上下文、随机种子或用户文件；模型释放后关闭全部映射。结果分别记录源文件大小、映射区间和权重字节数，它们都不等于峰值常驻内存。

进度由实际采样循环发出，包含首次、连续步骤和终止；解码与保存有独立阶段。结果保留实际参数、种子、采样步数、参考帧数、输出采样数、时长与各阶段耗时。`stopReason=end_of_speech` 表示模型完成；`stopReason=max_new_tokens` 且 `truncated=true` 表示达到用户上限，音频可能不完整。取消或失败不接纳部分 WAV，保留原始模型与设置供用户重试。

## 已知参考模式问题

3 秒参考音频搭配相同短文本的实际案例持续生成至 375 步输出上限，输出 27.44 秒 WAV，未得到正常结束信号。**参考模式的正常结束验收失败**，原因仍在排查，不能据此宣称声音克隆或 MOSS 全系列已经可用。任务仍须如实记录截断、保存原始输出，并允许用户编辑参数后重试；App 不自动重跑。模型选择页面已有相应提示。[原始失败](../verification/research/openmoss-reference-issue/first-run.json) · [官方格式对照与边界](../research/openmoss_trained/reference-investigation.json)。

还核对了上游[续接前缀默认值问题与修复](https://github.com/pwilkin/openmoss/issues/17)。本轮锁定版本已包含修复，实际参考案例的 `continuationPrefixFrames=0`，因此不能用该历史问题解释本次失败，也没有据此改换版本、增加上限或宣告质量通过。

从任务或素材打开达到上限的结果时，页面会显示“内容可能不完整”；正常结束的结果不会沿用该提示。实际结果和参数记录独立保留。

## 验证边界

中英文原始发声在新旧加载方式下分别逐字节一致。英文原始 WAV SHA-256 为 `403d4aa9d0341c3cd8df4619311389941fea5326ab7fa77316d2c31b3fb24ac1`，中文为 `7575ef696518c2247ae5b04f4682aee01f078805bb73fe45c1567a5b903d9311`。修改前的原始报告和主动中止后续参考案例的记录保存在[不可变对照记录](../verification/research/openmoss-memory/baseline.json)，不会将中止的完整测试记为通过。

英文映射案例记录加载约 1.5 秒、总耗时约 97 秒；主机观察到的峰值工作集约 10.89 GB，源文件 13.43 GB、辅助映射区间约 5.37 GB。这些是 Windows 主机观测值，不是受控性能对比或 Android 内存预算。

Android 编译、完整公开资产 SHA 校验、530 项 MOSS 专项、25 项真实映射与 490 项共用页面检查通过。完整原生管线完成 5 个 WAV 案例与 6 项控制检查，业务检查通过，参考模式正常结束失败。实际生产 Java 完成 87 项检查、5 次原生运行和 3 个 WAV：已有文件完整校验接入、独立设置与归位、不可变请求、参考输入、实际步骤后取消、预算错误、恢复和进程 / 工作文件清理，网络调用为零。已有文件接入不能代替尚未通过的流式复制；所有界面媒体明示模拟桥接，不构成 Android 或音质通过。

本项仅是冻结 MOSS 九个目标中的 **TTS-v1.5**。TTS-v1.0、旧 Local、Local-v1.5、TTSD、VoiceGenerator、旧 SoundEffect、SoundEffect-v2 与 Realtime，以及所有模型的质量、资源和同手机后台验收仍属于同一 v0.3.0 完整要求；不会自动延期或据此发布缩减范围的 Release。

## 文件复用与开发者复现

同一完整文件可通过现有文件关联流程复用，仍逐字节计算 SHA 后才登记；执行目录只建立私有硬链接，任务结束清理链接。用户须明确选择文件与目标组合，不会因为浏览页面或升级 App 自动关联。

本轮主机流式导入复制在 900 秒检查时限内未完成，留下 3,565,027,328 字节未验证临时数据，尚未启动模型。该[原始未通过记录](../verification/research/openmoss-import-issue/attempt.json)保留。已有文件的完整校验接入是另一条生产路径，不能代替完整流式复制或 Android 文件选择器验收。

以下只用于原生 Windows 开发验证，须预先准备锁定源码、JDK、NDK 与依赖；不成为用户安装前置步骤。第一条明确下载约 13.43 GB，App 不会自行执行这些命令。

```powershell
python tools/fetch_openmoss_trained.py --download
python tools/build_openmoss_host.py
python tools/test_openmoss_mapping.py
python tools/test_openmoss_trained.py
python tools/test_openmoss_app_host.py --reuse-existing-local-files
python tools/build_openmoss.py
python tools/build.py
```

完整原生测试保留参考模式失败并返回非零。实际业务检查、自然结束、音质、Android 和完整 Release 分开判断；不能通过提高生成上限或改种子把原失败记为通过。原始证据只读保留；相同二进制与精确请求才能显式复核旧捕获，复用项目记录为未重新执行。

## 实际产物与报告

以下来自实际原生 Windows 执行，原始 WAV 字节保持不变。波形 GIF 和带原始音频内容的 MP4 是产物展示，不是 Android 录屏。参考案例明确标记输出上限与自然结束失败；MP4 音频另转为 48 kHz AAC，不能替代原 WAV 校验。

[中文 WAV](media/development/openmoss-trained-zh.wav) · [英文 WAV](media/development/openmoss-trained-en.wav) · [参考输入 WAV（截断）](media/development/openmoss-trained-reference.wav) · [波形 GIF](media/development/openmoss-trained-waveforms.gif) · [实际音频 MP4](media/development/openmoss-trained-speech.mp4)

![实际主机 WAV 与验证范围，非 Android 录屏](media/development/openmoss-trained-contact-sheet.png)

[完整原生执行与原始失败](../verification/development/openmoss-trained.json) · [生产 Java 87 项检查](../verification/development/openmoss-app-host.json) · [媒体来源及每文件 SHA](media/development/openmoss-trained-media.json)。图表耗时取自直接原生捕获；本轮 Java 英文 / 参考 / 恢复分别约 724 / 1551 / 43 秒。磁盘缓存和负载不同，不能据这些数值外推手机速度或作为受控性能比较。
