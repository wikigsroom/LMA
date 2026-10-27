# Changelog / 更新记录

用户可见行为、验证范围和交付文档在此同步。User-facing behavior, evidence, and delivery documentation are maintained together.

## Unreleased / 后续维护

- 2026-10-27：按最新范围补齐[双语需求与发版评估](docs/MULTIMODAL_RELEASE_PLAN.md)和[结构化编号 / 标签](docs/proposals/multimodal-release-scope.json)：01–14 / 16 / 17、12 项基座需求、四版拟定范围、子目标与真机验收；所有模型平级，功能 / 基座依赖 / 兼容 / 许可 / 内容标签独立。Complete bilingual requirements, feasibility, 16-group scope, flat tags, foundation requirements, four proposed releases and device acceptance.
- 撤回画布 / 连线 / 用户节点 / 插件生态 / ComfyUI 导入的交付要求，改为模型选择 → 任务表单 → 本机队列 → 结果；旧 JSON 标为历史不可执行示例。保留推荐；MOSS / SoulX 研究关卡不冒充已支持；APK / 版本 / 媒体 / 已发布附件不变。Withdraw canvas/wiring/user-node/plugin/import requirements; use forms/shared jobs/artifacts, retain historical drafts and recommendations, and keep research gates explicit. No APK/version/media/published-asset changes.

- 2026-10-27：新增可扩展多模态基座双语评估，区分架构 / 引擎 / 硬件后端，说明模型数据与原生代码扩展边界、组件和配方、内部引擎发行、任务 / 产物、现有代码迁移及跨模态完成标准；仍为设计，不改 APK。Add bilingual extensible-foundation assessment covering layers, data/code extension boundaries, bundles/recipes, engine distribution, jobs/artifacts, source migration and cross-modality acceptance; proposal only, no APK changes.
- 2026-10-27：按用户要求将多模态扩展重新评估为全部同一 Android 手机执行，撤回外部推理 / 回退方案并记录长期约束。Reassess every multimodal stage for execution on the same Android phone; remove off-device inference/fallback designs and persist the requirement.
- 修正视频判断：新增 Wan 1.3B Vulkan 与旧 LTX-Video 2B Vulkan / 芯片特定 QNN 的 Android 证据，区分作者手机结果、桌面 CUDA、下载大小和 LMA 实测；补充 Qwen3-TTS Android 示例与许可边界。Correct the video assessment with Android implementation evidence, separate author/desktop/download/device claims, and add Qwen3-TTS Android samples and licensing limits.
- 早期研究（现已由表单 / 队列范围覆盖）：更新纯本地 DAG、组件包、独立模型参数、后台任务 / 恢复提案；用图片旁白与本机 Wan 两份明确不可执行的 JSON 替换混合方案，加入来源记录。Earlier research, superseded by forms/queue scope: revise local DAG/bundle/per-model-settings/background contracts; replace the hybrid example with two non-executable local drafts and a source ledger.
- 同步双语 README / 指南、导航和 v0.2.0 发布后维护说明。当前 APK、推荐、截图 / GIF 和公开附件不变，未新增手机推理结论。Synchronize bilingual documentation and post-release notes; no APK/recommendation/media/published-asset changes or new phone inference claims.

## 0.2.0 — 2026-10-27

**本地模型、HF 发现、本地管理与模型独立参数 / Local models, HF discovery, Local management and per-model settings.** APK versionCode 4; original signing identity preserved.

- 产品文案改为“本地模型”；“推荐”固定保留 `m08 → m06 → m01`、顺序、标签、具体权重和作者依据；原轻量 / 进阶分组保留。Rename product positioning to local models while preserving the exact recommendations and curated groups.
- “全部”和搜索新增 HF 关键词 / 精确仓库 / URL 检索、GGUF / 全格式发现、下载 / 喜欢 / 更新排序与前后分页；原生固定仓库提交，递归分页选择 GGUF 量化文件。Add native HF discovery, sorting, pagination and a commit-pinned quantization picker.
- 新增“本地”栏目，统一管理内置、HF、导入的已下载模型及下载任务；本地搜索、加载、暂停 / 续传、删除。HF 稳定 ID 去重并跨重启保留。Add a dedicated Local manager with durable HF identities.
- 上下文、输出上限、线程、温度、思考和系统提示词迁至“本地”的每个模型设置，独立存储并迁移旧全局值。数值支持可编辑预设；GGUF 上下文、共享输入 / 输出、设备线程和应用温度双重校验，超限自动回填。Store inference preferences per model, migrate legacy globals, and combine editable presets with UI/native bounds and automatic clamping.
- 无审查作为独立标签：已核对作者声明与“无审查 · 元数据”提示分开；普通模型不带标签，也能下载。Make uncensored an optional separate tag with explicit evidence levels.
- 可选 HF 令牌仅发送官方 HTTPS 主机，认证请求不走镜像，重定向到 CDN 时不转发令牌；提供保存 / 清除。Add optional private HF-token preferences and restrict credentials to the official origin.
- 明确单文件 GGUF 文本运行范围；分片、投影器、超限大小及已知非文本任务禁用选择，其他格式可发现来源。State runtime boundaries without equating HF visibility with phone compatibility.
- 修复暂停时断连与工作线程结尾竞争造成 pausing 残留。Finalize cancellation and job retirement under one lock.
- 同步完整双语指南、12 张截图、MP4、4 份 GIF 及公开验证。Synchronize bilingual docs and refreshed media, including the HF-to-Local flow.
- 85 后端 + 45 HF 逻辑 + 25 协议 + 5 SQLite + 66 UI = 226 项桌面断言；另 5 项实时公开 HF Mirror 元数据检查；Lint 0 错误 / 7 警告。226 desktop assertions, five live metadata checks, Lint 0 errors/7 warnings. No phone inference, private-token access or screen-off endurance was tested; prerelease.

## 0.1.2 后续工具维护 / Post-release tooling

- 修复发布工具在 GitHub 按标签查询草稿返回 404 时失败的问题，改用已认证、支持分页的发行列表定位同一草稿。本次首发已用该方式完成附件核验和公开。Resolve draft releases through the authenticated paginated release list; the initial release was successfully finalized using this lookup.
- 仓库检查新增 `--published`：后续文档 / 工具提交核对既有源码附件与发布标签，不改写附件字节。Add post-publication checks against the immutable tagged source rather than requiring later maintenance to overwrite released archives.
- APK 字节、签名、v0.1.2 标签、已公开附件和界面素材不变。同步修改了本维护说明与双语发布流程；行为不涉及 UI，因此无需重录。APK, tag, assets, and UI remain unchanged; bilingual maintenance notes/procedure are synchronized, with no UI recapture needed.

## 0.1.2 — 2026-10-27

**首次仓库预发布 / Initial repository prerelease.** APK versionCode 3. Earlier 0.1.0 / 0.1.1 were local iterations, not historical GitHub releases.

### 功能 / Features

- 14 个内置候选全部核对作者 Uncensored / Abliterated 声明及具体 GGUF 权重；构建强制匹配依据、版本和哈希。All 14 built-ins require matching publisher uncensored evidence and pinned weights.
- 界面显示无审查方式及固定作者说明；修正 Qwen 4B 名称中的 Abliterated 标识，自定义导入显示属性未核对。Visible methods/evidence, corrected Qwen 4B variant label, and unclassified custom imports.
- 模型下载、暂停续传、GGUF / SHA256 校验、本机对话、SQLite 历史及带密钥的 OpenAI 兼容 API。Downloads/resume, integrity checks, local chat/history, and authenticated API serving.
- 无 ROOT 的原生前台服务和 ARM64 CPU 引擎，支持用户开启 LAN、后台设置与可选恢复。Native no-ROOT foreground serving, ARM64 CPU runtime, optional LAN and restoration.
- LMA 不额外添加关键词、云端审核或回复过滤；系统提示词可编辑。No added keyword/cloud moderation or response filtering; editable system prompt.

### 文档与交付 / Documentation and delivery

- 完整中英文 README、使用 / API / 构建 / 架构 / 模型 / 验证 / 真机验收指南，以及双语贡献与发布流程。Bilingual READMEs and supporting guides, contribution and release procedures.
- 7 张实际界面截图、MP4 录屏和 2 份 GIF，持续标注演示桥接与非真机范围。Seven screenshots, MP4, and two GIFs with explicit simulated-state labeling.
- 公开验证记录、版本附件清单、SHA256SUMS、带原生库的源码 ZIP；排除私钥、口令、权重和缓存。Public evidence, manifests, hashes, source ZIP with native libraries; no secrets, weights, or caches.
- 固化后续更新同步代码、双语文档、相关媒体和更新说明后推送本仓库的要求。Standing instruction to synchronize future changes and push matching documentation/release notes.

### 验证与限制 / Validation and limits

- 115 项桌面断言：54 后端、25 协议、5 SQLite、31 界面。115 host assertions; Android framework adapters and UI fixtures are explicit.
- Lint 0 错误、7 条已复核警告；APK 签名、原生库、对齐及目录来源通过相应检查。Lint: 0 errors, 7 reviewed warnings; package/native/alignment/provenance checks pass.
- **0 项真机检查；未实测手机推理、拒答率、tokens/s、温度或锁屏耐久。** Zero physical-device tests; inference, refusal rates, speed, thermals, and endurance remain unmeasured.

详细说明 / Details: [v0.1.2](docs/releases/v0.1.2.md)。
