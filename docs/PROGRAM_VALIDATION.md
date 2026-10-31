# 仅程序验证策略

[English](PROGRAM_VALIDATION.en.md) · [v0.3.4](releases/v0.3.4.md) · [策略 JSON](proposals/program-validation-policy.json)

用户于 2026-10-31 要求后续只做程序验证。完整训练模型下载 / 复制 / 推理、ASR、手机推理和长时耐久不再作为开发或发版前置项。缺失代码不因此豁免，原完整冻结范围不削减。

v0.3.4 保留 F-01–F-12、生文、01–14 / 16 / 17、社区和语音 / 单图 3D，新增 RF Shape 与部件几何，保留真实四视图 CPU 与持久诊断。[当前实现](IMPLEMENTATION_V034.md) · [完整新方案](RF_SHAPE.md)。

| 检查 | 当前结果 |
| --- | --- |
| 程序覆盖 | **27 组 / 5,306 项**，当前源码指纹 |
| 社区 / 共用扩展 / MV / RF | 818 / 428 / 63 / 161 项（社区 / 共用扩展 / MV / RF） |
| 完整生产页面 | **633 项**，明确模拟桥 |
| 五组当前录制 | 社区 34 / 工作台 8 / 语音与 3D 32 / MV 19 / RF 17 项 |
| APK | ARM64、API28+、原签名、**39 个库**、依赖完整、16 KiB ELF / ZIP 对齐 |
| Lint | 0 错误 / 16 个保留警告 |
| 当前媒体 | **25 张截图 / 5 GIF / 5 MP4**，UI FIXTURE 标识 |
| 完整训练模型下载 / 复制 / 运行 | 全部为 0 |
| 手机 / 模型效果 / 锁屏耐久 | 未执行，不声称通过 |

[37 份当前记录＋状态](../verification/program/status.json)绑定本版程序。[v0.3.2 归档](../verification/history/v0.3.2-program-archive.json)按提交 `3f59f2e9f61e72ea3400fe268f85f959c759fc3b` 原样保存 34 份 JSON；旧三组媒体位于 `docs/media/history/v0.3.2/`。先前版本和模型失败记录继续保留原身份。

原生 Windows 的 JVM / HTTP / 文件 / 子进程检查通过明确的 Android 适配替身调用生产逻辑。有界随机神经小图不等于训练生成。页面使用标记的模拟桥；真实 Android Service、SAF、MediaCodec、电源状态与进程 RSS 只有编译 / 包检查，没有设备执行。Windows worker RSS 明确不可用，不伪造 RAM 测量。

`release_ready` 指满足本程序发行策略。`full_scope_implementation_complete` 明确限于原 F-01–F-12、文本和所选编号，不是所有模型的通用支持声明：状态另列 **all_benchmark_architectures_integrated=false** 与 D04–D10。[固定源码审计](../research/portability/audit-v0.3.4.json)列出实际架构移植缺口，补测不能代替运行器开发。

运行 `tools/run_program_checks.py`（先后端，再三组有界检查）、`tools/test_foundation.py`、`tools/test_expansion.py`、`tools/test_multiview.py`、`tools/test_shape.py`、`node tests/ui-smoke.cjs`。当前 APK 构建后检查签名包与 Lint，刷新五组相关 `capture_workbench.cjs` 媒体，然后按[发版流程](RELEASING.md)导出打包。只有精确指纹仍一致时才复用已有通过记录。

不得改写指纹制造通过、删除失败、把登记条目视作接入、恢复已取消的模型 / 真机门槛、调用 Docker / WSL / VM / 模拟器或静默取得模型。浏览器 finally 关闭；保留本机签名、用户原有盘符、推荐和模型资产控制权。

当前 27 组 / 5,306 项含 161 项 RF Shape 与 633 项 UI；Android worker 已编译，完整训练模型导出和手机推理未做。Current version adds matched-export RF Shape / multipart geometry while retaining the full frozen scope. [Design / 方案](RF_SHAPE.md) · [English](RF_SHAPE.en.md).

v0.3.3 的 36 JSON 和四组媒体按[Git 原身份](../verification/history/v0.3.3-program-archive.json)保留，不与当前记录混淆。
