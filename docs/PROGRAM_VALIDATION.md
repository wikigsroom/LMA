# 仅程序验证策略

[English](PROGRAM_VALIDATION.en.md) · [v0.3.0](releases/v0.3.0.md) · [policy JSON](proposals/program-validation-policy.json)

用户于 2026-10-31 明确要求：“请你后续内容只做程序验证，不需要走完完整的模型运行验证，太耗费时间了。”此指令覆盖旧文档的完整训练模型运行、ASR、真机推理和长时耐久发布门槛；不豁免缺失的程序功能，不拆分冻结范围。

v0.3.0 已补齐旧 LTX 原始 PixArt T5 / 多尺度程序路线，并包含此前接入的 Sana-Sprint。F-01–F-12、原有文本、01–14/16/17 的完整程序映射见[实现矩阵](IMPLEMENTATION_V030.md)。

| Validation / 验证 | Current result / 当前结果 |
| --- | --- |
| Program suites / 程序回归 | 23 suites, 3,590 assertions; source fingerprints checked |
| Android package / 安装包 | ARM64, API28, 35 native libraries, resolved dependencies, 16 KiB ELF/ZIP alignment, original signing certificate |
| Android Lint | 0 errors, 16 retained warnings |
| Current UI / 当前界面 | 530 regression checks; 9 screenshots, 2 GIFs and 2 MP4 recordings across two flows |
| Bounded neural fixtures / 有界神经夹具 | Small random T5/upsampler/MNN graphs and reference math; not complete trained models |
| Complete weights / 完整模型 | 0 complete downloads, copies or executions for this validation |
| Phone / quality / endurance | Not tested; not required by updated policy; no quality or phone suitability claims |

当前[28 份记录](../verification/program/status.json)绑定本版源码与 APK。此前 dev.45 程序记录逐字节归档到[历史目录](../verification/history/dev45-program/status.json)；dev.44/dev.42 与旧完整模型失败保持原身份。旧失败不改为通过。`release_ready` 仅表示符合本策略的程序发行要求，不表示手机可用性已实测。

检查通过明确的桌面 Android / 媒体 / 神经阶段替身调用生产校验、存储、调度及进程管理。Android Service、SAF、MediaCodec 的真实系统执行只做编译及包检查，未在设备执行。页面素材明确标记夹具，浏览器在 finally 中关闭。未使用 Docker、WSL、虚拟机或模拟器。App 只更新程序和元数据，模型取得与管理仍由用户主动决定。
