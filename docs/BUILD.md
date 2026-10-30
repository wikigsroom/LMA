# 构建与验证

dev.37 新增完整 FLUX.2-klein 本地验证：`python tools/fetch_flux2_trained.py` 默认仅核验已有文件；`python tools/test_qwen_tokenizer.py`、`python tools/test_flux2_trained.py` 与 `python tools/test_flux2_app_host.py` 分别验证独立分词、真实原生及完整业务。仅显式 `--download` 取得模型；不使用虚拟化。详见[完整复现](FLUX2_KLEIN.md#5-实际证据与复现)和[完整同版待办](releases/v0.3.0-dev.37.md)。

dev.31 共用资源保护：生产调度检查 `python tools/test_scheduler.py`，完整界面 `node tests/ui-smoke.cjs`，新页面媒体 `node tools/capture_workbench.cjs resources`。受控系统读数及主机子进程不冒充 Android 测量。见[中文方案](RUNTIME_RESOURCES.md) / [完整同版待办](releases/v0.3.0-dev.31.md)。

内部 dev.28 增加 `tools/test_lcm_app_host.py`：完整源通过生产准备 / 关联 / 实际生成，并有 26 组 Java / 原生布局检查；只读取已取得的本地文件。准备模块由 App 随包分发，不含学习参数。[方案与复现](LCM_APP_FLOW.md) · [当前编号交付](releases/v0.3.0-dev.28.md)。

内部 dev.27 用 `tools/test_recovery.py` 检查真实主机进程中断、结果对账、持久清理和鉴权 HTTP；调度与完整 UI 套件覆盖实际容量及用户确认。签名 APK、包核验、Lint 和当前指纹须一致，见[编号交付](releases/v0.3.0-dev.27.md)。

[English](BUILD.en.md) · [文档目录](README.md)

dev.27 的开发证据使用 `tools/export_development.py` 与 `tools/check_repository.py --development`。当前业务记录重新检查；历史模型 JSON 与完整 Git 历史中的 `6b1f345` 逐字节核对，不能作为新版 APK 推理验收。完整 Release 导出不接受开发检查点。

## 已验证工具链

使用 Windows 原生工具：JDK 21（PATH 中含 java / javac / keytool）、Python 3、Android SDK Platform 35、Build Tools 35.0.1。独立 Lint 需要 SDK Command-line Tools。主构建脚本明确调用 `.exe`，Linux / macOS 没有验证；不使用 Docker、WSL、虚拟机或模拟器。

界面检查需 Node.js 和 Playwright，可使用已安装 Edge / Chromium。媒体录制另需 FFmpeg / FFprobe，以及 Playwright 的 FFmpeg 组件（`npx playwright install ffmpeg`）。安装依赖时应使用本项目或用户指定目录，不把依赖提交进 Git。

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
python tools/bootstrap_runtime.py
python tools/bootstrap_native.py
python tools/fetch_native.py --transport ssh
python tools/build_native.py --jobs 4
python tools/collect_native_notices.py
# 检查 engine-lock.json 的本机重建差异，再构建 APK
python tools/build.py --sdk C:/path/to/Android/Sdk
```

未指定 `--sdk` 时先读 `ANDROID_SDK_ROOT`，否则使用当前用户 LocalAppData 的 Android SDK 默认目录。SDK 平台与 Build Tools 不会被脚本自动安装。Android Studio / Gradle 配置供继续开发，当前标准 Gradle 路径未执行验证，没有 Gradle wrapper。

## 引擎与目录重建

`bootstrap_runtime.py` 下载 ServLlama 1.2.2 的固定 ARM64 发行包，校验 `551e5be8494bd2ae9955992faaaca1a4f5cf29e3a97f90d2e04205eb460fcde6`，提取 14 个 CPU 库到 `app/src/main/jniLibs/arm64-v8a/`，不打包 OpenCL / Hexagon。Git 忽略原生库和缓存；Release 专用源码 ZIP 带有这些已核对的库。这 14 个文件为预编译文本组件；新增扩散 worker 则在本项目使用 Windows NDK 编译，详见下一节。

构建先执行 `build_catalogue.py`，要求 14 个内置模型的作者依据、GGUF 固定提交和权重哈希一致。普通重建使用已有证据，不需要重新访问所有模型卡。模型新增或来源变更时重新运行相应审计，并检查人工归属判断；不要只改模型名称。

该校验保护既有精选及“已核对”标签，不限制 HF 在线发现。保留推荐 `m08 → m06 → m01`；普通 HF 模型通过原生 HubClient / HubCatalog 获取、选文件并交给 Store / Downloads。“本地”汇总所有来源。`test_hub.py --live` 在后端编译后运行 45 项 HF 检查和 5 项公开 API 检查；live 使用 HF Mirror，未下载完整权重或认证私有仓库。网络不可用时可先运行不带 `--live` 的逻辑检查，但新发布仍需要当前实时记录。

`build.py` 使用 AAPT2 编译 / 链接资源，javac 编译 Java，D8 生成 DEX，加入原生库，zipalign，签名并验证 APK。证据保存输入文件的原始字节 SHA256；`.gitattributes` 禁止自动换行转换，避免 checkout 改变指纹。

## 新增原生引擎与开发构建

`bootstrap_native.py` 在忽略的 `build/toolchain/` 内校验并提取 NDK 30.0.16248370 与 CMake 3.31.6，不改系统 SDK。`fetch_native.py` 获取 engine-lock 中固定的 sd.cpp / ggml；不获取权重。`build_native.py` 使用 Windows NDK，临时 SUBST 盘符仅为绕开非 ASCII 路径的 CMake 崩溃，结束必移除，不是虚拟机。`collect_native_notices.py` 收集对应许可并更新原生文件锁；检查锁文件差异后提交，不把任意二进制直接打包。

APK 构建核对原生回执、源码指纹、固定文件集合、SHA256 与许可原始字节，生成 engine-builds.json。上游内嵌词表已替换为用户选择的外部组件，不进入 APK。Git 不携带原生二进制，内部签名包输出为 `dist/LMA-0.3.0-dev-arm64-v8a.apk`；它不是完整 Release。

开发复查使用 `test_foundation.py`、旧后端 / HF / UI 检查、`verify_package.py`、`test_android_lint.py`、`capture_foundation.cjs`、`export_development.py` 和 `check_repository.py --development`；详细边界见 [DEVELOPMENT.md](DEVELOPMENT.md)。完整发布流程仍必须完成全部模型与物理手机验收，`-dev` 被发布工具拒绝。

## 签名和产物

首次构建在 `signing/` 创建 RSA3072 本地身份及随机口令。请安全保留以覆盖升级；不要提交、分享或上传该目录。个人 clone 生成的密钥不能覆盖官方 Release 安装，除非使用同一签名；卸载旧包会丢失模型和聊天。

- `dist/LMA-<version>-arm64-v8a.apk`：对应当前 Manifest 的签名安装包；当前内部为 0.3.0-dev，公开版仍为 0.2.0。
- `dist/*.sha256`：实际附件哈希。
- `dist/build-info.json`：包信息和输入指纹。
- `build/`：编译、测试、Lint、媒体临时数据；不提交。
- `verification/`：发布用的可公开复查证据，不含签名密钥和设备 API 密钥。

## 检查顺序

```powershell
python tools/test_protocol.py
python tools/test_backend.py
python tools/test_hub.py --live
python tools/test_sqlite.py
python tools/test_android_lint.py
node tests/ui-smoke.cjs
python tools/verify_package.py
python tools/build_acceptance.py
```

测试所需 org.json JAR 会下载到 `build/test-deps/` 并检查固定哈希；后端测试执行实际生产 Java、真实 TLS 和 JVM 子进程，Android 框架使用明确适配替身，不执行 ARM 模型。SQLite 在主机运行。UI 使用测试桥接，并在 finally 关闭页面与浏览器。

可通过环境变量 `LMA_PLAYWRIGHT` 指定 Playwright 模块路径，`LMA_BROWSER` 指定浏览器可执行文件。例如先在 `build/ui-deps/` 安装 Node 依赖，再设 `LMA_PLAYWRIGHT` 为对应的绝对模块路径。不设置时由普通 Node 模块查找规则解析 `playwright`。

`build_acceptance.py` 生成同签名的独立真机验收 APK，编译成功不代表执行成功。有真机时按 [DEVICE_ACCEPTANCE.md](DEVICE_ACCEPTANCE.md) 运行。没有设备不启动模拟器，也不把 phone flags 改为 true。

## 媒体和交付

```powershell
node tools/capture_media.cjs
python tools/package_delivery.py
python tools/prepare_release.py
python tools/check_repository.py
```

录制只使用本地界面和明确演示桥接；MP4 / GIF 由 FFmpeg 生成。`package_delivery.py` 检查当前证据指纹后更新验证 JSON、公开证据和带原生库的源码 ZIP；`prepare_release.py` 生成版本专用附件清单和 SHA256SUMS。没有改代码且指纹仍一致时无需重复所有测试。

`dist/` 不提交 Git，附件上传 Release；源码、文档、媒体和公开验证记录提交仓库。发布和后续同步约定见 [RELEASING.md](RELEASING.md)。

开发接口另运行 / Development API checks: `python tools/test_api.py`。该检查使用生产 HTTP / 路由和真实本机 socket，执行器是显式测试替身，不是手机推理。

## 开发语音引擎

在扩散源码与 Windows NDK 准备完成后，依次运行 `python tools/fetch_tts.py --transport ssh`、`python tools/build_tts.py`、`python tools/collect_tts_notices.py`；然后运行 `python tools/test_tts.py` 和通用 APK 构建 / 检查。下载的是固定代码库和通用许可，不含模型。sherpa / ORT 使用上游预编译库，LMA worker 使用本项目 NDK 编译；源码 / 哈希 / 参数 / 验证边界见 [TTS_ENGINE.md](TTS_ENGINE.md)。

## Nano 原生执行器

完成共享 ORT / sd.cpp 前提后，依次运行 `fetch_moss_nano.py`、`build_moss_nano.py`、`collect_moss_nano_notices.py`、`test_moss_nano.py`，再执行通用 APK 检查。源码固定，使用原生 Windows 工具；主机 C++ 解析检查需 MSVC，可由 `LMA_VCVARS` 指定初始化脚本；不使用虚拟化。见[完整步骤](MOSS_NANO_ENGINE.md)。

文本基座新增 `python tools/test_text.py`，使用真实主机子进程 / 回环 HTTP 与 metadata-only GGUF，未执行模型或 Android。现有文本 runtime 由 `runtime-lock.json` 与 `BUILD_INFO.json` 生成单独签名包元数据并核对全部依赖；不新增权重。见[文本基座](TEXT_ENGINE.md)。

dev.9 的 `python tools/test_migration.py` 编译实际 Store / BundleStore / EngineHost，并在独立 `build/migration-tests/` 中检查本机文件、硬链接、并发设置和真实协议子进程。依赖与先决条件沿用后端检查；零 tensor GGUF 只用于 metadata，不运行模型。App 启动迁移与物理 Android 升级仍须独立验收。见[迁移指南](MODEL_MIGRATION.md)。

共用调度回归：构建完成后运行 `python tools/test_scheduler.py`，再执行 `python tools/test_android_lint.py` 与 `python tools/verify_package.py`。前者编译生产 `LocalJobs` / `EngineHost` / `ChatRunner` / `ApiHost`，使用受控主机 Android 端口、真实子进程和固定 HTTP 协议；不启动模拟器、不下载模型，也不执行推理。回执为 `build/scheduler-tests/results.json`，通过开发导出进入 `verification/development/scheduler.json`。

本地素材检查：`python tools/test_inputs.py` 编译生产 core 和真实文件 / WAV / HTTP 测试，回执为 `build/input-tests/results.json`，开发导出至 `verification/development/inputs.json`。依赖已固定的主机 org.json；不需要 Android 或模型，不生成推理样本。见[输入指南](LOCAL_INPUTS.md)。

Dev.12 diffusion / 扩散检查：`python tools/test_diffusion.py` 编译生产 Java 绑定并运行实际主机协议子进程、编译执行共用 C++ 采样 / 架构约束；不是 Android 或图像推理。Native Windows host checks are exported as `verification/development/diffusion.json`.


dev.13 重新编译扩散 worker：8,836,200 bytes，SHA256 `01e6c0a37fc56bb9268d0890c71d8dae57bd0ac41922cb2ec64ad6e5e7fd1d3c`，同一 sd.cpp / ggml 固定提交、CPU、API 28 / 16 KiB 对齐。安装包原签名保留；[更新说明](releases/v0.3.0-dev.13.md)记录精确 APK 和检查，不表示手机执行。

Sana MNN 构建在同一原生 Windows 工具链下依次运行 `python tools/fetch_mnn.py`、`python tools/build_mnn.py`、`python tools/collect_mnn_notices.py`、`python tools/test_mnn.py`，然后通用 APK / Lint / 包检查。源码、header、覆盖补丁和许可固定，不下载模型。74 项主机 / C++ 检查不执行 MNN 模型；详见 [MNN Sana 构建与组件](MNN_SANA_ENGINE.md)。

Qwen 原生语音使用同一 Windows 工具链：`fetch_qwen_tts.py` → `build_qwen_tts.py` → `collect_qwen_tts_notices.py` → `test_qwen_tts.py`（均在 `tools/`）。CPU / API 28 / 16 KiB，源码和许可固定，不自动下载模型。开发者可明确运行 `python tools/audit_qwen_headers.py --origin https://hf-mirror.com` 核对固定 GGUF 文件头，未读张量。见 [Qwen 语音构建](QWEN_TTS_ENGINE.md)。

## MOSS Delay 原生引擎

固定 fork / 原生提取 / NDK 编译 / 许可步骤见 [MOSS Delay](MOSS_DELAY_ENGINE.md)。依次运行 `tools/fetch_moss_delay.py`、`tools/build_moss_delay.py`、`tools/collect_moss_delay_notices.py`；`tools/test_moss_delay.py` 执行主机 Java 契约和上游原生 Delay 算法自检。所有文件保留项目内，不下载或转换模型权重。

新增原生路线见 [openmoss 构建](OPENMOSS_ENGINE.md#5-固定来源与构建)：先 fetch_openmoss.py / build_openmoss.py / collect_openmoss_notices.py，再使用共用 APK 构建；不下载或转换模型。

Stable Audio 原生构建：`fetch_stable_audio.py` → `build_stable_audio.py` → `collect_stable_audio_notices.py` → `test_stable_audio.py`（`tools/`）。原生 Windows NDK、固定官方 LiteRT AAR / SDK、CPU，所有缓存在 build/。主机测试还需 Python flatbuffers（本轮 25.12.19）、MSVC 与 Java；固定 Windows DLL 只执行合成微型图，不进 APK。详见[组件、命令、源码与许可](STABLE_AUDIO_ENGINE.md)。


SoulX生产worker原生构建：`build_soulx.py`（主机）→ `build_soulx.py --android` → `collect_soulx_notices.py` → `test_soulx.py` /显式准备权重后的 `test_soulx_worker_trained.py` →共享APK构建。复用固定llama /ggml /ORT，模型资产不进APK；全部命令使用原生Windows /NDK，缓存留在build。API28 /16KiB与许可回执见 [完整指南](SOULX_ENGINE.md)。

旧LTX 0.9.8研究组件构建：显式 `fetch_native.py` → `fetch_ltx098.py --python-dependencies` → `test_ltx098.py`（顺序CPU /Vulkan）→ `build_ltx098.py --android --vulkan`，命令均在 `tools/`。项目内锁定新版Windows shaderc及Vulkan /SPIRV headers，原生MSVC /NDK，无虚拟化；临时SUBST在finally移除，构建不可并发。只准备代码 /开发工具，不获取模型权重，不打包到APK。精确依赖、F32 shader策略与范围见[中文](LTX098_DIT.md) / [English](LTX098_DIT.en.md)。

旧LTX训练采样的[独立复现步骤](LTX098_SAMPLING.md)补充显式 `fetch_ltx098_trained.py --download`、本地 `export_ltx098.py`、未训练 /训练 `ltx098_sampling_oracle.py` 与 `test_ltx098_sampling.py --trained --skip-build`。均在 `tools/`，缺件不补下载；模型缓存不入APK。原生构建顺序执行，两份ARM64 ELF分别核验；开发者真实检查点与完整用户下载候选 /Android验收保持区分。

旧LTX T5组件按[中文复现](LTX098_TEXT.md)显式准备量化encoder与原始外部分词配置，再顺序执行 `tools/build_ltx098_text.py`、`tools/ltx098_text_oracle.py --trained`、`tools/test_ltx098_text.py --trained`、`tools/build_ltx098_text.py --android`。默认不获取任何模型；开发依赖 /模型缓存均在项目内，无虚拟化，不进入APK。CLI必须单独传入原始tokenizer_config；临时F32矩阵缓冲复用与主机 /Android证据分别说明。


旧LTX训练VAE按[完整离线复现](LTX098_VAE.md)显式准备已固定的原始检查点，再运行 `tools/ltx098_vae.py export`、`references`、`tools/build_ltx098_vae.py`、其 `--android` 编译及 `tools/test_ltx098_vae.py`。原始官方forward作为独立参考；导出目录拒绝覆盖，不自动获取模型。两种原生编译顺序运行，SUBST别名在finally释放，所有缓存 /临时文件在项目内，不调度虚拟化；研究可执行文件和模型图不进入APK。


旧 LTX 真实提示词管线按[中文完整复现](LTX098_PIPELINE.md)显式准备已有固定组件及外部资产，再顺序构建 `tools/build_ltx098_tensors.py` / `--android`，执行 `tools/test_ltx098_tensors.py` 与 `tools/test_ltx098_pipeline.py`。后者实际运行 A/B/A 三个训练任务和两个原始前向参考；无模型自动下载、无虚拟化或模拟器。开发 MP4 使用主机 FFmpeg，App 仍须接入同机 MediaCodec；源码后续不改 APK。

当前完整管线测试按原门槛返回 exit 1，并写出163项记录中的6项浮点失败；两组RGB通过。可重放已捕获且指纹有效的输出核验，不重新冒充推理执行。[详见数值失败与复用逻辑](LTX098_PIPELINE.md)。

旧 LTX 精度定位采用原生 Windows MSVC、已锁定的现有 GGML 静态库与独立源码副本；命令与前置资产见[中文指南](LTX098_PRECISION.md) / [English](LTX098_PRECISION.en.md)。不修改生产源、不自动取模型；314 / 628 / 120 为诊断 / 文件 / 算子数量。候选 F64 计算尚非 Android 构建或验收，不提升 APK 版本；全部完整链路门槛保持。

原生旧 LTX 转换复现见[中文指南](LTX098_PREPARE.md) / [English](LTX098_PREPARE.en.md)：顺序运行 `tools/build_ltx098_prepare.py`、`--android`、`tools/test_ltx098_prepare.py --trained`，然后开发导出、`tools/plot_ltx098_prepare.py` 和开发仓库检查。仅复用显式取得的本地开发资产，无自动下载。自有 SHA / 半精度转换与已有固定 JSON 头，ARM64 API28 / 16KiB；源码组件不进入本次 APK。

旧 VAE 准备复现见[中文](LTX098_VAE_PREPARE.md) / [English](LTX098_VAE_PREPARE.en.md)：审计图模板，顺序构建 DiT / VAE 两种准备器的 MSVC 与 ARM64 版本，再执行各自完整训练文件测试和 VAE 真实解码。`tools/prepare_ltx098_vae_templates.py` 是开发构建工具；Android 转换不使用 Python / Torch / ONNX 或网络。使用公开记录回退的构建仍核对图审计输入及模板输出指纹。

## dev.22：准备模块打包与证据

[运行资产方案](MODEL_PREPARATION.md)的两个准备器按原生Windows/NDK步骤顺序构建，九份无模型参数图经过模板审计后才由 `tools/package_preparations.py` 打包；不运行权重下载或转换。`tools/preparation_build_inputs.py`在既有构建指纹上加入全部准备源码/锁/合同；不修改其他神经网络数学检查的通用指纹辅助文件。构建 `python tools/build.py`、核心 `python tools/test_preparations.py`、完整已有训练源 `python tools/test_preparations.py --trained`、包验证/Lint/相关回归、开发证据导出与仓库审计分别执行。训练转换与构建分开，输出和checkpoint都不进入APK/Git。77份Java编译输入、29个原生文件；签名密钥沿用原有本地文件。Android测试、完整视频数值/质量和完整Release仍未完成。


## dev.24 原生增量构建

`tools/build_native.py` 优先使用现有 CMakeCache 的 ASCII 驱动器身份，避免旧 T: 缓存误用新 R:；别名被其他任务占用时明确失败并保留缓存。仅映射本工作区，结束后释放自己创建的别名，不借用或删除其他映射。SD1.5 训练验证另见[开发流程](SD15_TRAINED.md)，不把 Windows 测试程序打入 APK。
