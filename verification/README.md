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

`development/openmoss.json` records Local-v1.5 / SoundEffect-v2 production-Java bindings, six actual host children, structural WAV validation and pinned upstream sound formatting/noise/sigma checks. It contains no model inference or physical Android evidence and cannot satisfy complete v0.3.0 gates.


dev.19: [development/moss-rq.json](development/moss-rq.json) has 178 scoped checks: 132 Java / 10 actual host children, 30 native policies, 14 metadata-only GGUF checks and two actual synthetic tiny graphs. No trained checkpoint inference or Android execution. [development/openmoss.json](development/openmoss.json) now records 514 checks / 21 host children including old SoundEffect ambient conditioning; the old six-child description above belongs to dev.17. 550 foundation / 280 UI checks, original-signature APK with 24 native files, 55 UI FIXTURE screenshots plus recording/GIF and 0-error/13-warning Lint remain development evidence. 完整模型、手机质量 / 资源 / 耐久和所有冻结目标继续待验收，状态保持 `release_ready=false`。见[本轮编号说明](../docs/releases/v0.3.0-dev.19.md)。

SoulX开发证据分别记录未训练声学、真实参考组件与真实声学重建，不能互相代替。[参考145项](development/soulx-reference.json)、[训练重建253项](development/soulx-trained.json)、[参考ARM64编译](development/soulx-reference-arm64.json)包含当前源码指纹、真实进程 /图计数与明确的未完成标记。Complete TTS/App/quality/physical Android/Release remain unaccepted; see [中文边界](../docs/SOULX_REFERENCE.md) / [English scope](../docs/SOULX_REFERENCE.en.md).

SoulX语言与完整训练主机链路新增[语言546项](development/soulx-language.json)、[host构建](development/soulx-language-host.json)、[ARM64编译](development/soulx-language-arm64.json)及[整链路60项](development/soulx-pipeline.json)：20次语言 /5次整链路原生子进程，完整官方Qwen3、独立HF BF16 logits、原始RAS /历史和实际取消；新文字输出1.44 /1.76秒WAV。Complete trained host execution with synthetic references is now recorded separately; App integration, speech quality, physical Android and complete-target acceptance remain false. Status exposes separate host/Android flags and their definitions; see [中文](../docs/SOULX_LANGUAGE.md) / [English](../docs/SOULX_LANGUAGE.en.md). No model/tokenizer/WAV is shipped.

Old LTX0.9.8 adds independent [DiT parity](development/ltx098-transformer.json) and [ARM64 Vulkan compilation](development/ltx098-transformer-arm64.json) receipts:675 checks /80 actual host children /48 original PyTorch comparisons,untrained reduced-width2/3/28-layer graphs,F32/F16 dense weights and actual RTX3060 Vulkan execution. Exact715-tensor full checkpoint layout is checked without trained weights. Complete video,App registration and physical Android remainfalse. See [中文](../docs/LTX098_DIT.md) / [English](../docs/LTX098_DIT.en.md) and [numbered handoff](../docs/releases/v0.3.0-dev.21-ltx-dit.md).

旧LTX新增 [sampling receipt](development/ltx098-sampling.json)：692检查 /58真实原生子进程 /111误差记录，22数学案例、10条未训练CPU /Vulkan八步轨迹及完整训练28层Vulkan velocity /latent采样。主机进程内存 /图缓冲分别记录，未测GPU /系统总占用。状态新增 `ltx098_trained_dit_latent_host_tested`；T5 /VAE /视频 /App /手机 /完整Release继续false。ARM64记录同时核对probe /sampler。No model data enters APK; see [中文](../docs/LTX098_SAMPLING.md) / [English](../docs/LTX098_SAMPLING.en.md) / [numbered handoff](../docs/releases/v0.3.0-dev.21-ltx-sampling.md).


旧LTX T5新增 [491项文本组件检查](development/ltx098-text.json)、[主机构建](development/ltx098-text-host.json)、[ARM64编译](development/ltx098-text-arm64.json)：76真实原生子进程 /39防护、完整训练24层 /219张量与三个不同短提示词、原始外部分词配置和全学习词表身份、真实计算中取消。49个独立参考文件先核对尺寸 /SHA；映射 /张量 /临时F32图缓冲与Windows进程采样分开记录。`ltx098_t5_host_tested=true` does not establish Android execution, video, App or quality acceptance. Historical sampler receipts retain their synthetic-caption scope. [中文](../docs/LTX098_TEXT.md) / [English](../docs/LTX098_TEXT.en.md) / [本轮编号实现与完整待办](../docs/releases/v0.3.0-dev.21-ltx-text.md).


旧LTX VAE新增 [355项组件检查](development/ltx098-vae.json)、[主机构建](development/ltx098-vae-host.json)、[ARM64编译](development/ltx098-vae-arm64.json)：36真实原生子进程 /31防护 /40误差记录，完整训练132张量 /552,814,641参数、九段CPU装卸及未修改官方Decoder.forward。四种几何 /时间 /噪声条件、44个SHA固定参考、18个外部资产、实际ORT计算中终止均单独验证。`ltx098_vae_executed` is a host-only compatibility alias; explicit host/Android-compiled/Android-tested fields prevent treating it as phone or full-video support. Earlier component receipts remain unchanged. No App/APK/quality/phone/Release acceptance is added. [中文](../docs/LTX098_VAE.md) / [English](../docs/LTX098_VAE.en.md) / [编号交付与全部待办](../docs/releases/v0.3.0-dev.21-ltx-vae.md).


Old-LTX real-prompt host follow-up adds [portable tensor checks](development/ltx098-tensors.json), separate [host](development/ltx098-tensors-host.json) / [ARM64 compile](development/ltx098-tensors-arm64.json) and [trained pipeline](development/ltx098-pipeline.json) records. 原始前向完整链路 / A/B/A / 实际主机视频，与官方默认多尺度、PixArt 权重身份、质量 / App / 物理 Android 分别记录；已有组件记录保留原有历史范围。The [host media receipt](../docs/media/development/ltx098-host-media.json) fixes actual source frames, hashes and GIF/MP4 timings, without claiming an App recording. See [中文](../docs/LTX098_PIPELINE.md) / [English](../docs/LTX098_PIPELINE.en.md) / [numbered implemented and complete pending scope](../docs/releases/v0.3.0-dev.21-ltx-pipeline.md).

Current old-LTX pipeline evidence records 163 checks:157 passed/six float gates failed; test exit1 is preserved. Both final RGB comparisons pass. Three actual trained jobs are executed, but strict host numerical acceptance remains false. Same-caption native DiT isolation is separate evidence. Repository audit success validates this failure record, not complete model or Release acceptance.
