# 本地语音基座：实现、模型资产与验证边界

[English](TTS_ENGINE.en.md) · [开发状态](DEVELOPMENT.md) · [完整 v0.3.0 需求](MULTIMODAL_RELEASE_PLAN.md)

内部 **0.3.0-dev.3 / code 7** 接入真实编译的 `sherpa_tts` ARM64 CPU worker，绑定 sherpa-onnx 2.0.1 C API。Kokoro、Piper / VITS 和 Matcha 已有代码路径、固定组件候选和任务表单。**没有执行 Android 推理；不表示编号 10 已通过完整验收，也不是新 Release。** v0.3.0 的其余必需范围保持不变。

## 用户流程与资产边界

在“模型 → 全部”按“生音频”筛选，查看候选的引擎、许可、完整组件、总大小及可复用数据；用户点击下载才创建传输。下载完成后在“本地”编辑模型设置或点击“使用”，填写朗读文本，提交到同一任务队列。dev.10 已接入[共用执行槽](SCHEDULING.md)，等待回复后自动切换并在空闲时恢复仍被用户选择的文本模型；结果通过同一音频预览、原文件导出和接口读取。API 任务类型为 `speech.synthesize`，输入为 `input.prompt`，用已安装的模型包 ID 提交。

App 提供语音引擎代码，不提供音色或语言资产。安装、升级、浏览、接口启动及缺资产的任务均不下载模型。下面是数据专用候选配方，**不是预装模型**：

| 配方 | 用户选择后需要的组件 | 标签及当前边界 |
| --- | --- | --- |
| Kokoro 82M v1.0 · English | 固定 ONNX、54 音色的 voices.bin、tokens.txt、英语 lexicon | 生音频 / TTS / sherpa_tts / CPU；本配方仅英语，不能据多语种权重自动宣称已支持全部语言 |
| Piper en_US Lessac medium | 固定 VITS ONNX、tokens.txt、英语 lexicon | 生音频 / TTS / CPU；单音色；发布者 MODEL_CARD 引用 Lessac 数据条款 |
| Matcha en_US LJSpeech / Vocos | 固定声学 ONNX、Vocos 22 kHz 声码器、tokens.txt、英语 lexicon | 生音频 / TTS / CPU；单音色；声学权重卡未明确声明权重许可，仍待核对 |

配方及每个组件的 SHA256 / 大小 / 来源见 [model-bundles.json](../catalogue/model-bundles.json) 和 [bundle-evidence.json](../catalogue/bundle-evidence.json)。HF 文件固定完整提交；共享英语 lexicon 和 Vocos 使用上游 GitHub 资产，另以 SHA256 固定内容并记录资产 ID。Vocos 的哈希同时核对发布者 HF 文件页。构建阶段不下载权重。候选的许可尚需逐组件完成复查，不能把引擎的开源许可自动套给模型数据；这仍是完整版本验收项。

## 参数与实际执行

参数随模型 / 配方独立保存，表单支持预设和手动填写。配方范围之外还有签名引擎内的应用保护范围，自定义清单不能扩大这些范围：

| 参数 | 应用范围 | 处理 |
| --- | --- | --- |
| 线程 | 1–16 | 默认 2；不是设备实测的最优线程数 |
| 语速 | 0.25–3 | 默认 1 |
| 音色 ID | 配方声明范围；原生加载后再读实际数量 | 超限归位；实际有效 ID 写入产物来源 |
| 停顿比例 | 0–3 | 默认 1 |
| 输出时长保护 | 1–600 秒 | 默认 180；超出则失败，不把截断音频记为完整输出 |
| Piper / Matcha 噪声 | 0–2 | Piper 另有时长噪声参数；不向其他管线传无效参数 |
| 输入文本 | 1–4000 字符 | 必须由所选语言词表覆盖；拒绝负面提示词和空字符 |

sherpa 2.x 不再使用旧 espeak-ng-data。此接入明确要求用户词表；可通过独立 lexicon_2–lexicon_8 提供附加词表，语言 / 发音匹配仍须配方实测。代码检测到上游跳过未知词时拒绝成功，避免把漏字音频作为完整结果；仍需真机验证该日志路径及各种标点 / 数字的实际处理。当前候选未包含语音克隆能力。

`NativeWorker` 共用于扩散与语音模块。私有 JSON 文件传递文本，命令行仅包含请求文件路径；任务持有模型组件引用，取消会终止所属子进程。原生 worker 设置父进程死亡信号，输出单声道 16-bit PCM WAV，并检查样本数量、有限值、非全静音、采样率、大小和落盘结果。来源记录保留有效参数、音色数量、时长、峰值和 RMS；这些技术检查不证明朗读准确度或听感。

第三方标准输出 / 错误输出不转发；worker 在本进程截获固定库使用的三个 liblog 符号，构建检查导入 / 导出闭合。**Android 上的日志绑定与隐私行为尚未实际验证**，仍需设备检查。所有计算均在同一手机，词表不足或资源不足时本机报错。

## 构建与证据

```powershell
python tools/fetch_tts.py --transport ssh
python tools/build_tts.py
python tools/collect_tts_notices.py
python tools/test_tts.py
python tools/build.py
python tools/verify_package.py
```

在完成 [通用原生工具链准备](BUILD.md) 后运行。源码固定 `af2d8d81dbfa61c4cea4c568da78f3982edca005`；sherpa C API / ONNX Runtime 来自官方 v2.0.1 Android 发布包，**是上游预编译依赖**；LMA worker 在本项目用 Windows NDK r30 编译。依赖的 ELF API note 分别为 21 / 27，worker 为 28，均满足 Android 9 的声明门槛及 16 KiB 对齐。源码 / 包 / 组件锁、许可分别见 [tts-source-lock.json](../third_party/tts-source-lock.json)、[engine-lock.json](../third_party/engine-lock.json)、[许可来源](../third_party/tts-notice-sources.json)。bootstrap 和许可收集均只处理代码 / 通用许可，不下载模型；缓存保存在项目内。

62 项主机检查验证生产 Java 组件契约、参数上限、私有输入、进程取消、错误 / 重复 / 缺失完成事件、非零退出及清理。子进程输出是明确的任意测试字节，**不是 WAV、语音或模型输出**。当前没有手机离线语音、发音覆盖、三次加载卸载、速度 / 内存 / 发热、锁屏耐久或 Android 日志证据；这些以及各语言 / 音色许可仍须按完整发布门槛验证。

上游依据：[Android 文档](https://k2-fsa.github.io/sherpa/onnx/android/build-sherpa-onnx.html)、[TTS C API](https://k2-fsa.github.io/sherpa/onnx/c-api/html/tts.html)、[固定版本源码](https://github.com/k2-fsa/sherpa-onnx/tree/af2d8d81dbfa61c4cea4c568da78f3982edca005)。上游能力与 LMA 真机证据分别记录。
