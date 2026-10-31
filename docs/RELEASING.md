# 更新、同步与发布 / Updating and releasing

上游 safetensors 的 `*.header.json` 按原始字节保留（含 JSON 填充）；`.gitattributes` 仅为这些原始头保留行末填充，大小 / SHA256 核对继续生效。Publisher headers retain exact padding; identity checks remain mandatory.


## v0.3.4 当前发布流程 / Current program-only release

**已发布后的文档维护 / Documentation maintenance after publication:** APK 内容不变时保留 versionName / code 和全部发布附件。更新双语 README、CHANGELOG 与维护说明；只做相关文档 / 工具检查。若修改发布核查工具，运行 `python tools/test_published_source.py`，再用 `python tools/program_evidence.py --export` 更新工具指纹并用 `python tools/check_repository.py --published` 核对当前链接、原标签 Git blob 与原源码 ZIP / 附件。不运行 package/prepare 覆盖已发布文件；不以文档变动触发模型或手机验收。See [README repair](releases/v0.3.1-readme.md).

按用户明确指令仅做程序验证；下文旧完整模型 / 真机运行门槛保留为历史，不能再次作为本版前置要求。完整冻结程序范围不缩减。See [validation policy](PROGRAM_VALIDATION.md), [implementation matrix](IMPLEMENTATION_V034.md) and [release notes](releases/v0.3.4.md).

1. 完成受影响的生产代码、Java/原生合约、队列 / API / 生命周期与有界小图检查；不使用 `--trained`，不下载 / 复制完整模型，不调度 Docker / WSL / 模拟器。Run affected program checks only.
2. 原生模块改变时用现有锁定构建器重新编译 / 打包；`python tools/build.py`、`python tools/verify_package.py`、`python tools/test_android_lint.py` 检查完整签名 APK。Preserve the original signing identity.
3. 页面回归：`node tests/ui-smoke.cjs`。录制：`node tools/capture_workbench.cjs community` 、`node tools/capture_workbench.cjs release-workbench` 与 `node tools/capture_workbench.cjs expansion` 与 `node tools/capture_workbench.cjs multiview`、`node tools/capture_workbench.cjs shape`。使用显式桥接夹具，finally 关闭浏览器。Protect user weights and credentials.
4. 更新双语 README、指南、CHANGELOG、本版说明与当前媒体；旧证据原样归档。`python tools/release_scope.py` 核对完整范围；`python tools/program_evidence.py --export` 核对 当前程序记录、检查数量及源码指纹。
5. `python tools/package_delivery.py` 生成源码 / 验证清单，`python tools/check_repository.py` 检查公开文件、敏感内容、文档链接和源码 ZIP，`python tools/prepare_release.py` 生成哈希核对过的附件白名单。Any source/doc changes after packaging require repackaging; stale evidence fails locally.
6. 精确暂存代码与文档（排除受保护文件和签名材料），普通提交与推送 main。创建并推送未存在的 `v0.3.4` 标签；不 force，不改写旧标签。
7. `python tools/publish_release.py --gh PATH_TO_AUTHENTICATED_GH --publish`。工具要求干净提交、远端标签一致、附件身份一致；先草稿上传，逐项验证 GitHub SHA256，再公开 prerelease。Never overwrite published assets under the same filename.

GitHub prerelease 表示手机与模型质量未验，不表示拆分了功能版本。模型仍为可选用户资产。APK、源码、程序证据、截图、GIF/MP4、发布说明及 SHA256 清单全部同版交付。Historical guidance follows.


**当前验收规则（2026-10-31）：[后续仅做程序验证](PROGRAM_VALIDATION.md) / [Program-only validation](PROGRAM_VALIDATION.en.md)。** 该用户指令覆盖本页下方历史要求中的完整模型、ASR、真机推理及耐久门槛；缺失功能仍需实现，不能改写成已支持。Current dev.45/code49 uses `python tools/export_development.py` and `python tools/check_repository.py --development`, exports fresh program records to `verification/program/`, retains historical model results, and does not run trained models. See [numbered delivery and full scope](releases/v0.3.0-dev.45.md). dev.45 不创建完整 v0.3.0 标签；当前原因是具体代码适配尚未完成，**不是**缺少完整模型运行验证或手机。

下面各开发条目与原 v0.2.0 发布步骤保留历史语境。后续正式版本需以程序验收、完整代码覆盖、原签名、精确源码 / APK SHA、双语文档、媒体身份与更新说明发布，不恢复已取消的模型实跑门槛。

dev.43：[提示、排空与缓存修正](MOSS_DELAY_FIX.md) / [English](MOSS_DELAY_FIX.en.md) / [编号交付与完整待办](releases/v0.3.0-dev.43.md)。官方算法比较、完整权重、实际 Java 业务及手机验收分开；保留原始失败，未改动的页面媒体按精确历史核对，完整 Release 门槛不变。

dev.42：[导入暂停与恢复](MODEL_TRANSFERS.md) / [English](MODEL_TRANSFERS.en.md) / [编号交付与完整待办](releases/v0.3.0-dev.42.md)。当前阻塞输入回归、原生模型及历史 dev.41 Java 模型运行分别留证；保留格式差异、未完成候选和 ASR 失败。App 只更新基座，完整 Release 门槛不变。

dev.41：[MOSS-TTS 1.5 方案](MOSS_TTS15.md) / [English](MOSS_TTS15.en.md) / [编号交付与完整待办](releases/v0.3.0-dev.41.md)。先检查完整显式资产、原生真实采样 / 原始 WAV、生产 Java 绑定和已释放映射，再检查原签名 APK 与页面媒体。已有文件的完整 SHA 接入不替代流式复制或 Android 文件选择器；参考案例触及上限的正常结束失败继续保留。Scoped development evidence never clears the complete v0.3.0 Release gates.

dev.40 的 Wan 参数与诊断修改参照[中文](WAN_DECODER.md) / [English](WAN_DECODER.en.md)：保留旧任务输出、逐模型设置、显式用户资产与原默认内存策略；实际主机 VAE 对照和质量失败不作为完整生成器 / Android 验收。Run relevant native/Java/UI checks, retain original reports and failed gates, and refresh bilingual media.

dev.38：[Z-Image-Turbo 完整流程](ZIMAGE_TURBO.md) / [English](ZIMAGE_TURBO.en.md) / [编号交付与全部待办](releases/v0.3.0-dev.38.md)。实际完整组件与生产 Java、控件 / 界面、原签名 APK / 当前指纹分开核验；按原字节保留 dev.37 的39份报告和状态，所有完整 Release 门槛不变。

dev.35 内部检查点：[Sana 真实组件](MNN_SANA_TRAINED.md) / [English](MNN_SANA_TRAINED.en.md) / [完整待办](releases/v0.3.0-dev.35.md)。先核对完整显式开发资产与生产原生 / Java 训练链路、相同生成源码的 ARM64 构建，再核对签名 APK、控件回归、真实产物媒体及双语文档。主机执行不关闭画质、独立数值或手机门槛；dev.34 的 33 份当前记录与原状态按原提交留存，不发布缩减正式版。

dev.31 历史检查点：[共用运行资源保护](RUNTIME_RESOURCES.md) / [English](RUNTIME_RESOURCES.en.md) / [编号实现与完整待办](releases/v0.3.0-dev.31.md)。仅开发签名包；当前源码回归、主机训练链路、页面夹具和 Android 编译分别留证，完整 Release 门槛不变。dev.30 的 27 份当前记录及原状态按原提交保存在 `verification/history/0.3.0-dev.30/`。以下保留旧 LTX、音频与基座的构建 / 历史说明。

dev.30 历史检查点：[旧 LTX 本地视频闭环](LTX098_APP_FLOW.md) / [English](LTX098_APP_FLOW.en.md) / [编号交付与完整待办](releases/v0.3.0-dev.30.md)。仅原签名开发包；四个原生阶段、实际生产 Java 主机链路、界面夹具与 Android 编译分别留证。原六项数值失败不改写，官方变体 / 质量 / 手机与完整 Release 仍待验收。dev.29 的 22 份当前记录及原状态按原提交留存在 `verification/history/0.3.0-dev.29/`。

旧 LTX 本地构建使用已有锁定源码：`python tools/build_ltx098_app.py`、`python tools/build_ltx098_app.py --android`、`python tools/package_ltx098_app.py`，再执行下述正常 APK 构建 / 验证。生产编排控制为 `python tools/test_ltx098_app.py`；`--trained` 只读取开发者已有完整资产并做全量 SHA 校验，不自动下载。`python tools/ltx098_app_media.py` 从已执行报告生成主机媒体；`node tools/capture_workbench.cjs ltx` 录制明确标记的页面夹具。开发资源不是用户运行前置要求，不能打入 APK。Existing pinned source and explicit local developer assets only; full-model output, UI fixtures and phone acceptance remain separate.

dev.29 新增 [增量音频 / 中文](AUDIO_STREAMING.md) / [English](AUDIO_STREAMING.en.md)。协议子进程、真实小型图、UI 与 ARM64 编译各自留证；训练 Realtime 和 Android 不冒充通过。dev.28 的 21 份原始收据与状态按原提交逐字节保留；不因共用源码变化重复运行历史训练模型。完整 Release 门槛及全部冻结目标不变。


[贡献约定 / Contributing](../CONTRIBUTING.md) · [文档目录 / Documentation](README.md)

当前为 [dev.27 任务恢复、历史与容量](releases/v0.3.0-dev.27.md)，见 [中文](TASK_RECOVERY.md) / [English](TASK_RECOVERY.en.md)；保留 dev.26 运行前检查与 dev.25 生成工作台。当前 APK 需新签名核对和业务回归；旧训练实验按原提交冻结并明确标为历史，不能用于新 APK 的推理验收。`export_development.py` / `check_repository.py --development` 识别 checkpoint/2；完整 Release 导出器及所有模型 / 手机门槛不变。

本轮新增 [LCM 小型原生准备](LCM_LOCAL_PREPARATION.md) / [English](LCM_LOCAL_PREPARATION.en.md)。五份公开 JSON、编译与真实训练主机媒体分别审计；程序未打包，App 接入 / 质量 / 真机仍阻塞。APK 输入 / 字节不变；[编号完整待办](releases/v0.3.0-dev.24-lcm-preparation.md)继续保留完整同版范围。 新 C++ 候选像素门槛仍失败（8 > 5），未提升为产品支持。

本轮新增 [SD-Turbo / 独立 LCM 主机专项](SD_DISTILLED_TRAINED.md) / [English](SD_DISTILLED_TRAINED.en.md)，五份公开 JSON 与真实图像静态媒体纳入开发审计。完整 UNet 数值通过、原生出图或 Java 导入不能关闭 LCM 产品准备、画质、完整官方采样、Android / Release 门槛。See [numbered full pending scope](releases/v0.3.0-dev.24-sd-distilled.md).

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

dev.39 Wan 本地视频：[中文](WAN_VIDEO.md) / [English](WAN_VIDEO.en.md)。CPU 文字 / VAE、Vulkan 扩散、同手机 MP4 使用共用模型 / 参数 / 任务 / 结果基座；四组件用户明确取得，实际 GPU 运算与枚举分开记录。原生 Windows 模型 / FFmpeg、界面夹具、ARM64 编译与未完成的手机 / 画质 / 完整 Release 分开验收；保留全部冻结范围和历史失败。

当前 dev.32：[生图选择与依赖闭环](CURATED_DIFFUSION.md) / [English](CURATED_DIFFUSION.en.md) / [编号实现与完整待办](releases/v0.3.0-dev.32.md)。原签名开发 APK；本轮仅运行相关控制 / 界面检查，训练结果保留历史身份。dev.31 的 28 份当前记录及原状态按原提交完整归档；不为清单 / 界面修改重复运行无变化的训练模型。完整 Release 门槛不变。

SoulX训练参考 /声学重建后续：先显式准备发布者权重，再顺序执行 `python tools/test_soulx_reference.py`、`python tools/test_soulx_trained.py`、`python tools/build_soulx_reference.py`；共享ORT修改需重跑声学244项和ARM64编译。开发导出 /仓库检查同时核对145参考 /253训练重建证据及完整模型未通过标记，绝不凭这些主机 /编译检查发布Release。Trained component execution does not close complete TTS, quality, App or phone gates. See [中文](SOULX_REFERENCE.md) / [English](SOULX_REFERENCE.en.md) / [编号交付](releases/v0.3.0-dev.20-soulx-reference.md).

SoulX语言与完整主机链路后续：显式准备官方权重 /较早社区对照GGUF，按[中文](SOULX_LANGUAGE.md) / [English](SOULX_LANGUAGE.en.md)依次原生构建、完整导出、语言测试、ARM64编译和新文字整链路测试，再导出开发证据 /核对仓库。原始HF BF16 logits、上游RAS /历史、真实取消及完整host链路不能关闭App /语音质量 /物理Android /Release门槛。Complete trained host execution is recorded separately from all complete Android acceptance gates. No weights/tokenizers/WAVs enter APK or Git; see [numbered handoff](releases/v0.3.0-dev.20-soulx-language.md).


dev.21 SoulX App接入使用 [中文](SOULX_ENGINE.md) / [English](SOULX_ENGINE.en.md) 中的生产worker构建与两种检查，并在共享输入schema变化后重跑基座 /其他引擎 /API /UI回归。`export_development.py` 分别导出222项契约和95项完整训练生产worker主机证据；`check_repository.py --development` 保留目标13下载候选 /质量 /物理Android /完整Release未通过。This checkpoint registers actual App code, without treating host output or compilation as complete user/device acceptance. See the [numbered handoff](releases/v0.3.0-dev.21.md).

旧LTX源码后续使用 [中文](LTX098_DIT.md) / [English](LTX098_DIT.en.md) 的CPU /Vulkan官方前向检查与ARM64编译命令。开发导出 /仓库检查新增独立DiT与Android编译记录，检查固定精度门槛，并强制训练视频 /App注册 /物理Android /完整管线标记为false。这批研究证据不关闭17号或完整v0.3.0门槛；APK /页面媒体沿用dev.21，不创建Release。See the [numbered implemented/pending handoff](releases/v0.3.0-dev.21-ltx-dit.md).

旧LTX采样后续见 [中文](LTX098_SAMPLING.md) / [English](LTX098_SAMPLING.en.md) / [编号实现与待办](releases/v0.3.0-dev.21-ltx-sampling.md)。开发导出新增独立 `ltx098-sampling.json`，核对111组固定精度门槛、完整训练检查点 /GGUF身份、主机内存采样及两份ARM64 ELF。状态分别记录训练DiT latent host通过与T5 /VAE /视频 /App /物理Android未通过，不能以host证据创建完整Release。Neither trained latent sampling nor a developer conversion closes target17 or the single complete v0.3.0 gate. APK and UI media remain unchanged.

旧LTX T5后续：[中文](LTX098_TEXT.md) / [English](LTX098_TEXT.en.md) / [编号交付与同版待办](releases/v0.3.0-dev.21-ltx-text.md)。导出新增独立text /host /ARM64三份记录；仓库检查核对491检查、76真实子进程、固定精度门槛、完整219张量与外部资产身份、全学习词表 /归一化表、临时F32缓冲及实际计算中取消。`ltx098_t5_host_tested`与Android编译可以为true，但Android执行 /VAE /视频 /App /完整Release仍为false。The older synthetic-caption sampler record retains its original scope; separate T5 host evidence never closes video/phone/quality or full frozen-v0.3.0 acceptance. APK/UI media remain unchanged.


旧LTX VAE后续：[中文](LTX098_VAE.md) / [English](LTX098_VAE.en.md) / [编号交付与完整待办](releases/v0.3.0-dev.21-ltx-vae.md)。新增独立VAE /host /ARM64三份记录，核对完整132张量、18外部资产、独立参考、精度门槛、顺序装卸与实际ORT计算中取消。`ltx098_vae_executed`仅为主机证据的兼容别名；Android执行 /完整提示词视频 /质量 /App /完整Release仍为false。Earlier DiT, synthetic-caption sampling and T5 records retain their independent scopes. APK/UI media and original signing identity remain unchanged.


旧 LTX 真实提示词串联见[中文](LTX098_PIPELINE.md) / [English](LTX098_PIPELINE.en.md) / [编号交付与完整待办](releases/v0.3.0-dev.21-ltx-pipeline.md)。开发导出新增 tensor / host / ARM64 / pipeline 四份记录，独立核对原始前向门槛、A/B/A 实际训练任务、真实视频媒体与资源范围。本轮 `ltx098_complete_prompt_to_video_host_executed=true`，严格数值验收字段 `ltx098_complete_prompt_to_video_host_tested=false`；兼容字段 `ltx098_trained_video_tested` 明确定义为完整 Android 目标验收，仍为 false。官方多尺度默认 / PixArt 权重身份、画质、App / 手机验收不得由主机视频替代。No new APK, tag or Release is created for this source-only checkpoint; complete frozen v0.3.0 acceptance remains mandatory.

本轮实际状态：`ltx098_complete_prompt_to_video_host_executed=true`，`ltx098_complete_prompt_to_video_host_tested=false`，`ltx098_full_chain_numeric_accepted=false`。163项记录中6项浮点门槛失败，测试必须保留exit 1；开发审计即使通过也只表示失败记录 / 媒体 / 指纹一致，不能签发模型验收或完整Release。The six failed float comparisons remain required work in the same version.

旧 LTX 文本数值[中文定位](LTX098_PRECISION.md) / [English](LTX098_PRECISION.en.md) / [编号交付](releases/v0.3.0-dev.21-ltx-precision.md)包含逐层 / 算子 / 重算记录与来源图。必须交叉核对原生及原始参考最终 SHA、628 原始文件审核、公开指标与图的来源；诊断成功或候选 embedding 改善都不得覆盖冻结完整链路的六项失败。`ltx098_t5_roundoff_repair_accepted=false` 保持，App / 真机 / 全部冻结模型与正式 Release 门槛保持；本轮不改 APK / tag / Release。

候选 `ltx098-text-precision-attention.json` / `ltx098-text-precision-linear.json` 各三次完整T5，不等同完整视频验收。两份 `ltx098-precision-sampling-*.json` 是复核捕获的A轨迹，均未过原0.003门槛并保持exit 1；必须保留partial / reused / no-VAE / no-B-video范围，不能由开发审计成功覆盖失败结论。

旧 LTX [原生资产准备](LTX098_PREPARE.md) / [English](LTX098_PREPARE.en.md)公开转换测试、独立 Windows / ARM64 编译身份与来源图；开发审计需交叉验证完整源 / 输出身份、各进程范围、内存和失败保护。转换不是推理，inspect 不等于完整源校验。组件未进入 APK / App registry；完整链路六项数值失败和全部冻结手机 / Release 门槛继续保持。This source-only handoff creates no new Release or tag.

旧 VAE [原生准备](LTX098_VAE_PREPARE.md) / [English](LTX098_VAE_PREPARE.en.md)增加九图数据分离审计、完整源转换、18 资产独立重读身份和四组原生解码证据；需要重新核对共用 DiT 回归与两类 ARM64 构建。图模板是架构代码，不允许任意学习数据进入模板；开发仓库检查会重新解析全部图。转换 / 解码 / Android 编译均不关闭完整提示词视频六项失败、App 集成、任何冻结目标或真机 / Release 门槛。

## dev.22 准备流程 / Preparation checkpoint

当前内部APK为dev.22/code26，[双语方案](MODEL_PREPARATION.md)及[编号交付](releases/v0.3.0-dev.22.md)记录完整余项。原生准备器/无参数结构图的打包身份、44项核心契约、完整训练转换、UI夹具与Android执行分别记录；公开 `preparation-core.json` / `preparation-trained.json`不能代替手机验收。APK构建相关工具采用 `preparation_build_inputs.py`扩展输入指纹，全部模型数学门槛保持。新的截图62–65、MP4/GIF均标明演示。不得以此内部检查点新建完整v0.3.0 Release，所有冻结门槛仍须通过。

The dev.22/code26 internal APK has separate packaging, host core/trained conversion, UI-fixture and Android scopes. Preparation receipts cannot establish device acceptance. APK tools include preparation sources in their fingerprints; numerical gates remain unchanged. Refresh bilingual docs/media together, preserve original signing identity and publish the complete v0.3.0 only after every frozen gate passes.


Runtime association / 运行模型关联后续需执行 `python tools/test_assemblies.py`，完整训练准备完成后执行 `python tools/test_assemblies.py --trained`；重跑共用队列、API/UI、APK/包/Lint，并导出 `assembly-core.json` / `assembly-trained.json`。完整训练文件关联仅证明主机文件身份、硬链接及缺失依赖暂停，不代替模型生成、Android或正式Release。见[中文](MODEL_ASSEMBLY.md) / [English](MODEL_ASSEMBLY.en.md)。

Nano100M真实训练后续：[中文](MOSS_NANO_TRAINED.md) / [English](MOSS_NANO_TRAINED.en.md) / [编号交付与全部待办](releases/v0.3.0-dev.24-moss-nano.md)。先显式取得11组件和隔离主机ORT，再运行生产C++/Java真实测试、独立原始复核/错误范围标记检查、媒体渲染、开发导出和仓库审计。新增五份公开JSON区分取得/主机构建/训练/Java/原始复核；主机ORT1.28.0不冒充Android1.28.2。APK输入未改，不重建、不创建tag或Release。The user-importable manifest is metadata only; no mandatory model, automatic download or complete target09/quality/physical acceptance is introduced.

编号10三套真实语音后续：[中文](TTS_TRAINED.md) / [English](TTS_TRAINED.en.md) / [编号交付与全部待办](releases/v0.3.0-dev.24-tts.md)。显式取得固定官方主机C API/ORT及全部9对象，依次执行实际生产C++、Java完整导入/worker、原始复核/8项错误范围控制，再渲染原音频/波形媒体、导出五份独立JSON并审计。核对54/1/1音色覆盖、原始请求/协议、每文件SHA和随机A重复的实际结果；Windows不通过Android liblog路径。APK输入未改，仍原dev.24字节，不新建tag或Release。Current host evidence cannot waive per-component license review, speech quality, physical-phone execution/endurance, any frozen model or full-version release gates.


编号11真实Qwen后续：[中文](QWEN_TTS_TRAINED.md) / [English](QWEN_TTS_TRAINED.en.md) / [编号交付与全部待办](releases/v0.3.0-dev.24-qwen-tts.md)。显式取得两个固定GGUF，运行原生Windows生产源码、Java完整导入/真实worker、独立原始复核/8项错误范围控制，再渲染原始语音/波形媒体、导出五份JSON并审计。核对18WAV/12控制、94项Java/6子进程、145文件/31协议/22WAV/2对象；保留30秒贪心预算样例及质量/结束原因未验收。APK输入/字节未改，不建tag或Release。All complete-v0.3.0 model, quality, physical-phone, endurance, upgrade and asset-control gates remain mandatory.

完整 SDXL / 双架构 LoRA 后续：[中文](SD_VARIANTS_TRAINED.md) / [English](SD_VARIANTS_TRAINED.en.md) / [编号全部待办](releases/v0.3.0-dev.24-sd-variants.md)。显式取得固定五新对象，复用既有 SD1.5 / 词表，依次执行实际生产 C++、LCM 权重反事实、Java 全量导入 / 实际 worker、独立原始复核 / 九项错误证据控制，再渲染原始 PNG / 联系图 / 静态 GIF / MP4、导出五份 JSON 并审计。逐项核对真实 sampler 步数、原始请求 / 协议、每文件 SHA 与零强度 / 启用 / 恢复关系；LCM 强度 0 仅为原生诊断，不是用户配方。Production/APK inputs and bytes stay unchanged. Preserve observed low-step quality failures and every SD-Turbo, independent LCM checkpoint, phone, license, endurance and full-version gate; do not tag or publish a reduced Release.
