# 构建与验证

[English](BUILD.en.md) · [文档目录](README.md)

## 已验证工具链

使用 Windows 原生工具：JDK 21（PATH 中含 java / javac / keytool）、Python 3、Android SDK Platform 35、Build Tools 35.0.1。独立 Lint 需要 SDK Command-line Tools。主构建脚本明确调用 `.exe`，Linux / macOS 没有验证；不使用 Docker、WSL、虚拟机或模拟器。

界面检查需 Node.js 和 Playwright，可使用已安装 Edge / Chromium。媒体录制另需 FFmpeg / FFprobe，以及 Playwright 的 FFmpeg 组件（`npx playwright install ffmpeg`）。安装依赖时应使用本项目或用户指定目录，不把依赖提交进 Git。

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
python tools/bootstrap_runtime.py
python tools/build.py --sdk C:/path/to/Android/Sdk
```

未指定 `--sdk` 时先读 `ANDROID_SDK_ROOT`，否则使用当前用户 LocalAppData 的 Android SDK 默认目录。SDK 平台与 Build Tools 不会被脚本自动安装。Android Studio / Gradle 配置供继续开发，当前标准 Gradle 路径未执行验证，没有 Gradle wrapper。

## 引擎与目录重建

`bootstrap_runtime.py` 下载 ServLlama 1.2.2 的固定 ARM64 发行包，校验 `551e5be8494bd2ae9955992faaaca1a4f5cf29e3a97f90d2e04205eb460fcde6`，提取 14 个 CPU 库到 `app/src/main/jniLibs/arm64-v8a/`，不打包 OpenCL / Hexagon。Git 忽略原生库和缓存；Release 专用源码 ZIP 带有这些已核对的库。下载的是预编译组件，不在本机编译 ARM 引擎。

构建先执行 `build_catalogue.py`，要求 14 个内置模型的作者依据、GGUF 固定提交和权重哈希一致。普通重建使用已有证据，不需要重新访问所有模型卡。模型新增或来源变更时重新运行相应审计，并检查人工归属判断；不要只改模型名称。

该校验保护既有精选及“已核对”标签，不限制 HF 在线发现。保留推荐 `m08 → m06 → m01`；普通 HF 模型通过原生 HubClient / HubCatalog 获取、选文件并交给 Store / Downloads。“本地”汇总所有来源。`test_hub.py --live` 在后端编译后运行 45 项 HF 检查和 5 项公开 API 检查；live 使用 HF Mirror，未下载完整权重或认证私有仓库。网络不可用时可先运行不带 `--live` 的逻辑检查，但新发布仍需要当前实时记录。

`build.py` 使用 AAPT2 编译 / 链接资源，javac 编译 Java，D8 生成 DEX，加入原生库，zipalign，签名并验证 APK。证据保存输入文件的原始字节 SHA256；`.gitattributes` 禁止自动换行转换，避免 checkout 改变指纹。

## 签名和产物

首次构建在 `signing/` 创建 RSA3072 本地身份及随机口令。请安全保留以覆盖升级；不要提交、分享或上传该目录。个人 clone 生成的密钥不能覆盖官方 Release 安装，除非使用同一签名；卸载旧包会丢失模型和聊天。

- `dist/LMA-0.2.0-arm64-v8a.apk`：签名安装包。
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
