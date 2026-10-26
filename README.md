# LMA · Android 无审查模型工作台

[中文](README.md) · [English](README.en.md) · [下载 / Releases](https://github.com/wikigsroom/LMA/releases) · [文档导航](docs/README.md) · [更新记录](CHANGELOG.md)

Android 版的本地模型管理、下载、对话和 API 服务应用。当前修订版本为 **0.1.2 / ARM64 / Android 9+**。

安装包：[v0.1.2 Release](https://github.com/wikigsroom/LMA/releases/tag/v0.1.2) 中的 `LMA-0.1.2-arm64-v8a.apk`，约 10.9 MB。模型权重由用户在应用中选择下载，APK 不含模型权重。LMA（Local Model App）是独立社区项目，与 LM Studio 无隶属关系；当前应用界面主要为中文，文档提供中英双语。

> **预发布状态：** 已签名构建，通过 115 项桌面断言和 APK / 原生库 / Android Lint 检查。当前没有可用 Android 真机；安装、实际推理、速度和后台耐久未实测。以下图片、视频与 GIF 来自随 APK 分发的实际界面，原生状态为明确的演示数据，**不是手机推理实录**。

<p>
  <img src="docs/media/01-library.png" width="260" alt="LMA 无审查模型库，界面演示数据">
  <img src="docs/media/05-api.png" width="260" alt="LMA API 服务，界面演示数据">
  <img src="docs/media/07-dark.png" width="260" alt="LMA 深色主题，界面演示数据">
</p>

## 阅读路线

| 需求 | 中文 | English |
| --- | --- | --- |
| 安装、页面操作、后台与排错 | [使用手册](docs/USER_GUIDE.md) | [User guide](docs/USER_GUIDE.en.md) |
| 模型清单、具体量化、作者依据 | [无审查模型](docs/UNCENSORED_MODELS.md) | [Uncensored models](docs/UNCENSORED_MODELS.en.md) |
| 技术实现、生命周期、存储与网络 | [架构](docs/ARCHITECTURE.md) | [Architecture](docs/ARCHITECTURE.en.md) |
| curl、Python、PowerShell 和 SSE | [API 接入](docs/API.md) | [API integration](docs/API.en.md) |
| 工具链、重建和验证 | [构建](docs/BUILD.md) | [Build](docs/BUILD.en.md) |
| 已通过检查与实测边界 | [验证](docs/VALIDATION.md) | [Validation](docs/VALIDATION.en.md) |
| 真机验收工具 | [设备验收](docs/DEVICE_ACCEPTANCE.md) | [Device acceptance](docs/DEVICE_ACCEPTANCE.en.md) |
| 截图、录屏和 GIF 的生成 | [双语媒体说明](docs/MEDIA.md) | [Bilingual media guide](docs/MEDIA.md) |
| 后续同步与发布 | [贡献约定](CONTRIBUTING.md)、[发布流程](docs/RELEASING.md) | [Contributing](CONTRIBUTING.md), [Releasing](docs/RELEASING.md) |

## 运行方案

```mermaid
flowchart TD
  UI[本地 WebView：模型库 / 对话 / 服务 / 设置] -->|JSON 命令和状态| FGS[Android 原生前台服务]
  FGS --> DL[HTTPS 下载 / 续传 / SHA256 / SAF 导入]
  FGS --> ENGINE[独立 ARM64 llama-server 进程]
  FGS --> CHAT[原生 ChatRunner / SSE / SQLite]
  CHAT -->|本机 HTTP| ENGINE
  CLIENT[本机或局域网客户端] -->|Bearer API 密钥| ENGINE
```

同时加载一个模型、一个推理槽。界面退出不会主动取消原生下载与生成；下载完成与加载完成是两个阶段。模型加载后，本地对话和外部 API 共用同一引擎。应用内“停止生成”只取消当前回复，通知中的“停止服务”结束后台工作。完整状态机和恢复规则见架构文档。

## 操作演示

<p><img src="docs/media/lma-walkthrough.gif" width="320" alt="LMA 操作 GIF，模拟原生状态，非真机推理"></p>

[完整 MP4 视频](docs/media/lma-walkthrough.mp4) · [API / 深色主题 GIF](docs/media/lma-api-theme.gif) · [全部截图](docs/MEDIA.md) · [来源与文件哈希](docs/media/manifest.json)。顶部全程显示 UI DEMO；下载进度为模拟状态，对话为脚本文本，IP 和密钥为示例，没有执行 Android 或模型。录制脚本位于 `tools/capture_media.cjs`，结束时自动关闭所有测试页面和浏览器。

## 安装包核对

```text
APK SHA256: e9e3b7103f5e63c86953acdb986387f73cae9e3fb42851f6af1b9fffe6c1cc28
包名: com.lma.app / versionCode 3
签名证书 SHA256: 90444a717a55549e2094364d8d7d005cf8b7f4df24562da62cc1884a2f341c17
```

可运行 `Get-FileHash .\LMA-0.1.2-arm64-v8a.apk -Algorithm SHA256`。后续升级须使用同一签名来源；自行构建会使用自己的密钥。Release 同时提供源码 ZIP、SHA256、验证 JSON 和演示视频。

## 使用

1. 将 APK 传到手机并安装；如果系统提示，允许当前文件管理器安装此 APK。
2. 打开 LMA，在“模型库”中选择模型并点击“下载”。默认自动尝试 Hugging Face，连接失败后切换到 HF Mirror；也可手动固定下载源。也能通过 HTTPS 直链添加或从设备导入 GGUF。
3. 下载完成后点击“加载模型”。默认情况下，第一个下载完成的模型会自动加载。进入“对话”即可本地聊天。
4. 到“服务”页面设置电池优化豁免，并允许前台服务通知。努比亚等厂商系统可能还要在应用管理中允许后台运行、自启动和后台网络。
5. 模型加载成功后即提供 API。返回桌面或锁屏后，推理与下载由原生前台服务继续执行。通知中的“停止服务”会停止模型及当前下载。

首次下载需要网络；下载完成后的文本推理不依赖云端。应用不需要 ROOT、Termux、Docker 或 WSL。

## 已实现

- 内置 14 个有作者无审查说明的 Uncensored / Abliterated GGUF，支持筛选、搜索、下载、暂停、断点续传、删除、模型切换。全部展示“无审查”标签及作者说明入口。
- 内置目录构建时强制核对作者声明与实际下载权重的仓库、固定版本和 SHA256；新增条目必须提供对应依据。自行导入或添加的文件显示“属性未核对”。
- 14 个内置候选均固定具体仓库提交、准确字节数及 SHA256。通过 HF Mirror 元数据与实际字节探测核对；下载完整文件后再计算哈希比对。自定义链接没有预期哈希时只做格式、长度与本地哈希检查。
- 原生后台下载和独立原生推理进程；WebView 仅承载随包分发的本地界面。
- 本地聊天、SSE 流式显示、停止生成、思考过程、代码复制、SQLite 对话历史；中断后保存已收到的内容。
- OpenAI 兼容的 `/v1/models`、`/v1/chat/completions` 和 SSE；每次安装生成独立 API 密钥。
- 默认仅监听本机；用户可开启局域网访问。CPU 线程、上下文、输出长度、温度、端口、思考模式和系统提示词可设置。
- 运行日志导出、浅色 / 深色主题、可选开机解锁后恢复服务、进程异常退出后的有限恢复。

## 内置候选模型

全部选定文件为 `Q4_K_M` GGUF，下表使用十进制近似体积，**文件体积不等于运行内存**。精确字节数、文件名、固定版本和哈希见 [models.json](app/src/main/assets/models.json)；[作者依据清单](docs/UNCENSORED_MODELS.md)逐项链接固定说明。

| ID | 无审查模型 | 下载体积 | 定位 |
| --- | --- | ---: | --- |
| `m01` | Dolphin 3 · Qwen 0.5B Uncensored | 398 MB | 最小起步候选 |
| `m04` | Dolphin 3 · Llama 1B Uncensored | 808 MB | 轻量、英文 |
| `m05` | Gemma 3 · 1B Abliterated | 806 MB | 轻量、多语言 |
| `m06` | LFM 2.5 · 1.2B Uncensored | 731 MB | 推荐候选 |
| `m08` | Qwen 3 · 1.7B Abliterated | 1.11 GB | 中文推荐候选 |
| `m10` | LFM 2.5 · 2.6B Uncensored | 1.67 GB | 进阶、思考模型 |
| `m11` | Dolphin 3 · Qwen 3B Uncensored | 1.93 GB | 进阶、中文 |
| `m12` | Dolphin 3 · Llama 3B Uncensored | 2.02 GB | 进阶、英文 |
| `m13` | Llama 3.2 · 3B Uncensored | 2.24 GB | 进阶、英文 |
| `m14` | Qwen 3 · 4B Instruct 2507 Abliterated | 2.50 GB | 进阶、中文 |
| `m16` | Gemma 3 · 4B Abliterated v2 | 2.49 GB | 进阶、多语言 |
| `m03` | Qwen 3.5 · 0.8B Abliterated | 528 MB | 新架构、实验候选 |
| `m09` | Qwen 3.5 · 2B Abliterated | 1.27 GB | 新架构、实验候选 |
| `m15` | Qwen 3.5 · 4B Uncensored · HauhauCS Aggressive | 2.71 GB | 新架构、实验候选 |

自定义文件即使名称中含 uncensored，也不会自动变成已核对的内置条目。作者声明不保证绝不拒答；LMA 未独立实测拒答率，也没有逐个候选的 Android 推理记录。

## 努比亚 Z20 起步配置

为骁龙 855+ 提供 ARMv8 CPU 基线内核，默认 **4 线程 / 2048 上下文 / 512 输出 tokens / 关闭可切换的思考模式**。优先用 Dolphin 3 Qwen 0.5B 验证流程，再比较 Qwen 3 1.7B 或 LFM 2.5 1.2B。3B–4B 候选需要结合实际可用内存、温度和持续速度决定是否使用。

**当前没有连接 Z20 真机，未测量任何模型在手机上的 tokens/s、峰值内存或锁屏持续时长。** 目录中的候选、支持的架构和静态库检查不等于具体 GGUF 在该手机上已成功推理。

后台服务通过前台通知、CPU 唤醒锁和 Wi-Fi 锁维持工作。Android、厂商省电策略、用户强行停止、内存不足和发热仍可能终止或影响服务，无法承诺永久存活。一次请求会在 EOS、输出上限或客户端取消时结束；“后台持续输出”指请求生成期间仍可流式输出，不表示无限生成。

开机恢复为用户可选项，仅恢复此前启用且文件仍在的模型。系统是否允许开机启动以前台服务及厂商策略为准；失败后重新打开应用可再次恢复。应用没有静默跳过首次下载、通知和系统电池设置的机制。

## 接口

本机默认地址：`http://127.0.0.1:8080/v1`。局域网开启后，请使用“服务”页面展示的手机地址。同网设备连接时需要相同 API 密钥；局域网接口使用 HTTP。

```bash
curl http://PHONE_IP:8080/v1/chat/completions \
  -H "Authorization: Bearer YOUR_LMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"m08","messages":[{"role":"user","content":"你好"}],"stream":true}'
```

请从 `/v1/models` 获取当前模型 ID；模型别名对应目录 ID，例如 `m08`。应用内“复制连接示例”会填入当前地址、模型 ID 和实际密钥。

## 本地构建

主构建路径使用 **Windows 原生 JDK + Android SDK**，已实际验证，不需要 Gradle 联网拉取插件、NDK、模拟器或虚拟化环境。

需要 JDK 21（`java`、`javac`、`keytool` 在 PATH）、Python 3、Android SDK Platform 35 和 Build Tools 35.0.1。

在本目录执行：

```powershell
python tools/bootstrap_runtime.py
python tools/build.py
python tools/test_protocol.py
python tools/test_backend.py
python tools/test_sqlite.py
python tools/test_android_lint.py
python tools/verify_package.py
```

首次获取源码可执行 `git clone git@github.com:wikigsroom/LMA.git`，然后进入 `LMA/`。Git 不提交可重新获取的原生二进制；先运行上述 bootstrap，再构建。专门的 Release 源码 ZIP 带有原生库与验证记录。

可通过 `python tools/build.py --sdk C:/path/to/Android/Sdk` 指定 SDK。预编译引擎缓存位于 `third_party/cache/`；已有完整原生库时，构建无需再次下载引擎。

`tools/build.py` 执行 AAPT2、javac、D8、zipalign 和 apksigner，生成 `dist/` 中的 APK、SHA256 与构建记录。应用源码和资源也可导入 Android Studio；标准 Gradle 路径未在本次运行中执行。

**升级需保留本机 `signing/` 目录。** 私钥与随机口令只保存在该目录，已加入 `.gitignore`，不会放进 APK。更换签名会导致无法覆盖安装原版本；不要把签名私钥或口令公开上传。

本轮通过 54 项桌面后端检查、25 项协议检查、5 项 SQLite 查询检查和 31 项界面检查。桌面后端执行真实生产 Java、TLS 连接与子进程，但使用明确的 Android 框架替身；没有运行 ARM 模型。

Android SDK 独立 Lint 对全部 12 个生产 Java 文件执行默认检查，结果为 0 错误、7 警告；需要 SDK Command-line Tools。14 个原生库的二进制 API 标记均为 28，15 个启动参数与固定上游版本吻合。这些均为静态证据，详细警告与待实测项目见 docs/VALIDATION.md。

界面检查可在安装 Playwright 的 Node 环境执行 `node tests/ui-smoke.cjs`。`LMA_PLAYWRIGHT` 可指定 Playwright 模块路径，`LMA_BROWSER` 可指定 Edge / Chromium 路径。测试使用明确的原生桥接测试数据，不运行模型，结束时关闭所有测试页面及浏览器。

完整发布前还执行 `python tools/build_acceptance.py`、`python tools/package_delivery.py`、`python tools/prepare_release.py` 和 `python tools/check_repository.py`。真实 Android 验收需要已授权的 ARM64 真机；工具不会启动模拟器。原始、可核对的检查记录整理在 [`verification/`](verification/)。

## 文件与验证

- `app/src/main/java/com/lma/app/`：原生服务、下载、推理进程、聊天、WebView 桥接。
- `app/src/main/assets/`：离线界面、模型目录及许可。
- `catalogue/research-source.json`：此前调查数据的本项目副本，构建不依赖上级目录。
- `catalogue/verified-models.json`：14 个条目的固定版本、大小、SHA256 与字节探测记录。
- `catalogue/architecture-check.json`：真实 GGUF 架构与固定上游源码、已打包原生库的静态对照。
- `catalogue/uncensored-policy.json`、`catalogue/uncensored-evidence.json`：14 个内置无审查版本的准入依据、固定作者说明及对应权重哈希。
- `third_party/runtime-lock.json`：上游发行包及每个原生库的 SHA256。
- `third_party/runtime-audit.json`：固定上游源码、启动参数、鉴权及 CPU 内核发现的静态核对。
- `docs/ARCHITECTURE.md`：后台生命周期、数据和接口边界。
- `docs/VALIDATION.md`：本轮复查结果、修复清单及尚未完成的验收。
- `docs/COMPLETION_AUDIT.md`：用户要求的逐项完成条件、当前证据和真机阻塞项。
- `docs/DEVICE_ACCEPTANCE.md`：真实 Android 验收工具的构建和运行方式。
- `docs/UNCENSORED_MODELS.md`：无审查模型清单、处理方式和作者依据。

LMA 自有代码使用 MIT 许可。llama.cpp 及其依赖保留各自许可；模型按各来源仓库的许可使用。目录中的“uncensored / abliterated”社区命名不保证任意问题都不拒答，也不代表模型能力已经过本应用实测。

## 后续更新约定

每次后续修改需同步更新代码、中英文 README / 配套文档、受影响截图与 GIF、[CHANGELOG.md](CHANGELOG.md) 及对应[版本说明](docs/releases/)，完成检查后提交并推送 `git@github.com:wikigsroom/LMA.git`。此要求已写入 [AGENTS.md](AGENTS.md)；具体执行见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [RELEASING.md](docs/RELEASING.md)。不覆盖已发布版本的不同字节附件，不强制推送，不改写已有标签。

`v0.1.2` 是本仓库首次公开发布的版本；此前 0.1.0 / 0.1.1 为本地迭代，不伪造历史 Release。当前发布按预发布标记，真机验收范围保留在发布说明中。

发布后的文档 / 工具维护使用 `python tools/check_repository.py --published`，核对不可变源码附件与发布标签，并检查当前文档和公开文件。草稿发行通过已认证列表定位，避免 GitHub 按标签查询草稿的 404；维护变更记录在 CHANGELOG 的后续维护段，不改写已公开的 APK、标签或附件。
