# v0.3.0 开发状态与复查

[English](DEVELOPMENT.en.md) · [完整范围](MULTIMODAL_RELEASE_PLAN.md) · [构建](BUILD.md) · [中文首页](../README.md)

当前公开发行仍为 **v0.2.0**。本分支为 **0.3.0-dev.17 / versionCode 21**，不是完整 v0.3.0，也没有创建对应 Release。下一版本仍一次交付 F-01–F-12、01–14 / 16 / 17 及冻结子目标；以下是同一版本内的实施记录，不是拆版安排。

## 已写入开发代码的部分

| 部分 | 当前行为 | 证据边界 |
| --- | --- | --- |
| 模型包 / 组件 | `lma.model-bundle/1` 与 `/2`，固定 revision / 大小 / SHA256 或 Git blob 身份与实际 SHA256；共享内容对象、原子安装、暂停 / 续传、显式文件夹导入、删除引用保护 | 字节夹具与真实本机 HTTP 传输测试；不是模型推理 |
| 独立模型更新 | 用户指定固定目标、组件 / 参数差异、单独下载与确认启用、旧资产保留、回退、最近 64 次切换记录；队列引用保护 | 62 项真实主机存储 / 故障 / 传输检查；Android 升级仍待验证，见[版本指南](MODEL_UPDATES.md) |
| 用户控制 | 声明 / 浏览 / 计算下载计划不创建传输；下载须单独确认；缺组件生成失败；重启中的组件传输暂停，用户自行恢复 | 不把所有目录条目安装到手机；没有隐式模型下载 |
| 参数 | 模型包独立保存；可编辑预设、数值回填、联合尺寸校验；提交时固定参数快照 | 约束来自配方，未知上限不冒充已验证；设备预算独立 |
| 界面 | 同一列表显示旧文本和新包；生文 / 生图 / 生视频 / 生音频筛选、模型包详情、任务表单、任务页与结果库；推荐仍为 m08 → m06 → m01 | “全部”提供固定候选，用户也可导入自定义清单；dev.17 提供二十五种显式 HF 组件模板，其他架构不自动兼容 |
| 任务 / 结果 | 一次一个重任务；提交 / 取消 / 重试、持久事件、私有产物、SHA256、来源参数、系统文件导出；图片 / WAV / MP4 检查与分段预览 | 持久层当前为有界 AtomicFile JSON，既有聊天 SQLite 保留；旧文本已迁移并共用调度；各目标输入管线和物理设备仍待验收 |
| 统一接口 | 零模型独立启动；同一密钥访问模型 / 引擎、持久任务 / 事件与产物 Range；公开文本代理校验独立参数、跟踪占用，原生文本端点仅回环 / 独立进程密钥 | 生产 HTTP 与存储的实际本机 socket 检查；执行端是测试替身；不隐式下载模型，不跟随推理重定向 |
| Sana MNN 移动管线 | 固定源码构建的 CPU worker、13 个配套组件、受限配置、独立参数和真实进程绑定 | 74 项主机 / C++ 检查，无手机或图片输出；见 [Sana 文档](MNN_SANA_ENGINE.md) |
| 原生语音 | Qwen3-TTS Base 两组件与 MOSS Delay first-class / 可选参考编码器；独立参数和实际进程绑定 | 81 / 176 项主机检查，不代表模型语音或手机验收；[Qwen](QWEN_TTS_ENGINE.md) / [MOSS](MOSS_DELAY_ENGINE.md) |
| Android 执行 | 签名 APK 内的 sd.cpp ARM64 CPU worker；数据专用包不能提供可执行代码；词表由用户组件提供；子进程跟随宿主结束 | 已编译 / 已打包，**未执行手机推理**；列出架构并不证明目标配方可用 |
| 视频路径 | 原生生成帧交给 Android MediaCodec / MediaMuxer 编码；不以重复静态图冒充运动输出 | 编码器及生成帧仍须真机验证；没有任何 LMA 视频输出证据 |
| 后台 | 前台服务持有组件传输和任务，取消终止相应进程；进程死亡后标记中断，不虚构 checkpoint；两小时单任务保护时限 | 未测锁屏 / 内存回收 / 厂商省电 / 发热 / 重启表现 |

APK 仅含通用应用代码、引擎、目录 / 标签 / 配方元数据及许可。**不含权重、模型专用词表 / tokenizer / 音色 / 语言包。** 原生 worker 移除了上游内嵌词表，实现见 [vocab_external.cpp](../native/vocab_external.cpp)。用户可零模型启动；下载所选包前展示完整必需组件、总量和复用量。App 升级保留原模型与独立设置，不静默替换权重。

自定义清单不会获得“设备已验证”或已核对无审查标签。未实测配方须用户明确允许尝试；资源、算子或组件不符时在本机失败。dev.10 已将旧聊天 / 同步 API 与共用任务接入自动调度，等待回复、回收旧进程并恢复仍被用户选择的文本模型。原有资产迁移已接入，物理升级与完整模型验收继续要求在本版完成。

## 已获得的开发证据

公开记录在 [verification/development](../verification/development/status.json)，与根目录的 v0.2.0 历史验证分开。它们**不满足完整版本验收**。

| 检查 | 当前结果 | 能证明什么 |
| --- | --- | --- |
| 基座核心 | 485 项 | 组件完整性、真实 HTTP 续传、共享引用、独立设置、队列代次 / 取消 / 重启、产物与 Range 读取 |
| 接口 / 传输 | 67 项 | 鉴权、零模型、JSON / 长度 / 请求边界、幂等 / 取消 / 事件、原始产物 / Range / 引用保护与文本策略；真实本机 socket，非 Android 推理 |
| 旧文本后端 / 代理 | 98 项 | 显式桌面 Android 适配器下的既有下载 / 引擎进程 / HTTP SSE / 参数回归 |
| HF 逻辑 | 78 项 | HF 搜索、固定提交、分页、选择与令牌边界；不是所有 HF 模型运行覆盖 |
| MOSS Delay | 176 项 | 生产 Java / 实际主机子进程及固定上游 Delay / sampler / de-delay 自检；WAV 为结构夹具 |
| MOSS Local / SoundEffect | 180 项 | 生产 Java、6 次实际主机子进程与固定上游音效格式化 / 噪声 / sigma 自检；结构 WAV，不是神经网络输出 |
| 扩散接入 | 174 项 | 生产计划 / 绑定、实际主机协议子进程和共用 C++ 策略；非模型图片 |
| 本地输入素材 | 64 项 | 私有文件导入、生产 WAV 校验、鉴权分块上传 / 续传、不可变输入回执与引用保护；非 Android 媒体解码 |
| 共用调度 | 49 项 | 生产队列 / 常驻文本 / 聊天 / API、真实主机子进程与回环 HTTP、取消与回收边界；非 Android 推理 |
| 界面 | 244 项 | 实际 HTML / CSS / JS 配合明确的模拟原生状态；推荐、标签、下载确认、参数、队列与窄屏回归 |
| 原生包 | 23 个 ARM64 文件 | 固定哈希、依赖闭合、Android API 28、16 KiB ELF / APK 对齐、原签名、资产白名单 |
| 手机推理 / 耐久 | 0 | 尚无证明；没有真实图片、音频、运动视频或锁屏持续运行结论 |

sd.cpp 来源固定为 `be486498eadc29dc3cd234d944c2180ed42b1415`，ggml 为 `a5915eb0e47adef21c3f25b889a008925ea838c2`，使用本项目内的 NDK 30.0.16248370 原生 Windows 编译。独立新增 worker 的 SHA256 为 `01e6c0a37fc56bb9268d0890c71d8dae57bd0ac41922cb2ec64ad6e5e7fd1d3c`。许可与文件哈希见 [engine-lock.json](../third_party/engine-lock.json)。新引擎仅注册真实已编译模块，不登记空 provider 充数。

SD1.5 候选包使用 [Second State 的固定 GGUF 权重](https://huggingface.co/second-state/stable-diffusion-v1-5-GGUF/tree/031b5f5df991f511b3f5fa8fed6d99048ababb69) 和[原模型的 CLIP merges](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/blob/451f4fe16113bff5a5d2269ed5ad43b0592e9a14/tokenizer/merges.txt)，共 1,567,293,035 字节，按 CreativeML Open RAIL-M 来源许可使用。仅核对公开元数据、权重发布者哈希及小型词表，不下载权重；词表与固定引擎原数据一致。配方元数据可以随 APK 更新，模型资产仍需用户下载，未选择时不会出现在已下载“本地”。该候选没有获得运行支持验收；见 [bundle-evidence.json](../catalogue/bundle-evidence.json)。

## 尚未完成的同版工作

1. 对已接入的[共用调度](SCHEDULING.md)、资产迁移和独立更新完成物理 Android 的跨模态、取消、恢复与升级验收。49 项主机调度检查和 dev.9 本地迁移不代替这些设备门槛。
2. 全部 01–14 / 16 / 17 的固定资产、完整管线、各子目标和 SD1.5 / SDXL LoRA 配对。原生 MNN、Qwen 与 MOSS Delay 代码已接入；其余音频、完整 MOSS / SoulX、旧 LTX 继续实现，每条已有管线仍须实际模型和物理 Android 验收。
3. 已实现的异步 / 文本接口继续覆盖其余所有引擎的真实输入管线、各模态兼容表面与设备生命周期验收。旧文本共用执行槽已接入；新增模块必须复用这一调度边界。见 [API](API.md#030-dev2独立接口任务与结果)。
4. 实测资源档案、温控、本地输入在各配方和设备上的验证、阶段恢复 / checkpoint 能力、跨模态连续加载 / 卸载与升级迁移的完整验证。
5. 所有冻结子目标的物理 Android 新输入离线输出、质量、取消、清理及 A7 锁屏 15 分钟 / 一小时交替服务等证据；现无可用真机。
6. 全部 A1–A11 / R-01–R-05 验收后的完整源码 / APK / 说明 / 实际功能媒体和 Release。开发包不能替代完整交付；发布脚本拒绝 `-dev`。

## 开发界面媒体

画面顶部固定标记“开发界面演示 / UI FIXTURE · 非真机 · 非模型输出”。下载、安装和采样状态是测试数据，不下载权重，也没有生成结果。

<img src="media/development/02-local-tags.png" width="280" alt="平级本地模型与标签，界面演示" /> <img src="media/development/06-queue-results.png" width="280" alt="队列与结果库，模拟状态" />

<img src="media/development/08-zero-model-api.png" width="280" alt="零模型接口控制，界面夹具" />


[视频](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif) · [媒体哈希与来源](media/development/manifest.json)

浏览器、页面和录制进程在 `finally` 中关闭。未调用 Docker、WSL、虚拟机或 Android 模拟器。

## dev.3：语音引擎接入

新增真实编译的 sherpa_tts ARM64 worker 与 Kokoro / Piper / Matcha 适配，三套完整组件候选均由用户选择下载，标生音频 / TTS / CPU。共享 NativeWorker 生命周期，支持语音参数、输出时长保护、PCM WAV 及有效参数 / 波形来源记录。第三方代码依赖来自官方固定发布包，不随模型下载代码。23 项新许可原文和依赖闭合纳入包检查；部分模型数据许可仍待核对。

新增 **62 项 TTS 契约 / 实际主机子进程检查**，验证组件 / 参数、取消、错误退出、完成协议及请求清理，输出是任意测试字节，不是语音。89 项界面检查通过。语音波形、发音、实际 RAM / 速度 / 发热、Android 日志绑定和后台仍无真机证据；编号 10 未完成验收。其余全部所选模型 / 配方、统一调度和物理设备门槛继续属于同一 v0.3.0。详见[语音基座](TTS_ENGINE.md)。

<img src="media/development/09-tts-form.png" width="280" alt="语音专用表单，明确的界面夹具，非实际语音" />


## dev.4：平级适配器与显式配对

新增 `lma.adapter/1` 数据声明与 SD 1.5 / SDXL 基础架构、配方及可选模型 ID 配对约束。LoRA 保持生图平级条目，用户选择已安装基础模型或在基础模型表单选择最多八个 LoRA；各自强度独立保存，任务编辑自动回填上限。缺失基础模型不会触发选择或下载。

任务与 API 固定包 ID、强度和修正；执行时原子持有完整基础 / 适配器引用组，保护运行资产，传递真实私有组件路径到现有原生 `loras` 数组，保留适配器来源。新增 45 项主机契约检查，总计 130 项基座与 97 项 UI 检查；它们使用字节 / 界面夹具，不是 LoRA 输出。

本次没有新增已核对 LoRA 下载候选，真实 SD 1.5 / SDXL / LCM 配方、量化兼容和效果仍待验收。详见[配对指南](ADAPTERS.md)和[基座 / 用户资产需求核对](ASSET_CONTROL_AUDIT.md)。APK 为 `0.3.0-dev.4 / code 8`；完整 v0.3.0 仍未完成或发布。

![LoRA 显式配对，界面夹具](media/development/10-lora-pairing.png)
![独立适配器强度，界面夹具](media/development/11-lora-form.png)


## dev.5：用户自选 HF 组件与完整性

新增七种签名 App 数据模板：SD 1.5 / SDXL 完整 checkpoint、两者 LoRA、Kokoro / Piper / Matcha 英语配方。用户明确选择全部组件，可跨 HF 仓库固定提交；固定依赖预先披露。“加入本地”只登记清单，下载须再次确认。模型继续平级，按生图 / 生音频和引擎等独立标签筛选；没有随 App 下载模型。

新增 schema 2 的 Git blob 身份与实测 SHA256 回执、任务组件来源、按角色区分导入路径；schema 1 兼容。87 项配方 / 完整性新增断言令基座合计 217，HF 74、UI 112；其他当前检查见上表与公开回执。不是手机推理或任意 HF 兼容验收。详见[完整操作与限制](HF_RECIPES.md)和[开发更新说明](releases/v0.3.0-dev.5.md)。

![HF 配方界面夹具](media/development/12-hf-components.png)
![HF 组件文件界面夹具](media/development/13-hf-component-files.png)

## dev.6：MOSS Nano 执行与私有资产工作区

新增编译的 ARM64 SentencePiece / ONNX / codec 语音 worker、第八种 HF 组件模板、外置数据显式选择、持有租约的私有硬链接，以及共享 ORT 冲突检查。190 项新增主机检查覆盖 Java 契约 / 真实子进程 / 硬链接、实际执行的 C++ 引用校验和依赖身份；词表、音色和权重均由用户选择。详见[完整流程、边界与来源](MOSS_NANO_ENGINE.md)和[检查点说明](releases/v0.3.0-dev.6.md)。尚无实际 MOSS 语音或设备证据，09 与完整 v0.3.0 全部目标仍须验收。

## dev.7：用户控制的模型版本

通用包新增原生版本索引、组件 / 许可 / 参数差异、明确下载或文件夹导入、单独确认切换和回退。新旧参数与不可变任务来源分开保留；过期确认被拒绝。App 安装 / 升级仍不触发任何模型下载，APK 只新增基座代码。排队 / 运行任务的主模型及 LoRA 不能删除。

302 项基座检查含 62 项独立版本检查；132 项界面回归通过。新增截图 17–21，并重录 [视频](media/development/foundation-ui.mp4) / [GIF](media/development/foundation-ui.gif)，均标记 UI FIXTURE。详见[使用与失败规则](MODEL_UPDATES.md)和[内部更新说明](releases/v0.3.0-dev.7.md)。旧记录统一、所选全部模型和真机门槛继续阻塞完整 v0.3.0，不创建新 Release。

## dev.8：文本包接入共用执行

第九种 HF 配方接受用户明确选择的完整文本 GGUF。现有签名 llama runtime 接入 `LocalEngine`，新文本包复用参数、租约、队列、取消、产物与来源记录；每任务使用鉴权的私有回环端点。保存和执行读取 GGUF context，前端 / 原生端共同约束输出上限；有效 schema 独立于不可变清单，不兼容记录不会阻断模型库。

新增 66 项真实主机文件 / 子进程 / HTTP 检查；文本输出为固定夹具，未运行模型。现有基座总计 310、界面 147，Lint 0 错误 / 10 警告。APK 含 50 个生产 Java 源文件、原有 19 个原生文件，没有新增权重。正文 / 思考以受控本地 JSON 与纯文本预览，支持复制和导出。见[双语指南](TEXT_ENGINE.md)、[回执](../verification/development/text.json)与[更新说明](releases/v0.3.0-dev.8.md)。

新增截图 22–24，开发录屏 / GIF 保留 UI FIXTURE。旧文本记录的完整迁移、聊天 / API 的完整统一调度、全部所选模型和物理 Android 验收仍待完成；当前所有队列任务仍须先停止旧常驻文本服务。没有新 Release。

## dev.9：已有模型共用资产与配置

原有完整 GGUF 以硬链接、实际摘要和原 ID 原子绑定纳入共用库，不启动网络下载或隐式加载。原详情提供共用任务 / 版本管理，列表与 API 合并重复行；旧设置和模型包设置访问同一配置，加载参数变更通过引擎租约正确重载。恢复后的未完成下载须用户明确继续。

69 项新增主机迁移和 156 项 UI 检查通过；文本 66、TTS 62、Nano 190、API 67、后端 98、HF 76 与基座 310 均为有限范围的主机 / 界面证据。详见[迁移指南](MODEL_MIGRATION.md)、[回执](../verification/development/migration.json)与[更新说明](releases/v0.3.0-dev.9.md)。新增截图 25–26，录屏 / GIF 保留 UI FIXTURE。完整自动调度、全部所选管线和物理 Android 的安装 / 升级 / 输出 / 后台继续属于同一完整 v0.3.0，未创建新 Release。

## dev.10：共用执行槽与文本自动切换

生产 `LocalJobs`、常驻 `EngineHost`、`ChatRunner` 和 `ApiHost` 共用可取消 FIFO 槽。任务等待当前回复，真实进程退出后再检查可用内存 / 温度并启动；空闲恢复只复用用户仍希望运行的模型，停止 / 更换代次和迟到清理保持隔离。异步任务仍持久化，文本历史保留；不新增模型资产或隐式下载。

43 项新增检查实际编译生产任务运行器，运行真实主机子进程和回环 HTTP；检查等待取消、API 关闭、停模型 / 停服务、延迟回收、原资产 / 参数与有限恢复回归。167 项 UI 检查通过，开发媒体扩展至 28 张截图及录屏 / GIF，均为明确夹具。完整模型和物理 Android 的迁移 / 资源 / 质量 / 后台门槛仍未关闭。详见[指南](SCHEDULING.md)、[回执](../verification/development/scheduler.json)与[更新说明](releases/v0.3.0-dev.10.md)。

## dev.11 · 本地素材与任务引用

新增[用户素材导入 / 上传](LOCAL_INPUTS.md)与共享任务输入：系统文件选择、前台复制 / 取消、PNG / JPEG / WAV / MP4 校验、hash / 来源标记；四个有界上传会话、256 KiB 分块和显式续传。任务按签名引擎角色接受已有素材或结果，固定回执并保护排队 / 执行引用，启动前重算完整 hash。现有生产引擎默认只接受文字，其他实际输入管线仍待逐模型接入。

新增 64 项文件 / WAV / 实际 HTTP 检查；生产调度扩展至 49 项，包含实际子进程读取所选素材、损坏拦截与取消释放；UI 为 182 项。开发媒体 30 张截图加 MP4 / GIF 均明确标记夹具。原生库仍为 19 个，无新增权重；Android 文件选择器、图片 / 视频 codec 和完整设备门槛没有被桌面检查替代。见[更新说明](releases/v0.3.0-dev.11.md)及[素材回执](../verification/development/inputs.json)。

## dev.12 · 扩散组件与低步数采样

新增七种数据模板，总计十六种；接入 SD1.5 / SDXL 完整与分离组件、SD-Turbo、LCM checkpoint 与双架构 LCM-LoRA。显式配对后生成独立 `diffusionPlan`，记录有效采样 / CFG / 步数与调整，不写回基础模型设置；重试重新派生，运行前用租约复核，原生再次校验采样与张量架构。没有新增模型权重或隐式下载。

83 项新增扩散检查包含 56 项生产 Java / 真实主机子进程协议与 27 项执行共享 C++ 策略的断言；输出为协议 JSON，不是图片。基座 381 项（配方 / 完整性 189），UI 194 项，32 张截图与 MP4 / GIF 均为 UI FIXTURE。58 个生产 Java 源文件、19 个原生文件，Lint 0 错误 / 13 警告。其他所选架构、全部固定模型许可 / 质量 / 资源及物理 Android 门槛仍须在同一完整 v0.3.0 关闭。见[指南](DIFFUSION_ENGINE.md)、[回执](../verification/development/diffusion.json)和[说明](releases/v0.3.0-dev.12.md)。


## dev.13 · 高级扩散与视频参数

dev.13 的[Z-Image / FLUX / Qwen / Wan 基座接入](ADVANCED_DIFFUSION.md)增加四种用户自选组件模板、严格组件角色、采样器 / 调度器 / flowShift 原生绑定、Qwen 尺寸与 Wan 帧数约束。174 项扩散主机检查（Java 117 / C++ 57）、425 项基座（配方 / 完整性 233）与 203 项 UI 通过；35 张截图与录屏 / GIF 是显式 UI FIXTURE。组件家族校验不证明具体规模或蒸馏方法；没有模型输出或 Android 实测。App 仅更新基座，二十个模板均不隐式下载；全部目标与设备门槛继续属于同一完整 v0.3.0，无新 Release。

## dev.14 · Sana MNN 实际引擎与资产边界

dev.14 接入 [Sana 移动管线 / MNN](MNN_SANA_ENGINE.md)：真实 ARM64 CPU worker、13 个用户自选组件、Qwen3 metadata 白名单、分阶段释放编码器、独立 CFG / token / 线程参数与不可变任务快照。74 项主机 / C++ 检查不包含模型推理；全部 21 个模板仍只登记元数据、由用户确认下载。445 项基座与 208 项界面检查通过；37 张截图及录屏 / GIF 均标识 UI FIXTURE。没有 Android 生图 / 耐久证据，完整 v0.3.0 的冻结目标和发布门槛保持不变，未创建新 Release。

## dev.15：Qwen3-TTS 本地语音与内含组件

内部检查点（**0.3.0-dev.15 / code 19**，未发布）：[Qwen3-TTS 0.6B Base](QWEN_TTS_ENGINE.md) 新增真实 ARM64 CPU worker、两个用户自选 GGUF 的完整本机语音管线、可选参考 WAV、独立采样参数及真实耗时 / RTF 记录。共享 `provides` 描述文件内含依赖，详情无需重复下载词表 / 预测器 / speaker encoder。81 项主机 Java / C++ 检查仅验证协议与结构 WAV；固定版本可选包只核对文件头，未运行模型。现有 22 个模板仍为元数据，不隐式下载。截图 38–39 与开发录屏 / GIF 保留 UI FIXTURE。App 仅交付基座，完整 v0.3.0 的全部目标、真实输出 / 质量 / 后台门槛继续保留；未创建新 Release。见[双语更新说明](releases/v0.3.0-dev.15.md)。

内部检查点（**0.3.0-dev.16 / code 20**，未发布）：[MOSS Delay 原生 CPU 管线](MOSS_DELAY_ENGINE.md)接入用户自选 first-class 主模型 / 解码器和可选参考编码器、独立文本 / 音频采样与共用任务。176 项 Java / C++ 主机检查包含固定上游 Delay 自检；结构 WAV 不是生成语音。23 个配方均为元数据；APK 不带模型或自动下载。截图 40–41 与录屏 / GIF 为 UI FIXTURE。完整 v0.3.0 的所有目标和物理设备门槛保留，未创建新 Release。见[双语更新说明](releases/v0.3.0-dev.16.md)。

内部检查点（**0.3.0-dev.17 / code 21**，未发布）：[MOSS Local-v1.5 / SoundEffect-v2 原生基座](OPENMOSS_ENGINE.md)接入两个独立 CPU 管线、用户自选主干 / extras、内含依赖标签、可选双声道参考、每模型独立参数与共用任务 / 回执。180 项 Java / C++ 检查包含 6 次实际主机子进程与固定上游音效采样公式；没有完整模型或 Android 推理。全部 25 个模板仅为元数据，不自动下载；SoundEffect 固定 30 秒 latent 成本已披露。截图 42–47、录屏 / GIF 为 UI FIXTURE。所有冻结目标和物理设备门槛继续属于同一完整 v0.3.0，未创建新 Release。见[双语更新说明](releases/v0.3.0-dev.17.md)。
