# LMA 文档 / Documentation

[项目首页 / 中文](../README.md) · [Project README / English](../README.en.md)

当前版本 **0.2.0**。文档整理日期：**2026-10-27（Asia/Taipei）**。产品行为以生产源码及对应版本的验证证据为准；历史审计保留其原始检查日期。

| 主题 / Topic | 中文 | English |
| --- | --- | --- |
| 安装与操作 / Installation and workflow | [USER_GUIDE.md](USER_GUIDE.md) | [USER_GUIDE.en.md](USER_GUIDE.en.md) |
| API 与 SSE / API and streaming | [API.md](API.md) | [API.en.md](API.en.md) |
| 构建 / Building | [BUILD.md](BUILD.md) | [BUILD.en.md](BUILD.en.md) |
| 架构 / Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) | [ARCHITECTURE.en.md](ARCHITECTURE.en.md) |
| HF 发现与本地管理 / HF discovery and Local | [HF_MODELS.md](HF_MODELS.md) | [HF_MODELS.en.md](HF_MODELS.en.md) |
| 模型独立参数 / Per-model settings | [MODEL_SETTINGS.md](MODEL_SETTINGS.md) | [MODEL_SETTINGS.en.md](MODEL_SETTINGS.en.md) |
| 无审查模型 / Uncensored models | [UNCENSORED_MODELS.md](UNCENSORED_MODELS.md) | [UNCENSORED_MODELS.en.md](UNCENSORED_MODELS.en.md) |
| 验证 / Validation | [VALIDATION.md](VALIDATION.md) | [VALIDATION.en.md](VALIDATION.en.md) |
| 真机验收 / Physical-device acceptance | [DEVICE_ACCEPTANCE.md](DEVICE_ACCEPTANCE.md) | [DEVICE_ACCEPTANCE.en.md](DEVICE_ACCEPTANCE.en.md) |
| 截图与录屏 / Screenshots and recordings | [MEDIA.md（双语 / bilingual）](MEDIA.md) | [Provenance / 来源](media/manifest.json) |
| 后续同步与发布 / Updates and publishing | [RELEASING.md（双语 / bilingual）](RELEASING.md) | [Contributing / 贡献约定](../CONTRIBUTING.md) |
| 版本 / Versions | [CHANGELOG.md（双语 / bilingual）](../CHANGELOG.md) | [v0.2.0（双语 / bilingual）](releases/v0.2.0.md) |

## 阅读建议 / Reading paths

- **用户 / Users：** README → 使用手册 / User guide → API → 常见问题 / Troubleshooting in the user guide。
- **开发者 / Developers：** 构建 / Build → 架构 / Architecture → 验证 / Validation → 贡献约定 / Contributing。
- **验收 / Acceptance：** [完成条件核对](COMPLETION_AUDIT.md) → 真机验收 / Device acceptance → [`verification/`](../verification/)。

## 证据和历史记录 / Evidence and audit history

- [DESIGN.md](DESIGN.md)：界面交互设计说明 / UI design rationale。
- [COMPLETION_AUDIT.md](COMPLETION_AUDIT.md)：逐项完成条件及真机阻塞项 / Requirement-by-requirement audit and device blocker。
- [`catalogue/`](../catalogue/)：固定模型、作者声明、GGUF 来源、哈希及架构记录 / Pinned models, publisher declarations, hashes, architecture records。
- [`third_party/README.md`](../third_party/README.md)：引擎来源、锁定版本、许可和部分上游审计源码 / Runtime provenance, locks, notices, selected audit sources。
- [`verification/README.md`](../verification/README.md)：可以公开复查的桌面及包验证记录 / Reviewable desktop and package evidence。

**界面演示不等于真机验收。UI demonstrations do not establish physical-device inference or background endurance.**
