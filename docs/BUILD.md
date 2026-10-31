# 构建与程序验证 · v0.3.5

**当前分支为 v0.3.6 开发源码，未发布完整适配 Release。** 下文 `v0.3.5` 命令用于重现已发布版本。当前开发先执行 `tools/fetch_f5_sources.py`、`tools/fetch_paint_sources.py`，再按 [F5](F5_FRONTEND.md) / [PBR](LOCAL_MATERIALS.md) 准备程序依赖和编译；不准备任何完整训练模型。新版本 APK 构建 / 验包 / Lint 入口不变，证据收口使用 `python tools/adaptation_evidence.py --export` 和 `python tools/check_repository.py --development`。完整适配发布由 `tools/audit_adaptations.py --require-complete` 单独约束；缺代码时不能沿用旧版“完整冻结范围”的完成标志。

[English](BUILD.en.md) · [发布流程](RELEASING.md) · [验证策略](PROGRAM_VALIDATION.md) · [构建历史全文](BUILD_HISTORY.md)

重建使用**带完整历史的 Git clone**，复现时切到 `v0.3.5`。历史证据身份检查会读取早期不可变 Git blob。Release 源码 ZIP 用于代码 / 文档 / 证据审阅，精确文件见源码清单；它排除 `.git`、原生二进制、模型、构建依赖与签名材料，不是自包含 SDK。编译和程序验证不需要完整训练模型。

## 工具链

原生 Windows：JDK21、Python3（本轮 3.13）、Node22、Android SDK Platform35 / Build Tools35.0.1，Lint 需 Command-line Tools。C++ 使用 MSVC、固定 NDK30.0.16248370 / CMake3.31.6。已验证入口为 Python 构建脚本；没有 Gradle wrapper，不声称 Android Studio / Gradle 路径已验。不使用 Docker、WSL、VM 或模拟器。

页面需 Playwright＋Edge / Chromium；录制另需 FFmpeg / FFprobe 和 Playwright 录制组件。可设置 `LMA_PLAYWRIGHT`、`LMA_BROWSER`、`LMA_FFMPEG`。依赖放忽略或任务指定目录，浏览器 finally 关闭。原生工具只在空闲字母上建立临时 ASCII 盘符，并只释放自身别名，不覆盖用户已有 `S:` 等映射。

## 源码与原生依赖

```powershell
git clone git@github.com:wikigsroom/LMA.git
cd LMA
git checkout v0.3.5
python tools/bootstrap_runtime.py
python tools/bootstrap_native.py
python tools/fetch_native.py --transport ssh
python tools/build_native.py --jobs 4
python tools/collect_native_notices.py
```

bootstrap 获取固定 runtime / 工具链代码，不下载模型。14 个 ServLlama 文本库为固定预编译组件，其余 worker 按各自锁和依赖构建。Git 与源码 ZIP 均不携带原生二进制。打 APK 前必须完成**所有已启用引擎**的源码 / 库、构建回执与许可；缺件或过期会阻止打包，不静默删减能力。

| 引擎家族 | tools/ 内源码 → 构建 → 许可入口 | 详细前置指南 |
| --- | --- | --- |
| sherpa / Kokoro / Melo / Piper / Matcha | fetch_tts.py → build_tts.py → collect_tts_notices.py | [TTS](TTS_ENGINE.md)、[Melo](SPEECH_3D_EXPANSION.md) |
| MNN / Sana | fetch_mnn.py → build_mnn.py → collect_mnn_notices.py | [MNN](MNN_SANA_ENGINE.md)、[Sprint](SANA_SPRINT.md) |
| MOSS Nano | fetch_moss_nano.py → build_moss_nano.py → collect_moss_nano_notices.py | [Nano](MOSS_NANO_ENGINE.md) |
| Qwen3-TTS | fetch_qwen_tts.py → build_qwen_tts.py → collect_qwen_tts_notices.py | [Qwen](QWEN_TTS_ENGINE.md) |
| MOSS Delay | fetch_moss_delay.py → build_moss_delay.py → collect_moss_delay_notices.py | [Delay](MOSS_DELAY_ENGINE.md) |
| OpenMOSS | fetch_openmoss.py → build_openmoss.py → collect_openmoss_notices.py | [OpenMOSS](OPENMOSS_ENGINE.md) |
| MOSS RQ / Realtime | fetch_moss_rq.py → build_moss_rq.py → collect_moss_rq_notices.py | [RQ](MOSS_RQ_ENGINE.md) |
| SoulX | build_soulx.py → build_soulx.py --android → collect_soulx_notices.py | [SoulX 固定前置](SOULX_ENGINE.md) |
| Stable Audio | fetch_stable_audio.py → build_stable_audio.py → collect_stable_audio_notices.py | [LiteRT](STABLE_AUDIO_ENGINE.md) |
| LTX 与准备器 | build_ltx098_app.py / --android；package_ltx098_app.py | [官方多尺度](LTX_MULTISCALE.md)、[准备图](LTX098_VAE_PREPARE.md) |
| audio.cpp / 单图 3D | fetch_expansion_sources.py --fetch；build_expansion.py speech_extra / mesh | [语音 / 3D](SPEECH_3D_EXPANSION.md) |
| Pixal3D MV | fetch_multiview_sources.py --fetch；build_multiview.py --host / 默认 Android | [固定源码、生成补丁与检查](MULTIVIEW_DIAGNOSTICS.md) |

新增语音 / 单图 / MV 构建后运行 `collect_expansion_notices.py`，检查回执和 `engine-lock.json` 差异。用户词典、tokenizer、codec 等仍为外部组件，不嵌入权重。各专门指南的旧训练实验保留为**历史**，其中 `--trained` 和模型下载命令不属于当前验证流程。

## APK 与有界程序检查

```powershell
python tools/build.py --sdk C:/path/to/Android/Sdk
python tools/verify_package.py
python tools/test_android_lint.py
python tools/run_program_checks.py
python tools/test_foundation.py
python tools/test_expansion.py
python tools/test_multiview.py
python tools/test_shape.py
node tests/ui-smoke.cjs
```

未指定 `--sdk` 时读 `ANDROID_SDK_ROOT` 或 LocalAppData 默认 SDK；不会静默安装 SDK 包。`build.py` 生成目录 / 配方、编译资源 / Java / DEX，检查原生回执、对齐签名并核对包身份。原字节指纹阻止旧通过记录混入；`.gitattributes` 保持换行与上游文件头填充。

runner 先编译后端生产类，供 HF / 社区检查使用，再运行三组有界检查。Sana / LTX 默认只做微型合成图与进程控制，不执行完整训练模型；另外四个 Python 专项和完整页面组成 27 组覆盖。主机检查使用明确 Android 替身、真实文件 / socket / 子进程，不是真机。只有精确指纹仍一致时才复用记录。

当前包：`com.lma.app`、0.3.4 / code54、ARM64、API28+ / target35、**39 原生库**、16 KiB ELF / APK 对齐。独立核验签名、依赖闭合、原生回执、页面与源码一致和无模型资产。Lint 为 0 错误 / 16 个保留警告。

## 媒体、证据与打包

```powershell
node tools/capture_workbench.cjs community
node tools/capture_workbench.cjs release-workbench
node tools/capture_workbench.cjs expansion
node tools/capture_workbench.cjs multiview
node tools/capture_workbench.cjs shape
python tools/release_scope.py
python tools/program_evidence.py --export
python tools/package_delivery.py
python tools/check_repository.py
python tools/prepare_release.py
```

六组明确标记的桌面生产页面产出 30 张截图、6 GIF、6 MP4。`verification/program/` 为当前记录；v0.3.2 的 34 份原始证据与三组媒体另行归档。原冻结完整范围与后续测评尚未移植架构分别核对，不用程序数量冒充画质 / 手机 / 耐久。

产物包括 `dist/LMA-0.3.4-arm64-v8a.apk`、构建 / 验证 / 源码清单、源码 / 验证 / 截图 ZIP 与版本附件，均不提交 Git，按授权发布流程上传。源码或文档变化后重新打包再发布；已发布后用 `check_repository.py --published` 核对原标签 / 源码 ZIP，不覆盖旧附件。

## 签名与私有材料

保留忽略目录 `signing/` 中的项目 RSA3072 身份以覆盖升级。新 clone 若未私下提供原密钥会创建不同签名，不能直接覆盖已发行安装。不得提交 / 打印密钥或口令。模型权重、音色、tokenizer、词典、缓存、个人浏览器资料不进 Git / 源码 ZIP / APK。

`license.js`、`foundation.js` 和上游 `*.header.json` 限于哈希 / 复制，不读出、转储或暂存；仓库和归档工具只核对身份。App 基座与用户模型 / 参数独立更新。见[贡献约定](../CONTRIBUTING.md)与[当前编号范围](IMPLEMENTATION_V035.md)。

## RF Shape source / 本地形状源码

```powershell
python tools/fetch_shape_sources.py --fetch
python tools/build_shape.py
python tools/build_shape.py --android
python tools/collect_expansion_notices.py
```

复用已经按 SoulX / sherpa 锁构建的 ORT 头、JSON、MV 的 stb 及 Android `libonnxruntime.so`；全部输入固定核对，API28 / 16 KiB / 禁网络进程接口检查。Host build uses MSVC; Android uses the pinned native NDK. All model conversion is a separate user asset operation; see [中文](RF_SHAPE.md) / [English](RF_SHAPE.en.md). Never invoke the exporter as a validation prerequisite with complete trained weights.

## Spatial CPU / Hunyuan shape / UltraShape

[中文方案](SPATIAL_SHAPE.md) · [English workflow](SPATIAL_SHAPE.en.md)

```powershell
python tools/fetch_spatial_sources.py --fetch
python tools/fetch_spatial_sources.py
python tools/build_spatial.py
python tools/build_spatial.py --android
python tools/collect_expansion_notices.py
python tools/test_spatial_shape_graphs.py
python tools/test_spatial.py
python tools/test_spatial_sparse.py
```

Only pinned code/config/license files are fetched. These checks use tiny random or synthetic graphs, not trained models. Android links ORT API17 and built-in CPU custom operations; no downloaded native plugins. 仅获取源码，先构建 host / Android 并收集许可后打包；40 native libraries, 50 templates / 82 bundles / 17 extensions plus text. Source lock, sidecars, input budgets and process cleanup are checked. 六组当前页面录制：community / release-workbench / expansion / multiview / shape / spatial，全部 finally 关闭浏览器。
