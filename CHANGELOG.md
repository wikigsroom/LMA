# Changelog / 更新记录

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
