# 更新、同步与发布 / Updating and releasing

[贡献约定 / Contributing](../CONTRIBUTING.md) · [文档目录 / Documentation](README.md)

## 持续要求 / Standing instruction

用户已要求后续 LMA 更新同步推送到 `git@github.com:wikigsroom/LMA.git`，且同步代码、文档、媒体和更新说明。This repository's authorized future changes must be committed and pushed together with both languages, affected media, and release notes. This is recorded in [AGENTS.md](../AGENTS.md); it is not a background scheduler.

## 下一版本完整范围 / Complete next-version scope

下一版本为 v0.3.0，按[完整需求](MULTIMODAL_RELEASE_PLAN.md)与[交付摘要](releases/v0.3.0-plan.md)一次完成 F-01–F-12、既有生文、01–14 / 16 / 17 和全部冻结子目标的运行支持能力与配方。内部工作包不拆为其他版本；必需项未过时保留为本版阻塞，不以缩减预览、空引擎或目录记录替代完成。当前公开 APK 仍为 v0.2.0；内部 0.3.0-dev 仅用于开发复查，不创建 v0.3.0 标签或 Release。The next v0.3.0 has one complete acceptance scope; missing required targets block completion, without automatic deferral. Internal 0.3.0-dev builds are development checkpoints; published v0.2.0 APK/tag/assets remain intact.

App 发行不含模型权重或模型专用数据；模型是用户单独选择的资产。安装 / 升级不得触发权重下载、强制模型更新或静默替换；推荐目录不表示安装。发布前 A11 验证零模型启动、显式下载、独立管理和升级保留；开发验收样本不能进入 APK。App releases carry the foundation, with user-selected model assets kept separate; A11 validates this boundary.

## 发布准备 / Prepare

1. 保留他人工作并检查远端；不强制推送、不改写公开标签。Inspect remote/local changes and preserve history.
2. APK 内容变化时提升 Manifest、Gradle、状态快照、关于页及夹具中的版本；同步中英文 README / 指南与 `CHANGELOG.md`。Bump app versions consistently for APK changes; synchronize both languages and notes.
3. 更新 `docs/releases/vVERSION.md`，写明最终行为、附件、验证和限制。Maintain bilingual version notes around the final implementation.
4. 对相关代码运行检查，构建签名 APK，核对当前证据指纹。Preserve the local signing identity and verify package/evidence.
5. UI 变化时重录媒体，保留演示标识，不把桌面桥接冒充 Android。Refresh affected media and retain scope labels.

```powershell
python tools/build.py
# 运行适用于当前改动的检查 / Run checks relevant to the actual changes
python tools/test_protocol.py
python tools/test_text.py
python tools/test_backend.py
python tools/test_hub.py --live
python tools/test_sqlite.py
python tools/test_android_lint.py
node tests/ui-smoke.cjs
python tools/verify_package.py
python tools/build_acceptance.py
node tools/capture_media.cjs
python tools/package_delivery.py
python tools/prepare_release.py
python tools/check_repository.py
```

工具链和环境变量见 [BUILD.md](BUILD.md) / [BUILD.en.md](BUILD.en.md)。未改 APK 时保留既有 APK 字节及版本，不为文档改动重复构建。If APK inputs are unchanged, reuse matching evidence and APK bytes instead of unnecessary rebuilds.

`package_delivery.py` 输出公开 `verification/` 与专用源码 ZIP；`prepare_release.py` 将白名单附件放到被忽略的 `dist/releases/vVERSION/`，生成 SHA256SUMS / manifest。原生库不提交 Git，但包含在专用源码 ZIP。私钥、口令、真实 API 密钥、权重、缓存和 profile 都不得发布。

## 提交和推送 / Commit and push

```powershell
git status --short
git add README.md README.en.md CHANGELOG.md docs app catalogue tools tests third_party verification .gitignore .gitattributes AGENTS.md CONTRIBUTING.md .github LICENSE build.gradle settings.gradle
git diff --cached --stat
git diff --cached --check
git commit -m "docs: describe the concrete update"
git push origin main
```

按实际改动选择路径，不提交 `dist/`、`build/`、`signing/` 或原生库缓存。Inspect exact staged content. Documentation-only updates still update changelog and affected bilingual notes, then push; a new APK Release is only needed for a versioned application change or an explicitly requested release.

## 创建 Release / Publish

新版本先创建带说明的标签并推送；不要使用已发布的不同版本标签。Create and push an annotated tag pointing to the reviewed release commit:

```powershell
git tag -a v0.2.0 -m "LMA v0.2.0: HF discovery and local model management"
git push origin v0.2.0
python tools/publish_release.py --gh C:/path/to/gh.exe
# 上一条只预检 / The command above only previews
python tools/publish_release.py --gh C:/path/to/gh.exe --publish
```

GitHub CLI 需已登录且具有目标仓库写入权限。The publisher uses the existing authenticated GitHub CLI, never stores credentials, and never prints a token. It requires a clean tree and a pushed matching tag. It creates a draft prerelease, uploads each whitelisted asset, checks server-reported size/hash, and only then publishes. It does not replace existing different assets. If upload fails, a draft remains for inspection; do not announce success.

GitHub 的按标签 REST 查询可能对草稿返回 404；工具通过已认证、支持分页的发行列表定位同一草稿，避免把它当成不存在而重复创建。GitHub's tag endpoint may return 404 for a draft; the publisher resolves it through the authenticated paginated release list instead of treating it as missing.

版本由 Manifest 读取，以上 `v0.2.0` 仅是本次具体例子。The version is read from the Manifest; update tag commands for future versions. Current release status is deliberately prerelease while physical acceptance is pending. Change stable status only with the corresponding device evidence and documentation.

发布后通过无认证公开 API 检查版本、附件、哈希和下载链接；本地回执位于 `dist/releases/vVERSION/publish-receipt.json`。After publication, verify the public release and downloads; retain the local receipt. Never describe a tag alone as a completed GitHub Release.

## 不可变附件 / Immutable assets

公开附件一旦发布，不以相同文件名替换不同字节。新的 APK、源码包或媒体修改应发布新版本或作为下一次仓库文档提交，避免破坏已公开的校验值。Never replace released bytes under an existing name. New binaries/source/media for a release require a new version; documentation changes may instead remain a later repository commit.

无设备时可发布明确说明范围的预发布包，但必须保留 `physical_device_tests=0` 等真实状态。If no phone is available, publish a clearly scoped prerelease with truthful false device flags, not fabricated acceptance.

发布后的文档或工具维护可运行 `python tools/check_repository.py --published`，把原始源码 ZIP 与已发布标签核对，再检查当前公开文件、文档和证据。不要为了让当前文件等于旧 ZIP 而改写已公开附件。For post-release documentation/tool maintenance, `--published` compares the immutable source bundle with its tag while checking current public files, links, and evidence. This permits later commits without rewriting published assets.
