# Contributing / 贡献与更新约定

[中文首页](README.md) · [English README](README.en.md) · [Release procedure / 发布流程](docs/RELEASING.md)

## 每次更新 / Every update

1. 修改前检查工作区与远端，不覆盖他人改动，不强制推送。Inspect local/remote state, preserve others' work, and never force-push.
2. 实现并运行与改动相关的检查；只在新改动或未解问题要求时重跑更广检查。Implement and run checks relevant to the change; broaden only for a concrete reason.
3. **同步中英文 README、受影响指南、截图 / GIF 和更新说明。** Synchronize both READMEs, affected guides, media, `CHANGELOG.md`, and version notes. UI changes require refreshed media; behavior-only changes need accurate explanations rather than unrelated recordings.
4. 区分桌面替身、静态证据与真机实测。Keep host adapters, static checks, and actual Android evidence distinct.
5. 运行 `python tools/check_repository.py`，检查链接、证据、公开文件与版本。Review public files and commit a concrete result.
6. 本会话用户已要求后续 LMA 更新完成后同步推送 `git@github.com:wikigsroom/LMA.git`。在该授权工作中使用普通提交 / 推送；认证或网络受阻则保留本地提交并明确说明。The user's standing instruction is to push subsequent authorized LMA updates to this remote, with matching docs and change notes; report actual blockers rather than claiming a push succeeded.

## 产品要求 / Product requirements

- 内置目录必须保持有作者依据的 Uncensored / Abliterated 变体。Built-ins require pinned publisher uncensored evidence and exact weight attribution.
- 不把自定义导入自动标记为已核对。Do not classify imported weights as verified built-ins.
- 保留离线界面、无需 ROOT 和原生后台工作方式。Preserve offline UI, no-ROOT operation, and native background ownership.
- 不调用 Docker、WSL、虚拟机或模拟器；浏览器任务用 finally 关闭无用页面和进程。Never invoke virtualization; always clean up browser resources.
- 不提交模型、API 密钥、签名、密码、浏览器 profile 或构建缓存。Never publish weights, secrets, signing files, profiles, or caches.

## 版本与验收 / Versions and acceptance

APK 代码或资源变化应提升 versionName / versionCode，并同步 Manifest、Gradle、应用状态/关于页及相应测试夹具。Documentation-only changes can remain on the existing app version when APK bytes are unchanged; published release assets remain immutable.

完整产物需当前指纹、哈希、签名、公开验证 JSON 和双语说明。未执行真机验收时保持预发布，不写“完全可用”“已验证所有手机”或虚构 tokens/s。Full release artifacts need current fingerprints, hashes, signing identity, public evidence, and bilingual notes. Do not claim device readiness, performance, or endurance without measurements.

问题报告请提供手机 / Android、LMA 版本、模型 ID/哈希、参数、步骤和已去除敏感信息的日志。Reports should contain device/OS, app/model versions, parameters, reproduction, and sanitized logs.
