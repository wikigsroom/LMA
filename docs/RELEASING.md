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
python tools/test_qwen_tts.py
python tools/test_text.py
python tools/test_migration.py
python tools/test_scheduler.py
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

Qwen 原生语音的源码 / 构建 / 许可步骤及固定 GGUF 文件头复查见 [中文](QWEN_TTS_ENGINE.md) / [English](QWEN_TTS_ENGINE.en.md)。新增 `qwen-tts.json` / `qwen-headers.json` 开发回执不能代替物理 Android 的实际模型输出或释放 / 后台验收。Header review is explicitly developer-invoked and never becomes an App/model download trigger.

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

已有 v0.2.0 预发布保留其真实 `physical_device_tests=0` 状态。下一完整 v0.3.0 必须满足上面的全部发布门槛；无设备的内部 dev 检查点不创建 Release。The historical v0.2.0 prerelease retains truthful device flags. The complete next v0.3.0 requires every gate above; internal dev checkpoints without device acceptance do not create Releases.

发布后的文档或工具维护可运行 `python tools/check_repository.py --published`，把原始源码 ZIP 与已发布标签核对，再检查当前公开文件、文档和证据。不要为了让当前文件等于旧 ZIP 而改写已公开附件。For post-release documentation/tool maintenance, `--published` compares the immutable source bundle with its tag while checking current public files, links, and evidence. This permits later commits without rewriting published assets.

MOSS Delay 的原生算法提取 / CPU worker / 许可见 [中文](MOSS_DELAY_ENGINE.md) / [English](MOSS_DELAY_ENGINE.en.md)。同步执行 `python tools/test_moss_delay.py`；其上游自检、结构 WAV 与主机进程证据不能替代完整 MOSS 家族或物理 Android 的模型输出 / 质量 / 后台验收。

dev.17 新增检查 `python tools/test_openmoss.py`；其主机子进程、结构 WAV 与上游数学检查不替代新输入断网模型输出或任何物理 Android 门槛。每轮开发交付需编号表格列出本轮实现与仍待完成项。The new openmoss checks remain scoped host evidence; each development handoff includes numbered implemented/pending tables without reducing the complete release scope.

SoulX DSP 源码后续更新不新增 APK / Release：执行 `python tools/test_soulx_dsp.py` 和 `python tools/build_soulx_dsp.py`，由开发导出与仓库检查记录未注册静态库及数值证据。它不关闭13号完整模型门槛。The unregistered source library adds scoped evidence only; it does not close target13 or any phone/Release gate. See [中文](SOULX_DSP.md) / [English](SOULX_DSP.en.md).

SoulX声学后续同样不发布 APK / Release：运行 `python tools/test_soulx_acoustic.py`、`python tools/build_soulx_acoustic.py`，并重跑 DSP检查和 ARM64静态编译后导出开发证据。完整结构未训练夹具、原生 ORT主机运行 / 真正终止和 ARM64编译分别核对；不能关闭13号整模型或手机门槛。The acoustic follow-up remains unregistered and does not alter complete Release gates. See [中文](SOULX_ACOUSTIC.md) / [English](SOULX_ACOUSTIC.en.md).

SoulX训练参考 /声学重建后续：先显式准备发布者权重，再顺序执行 `python tools/test_soulx_reference.py`、`python tools/test_soulx_trained.py`、`python tools/build_soulx_reference.py`；共享ORT修改需重跑声学244项和ARM64编译。开发导出 /仓库检查同时核对145参考 /253训练重建证据及完整模型未通过标记，绝不凭这些主机 /编译检查发布Release。Trained component execution does not close complete TTS, quality, App or phone gates. See [中文](SOULX_REFERENCE.md) / [English](SOULX_REFERENCE.en.md) / [编号交付](releases/v0.3.0-dev.20-soulx-reference.md).

SoulX语言与完整主机链路后续：显式准备官方权重 /较早社区对照GGUF，按[中文](SOULX_LANGUAGE.md) / [English](SOULX_LANGUAGE.en.md)依次原生构建、完整导出、语言测试、ARM64编译和新文字整链路测试，再导出开发证据 /核对仓库。原始HF BF16 logits、上游RAS /历史、真实取消及完整host链路不能关闭App /语音质量 /物理Android /Release门槛。Complete trained host execution is recorded separately from all complete Android acceptance gates. No weights/tokenizers/WAVs enter APK or Git; see [numbered handoff](releases/v0.3.0-dev.20-soulx-language.md).


dev.21 SoulX App接入使用 [中文](SOULX_ENGINE.md) / [English](SOULX_ENGINE.en.md) 中的生产worker构建与两种检查，并在共享输入schema变化后重跑基座 /其他引擎 /API /UI回归。`export_development.py` 分别导出222项契约和95项完整训练生产worker主机证据；`check_repository.py --development` 保留目标13下载候选 /质量 /物理Android /完整Release未通过。This checkpoint registers actual App code, without treating host output or compilation as complete user/device acceptance. See the [numbered handoff](releases/v0.3.0-dev.21.md).

旧LTX源码后续使用 [中文](LTX098_DIT.md) / [English](LTX098_DIT.en.md) 的CPU /Vulkan官方前向检查与ARM64编译命令。开发导出 /仓库检查新增独立DiT与Android编译记录，检查固定精度门槛，并强制训练视频 /App注册 /物理Android /完整管线标记为false。这批研究证据不关闭17号或完整v0.3.0门槛；APK /页面媒体沿用dev.21，不创建Release。See the [numbered implemented/pending handoff](releases/v0.3.0-dev.21-ltx-dit.md).

旧LTX采样后续见 [中文](LTX098_SAMPLING.md) / [English](LTX098_SAMPLING.en.md) / [编号实现与待办](releases/v0.3.0-dev.21-ltx-sampling.md)。开发导出新增独立 `ltx098-sampling.json`，核对111组固定精度门槛、完整训练检查点 /GGUF身份、主机内存采样及两份ARM64 ELF。状态分别记录训练DiT latent host通过与T5 /VAE /视频 /App /物理Android未通过，不能以host证据创建完整Release。Neither trained latent sampling nor a developer conversion closes target17 or the single complete v0.3.0 gate. APK and UI media remain unchanged.

旧LTX T5后续：[中文](LTX098_TEXT.md) / [English](LTX098_TEXT.en.md) / [编号交付与同版待办](releases/v0.3.0-dev.21-ltx-text.md)。导出新增独立text /host /ARM64三份记录；仓库检查核对491检查、76真实子进程、固定精度门槛、完整219张量与外部资产身份、全学习词表 /归一化表、临时F32缓冲及实际计算中取消。`ltx098_t5_host_tested`与Android编译可以为true，但Android执行 /VAE /视频 /App /完整Release仍为false。The older synthetic-caption sampler record retains its original scope; separate T5 host evidence never closes video/phone/quality or full frozen-v0.3.0 acceptance. APK/UI media remain unchanged.
