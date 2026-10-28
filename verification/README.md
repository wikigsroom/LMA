# Verification records / 验证记录

These records belong to **LMA 0.2.0** and are exported by `tools/package_delivery.py` after checking current input fingerprints. 本目录由交付工具核对输入后生成，可公开复查；不要手工把未通过项目改为成功。

| Record | Scope / 范围 |
| --- | --- |
| [validation.json](validation.json) | Release summary / 发布验证汇总 |
| [build.json](build.json) | APK identity, hash, and exact build inputs / 构建信息 |
| [package.json](package.json) | Signature, native ELF, alignment, packaged assets / 包验证 |
| [backend.json](backend.json) | 85 host assertions, Android framework adapters / 桌面后端 |
| [hub.json](hub.json) | 45 production HF/client/controller/store assertions / HF 与本地逻辑 |
| [hub-live.json](hub-live.json) | 5 live public HF Mirror API metadata checks, no weights/inference / 实时元数据 |
| [protocol.json](protocol.json) | 25 JVM protocol assertions / 协议 |
| [sqlite.json](sqlite.json) | 5 host SQLite query checks / SQL 查询 |
| [ui.json](ui.json) | 66 browser checks using an explicit test bridge / 界面 |
| [android-lint.json](android-lint.json) | 0 errors, 7 reviewed warnings / Lint |
| [runtime.json](runtime.json) | Pinned runtime configuration audit / 引擎静态核对 |
| [model-network.json](model-network.json) | Pinned publisher metadata and GGUF byte probes / 网络探测 |
| [uncensored-models.json](uncensored-models.json) | 14 publisher declarations and exact weight attribution / 无审查依据 |
| [acceptance-build.json](acceptance-build.json) | Acceptance APK compilation, not device execution / 验收工具构建 |
| [device.json](device.json) | Device unavailable; no successful phone checks / 无可用真机 |

**226 desktop assertions; 0 physical-device checks.** No Android model inference, refusal-rate measurement, or screen-off endurance was executed. 桌面与静态证据不替代手机实测。

See [validation / 验证](../docs/VALIDATION.en.md), [Chinese audit / 完成条件](../docs/COMPLETION_AUDIT.md), and [device acceptance / 真机验收](../docs/DEVICE_ACCEPTANCE.en.md). Media provenance is separate in [manifest.json](../docs/media/manifest.json).

内部 dev.8 验证另见 [development/status.json](development/status.json) 与 [text.json](development/text.json)：310 基座、66 新增文本主机、147 界面检查，0 真机结果，不替代上面的公开 v0.2.0 历史记录。Internal dev.8 evidence stays separate from published history and does not establish full-release acceptance.

内部 dev.9 的 [migration.json](development/migration.json) 是 69 项真实主机文件 / 硬链接 / 子进程检查；使用零 tensor 元数据与固定协议内容，不是 Android、真实模型输出或完整版本证明。 / Internal dev.9 migration evidence remains explicitly host-only.

开发 dev.10 增加 [scheduler.json](development/scheduler.json)：43 项生产任务运行器、真实主机子进程与回环 HTTP 调度检查；明确 `physical_android=false` / `model_inference=false`。Production scheduler host evidence is separate from pending physical-Android/model acceptance.

内部 dev.11 新增 [inputs.json](development/inputs.json)：64 项实际主机文件、生产 WAV 和 HTTP 上传 / 续传检查；[scheduler.json](development/scheduler.json) 扩展为 49 项，含生产输入引用与真实子进程读取。UI 为 182 项，全部非手机推理证据。Input and scheduler host evidence does not establish Android media/model behavior.

内部 dev.12 的 [diffusion.json](development/diffusion.json) 包含 83 项扩散检查：56 项生产 Java / 实际主机协议子进程、27 项执行共用 C++ 策略。基座 381 项、UI 194 项；无模型图片或物理 Android 结果。Diffusion host protocol/policy evidence does not prove phone inference or complete-release acceptance.


dev.13：[高级扩散 / 视频接入](../docs/ADVANCED_DIFFUSION.md)，174 diffusion（117 Java + 57 C++）、425 foundation（233 recipe/integrity）及 203 UI checks；35 screenshot fixtures。证据仍为主机 / 协议 / 原生编译与 APK 检查，不是 Android 模型输出；完整 v0.3.0 未发布。

dev.14：[Sana MNN](../docs/MNN_SANA_ENGINE.md) / [English](../docs/MNN_SANA_ENGINE.en.md)；新增 [mnn.json](development/mnn.json) 的 74 项生产绑定 / 真实主机进程 / C++ 策略检查；445 foundation（253 recipe/integrity）、208 UI，37 张截图与录屏 / GIF。20 个原生文件仅为编译 / APK 证据，无模型 / Android 输出，完整 v0.3.0 未发布。

dev.15：[Qwen3-TTS 0.6B Base](../docs/QWEN_TTS_ENGINE.md) / [English](../docs/QWEN_TTS_ENGINE.en.md)；[qwen-tts.json](development/qwen-tts.json) 的 81 项主机检查使用明确的静态结构 WAV，不生成语音；[qwen-headers.json](development/qwen-headers.json) 只核对两个固定 GGUF 的文件头，不读取张量。457 foundation、216 UI、39 张截图 / 录屏 / GIF、21 个原生文件及 APK / Lint 均为限定范围开发证据。No model/Android inference, quality, RTF or endurance is proven; every full v0.3.0 gate remains open where evidence is missing.

内部 dev.16 的 [development/moss-delay.json](development/moss-delay.json) 包含 176 项检查：69 项生产 Java / 实际主机子进程、107 项 C++ 算法 / 策略，包含固定上游 Delay 自检与 frame-major codec / WAV 边界。WAV 是结构夹具；没有 tensor / 模型 / Android 推理。App 更新基座，模型用户自行选择；完整 v0.3.0 仍需各冻结目标和设备验收。 / Internal dev.16 evidence is scoped and does not establish full Release acceptance.
