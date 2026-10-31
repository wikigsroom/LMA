# 仅程序验证策略 · v0.3.7

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
