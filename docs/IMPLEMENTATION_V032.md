# v0.3.2 程序实现与扩展

> 本页记录 v0.3.2 的实现。v0.3.3 已另增 D03 Pixal3D MV 真实四视图子集，见[当前方案与剩余移植工作](MULTIVIEW_DIAGNOSTICS.md)。下方旧数量 / 证据按原版本理解。

[English](IMPLEMENTATION_V032.en.md) · [完整新方案](SPEECH_3D_EXPANSION.md) · [机器矩阵](../catalogue/release-0.3.2-implementation.json)

保留 F-01–F-12、既有文本、01–14 / 16 / 17 与九个 MOSS 子目标，不把原有工作拆至后续版本。原[基座范围](IMPLEMENTATION_V030.md)和[社区模型](IMPLEMENTATION_V031.md)继续有效；本版增加能力，不缩减既有支持。

| 编号 | 本轮实现 | 生产代码与行为 |
| --- | --- | --- |
| 01 | 四类语音、六个可选包 | Kokoro INT8、Melo 中文 INT8 / FP32、F5 v1、Omni GGUF / 原版；外部组件与许可独立 |
| 02 | 新语音运行器 | `AudioCppSpec / ExpansionEngine / native/speech_extra`；真实 audio.cpp CPU 库、F5 外置中文前端、完整 WAV |
| 03 | Melo 中文前端 | `TtsSpec / native/tts`；词组 phones / tones、四份 FST，保留既有 Kokoro / Piper / Matcha |
| 04 | 单图生 3D 与五个包 | `MeshSpec / ExpansionEngine / native/mesh`；TRELLIS.2 / Pixal3D CPU、几何与可选贴图、GLB |
| 05 | 共用基座闭环 | `mesh.generate`、任务 / 草稿 / 资源检查 / 取消 / 结果库 / API；仍由用户主动下载和提交 |
| 06 | 3D 设置与结果 | `expansion.js / glb-preview.js / GlbFile`；独立参数、超限归位、有界几何预览、GLB / 记录导出 |
| 07 | 来源与交付 | 16 条测评审计、11 包来源锁、原生许可、程序检查、双语完整文档、原签名、截图 / GIF / MP4 |

当前：**44 模板、78 模型包、14 扩展引擎＋既有文本引擎**。新增模型均与原模型平级，任务、基座、组件、内容来源和安装标签独立。推荐仍为 `m08 → m06 → m01`。

测评中只有 TRELLIS.2 / Pixal3D 单图架构子集进入当前 APK；其余配置的待移植工作见[完整 D01–D16 表](SPEECH_3D_EXPANSION.md#2-对指定-3080-生-3d-测评的逐项检查)，不以登记目录冒充执行支持。当前证据为程序验证，不是完整模型、Android 实机或画质验收。
