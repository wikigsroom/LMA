# Changelog / 更新记录

## 0.3.0-dev.24 — diffusion progress and trained host evidence / unreleased

新增独立 SD-Turbo / LCM checkpoint 主机验证：10 原生子进程 / 6 PNG，80 项生产 Java / 绑定检查、完整2对象导入、5真实 worker / 3 PNG；LCM 原始687张量 / 859,602,884参数、686转换张量逐值对照、30完整 UNet 前向、仅5120字节偏置的固定引导候选及原生取消恢复。五份公开记录、原始PNG / GIF / MP4、[中文](docs/SD_DISTILLED_TRAINED.md) / [English](docs/SD_DISTILLED_TRAINED.en.md)及[编号完整待办](docs/releases/v0.3.0-dev.24-sd-distilled.md)同步。LCM face/detail quality remains failed; product preparation, canonical pipeline, phone/resource/endurance and full Release remain open. Production sources and APK inputs/bytes are unchanged.

新增完整 SDXL 与 SD1.5 / SDXL 风格 LoRA、LCM-LoRA 的真实训练主机专项：固定五新对象、双 CLIP / UNet / VAE 与适配器完整结构、零强度 / 启用 / LCM 权重反事实 / 组合 / 取消恢复对照；生产 Java 完整导入七唯一对象、模型参数 / 适配器租约 / 快照 / 实际 worker。原始 PNG、联系图、标明范围的 GIF / MP4、独立原始复核、五份公开 JSON、双语文档和[编号完整待办](docs/releases/v0.3.0-dev.24-sd-variants.md)同步。Low-step sample quality is not accepted; actual hash differences do not establish semantic quality. This developer-only follow-up leaves production sources/APK bytes unchanged and does not close SD-Turbo, the separate LCM checkpoint, Android or complete Release gates. [中文](docs/SD_VARIANTS_TRAINED.md) / [English](docs/SD_VARIANTS_TRAINED.en.md).

新增编号11完整Qwen0.6BBase/12Hz codec两GGUF/920MB取得及真实生产源码主机执行：18WAV/12控制涵盖十语言、参考、采样和frame16后取消恢复；94项生产Java检查、6真实worker、2完整对象导入且零网络，145原始文件/31协议/22WAV/2对象独立复核及8项错误范围提升控制。原始音频/波形PNG/GIF/MP4、双语指南/README与[编号完整待办](docs/releases/v0.3.0-dev.24-qwen-tts.md)同步；生产/APK字节不变。The greedy short-text output matches the30-second budget, without a separate EOS/budget reason; quality, voice similarity, Z20 fit, Android endurance and the complete Release remain unaccepted. [中文](docs/QWEN_TTS_TRAINED.md) / [English](docs/QWEN_TTS_TRAINED.en.md).

新增编号10全部三套冻结训练资产/真实生产worker主机验证：Kokoro54音色、Piper Lessac、Matcha LJSpeech/Vocos，共68成功WAV/13控制/82原生进程；157项生产Java检查、完整导入9对象/11引用、独立设置/快照、12真实子进程取消/时长错误/恢复。独立复核394原始文件/82协议/74WAV/9导入对象，拒绝8种错误范围提升。三套原始WAV/波形PNG/GIF/含实际音频MP4、五份公开JSON、双语文档及[编号完整待办](docs/releases/v0.3.0-dev.24-tts.md)同步。Unchanged production C++ uses official sherpa2.0.1/ORT1.28.2 Windows libraries; Android log interposition, speech quality, licenses, every phone/target and full Release remain open. No APK inputs/bytes or user asset policy change. [中文](docs/TTS_TRAINED.md) / [English](docs/TTS_TRAINED.en.md).

新增Nano100M真实训练资产与独立用户导入清单：固定11组件/717,414,286字节、18音色范围，7成功WAV/7控制及40项生产Java→真实worker检查；原始65文件/15协议/9WAV/11对象复核，8种错误提升验收标记被拒绝。三语原始WAV、波形图/GIF/含真实音频MP4、双语指南和[编号完整待办](docs/releases/v0.3.0-dev.24-moss-nano.md)同步。This source/metadata follow-up preserves existing APK bytes. Host ORT1.28.0/API28 differs from Android1.28.2/API28; production neural C++ is unchanged. Model assets remain user-selected and external; speech quality, Android/background, every frozen target and full Release remain pending. [中文](docs/MOSS_NANO_TRAINED.md) / [English](docs/MOSS_NANO_TRAINED.en.md).

修正生产扩散 worker 的 loading/generating 进度，避免把加载/VAE回调都当作采样；原生构建复用 CMake 缓存驱动器。新增固定 SD1.5 真实权重/外部词表、生产源码 CPU 推理、采样取消/恢复和 A/B/A 验证工具与实测媒体；首次错误阶段分类的尝试保留并重新执行。旧 LTX 两次原训练前向观察114调制位置、两次八步原生候选、478文件独立复算；两条B条件仍超冻结门槛。原签名 dev.24/code28 APK、限定回归、68界面截图/录像/GIF、双语文档及编号完整待办同步。

Corrects top-level diffusion progress without changing model math. Adds actual trained SD1.5 production-source host validation and a labelled still-image slideshow, with Windows/Android scopes separated. Old-LTX modulation staging matches all original observed sites but does not repair the failed full sampler gates. The App remains foundation-only, with explicit user-selected assets; all physical-phone, quality/background and complete-release gates remain open. [SD1.5 中文](docs/SD15_TRAINED.md) / [English](docs/SD15_TRAINED.en.md) / [LTX 中文](docs/LTX098_MODULATION.md) / [English](docs/LTX098_MODULATION.en.md) / [Numbered implementation and full pending scope](docs/releases/v0.3.0-dev.24.md).

## 0.3.0-dev.23 source follow-up / 2026-10-29 — original F32 operation staging

实现 F32 RMS 分组归约和 GeGLU 原始运算顺序；72 局部对照、四候选共 12 次真实 T5、三次实际 DiT/VAE/RGB 链路及重复 A 一致性。A 通过，B 三项浮点门槛失败；保留原参考和门槛。复核字段修复后显式恢复首条真实采样，执行与复用如实记录。新双语指南、误差图、真实主机帧/GIF/视频及来源审查同步；App/APK/注册引擎保持原状态。Four isolated T5 variants and actual host A/B/A improve diagnosis without accepting failed floats, Android or Release. [中文](docs/LTX098_STAGING.md) / [English](docs/LTX098_STAGING.en.md) / [编号及完整待办](docs/releases/v0.3.0-dev.23-ltx-staging.md).

补充五次完全相同参考条件的采样器诊断，定位 CPU 激活隐式 F16 转换；显式 F32 输入减少该误差但未关闭完整模型门槛，Vulkan 未改善。所有候选均未注册或打包，公开证据 / 范围标记与双语说明同步。Five fixed-reference sampler diagnostics preserve all failed gates and separate CPU/Vulkan behavior.

## 0.3.0-dev.23 — user-selected runtime model association / unreleased

新增通用签名关联方案、实际环境依赖指纹绑定、`model.assemble`共用任务、排队/运行引用保护、完整验哈希及本地硬链接复用。7个固定候选中新增旧LTX社区Google T5 Q5单尺度运行资产：20个派生组件复用，2项T5依赖由用户随后明确下载/导入，缺失时暂停、未安装。原模型参数和两份记录的独立删除保留。47项核心契约、生产队列/API检查、真实训练文件关联、原签名APK code27、中英说明及截图66–68/录屏/GIF同步。

Signed association plans bind preparation/runtime identities and share jobs, cancellation, explicit retry and storage. No automatic downloads, model bytes in the APK, remote execution or generation-engine availability is introduced. Actual trained asset association is a HOST filesystem check; UI media uses explicit fixtures. Six full-chain float failures, every frozen subtarget and all Android/background gates remain required for one complete v0.3.0. [中文](docs/MODEL_ASSEMBLY.md) / [English](docs/MODEL_ASSEMBLY.en.md) / [Numbered delivery and full pending scope](docs/releases/v0.3.0-dev.23.md).

## 0.3.0-dev.22 — explicit local runtime preparation / unreleased

用户下载/导入固定源模型后明确选择准备；签名方案、两个原生程序、共享任务/执行槽、独立派生存储/恢复/删除、源删除后本地可管理、过热/空间/内存检查。生产Java核心处理完整旧LTX源文件并校验20个结果（6,061,184,991字节），44项生命周期契约通过；两个准备器的Android父进程结束保护及主机/ARM64重编译。原签名APK code26含29原生文件和九份审计无参数图，不含学习模型数据。双语文档、截图62–65、录像/GIF与编号待办同步。

Trusted plans and two native preparers reuse shared jobs and atomic derived-asset storage. Full trained production-core HOST preparation passed; package/host/UI/Android evidence remains separate. Updated APK fingerprints include all preparation code without invalidating unchanged math producers. Android execution, T5 user assets, production video integration and six failed full-chain float gates remain open. No automatic model retrieval, frozen-target deferral or complete Release. [中文](docs/MODEL_PREPARATION.md) / [English](docs/MODEL_PREPARATION.en.md) / [Numbered delivery and full pending scope](docs/releases/v0.3.0-dev.22.md).


## 0.3.0-dev.21 source follow-up / 2026-10-29 — native VAE asset preparation

新增共用原生准备 I/O、旧 VAE 九图无学习数据审计、从原始用户 checkpoint 流式生成九份参数文件及事务提交。18 资产 /2.212 GB 与独立 Python 导出整文件身份一致；243 检查、25 组失败保护、31 原生子进程及四种尺寸的 40 个原始前向解码对照通过。DiT 156 检查与 Windows / ARM64 构建重新通过。

Architecture remains foundation code; learned weights, timestep multiplier and statistics stay user data. Synthetic-latent host decoding is separate from prompt-video quality, App acquisition, Android execution and the six failed complete-chain float gates. Existing APK/UI unchanged; full v0.3.0 scope retained, no new Release. [中文](docs/LTX098_VAE_PREPARE.md) / [English](docs/LTX098_VAE_PREPARE.en.md) / [numbered implementation and complete pending scope](docs/releases/v0.3.0-dev.21-ltx-vae-prepare.md).

## 0.3.0-dev.21 source follow-up / 2026-10-29 — native local asset preparation

旧 LTX safetensors → DiT GGUF 改为独立可移植原生流式组件：完整同流 SHA、F16 / F32 分块转换、旧版结构校验、取消 / 源保留 / 无覆盖提交。156 检查、46 组失败保护、51 原生子进程；6.34 GB 完整训练源与 3.85 GB Python 基线整文件身份一致，主机观测峰值工作集 13.27 MiB。Windows / Android ARM64 API28 /16KiB 编译通过。

Portable Python-free preparation contains no learned data and performs no inference. Production App acquisition, on-phone VAE preparation, six failed full-chain float gates and every frozen v0.3.0/device gate remain open. APK/UI unchanged; no new Release. [中文](docs/LTX098_PREPARE.md) / [English](docs/LTX098_PREPARE.en.md) / [numbered implemented and full pending scope](docs/releases/v0.3.0-dev.21-ltx-prepare.md).

## 0.3.0-dev.21 source follow-up / 2026-10-29 — text precision diagnostics

旧 LTX 真实训练 T5：314 中间张量、628 原始文件哈希 / 误差重算、120 同输入算子对照；原生及原始参考最终 embedding 均保持既有字节身份。新增独立注意力 / 可选线性 F64 候选构建及 A/B/A 复现工具、双语指南、来源图与开发证据审计。

Actual host diagnostics and separately identified precision candidates do not close six failed original full-chain float gates, establish phone execution or change APK. No automatic model retrieval or external inference is added. All frozen v0.3.0 targets remain required. [中文](docs/LTX098_PRECISION.md) / [English](docs/LTX098_PRECISION.en.md) / [numbered implementation and full pending scope](docs/releases/v0.3.0-dev.21-ltx-precision.md).

候选实测：两种实现各完成三次训练T5 A/B/A，重复字节一致；组合候选A / B embedding最大误差2.861e-6 /1.192e-6。两次A原始八步轨迹仍超原0.003门槛（0.003953 /0.003829），证据保持失败及exit 1；候选VAE / B视频 / 完整修复未验收。Six trained candidate text jobs, two failed partial video probes; no gate relaxation.

## 0.3.0-dev.21 source follow-up — real-prompt old-LTX host pipeline / unreleased

新增真实提示词、完整训练 T5、旧版 0.9.8 distilled DiT 八步采样、九段 VAE 与 RGB/MP4 的独立单尺度主机串联。可移植 RNG / 张量还原 / 帧封装组件独立 Android 编译；完整链路参考从原始模型前向传播到 RGB，保留固定精度门槛与实际 A/B/A 任务。基座与模型资产继续分离，没有模型隐式获取或 APK 模型数据。

Real host outputs, separately labelled comparison media, component identities/lifetimes, independent original-forward checks and distinct Android compilation evidence. The explicit Google/community Q5 text variant does not establish official PixArt weight identity or the default multi-scale preset. Quality, production App integration, public user acquisition, phone/endurance and all frozen v0.3.0 gates remain open; APK/UI media remain dev.21 and no Release is created. [中文](docs/LTX098_PIPELINE.md) / [English](docs/LTX098_PIPELINE.en.md) / [numbered implemented and complete pending scope](docs/releases/v0.3.0-dev.21-ltx-pipeline.md).


本次真实主机视频的完整参考验收：163 检查中 157 通过、6 项 float gate 失败；RGB 两组均通过。保留原门槛与 exit 1，并分开记录 executed=true / numeric accepted=false；同 caption 隔离诊断指向文本编码微小误差在采样中的放大。This checkpoint publishes real experimental outputs and the numerical failure, not successful full-chain acceptance or an APK Release.

## 0.3.0-dev.21 source follow-up / 2026-10-29 — trained old-LTX VAE

旧版0.9.8 distilled完整训练VAE：132张量 /552,814,641参数从原始BF16转F32，九段CPU ONNX会话依次装卸；外部图 /数据2,211,661,835字节不进入APK。噪声先在归一化空间混合，原始通道统计 /时间条件 /PixelNorm /时空上采样保留。355检查 /36真实原生子进程 /31防护 /40逐段与最终误差记录通过；独立未修改原始Decoder.forward四组几何参考，44参考文件先核对SHA；最终帧最大误差2.14577e-6，真实ORT计算中取消和无会话泄漏通过。

Full trained decoder host parity, distinct Android ARM64/API28/16KiB compilation and measured host memory are reported separately. No model graphs/statistics enter APK, no implicit model acquisition, no complete prompt-to-video/quality/App/phone claim. APK/UI media stay dev.21; all frozen v0.3.0 targets remain required in one complete release. [中文](docs/LTX098_VAE.md) / [English](docs/LTX098_VAE.en.md) / [numbered implemented/pending handoff](docs/releases/v0.3.0-dev.21-ltx-vae.md).



## dev.21 source follow-up — old LTX T5 / unreleased

新增完整24层T5原生CPU文本编码组件：外部量化存储 /原始tokenizer配置、全部32000学习词条与归一化身份、F32 GELU /临时矩阵解量化、raw embedding /mask、实际计算中取消与输出保护。491检查 /76真实原生子进程 /39防护通过；219张量 /4,762,310,656参数与独立解量化参考对照，训练最大误差3.27826e-6；ARM64/API28/16KiB编译单独核验。

Full trained T5 host execution with three short prompts and a repeated call, original external sentinel definitions,49 independently hashed oracle artifacts, bounded temporary matrix buffers and separate host process-memory counters. No weights/vocabulary or research executable enters APK; no unquantized-weight/prompt quality, full trained256-token completion, VAE/video/App/phone acceptance is claimed. APK/UI media staydev.21; the complete frozenv0.3.0 remains one release. [中文](docs/LTX098_TEXT.md) / [English](docs/LTX098_TEXT.en.md) / [numbered implemented/pending handoff](docs/releases/v0.3.0-dev.21-ltx-text.md).

## dev.21 source follow-up — old LTX trained DiT sampling / unpublished

固定完整旧0.9.8训练检查点，显式下载 /断点 /完整SHA核对，本地逐张量DiT GGUF转换；新增旧坐标 /unpatchify /精确8步RF与逐步事件 /取消。692检查 /58真实原生子进程 /111误差记录通过，含完整715张量 /28层训练Vulkan前向及8步latent官方对照；原有675项回归通过，ARM64 probe /sampler分别编译核验。训练最终latent最大误差3.57628e-6，人工caption embeddings未运行T5 /VAE，不是视频输出或手机验收。

Pinned external checkpoint, explicit acquisition and streaming local conversion; publisher geometry/RF/layout and native CPU/Vulkan trajectories, full trained DiT Vulkan velocity/eight-step latent parity, separate ARM64 compilation and host process-memory counters. No model data or research executable enters APK. APK/UI media stay dev.21; complete video/App/phone/quality and the full frozen v0.3.0 remain unaccepted. See [中文](docs/LTX098_SAMPLING.md) / [English](docs/LTX098_SAMPLING.en.md) / [numbered implemented/pending handoff](docs/releases/v0.3.0-dev.21-ltx-sampling.md).


## dev.21 source follow-up — old LTX native DiT / unpublished

精确LTX-Video2B0.9.8独立原生CPU /Vulkan DiT，全715张量布局核对；675检查 /80原生子进程 /48原始PyTorch数值对照通过，含28层小宽度未训练图、F32 /F16密集权重和31个拒绝用例。固定F32 shader计算、原生Windows /NDK与新版shaderc来源，ARM64/API28/16KiB编译单独记录。双语方案 /复现 /证据与编号待办同步；APK /UI媒体仍dev.21，训练视频 /App /手机 /完整v0.3.0仍未验收，公开Release仍v0.2.0。

Independent exact-old-version CPU/Vulkan transformer component with publisher-forward parity and separate Android compilation; UNTRAINED reduced-width graphs do not establish complete video support. No model data or research executable enters APK. See [中文](docs/LTX098_DIT.md) / [English](docs/LTX098_DIT.en.md) / [numbered implementation and complete pending work](docs/releases/v0.3.0-dev.21-ltx-dit.md).

## 0.3.0-dev.21 — SoulX App foundation / unpublished

- 完整SoulX CPU worker、14份用户资产（含40字节声源权重）、四说话人参考原文、独立联合参数及共用任务 /API接入；无模型数据进入APK。Complete native worker, paired inputs and shared foundation; explicit user assets only.
- 222项Java /C++契约与95项完整训练生产worker检查；两说话人新文字4.84秒WAV、四说话人截断、两次主机阶段强制终止，分别标识无质量 /手机结论。Trained host execution remains separate from complete Android acceptance.
- 582基座 /295UI /80HF回归；34个元数据配方，27原生文件，72份生产Java + 1份生成源码；原签名dev.21 /code25，修正Gradle /应用状态 /UA的旧版本字面量。Consistent version identity; refreshed bilingual docs, screenshots59–61, recording/GIF.
- 共享原生库校验允许严格字节 / SHA256 / API 一致的复用，拒绝冲突；10 项回归与最终 27 文件 APK 校验通过。Exact runtime identity is required for shared dependencies.
- 目标13仍缺完整公开用户下载候选、语音质量和Android；01–14 /16 /17、全部冻结子目标 /后台与完整Release保持同版阻塞。Public release remainsv0.2.0. [方案](docs/SOULX_ENGINE.md) / [English](docs/SOULX_ENGINE.en.md) / [编号交付](docs/releases/v0.3.0-dev.21.md)。


## dev.20 source follow-up — SoulX language and complete trained host pipeline / unpublished

源码后续更新（APK仍dev.20）：[SoulX语言与完整主机链路](docs/SOULX_LANGUAGE.md)已运行全部训练Qwen3 /S3 /CAMPPlus /Flow /HiFT，以两段新文字输出24kHz WAV。语言546项 /20次原生子进程、整链路60项 /5次原生子进程通过；官方与较早社区词表分开验证，实际原始HF logits、RAS /历史和运行中取消均核对。ARM64 /API28 /16KiB编译通过，执行器未进APK。参考PCM为合成输入，没有语音质量、App或手机验收结论；模型与WAV留在忽略目录，完整范围 /Release门槛保留。见[编号实现与完整待办](docs/releases/v0.3.0-dev.20-soulx-language.md)。

Source follow-up (APK remains dev.20): [SoulX language and complete host pipeline](docs/SOULX_LANGUAGE.en.md) execute trained Qwen3/S3/CAMPPlus/Flow/HiFT on fresh texts and write 24 kHz WAV. Language 546 assertions / 20 native children and pipeline 60 assertions/5 native children pass; distinct official/earlier community tokenizers, full original HF logits, RAS/history and actual decode cancellation are checked. ARM64/API28/16KiB compilation passes; executors are outside APK. Synthetic references provide no speech quality, App or phone acceptance. Models/WAVs remain ignored; all complete-scope/Release gates stay open. See [numbered implementation and remaining work](docs/releases/v0.3.0-dev.20-soulx-language.md).

## dev.20 source follow-up — trained SoulX reference/acoustic reconstruction / unpublished

- 新增完整训练S3Tokenizer v2 / CAMPPlus原生参考提取，完整ONNX / tensor身份保持，显式开发权重下载与严格来源锁；145项 /15主机子进程 /10图 /2实际终止。Native trained references with exact publisher identity and explicit asset preparation.
- 使用真实Flow / HiFT和原生训练参考完成253项声学重建、54图 /63阶段 /12隔离比较；定位F0浮点相位差，独立RMSE /SNR门槛，保留未训练244项原阈值。Shared CPU ORT contracts and Android ARM64/API28/16KiB compilation pass.
- [双语方案与复现](docs/SOULX_REFERENCE.md) / [English](docs/SOULX_REFERENCE.en.md) / [编号完成与待办](docs/releases/v0.3.0-dev.20-soulx-reference.md)。目标码来自合成PCM，未运行Qwen3 /完整TTS、未接App、无手机 /质量验收；APK /媒体仍为dev.20，公开Release仍v0.2.0，所有冻结范围保留在同一完整v0.3.0。

## dev.20 source follow-up — full SoulX acoustic networks / unpublished

新增完整 Flow / HiFT四图离线导出与原生 ORT/CPU声学链路、学习源、顺序会话 / 运行中取消，修复参考前缀帧预算。244项限定检查、12次主机子进程、57次完成图执行、1次实际 ORT终止；均为完整结构的未训练参数，不是完整 SoulX语音。ARM64/API28/16KiB编译及 DSP155项检查通过。双语方案、来源许可、独立证据和编号交付同步；APK / UI媒体沿用dev.20，不创建 Release。

Added full-network acoustic export and native execution with sequential ORT/CPU sessions, learned source and actual in-run termination. Scoped host / ARM64 evidence uses UNTRAINED parameters; language/reference models, App integration, trained speech quality and phone gates remain open in the same complete v0.3.0. See [numbered delivery](docs/releases/v0.3.0-dev.20-soulx-acoustic.md), [中文](docs/SOULX_ACOUSTIC.md) / [English](docs/SOULX_ACOUSTIC.en.md).

## dev.20 source follow-up — SoulX DSP / unpublished

新增尚未接入 APK 的 SoulX C++ 音频计算库：独立 S3 / Flow / CAMP 前端、sinc 重采样、CFG Euler、HiFT STFT / ISTFT / NSF，修复长序列半像素相位插值并检查30 / 120秒 F0。153项限定检查、49次主机子进程及 Android ARM64/API28 静态编译；双语文档、固定来源 / 许可和独立证据同步。模型推理 / 音频产物 / 真机仍0，完整执行器待完成，APK / 页面 / 媒体沿用 dev.20，不创建 Release。

Added unregistered SoulX native audio primitives with three distinct frontends, sinc resampling, CFG Euler and HiFT spectral/NSF operations, including long-offset interpolation alignment. 153 scoped checks/49 host children and Android ARM64/API28 static compilation; bilingual docs, pins/licenses and separate receipts. No complete-model/phone evidence; APK/UI/media remain dev.20. Full scope stays in the same v0.3.0. See [numbered delivery](docs/releases/v0.3.0-dev.20-soulx-dsp.md).

## 0.3.0-dev.20 — internal / unpublished

新增 Stable Audio Open Small 同机 LiteRT CPU 基座：顺序 T5 / DiT / 音频解码、四份用户自选组件、HF TFLite 文件识别、每模型可编辑参数与有效 token / 固定长度成本说明。144 项限定检查含实际 LiteRT 微型图和 6 次主机子进程，不是整模型或 Android 推理。

Added a native same-phone Stable Audio pipeline, strict pinned export layouts, isolated worker lifecycle, model-specific bounded settings and receipts. All 33 recipes are metadata; no implicit model transfers. Original-signature development APK, 561 foundation / 287 UI assertions, bilingual docs, screens 56–58 and refreshed recording/GIF. Full frozen scope and phone gates remain in one complete v0.3.0; no new Release. See [numbered notes / 编号交付](docs/releases/v0.3.0-dev.20.md).

## 0.3.0-dev.19 — 2026-10-28 (internal / unpublished)

新增旧 Local / Realtime 的独立原生 RQ 基座，三个用户自选 GGUF、24 kHz 可选参考、独立词表与实际输入预算校验；旧 SoundEffect 按官方模板绑定 Ambient Sound。Added separate native depth architectures and shared model-owned parameters/jobs/leases/cleanup. Realtime currently provides one text request to complete WAV, without incremental streaming or real-time claims.

178 scoped RQ checks include 10 actual host children, 14 GGUF metadata checks and two actual synthetic tiny graphs; openmoss 514 / foundation 550 / UI 280 checks pass. Original-signature APK, 32 metadata-only recipes, 24 native files, bilingual docs, 55 UI FIXTURE screens and refreshed recording/GIF. No complete-model or Android inference/quality/endurance evidence. Every frozen target stays in one complete v0.3.0; no new Release. See [双语说明与编号表 / bilingual numbered notes](docs/releases/v0.3.0-dev.19.md).

## 0.3.0-dev.18 — 2026-10-28 (internal / unpublished)

在现有原生 MOSS worker 中接入 TTS、v1.5、TTSD、VoiceGenerator 四种平级配方；按 32/16-codebook、8B/1.7B 实际 GGUF 几何校验。增加成对 S1/S2 参考、每模型声音描述/语言参数和真实生成网格的 prefill 前预算保护。Added native delay dispatch, explicit paired reference mapping, per-model bounded voice/language hints and a context guard in a generated copy of the pristine pinned source. All model/codec/BPE assets stay user-selected.

459 scoped Java/C++ assertions (18 actual host children), 521 foundation and 265 UI assertions pass. Refreshed original-signature APK, 29 metadata-only templates, bilingual guides, five new screenshots and recording/GIF. No complete model/Android inference, quality or endurance claims; all frozen targets stay in one complete v0.3.0 with no new Release. See [双语说明 / bilingual notes](docs/releases/v0.3.0-dev.18.md).

## 0.3.0-dev.17 — internal / unpublished

Two native CPU MOSS routes now share the foundation: Local-Transformer-v1.5 speech and SoundEffect-v2 flow matching. Users explicitly select matching backbone/extras GGUFs; embedded BPE/codecs remain user assets, with no implicit downloads. Independent editable parameters, optional stereo reference, actual solver/receipt events and isolated child cleanup are integrated. CFG=1 cannot silently ignore a supplied negative prompt; full 30-second latent cost is disclosed.

180 new host/native checks (100 Java / 80 C++, six actual host children), 485 foundation checks, 244 UI checks; original-signature APK with 23 native files and no model weights. Bilingual guides, six new screens, refreshed recording/GIF and numbered implemented/pending tables are included. These are scoped checks/fixtures, not full model or phone inference; all frozen targets remain in the same complete v0.3.0 with no new Release. See [bilingual notes](docs/releases/v0.3.0-dev.17.md).


## 0.3.0-dev.16 — 2026-10-28 (internal / unpublished)

- 新增 MOSS Delay first-class 签名 ARM64 CPU worker、生产 Java 管线、严格组件 / WAV 契约、模型独立采样和实际执行计时。Added a real local BPE/32-channel Delay/codec route with sequential model release.
- 第 23 个显式 HF 配方：主模型和解码器必需；参考编码器仅用户需要时选择，不隐式下载或打包模型数据。Plain TTS does not require reference assets; ordinary MOSS GGUFs and other family architectures remain distinct.
- 176 项新增 Java / C++ 检查包含实际主机子进程及固定上游 Delay 自检；基座 467、UI 228、Lint 0 errors / 13 warnings；更新双语文档、截图 40–41、录屏与 GIF。Fixtures are not generated speech or physical Android acceptance.
- 所有冻结目标、完整家族适配与模型质量 / 资源 / 后台 / 升级门槛保留在同一完整 v0.3.0，无新 Release。See [双语说明](docs/releases/v0.3.0-dev.16.md), [中文](docs/MOSS_DELAY_ENGINE.md), [English](docs/MOSS_DELAY_ENGINE.en.md).

## 0.3.0-dev.15 — 2026-10-28 (internal / unpublished)

- 新增 Qwen3-TTS 12Hz 0.6B Base 的签名 ARM64 CPU worker、生产 Java 适配器、可选本地参考 WAV、独立采样参数、严格 GGUF / 音频检查与实际耗时 / RTF 记录。Added a real same-phone Qwen speech route; model/device output remains untested.
- 两个固定 GGUF 的可选包、22 个 HF 模板和通用内含依赖 `provides`；用户选择下载，App 更新不带权重或默认音色。Pinned optional assets and embedded-role disclosure reuse shared downloads/settings/jobs; no implicit downloads.
- 81 项主机 / 原生检查、固定文件头核对、双语指南及截图 38–39 / 录屏 / GIF；结构 WAV / 界面夹具不代表模型推理。Every frozen target and gate remains part of one complete v0.3.0, without a new Release.
- 同步中英文首页与资产需求核对的当前统计；App 基座更新、用户自主选择模型及独立功能标签的约束一致。Synchronized current documentation counts and the foundation/model ownership assessment.
- [双语说明 / Notes](docs/releases/v0.3.0-dev.15.md) · [中文指南](docs/QWEN_TTS_ENGINE.md) · [English guide](docs/QWEN_TTS_ENGINE.en.md)


## 0.3.0-dev.14 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 实际 MNN Sana 移动端 CPU worker、Qwen3 特征编码与分阶段释放；新增 13 组件配方和 `.mnn` / `.mnn.weight` 用户选择。No bundled model assets, auto-downloads or remote execution.
- 配置白名单 / embedding 范围、独立参数快照、硬链接引用与延迟清理；74 项 Java / C++ 检查。Host protocol bytes are not generated images.
- 445 foundation / 253 recipe-integrity、208 UI、37 张显式 UI FIXTURE 与录屏 / GIF；原签名 APK 和双语文档同步。
- 所有冻结目标与 Android 真实输出、质量 / 资源 / 后台 / 升级门槛仍在同一个完整 v0.3.0，未创建 Release。See [双语 notes](docs/releases/v0.3.0-dev.14.md).

## 0.3.0-dev.13 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 补齐 Z-Image-Turbo、FLUX.2-klein 4B、Qwen-Image 2.1、Wan 2.1 T2V 1.3B 的显式四组件模板与角色校验；总计二十个数据模板，用户自行选择下载，不因 App 更新安装模型。Four complete recipes, without implicit asset downloads.
- 实际绑定采样器 / 调度器 / flowShift、蒸馏任务策略及 Qwen / Wan 几何；本次参数不改写普通基础配置。Actual native bindings and task-scoped policies.
- 174 项扩散、425 项基座与 203 项 UI 主机检查；原签名 APK、双语指南、35 张 UI FIXTURE 截图及录屏 / GIF 已同步。Host/package evidence does not establish Android model generation.
- 全部所选目标和手机离线 / 质量 / 资源 / 后台 / 升级验收保留在同一完整 v0.3.0；无新 Release。See [notes](docs/releases/v0.3.0-dev.13.md).

## 0.3.0-dev.12 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 十六种用户自选数据配方，新增 SD1.5 / SDXL 分离组件、SD-Turbo、LCM checkpoint 与双架构 LCM-LoRA。No weights or automatic model downloads.
- 明确 LCM 配对后固定本次采样 / CFG / 步数，保留模型独立设置；队列计划落盘稳定、运行前重算核对，原生再次验证策略和实际张量架构。Freeze effective sampling without overwriting base settings.
- 83 项新增扩散主机 / C++ 检查、381 项基座和 194 项 UI；原签名 APK、双语指南、32 张标识截图与录屏 / GIF 同步。Host protocol bytes are not generated images.
- 全部冻结模型、真实图像 / 音频 / 视频、物理 Android 质量 / 资源 / 后台 / 升级验收继续要求在同一完整 v0.3.0 完成；没有新 Release。

## 0.3.0-dev.11 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 用户显式导入本地素材，前台服务复制 / 取消，实际结构与 hash 校验；素材和生成结果分别标记、预览、导出、独立管理。Explicit local media import and ownership.
- 新增鉴权有界上传会话、256 KiB 二进制分块、持久偏移、显式续传、全文件 SHA256 / 媒体校验与原子完成对账。Resumable authenticated input uploads without URLs or model downloads.
- 签名引擎声明输入角色；任务固定 ID / hash / 元数据，保护排队和活动输入，执行前复核完整 hash；取消等待实际子进程退出再释放。现有生产配方保持文字输入。Immutable local task references, not new model-input claims.
- 64 项素材 / HTTP、49 项生产调度、182 项 UI 检查；双语输入指南、30 张带标识截图及录屏 / GIF 已同步。原签名和 19 个原生文件保留。
- 全部所选模型的实际管线、Android 媒体 / 后台 / 升级和离线新输入验收仍属于同一完整 v0.3.0；无新 Release。

## 0.3.0-dev.10 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 常驻文本加载、聊天、同步 API 和异步任务共用 FIFO 执行槽，回复结束再自动切换；空闲恢复用户仍希望运行的模型。Share engine scheduling without model downloads.
- 取消等待 / 关闭监听 / 停止文本 / 停止服务保持各自归属；旧进程未退出时保留执行槽、资产与临时文件，有限崩溃恢复继续受调度。Preserve cancellation and actual process-exit ownership.
- 43 项生产调度 / 真实主机子进程 / HTTP 检查及 167 项 UI；双语指南、28 张明确夹具截图与录屏 / GIF 同步。Host evidence does not establish Android or model inference.
- 完整输入产物、全部所选模型与物理设备门槛仍须在同一 v0.3.0 完成，未创建新 Release。Every complete-release requirement remains.

## 0.3.0-dev.9 · 2026-10-28 · internal / 内部检查点

- 文档复核：明确复述基座更新 / 用户模型资产 / 四类功能与依赖标签边界，校正双语指南的旧迁移状态与当前检查数量，README 增加直接入口。Documentation-only audit clarifies asset ownership and tags, corrects stale progress and adds README links.

- 旧文本 / HF / 导入 GGUF 通过本地校验、硬链接和原子 ID 绑定纳入共用资产、参数、任务与版本管理，原推荐 / 标签保留，无重复下载或自动模型选择。Adopt existing assets and retain stable IDs, labels and profiles.
- 旧 / 新管理入口共享传输、设置、删除与进程租约；加载参数变更保持正确重载，API 返回不可变 bundle_id 并合并重复行。Share asset lifecycle and preserve loaded-model configuration behavior.
- 恢复 / 升级不自动续传旧下载，用户明确继续；同步双语指南、26 张带标识截图及录屏 / GIF。Require explicit resume and update bilingual guides/media.
- 69 项新增主机迁移、310 项基座、156 项 UI 检查；仍无物理 Android 或模型推理证据。完整 v0.3.0 全范围与发布门槛不变，未创建新 Release。

## 0.3.0-dev.8 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 新文本 GGUF 包复用签名 llama runtime、共用参数 / 租约 / 队列 / 结果，新增第九种用户自选 HF 配方。Add actual shared text-bundle execution and a ninth explicit HF recipe, without model assets or automatic downloads.
- 读取实际 GGUF 上下文，输出联动回填；有效 schema 与来源分开，模型版本确认绑定实际约束。Inspect limits, enforce dependent bounds and invalidate stale version consent.
- Typed response/reasoning JSON, inert local preview, literal copy/export, bounded SSE and child cleanup. 正文与思考独立保存；受控同源读取，模型 HTML 不执行。
- 310 foundation / 66 new text-host / 147 UI checks, zero Lint errors; original certificate and 19 native files. No model or Android inference evidence.
- 同步[双语指南](docs/TEXT_ENGINE.md)、[更新说明](docs/releases/v0.3.0-dev.8.md)、截图 22–24、录屏 / GIF；旧记录迁移、全部所选模型及真机门槛继续属于同一完整 v0.3.0，没有新 Release。

用户可见行为、验证范围和交付文档在此同步。User-facing behavior, evidence, and delivery documentation are maintained together.

## 0.3.0-dev.7 · 2026-10-28 · 内部检查点 / Internal checkpoint

- User-selected immutable model-version updates, component/license/profile review, separate transfer and activation, retained assets, rollback and bounded history. 通用包独立更新，不随 App 升级下载或替换模型。
- Stale consent, atomic profile/pointer commit, running leases and queued base/LoRA deletion protection; fixed task/API identities. 过期确认与引用保护，旧参数和任务来源保留。
- 302 foundation checks including 62 version assertions; 132 UI checks; zero Lint errors. New [bilingual guide](docs/MODEL_UPDATES.md), [notes](docs/releases/v0.3.0-dev.7.md), screenshots 17–21 and refreshed visible-fixture recording/GIF.
- Complete legacy migration, every selected model and physical Android acceptance remain blockers for the same complete v0.3.0. No new Release; published v0.2.0 remains unchanged.

## 0.3.0-dev.6 · 2026-10-28 · 内部检查点 / Internal checkpoint

- MOSS Nano ARM64 CPU worker with actual SentencePiece/ONNX/codec calls; user-owned tokenizer, voice and external-weight data. 新增 Nano 语音原生路径，模型数据保持用户自选。
- Private leased hardlink workspaces, nested ONNX external-reference guards and identical shared-ORT packaging. 私有工作区、外置数据校验与运行库共用冲突检查。
- Eighth HF component recipe, `.model` / `.data` selection and 190 new native/Java/worker host checks; 240 foundation checks. 第八种组件模板与新增主机验证。
- Bilingual [guide](docs/MOSS_NANO_ENGINE.md), [checkpoint notes](docs/releases/v0.3.0-dev.6.md), visible-fixture screenshots/recording/GIF. No actual MOSS speech/Android acceptance or new Release; complete v0.3.0 scope remains open.

## Earlier development checkpoints / 早前内部检查点

- 2026-10-28：内部 0.3.0-dev.5 / code 9 新增七种显式 HF 组件模板、跨仓库固定版本选择与独立登记 / 下载确认，普通 Git blob 完整性及实际 SHA256 来源回执，兼容旧包。217 基座 / 74 HF / 112 UI 检查；同步[双语指南](docs/HF_RECIPES.md)、[需求核对](docs/ASSET_CONTROL_AUDIT.md)、截图 / MP4 / GIF 与[更新说明](docs/releases/v0.3.0-dev.5.md)。App 只更新基座，模型由用户管理；完整 v0.3.0 与真机门槛未完成，无新 Release。 / Add explicit user-selected component recipes, Git integrity receipts, scoped checks and bilingual media; preserve foundation-only updates and all complete-release gates.

- 2026-10-28：内部 0.3.0-dev.4 / code 8 新增平级 LoRA 包、显式 SD 1.5 / SDXL 基础配对、最多八个独立强度、任务 / API 冻结快照和完整组件引用保护，缺资产不下载。新增 45 项主机适配器检查，总计 130 基座 / 97 UI；同步[双语配对指南](docs/ADAPTERS.md)、[基座与资产核对](docs/ASSET_CONTROL_AUDIT.md)、媒体和[开发记录](docs/releases/v0.3.0-dev.4.md)。尚无手机 LoRA 输出或新增已核对 LoRA 候选，完整 v0.3.0 仍未完成、不创建 Release。Add explicit peer-adapter pairing, frozen strengths/leases, scoped tests and bilingual docs/media; retain all full-release/device gates.

## Unreleased / 后续维护

- 2026-10-28：内部 **0.3.0-dev.3 / code 7** 新增 sherpa_tts ARM64 CPU worker、Kokoro / Piper / Matcha 适配、三套明确由用户下载的完整候选、语音专用表单和独立音色 / 语速设置。扩散与语音共用进程管理；增加参数 / 时长 / WAV 检查、执行来源、固定库依赖 / 许可与原生日志边界。62 项语音主机检查、89 项 UI 检查、18 个原生文件包校验；没有手机语音输出。同步双语 [语音文档](docs/TTS_ENGINE.md)、实施记录和界面媒体；模型许可 / 发音 / 后台等仍待验收，不创建 Release、不缩减完整 v0.3.0。Add the compiled speech worker, three explicit user-owned candidates, speech controls, shared process ownership, WAV guards/provenance and pinned dependencies/notices in dev.3. Host/UI/package evidence stays separate from missing phone inference and full release acceptance.

- 2026-10-27：内部 0.3.0-dev.2 / code 6 新增可在零模型状态独立启停的鉴权接口、持久任务提交 / 幂等 / 事件 / 取消 / 重试、产物元数据与 Range 下载；文本引擎改为独立回环端口和进程密钥，统一接口校验模型独立输出上限并跟踪客户端占用。更新服务页、双语 API / 实施说明和明确标记的界面媒体。模型仍由用户选择，不自动下载；完整引擎 / 模型与真机验收仍待完成，不创建 Release。Add the independent authenticated zero-model gateway, shared durable job/event/artifact routes, private text endpoint and profile/lease enforcement in internal dev.2. Refresh UI, bilingual guides/media and scoped host evidence; full model/device gates remain open.

- 2026-10-27：开始实现同一完整 v0.3.0，内部版本 0.3.0-dev / code 5。新增多组件包、显式下载 / 导入、独立参数与联合约束、持久任务 / 产物、标签 / 表单 / 队列 / 导出界面，以及原生 Windows 构建的 Android ARM64 sd.cpp worker；外置模型专用词表，锁定新原生文件和许可，在“全部”新增一套未实测的固定 SD1.5 候选包元数据，资产仍由用户选择下载，保留推荐及旧文本路径。新增开发截图 / 录屏 / GIF 与[双语实施记录](docs/DEVELOPMENT.md)。完整模型范围、统一 API、真机生成及耐久仍未完成，不创建 Release、不拆版、不默认顺延。Begin the complete v0.3.0 implementation with internal 0.3.0-dev: bundles, explicit transfers/import, per-recipe schemas, durable jobs/artifacts, flat task UI/export and an ARM64 sd.cpp worker built on native Windows. Externalize vocabularies, pin native hashes/notices, preserve recommendations/text. Add labeled development media/evidence; all required model/API/device gates remain open and no Release is created.

- 2026-10-27：明确 App 仅更新基座，01–14 / 16 / 17 是运行支持 / 配方覆盖目标，权重与模型专用资产由用户独立选择、下载、导入、管理和删除。安装 / 升级 / 浏览不触发模型下载，不强制模型更新或静默替换；推荐为元数据，功能标签与安装状态分开。新增 A11 资产分离验收并同步双语文档 / 结构化策略。Clarify foundation-only App updates and explicit user model-asset control; add A11, preserve flat task/dependency tags and single-release coverage. Documentation only; no APK/runtime changes.

- 2026-10-27：按用户最新要求取消分版本工作线路，下一版本 **v0.3.0** 统一交付 F-01–F-12、既有生文、01–14 / 16 / 17 及全部冻结子目标，含 SD 1.5 / SDXL LoRA；新增同版发布门槛与[交付摘要](docs/releases/v0.3.0-plan.md)。撤销默认顺延或缩减预览代替完成；风险保留为本版阻塞。Consolidate the full foundation and selected models into one complete next v0.3.0, without release splitting or automatic deferral; add common release gates and delivery summary.
- 同步双语需求、模型目标版本、结构化范围 schema v2、基座 / 任务 / 研究文档、README / 导航 / 贡献与发布约定。仅文档维护，当前 APK / 公开版本 / 媒体与附件不变。Synchronize bilingual specs, schema v2, model targets and related guides; documentation only, current APK/version/media/assets unchanged.

- 早期提案（已由上述单版要求覆盖）/ Earlier proposal superseded by the single-release scope：按当时范围补齐[双语需求与发版评估](docs/MULTIMODAL_RELEASE_PLAN.md)和[结构化编号 / 标签](docs/proposals/multimodal-release-scope.json)：01–14 / 16 / 17、12 项基座需求、四版拟定范围、子目标与真机验收；所有模型平级，功能 / 基座依赖 / 兼容 / 许可 / 内容标签独立。Complete bilingual requirements, feasibility, 16-group scope, flat tags, foundation requirements, four proposed releases and device acceptance.
- 撤回画布 / 连线 / 用户节点 / 插件生态 / ComfyUI 导入的交付要求，改为模型选择 → 任务表单 → 本机队列 → 结果；旧 JSON 标为历史不可执行示例。保留推荐；MOSS / SoulX 研究关卡不冒充已支持；APK / 版本 / 媒体 / 已发布附件不变。Withdraw canvas/wiring/user-node/plugin/import requirements; use forms/shared jobs/artifacts, retain historical drafts and recommendations, and keep research gates explicit. No APK/version/media/published-asset changes.

- 2026-10-27：新增可扩展多模态基座双语评估，区分架构 / 引擎 / 硬件后端，说明模型数据与原生代码扩展边界、组件和配方、内部引擎发行、任务 / 产物、现有代码迁移及跨模态完成标准；仍为设计，不改 APK。Add bilingual extensible-foundation assessment covering layers, data/code extension boundaries, bundles/recipes, engine distribution, jobs/artifacts, source migration and cross-modality acceptance; proposal only, no APK changes.
- 2026-10-27：按用户要求将多模态扩展重新评估为全部同一 Android 手机执行，撤回外部推理 / 回退方案并记录长期约束。Reassess every multimodal stage for execution on the same Android phone; remove off-device inference/fallback designs and persist the requirement.
- 修正视频判断：新增 Wan 1.3B Vulkan 与旧 LTX-Video 2B Vulkan / 芯片特定 QNN 的 Android 证据，区分作者手机结果、桌面 CUDA、下载大小和 LMA 实测；补充 Qwen3-TTS Android 示例与许可边界。Correct the video assessment with Android implementation evidence, separate author/desktop/download/device claims, and add Qwen3-TTS Android samples and licensing limits.
- 早期研究（现已由表单 / 队列范围覆盖）：更新纯本地 DAG、组件包、独立模型参数、后台任务 / 恢复提案；用图片旁白与本机 Wan 两份明确不可执行的 JSON 替换混合方案，加入来源记录。Earlier research, superseded by forms/queue scope: revise local DAG/bundle/per-model-settings/background contracts; replace the hybrid example with two non-executable local drafts and a source ledger.
- 同步双语 README / 指南、导航和 v0.2.0 发布后维护说明。当前 APK、推荐、截图 / GIF 和公开附件不变，未新增手机推理结论。Synchronize bilingual documentation and post-release notes; no APK/recommendation/media/published-asset changes or new phone inference claims.

## 0.2.0 — 2026-10-27

**本地模型、HF 发现、本地管理与模型独立参数 / Local models, HF discovery, Local management and per-model settings.** APK versionCode 4; original signing identity preserved.

- 产品文案改为“本地模型”；“推荐”固定保留 `m08 → m06 → m01`、顺序、标签、具体权重和作者依据；原轻量 / 进阶分组保留。Rename product positioning to local models while preserving the exact recommendations and curated groups.
- “全部”和搜索新增 HF 关键词 / 精确仓库 / URL 检索、GGUF / 全格式发现、下载 / 喜欢 / 更新排序与前后分页；原生固定仓库提交，递归分页选择 GGUF 量化文件。Add native HF discovery, sorting, pagination and a commit-pinned quantization picker.
- 新增“本地”栏目，统一管理内置、HF、导入的已下载模型及下载任务；本地搜索、加载、暂停 / 续传、删除。HF 稳定 ID 去重并跨重启保留。Add a dedicated Local manager with durable HF identities.
- 上下文、输出上限、线程、温度、思考和系统提示词迁至“本地”的每个模型设置，独立存储并迁移旧全局值。数值支持可编辑预设；GGUF 上下文、共享输入 / 输出、设备线程和应用温度双重校验，超限自动回填。Store inference preferences per model, migrate legacy globals, and combine editable presets with UI/native bounds and automatic clamping.
- 无审查作为独立标签：已核对作者声明与“无审查 · 元数据”提示分开；普通模型不带标签，也能下载。Make uncensored an optional separate tag with explicit evidence levels.
- 可选 HF 令牌仅发送官方 HTTPS 主机，认证请求不走镜像，重定向到 CDN 时不转发令牌；提供保存 / 清除。Add optional private HF-token preferences and restrict credentials to the official origin.
- 明确单文件 GGUF 文本运行范围；分片、投影器、超限大小及已知非文本任务禁用选择，其他格式可发现来源。State runtime boundaries without equating HF visibility with phone compatibility.
- 修复暂停时断连与工作线程结尾竞争造成 pausing 残留。Finalize cancellation and job retirement under one lock.
- 同步完整双语指南、12 张截图、MP4、4 份 GIF 及公开验证。Synchronize bilingual docs and refreshed media, including the HF-to-Local flow.
- 85 后端 + 45 HF 逻辑 + 25 协议 + 5 SQLite + 66 UI = 226 项桌面断言；另 5 项实时公开 HF Mirror 元数据检查；Lint 0 错误 / 7 警告。226 desktop assertions, five live metadata checks, Lint 0 errors/7 warnings. No phone inference, private-token access or screen-off endurance was tested; prerelease.

## 0.1.2 后续工具维护 / Post-release tooling

- 修复发布工具在 GitHub 按标签查询草稿返回 404 时失败的问题，改用已认证、支持分页的发行列表定位同一草稿。本次首发已用该方式完成附件核验和公开。Resolve draft releases through the authenticated paginated release list; the initial release was successfully finalized using this lookup.
- 仓库检查新增 `--published`：后续文档 / 工具提交核对既有源码附件与发布标签，不改写附件字节。Add post-publication checks against the immutable tagged source rather than requiring later maintenance to overwrite released archives.
- APK 字节、签名、v0.1.2 标签、已公开附件和界面素材不变。同步修改了本维护说明与双语发布流程；行为不涉及 UI，因此无需重录。APK, tag, assets, and UI remain unchanged; bilingual maintenance notes/procedure are synchronized, with no UI recapture needed.

## 0.1.2 — 2026-10-27

**首次仓库预发布 / Initial repository prerelease.** APK versionCode 3. Earlier 0.1.0 / 0.1.1 were local iterations, not historical GitHub releases.

### 功能 / Features

- 14 个内置候选全部核对作者 Uncensored / Abliterated 声明及具体 GGUF 权重；构建强制匹配依据、版本和哈希。All 14 built-ins require matching publisher uncensored evidence and pinned weights.
- 界面显示无审查方式及固定作者说明；修正 Qwen 4B 名称中的 Abliterated 标识，自定义导入显示属性未核对。Visible methods/evidence, corrected Qwen 4B variant label, and unclassified custom imports.
- 模型下载、暂停续传、GGUF / SHA256 校验、本机对话、SQLite 历史及带密钥的 OpenAI 兼容 API。Downloads/resume, integrity checks, local chat/history, and authenticated API serving.
- 无 ROOT 的原生前台服务和 ARM64 CPU 引擎，支持用户开启 LAN、后台设置与可选恢复。Native no-ROOT foreground serving, ARM64 CPU runtime, optional LAN and restoration.
- LMA 不额外添加关键词、云端审核或回复过滤；系统提示词可编辑。No added keyword/cloud moderation or response filtering; editable system prompt.

### 文档与交付 / Documentation and delivery

- 完整中英文 README、使用 / API / 构建 / 架构 / 模型 / 验证 / 真机验收指南，以及双语贡献与发布流程。Bilingual READMEs and supporting guides, contribution and release procedures.
- 7 张实际界面截图、MP4 录屏和 2 份 GIF，持续标注演示桥接与非真机范围。Seven screenshots, MP4, and two GIFs with explicit simulated-state labeling.
- 公开验证记录、版本附件清单、SHA256SUMS、带原生库的源码 ZIP；排除私钥、口令、权重和缓存。Public evidence, manifests, hashes, source ZIP with native libraries; no secrets, weights, or caches.
- 固化后续更新同步代码、双语文档、相关媒体和更新说明后推送本仓库的要求。Standing instruction to synchronize future changes and push matching documentation/release notes.

### 验证与限制 / Validation and limits

- 115 项桌面断言：54 后端、25 协议、5 SQLite、31 界面。115 host assertions; Android framework adapters and UI fixtures are explicit.
- Lint 0 错误、7 条已复核警告；APK 签名、原生库、对齐及目录来源通过相应检查。Lint: 0 errors, 7 reviewed warnings; package/native/alignment/provenance checks pass.
- **0 项真机检查；未实测手机推理、拒答率、tokens/s、温度或锁屏耐久。** Zero physical-device tests; inference, refusal rates, speed, thermals, and endurance remain unmeasured.

详细说明 / Details: [v0.1.2](docs/releases/v0.1.2.md)。
