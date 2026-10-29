# 编号11：Qwen3-TTS 0.6B Base真实训练验证

[English](QWEN_TTS_TRAINED.en.md) · [用户流程和参数](QWEN_TTS_ENGINE.md) · [编号交付与完整待办](releases/v0.3.0-dev.24-qwen-tts.md) · [完整版本要求](MULTIMODAL_RELEASE_PLAN.md)

本次在原生Windows直接编译并运行未修改的生产Qwen C++及Java适配器，完成两个真实训练GGUF的取得、合成与管理验证。App仍为 **0.3.0-dev.24/code28**，APK输入、字节与签名不变。**这不是手机推理、语音质量或编号11完整验收；完整v0.3.0尚未发布。** 主机工具不构成App的外部推理方案。

## 1. 用户选择与完整资产

既有可选配方 `qwen3_tts_06b_base_q4_rb7ee2e8` 仍使用 `qwen3_tts_06b_base_cpu_v1`。在“模型→全部/搜索”检查任务、组件、来源、许可、大小和设备证据后，由用户明确下载或导入；“本地”管理、设置、更新、回退或删除。安装、升级、浏览、启动接口、缺资产请求均不下载或替换模型。推荐仍为m08→m06→m01，所有模型平级。

| 用户组件 | 字节 | 完整SHA256 |
| --- | --- | --- |
| `qwen-talker-0.6b-base-Q4_K_M.gguf` | 628,905,056 | `4b468ec7b1f62b90ef4ca316c0aa57deadfd54b2cf9651703ea753cedaf04226` |
| `qwen-tokenizer-12hz-Q8_0.gguf` | 291,150,624 | `1883beeed99348fc35e23dd225e9082f93f6f8c109330a33d935baa8acdbfd94` |

总量 **920,055,680字节**，固定 [Serveurperso/Qwen3-TTS-GGUF](https://huggingface.co/Serveurperso/Qwen3-TTS-GGUF/tree/b7ee2e8c7459c3bea99da23e3d178125a7d1713c) 提交 `b7ee2e8c7459c3bea99da23e3d178125a7d1713c`。本轮从明确选择的HF镜像取得，逐块严格核对Range与最终整文件SHA，未放宽冻结清单。两个完整文件、下载缓存和导入对象均在忽略目录；Git/APK不含训练数据。

Talker内含文本BPE、Code Predictor与speaker encoder；第二文件提供16码本、24kHz、1920样本/帧的音频codec。标签独立记录 `task:audio`、`engine:qwen_tts_native`、`pipeline:qwen3_tts_06b_base`、`backend:cpu`、`format:gguf` 与组件依赖；下载状态不等于可运行/已验收。发布者声明权重Apache-2.0，固定推理实现与ggml为MIT；引擎许可不替代权重和参考音频条款。

## 2. 执行路径与参数

固定 [Danmoreng/qwen3-tts.cpp](https://github.com/Danmoreng/qwen3-tts.cpp/tree/16bb5afcd06311031c72a8488f8d59660dc2fb46) 与ggml提交，直接编译现有35个库源文件和 `native/qwen_tts/worker.cpp`。只添加[Windows CRT/父进程/环境变量兼容层](../research/qwen_tts_host/NOTICE)，不修改上游神经代码或生产worker。构建关闭GPU、动态后端、OpenMP/BLAS、示例与自动取得；无需虚拟化或全局Python模型运行环境。

完整链路是格式化BPE→Talker自回归→多码本预测→12Hz codec→单声道PCM16 WAV。无参考模式不取得默认音色；可选参考模式只接入speaker embedding，不提供ICL文本、命名音色或VoiceDesign。参考使用上一轮[原字节Kokoro合成WAV](media/development/tts-trained-kokoro.wav)，24kHz、单声道、3秒；不涉及真实人的声音或相似度声明。

默认4线程、512输入token预算、375音频帧预算、温度0.9、topP1、topK50、重复惩罚1.05。除专门对照外固定实际种子1234、语言按样例选择；自动语言和种子5678另外测试。预算/采样/种子仍是本模型独立设置，允许手填并归位到[应用保护范围](QWEN_TTS_ENGINE.md#使用与参数)，不是手机性能或训练上限承诺。

18份成功输出覆盖中文A/B、其余九语言、auto、不同种子、零温度/topK1、16帧预算、参考A/B、取消后恢复A。12个控制涵盖错误schema、空文本、超线程、无效语言/种子/帧预算、负提示词、真实BPE预算不足、缺codec、组件错配、无效参考和生成后取消。取消只在真实execution事件记录已生成第16帧后触发，不把加载或预算当进度百分比；错误和取消均不接受部分WAV。

每次保留请求、完整stdout协议、stderr、输出身份和20ms主机进程内存采样。主机终止验证不等于Android服务取消或后台生命周期。生产Java另完整导入920MB两对象，检查每模型参数独立/超限归位、不可变任务快照、固定执行文件名硬链接、随机种子记录、参考选择、实际错误/取消/恢复、进程/请求/工作区清理与重启保留；零网络。Application/AtomicFile为明确主机端口，未运行SAF、Android Service或播放器。

## 3. 实测与媒体

[完整训练报告](../verification/development/qwen-tts-trained.json) · [生产Java绑定](../verification/development/qwen-tts-app-host.json) · [独立原始复核](../verification/development/qwen-tts-capture-audit.json) · [完整模型身份](../verification/development/qwen-tts-assets.json)

| 实际场景 | 音频秒 | 进程秒（含加载） | HOST峰值工作集MiB |
| --- | --- | --- | --- |
| 中文A | 4.00 | 11.363 | 871.7 |
| 英文 | 2.00 | 9.039 | 871.4 |
| 日文 | 3.12 | 9.614 | 871.3 |
| 合成参考中文A | 4.00 | 16.567 | 872.0 |
| 温度0、topK1 | 30.00 | 100.230 | 2486.4 |
| 恢复中文A | 4.00 | 11.783 | 871.7 |

18成功/12控制加info共31个真实原生子进程。相同种子首次/恢复A字节一致；不同文本、种子、贪心、帧预算及参考与A不同。取消到退出约0.084秒；16帧输出恰为30,720样本/1.28秒。Windows主机非独占基准环境，不能推算努比亚Z20的速度、内存或耐久。

生产Java完整重跑通过94项检查、6个真实子进程、4份WAV、两对象/920,055,680字节导入且零网络。独立复核重新读取145个原始文件、31条协议流、22份WAV（包括Java四份）和两份完整导入对象，并核对实际可执行文件身份；8项错误Android/质量/相似度/目标/Release范围提升均被拒绝。

**零温度/topK1的短文本输出恰好达到375帧/30秒预算。** 当前接口未记录EOS/预算耗尽的独立结束原因；不能把该输出或16帧截短输出当作完整朗读、自然度或语义正确性通过。十语言有真实波形，不等于逐语言质量通过；参考路径有输出，不等于音色克隆相似度通过。

| 原始真实音频 | 文件 |
| --- | --- |
| 中文A，无参考 | [WAV](media/development/qwen-tts-trained-zh.wav) |
| 英文，无参考 | [WAV](media/development/qwen-tts-trained-en.wav) |
| 中文A，合成参考 | [WAV](media/development/qwen-tts-trained-reference.wav) |

![Qwen真实主机波形与验证范围](media/development/qwen-tts-trained-contact-sheet.png)

[静音波形GIF](media/development/qwen-tts-trained-waveforms.gif) · [带实际音频MP4](media/development/qwen-tts-trained-speech.mp4) · [媒体身份/来源](media/development/qwen-tts-trained-media.json)

WAV直接复制原字节，无增益/归一化；MP4波形轮播使用实际音频，明确记录AAC转换与48kHz重采样。它们不是手机/App录屏。现有68张UI夹具截图保留；本轮未修改界面或打开浏览器。

## 4. 开发复现

使用[原生Windows工具链](BUILD.md)，先明确取得锁定Qwen源码及既有JSON头，再依次执行：

```powershell
python tools/fetch_qwen_tts_trained.py --download --hf-origin https://hf-mirror.com
python tools/build_qwen_tts_host.py
python tools/test_qwen_tts_trained.py
python tools/test_qwen_tts_app_host.py
python tools/check_qwen_tts_trained_evidence.py --recompute-raw --adversarial
python tools/render_qwen_tts_trained.py
python tools/export_development.py
python tools/check_repository.py --development
```

源码、下载、构建、原始测试、Java测试、独立复核和媒体各有指纹，失败run不覆盖。取得工具不带`--download`时只核验；测试不下载。`--smoke`仅快速探查，不产生可通过完整测试的报告。Java工具初次错误地寻找未登记的Nano目录条目，已改为实际存在的Kokoro作为独立参数对照，再重新完整运行；失败现场保留，未更改生产代码/配方。

独立检查重算原始WAV、协议、完整导入对象和实际二进制，另用8项错误范围提升控制，保持手机、质量、相似度、目标11和Release为false。此前文件头/81契约测试保持原始范围，不能事后改称真实训练推理。

## 5. 完整版本仍需完成

逐语言听感/文本完整性、参考相似度、长文本与采样退化、资源适配、Android实际加载卸载/生成/取消/恢复、15分钟锁屏、1小时API和升级/A1–A11/R01–R05均待完成。当前没有可用真机。完整F-01–F-12、既有生文、01–14/16/17的每个冻结子目标继续同版必需，见[完整P01–P09表](releases/v0.3.0-dev.24-qwen-tts.md#完整待完成范围--full-remaining-scope)。APK只交付基座，用户自主管理模型；全部产品推理仍须同一Android、无需ROOT，无远程回退或ComfyUI节点体系。
