# Verification records / 验证记录

These records belong to **LMA 0.2.0** and are exported by `tools/package_delivery.py` after checking current input fingerprints. 本目录由交付工具核对输入后生成，可公开复查；不要手工把未通过项目改为成功。

| Record | Scope / 范围 |
| --- | --- |
| [validation.json](validation.json) | Release summary / 发布验证汇总 |
| [build.json](build.json) | APK identity, hash, and exact build inputs / 构建信息 |
| [package.json](package.json) | Signature, native ELF, alignment, packaged assets / 包验证 |
| [backend.json](backend.json) | 85 host assertions, Android framework adapters / 桌面后端 |
| [hub.json](hub.json) | 45 production HF/client/controller/store assertions / HF 与本地逻辑 |
| [hub-live.json](hub-live.json) | 5 live public HF Mirror API metadata checks, no weights/inference / 实时元数据 |
| [protocol.json](protocol.json) | 25 JVM protocol assertions / 协议 |
| [sqlite.json](sqlite.json) | 5 host SQLite query checks / SQL 查询 |
| [ui.json](ui.json) | 66 browser checks using an explicit test bridge / 界面 |
| [android-lint.json](android-lint.json) | 0 errors, 7 reviewed warnings / Lint |
| [runtime.json](runtime.json) | Pinned runtime configuration audit / 引擎静态核对 |
| [model-network.json](model-network.json) | Pinned publisher metadata and GGUF byte probes / 网络探测 |
| [uncensored-models.json](uncensored-models.json) | 14 publisher declarations and exact weight attribution / 无审查依据 |
| [acceptance-build.json](acceptance-build.json) | Acceptance APK compilation, not device execution / 验收工具构建 |
| [device.json](device.json) | Device unavailable; no successful phone checks / 无可用真机 |

**226 desktop assertions; 0 physical-device checks.** No Android model inference, refusal-rate measurement, or screen-off endurance was executed. 桌面与静态证据不替代手机实测。

See [validation / 验证](../docs/VALIDATION.en.md), [Chinese audit / 完成条件](../docs/COMPLETION_AUDIT.md), and [device acceptance / 真机验收](../docs/DEVICE_ACCEPTANCE.en.md). Media provenance is separate in [manifest.json](../docs/media/manifest.json).

内部 dev.8 验证另见 [development/status.json](development/status.json) 与 [text.json](development/text.json)：310 基座、66 新增文本主机、147 界面检查，0 真机结果，不替代上面的公开 v0.2.0 历史记录。Internal dev.8 evidence stays separate from published history and does not establish full-release acceptance.

内部 dev.9 的 [migration.json](development/migration.json) 是 69 项真实主机文件 / 硬链接 / 子进程检查；使用零 tensor 元数据与固定协议内容，不是 Android、真实模型输出或完整版本证明。 / Internal dev.9 migration evidence remains explicitly host-only.
