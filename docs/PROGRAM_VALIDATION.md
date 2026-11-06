# v1.2.1 m04 / DSH 修复验证

用户已确认手机空闲并授权调试。本轮保留实际m04权重、131072上下文、原参数与DSH全部41工具；程序门禁、实际SDK、DSH任务、模型质量和插件平台支持分别记录。无模型下载／替换、外部代执行或虚假成功。[完整结果](DSH_M04_REPAIR.md)。以下版本策略保留历史语境。

# v0.3.12 验证：程序门禁与授权实机联调

用户最新要求本次交付完成实机接口联调与测评，视频真实时长大于 5 秒，并取消生成固定耗时上限。常规程序门禁计数继续只包含程序检查；真实模型调用、失败、质量与后台时长单独记录。见[本版实机测评](DEVICE_BENCHMARK_V0312.md)。下面旧策略和数字保留其历史范围。

# 仅程序验证策略 · v0.3.11
当前门禁 **60 组 / 15,063 项、73 份记录、794 项页面检查**；独立真机程序 **23 项 / 60.239 秒锁屏 API 健康检查**。另获授权的已安装模型检查保留精确 APK、成功与未完成结果，见[独立模型记录](../verification/releases/v0.3.11/physical-models.json)。门禁仍不运行完整模型，另行授权的实跑不改写成“零推理”。[当前完整清单](IMPLEMENTATION_V0311.md)。

## 历史 v0.3.7 策略与数字

**v0.3.11 授权补充（2026-11-01）：** 用户允许部分真机和模型验证，由开发者选择。仅对已下载模型做限时检查，结果另存 `physical-models.json`；常规门禁仍为程序验证，不恢复全部模型质量或耐久前置要求。下面 v0.3.7 数字为历史记录。

[English](PROGRAM_VALIDATION.en.md) · [版本说明](releases/v0.3.7.md) · [策略 JSON](proposals/program-validation-policy.json) · [实现与全部测试](IMPLEMENTATION_V037.md)

用户于 2026-10-31 要求后续只做程序验证。完整训练模型下载 / 复制 / 推理、ASR、手机推理和长时耐久不作为开发或发版前置项；缺失代码仍须实现，原冻结范围不削减。

v0.3.7 完成原 F01–F12、生文、01–14 / 16 / 17，以及 P01–P06 追加适配。交付 62 个配方、82 个目录包、18 个扩展引擎加文本引擎。所有模型平级，安装或升级只更新基座；用户决定下载、导入和安装什么模型。

| 编号 | 检查 | 当前结果 |
| --- | --- | --- |
| V01 | 程序覆盖 | **59 组 / 14,939 项断言**，精确源码指纹 |
| V02 | 基座 / 社区 / 共用扩展 | 1,226 / 818 / 884 项 |
| V03 | 完整生产页面 | **748 项**，显式桌面模拟桥 |
| V04 | 当前证据 | **72 份 JSON 记录另附 status.json**；815 个历史文件身份保留 |
| V05 | APK | ARM64、API28+、原签名、**41 个原生库**、依赖完整、16 KiB ELF / ZIP 对齐 |
| V06 | Lint | **0 错误 / 16 个原有警告** |
| V07 | 当前媒体 | **9 组 / 52 张截图 / 9 GIF / 9 MP4**，UI FIXTURE 标记 |
| V08 | 完整训练模型下载 / 复制 / 运行 | 均为 0 |
| V09 | 手机推理 / 质量 / 速度 / 峰值 RAM / 锁屏耐久 | 未执行、未声称通过 |
| V10 | 真机程序专项 | **19 项；约 60 秒锁屏 API 健康检查**，不是推理或耐久 |

[当前记录及指纹](../verification/releases/v0.3.7/status.json)与[固定源码审计](../research/portability/adaptation-current.json)明确区分：`all_requested_adaptations_complete=true` / `all_benchmark_architectures_integrated=true` 限于版本化有界 CPU 适配；`full_benchmark_workflows_reproduced=false`。这不表示任意 HF 架构、上游所有 CUDA 配置、完整公开导出包或所有手机已经验证。

原生 Windows 的 JVM / HTTP / 文件 / 子进程检查通过明确的 Android 框架适配替身调用生产逻辑。原始源码类、固定配置的 meta 构造、有界随机网络和 C++ / 上游数值对照验证结构与算法，不等于完整训练生成。页面使用标记的模拟桥；Android Service、SAF、MediaCodec、电源状态和 RSS 没有真机执行记录。Windows 无法提供的 worker RSS 不伪造成实测值。

按[构建指南](BUILD.md)恢复固定源码、编译所有启用的原生引擎；按[完整测试表](IMPLEMENTATION_V037.md#program-checks)运行相应入口。生产页面运行 `node tests/ui-smoke.cjs`，九组录制见[媒体索引](MEDIA.md)。APK、签名和 Lint 检查后，执行 `python tools/audit_adaptations.py --require-complete`、`python tools/program_evidence.py --export`、源码和发行打包。只在精确输入指纹仍一致时复用通过记录；改动相关源码必须重跑对应检查。

不得改写指纹制造通过、删除失败、把登记条目冒充运行器、恢复已取消的模型 / 真机门槛、调用 Docker / WSL / VM / 模拟器或静默取得模型。浏览器在 finally 关闭；保留签名材料、用户已有盘符、推荐 `m08 → m06 → m01` 和模型资产控制权。

`verification/program/`、`verification/history/` 与旧 Release 附件保留原身份，当前证据另存 `verification/releases/v0.3.7/`。旧 v0.3.5 的 30 组 / 5,820 项和此前缺适配审计仍是历史记录，不能覆盖成新数据；旧模型输出、误差和失败继续可查。

[Physical acceptance / 真机专项](DEVICE_ACCEPTANCE.md) · [English](DEVICE_ACCEPTANCE.en.md). Optional physical program evidence is version/APK-bound; it does not restore cancelled model-run prerequisites.
