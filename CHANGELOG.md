# Changelog / 更新记录

## 未发布 / Unreleased — v0.3.6 开发中

- F5 官方兼容前端：固定 jieba DAG / HMM、pypinyin 多音字 / 变调及 F5 词元 / ID，2,222 文本 / 6,671 项真实 C++ 对照；新语言资产配方由用户明确选择，旧配方保留。No dictionaries or weights in APK.
- Hunyuan3D Paint 本机完整程序路径：PNG＋GLB、六视图条件、DINO / VAE、双材质 / 多视图 UNet、UniPC、RealESRGAN、xatlas 与 PBR GLB；独立 CPU 光栅 / 最近可见纹理填充的差异明确披露。Offline five-graph conversion, real checksums and actual CLI checks use random architecture fixtures, not trained models.
- UltraTex 所需 BSA 加入签名内置 CPU / ONNX：smooth-K 分块选择、FP32 / BF16、在线 softmax、有界资源和原源码选择对照；47 项检查。This is a shared operator, not a complete UltraTex adapter.
- UltraTex 补齐固定 FLUX.1 dev / FLUX.2 网络转换、动态前景 / 原位置、双精度来源的精确 RoPE 表和严格 LoRA 合并；101 项检查覆盖实际源码网络、生产 C++ ORT、两种真实转换 CLI 和旧导出不覆盖。Flow components only; complete on-phone text/VAE/sampling/application orchestration remains missing.
- 开发范围52模板 / 82包 / 17扩展引擎加文本；原推荐与全部冻结范围保留。独立参数 / 归位、输入角色、导入、预检、草稿、幂等、子进程取消 / 清理和队列复用；新增34页面检查和6截图 / GIF / MP4；PBR预览验证实际像素、UV、金属 / 粗糙度、旋转和资源回收。
- 中英 README 保留原有案例，新增 C31–C36；详细前端 / 材质指南、完整编号待办、当前开发证据与原发布证据分开。Correct stale completion guidance: program-only validation no longer requires a phone or full-model runs.
- 当前程序验证37组 / 13,076项，UI687；三个实际发布入口在缺代码时拒绝操作，9项回归确认67个原发布文件未改。原签名APK、独立包检查与Lint0错误 / 16既有警告同步。No trained-model runs, virtual machines or device claims.
- **D04 / D05 / D08 / D09 / D10 与已披露子集之外仍缺实际实现；没有发布“全部适配完成”Release。** New APK identity is code56 / 0.3.6; preserve original signer and immutable v0.3.5 assets. Release preparation rejects these missing-code gaps. See [开发交付 / Development notes](docs/releases/v0.3.6-development.md).

## 0.3.5 — 本地形状精修与稀疏运算基座 / Local shape refinement and sparse CPU foundation

- 新增配套 ONNX CPU Hunyuan3D 2.1 形状与 UltraShape 1.0 精修；DINO、真实 MoE 路由、voxel RoPE / masked 条件、VAE cache / query、SDF / GLB 全部同一手机。UltraShape uses explicit PNG + coarse GLB, area/sharp-edge sampling and float16 positions. Paint is not implemented.
- 离线 safetensors / weights-only PT 导出、真实文件 SHA256 清单、五个必需组件及 data；两条平级自选配方，无伪造公开整包下载。50 templates / 82 bundles / 17 extensions plus text; model assets remain explicit user choices.
- 五个编译内置 sparse CPU / ONNX 运算，保留 UniForge / SAM 不同池化与细分规则。109 native comparisons; these are shared building blocks, not complete SAM/UniForge/SUPRA adapters.
- 复用 Local、逐模型归位、PNG / GLB 角色、预检、草稿、幂等、队列、取消与原子结果；修正 App 快照遗留的旧版本号。原冻结 F01–F12、01–14/16/17、九个 MOSS、SD1.5/SDXL LoRA 与推荐保留。
- 30 组 / 5820 程序项；专项188 / 图60 / sparse109、扩展533、UI653。原签名 code55、40库 / API28 / 16 KiB、Lint 0错误 / 16保留警告；zero complete trained models downloaded/copied/run, no phone inference/endurance claim.
- 双语详细方案与30使用用例，保留H01–H18；30截图 / 6GIF / 6MP4。v0.3.4 的38 JSON / 40媒体文件按原Git blob归档。D04/D05/D07 Paint/D08/D09/D10与F5中文完整前端仍缺实际适配，完整待办不隐藏。

## 0.3.4 — 本地 RF 形状与部件几何 / Local RF Shape and part geometry

- 新增 TripoSG / PartCrafter 物体 / 场景匹配 FP32 ONNX CPU：DINOv2、RF / 部件 DiT、SDF VAE cache / query、均匀网格提取与多部件 GLB，全部阶段同一手机。No remote fallback, texture or auto segmentation claim.
- 离线 safetensors 转换与真实哈希清单，五必需角色及 data 校验导入；尚无核实公开配套 ONNX 下载包，不虚构一键下载。Three custom recipes; 48 templates / 82 catalogue bundles / 16 extensions plus text.
- 复用本地模型、独立可编辑归位、PNG、预检、草稿 / 恢复、共用队列、幂等、取消和原子结果导出；保留原推荐与完整冻结范围。No model or auxiliary learned data bundled or automatically acquired.
- 27 组 / 5,306 项程序检查，RF 专项161、Java 共用扩展428、完整 UI633；原签名 code54，39 库 / 16 KiB / API28，Lint 0 错误 / 16 保留警告。Zero complete trained-model downloads/copies/runs; full trained export and phone quality remain untested.
- 中英 README 保留历史并扩展到 27 用例 / 27 测试组；25 当前截图 / 5 GIF / 5 MP4，v0.3.3 的36 JSON / 四组媒体按 Git 原字节归档。D04–D10 七配置 / 六组仍需原生移植；D11/12/15/16 为形状子集。[完整编号实现与待办 / Delivery](docs/releases/v0.3.4.md)。

## 0.3.3 — 本地多视图 3D 与诊断 / Local multiview 3D and diagnostics

- 新增真正 Pixal3D MV CPU / ARM64、四张 RGBA PNG、标准转台 / 自定义相机、独立参数、草稿、预检、共用队列与 GLB。Actual feature projection/fusion, not repeated single-image generation; all stages remain on the same phone.
- 四个 F16 / Q8_0 几何 / PBR 平级包，按发布者固定清单校验导入；尚无已核实公开权重下载端点，不伪造一键下载。Generic HF MV recipe supports explicit compatible component selection. 82 bundles / 45 templates / 15 extensions plus text; original recommendations and frozen scope remain.
- 新增支持 worker 的阶段耗时 / 进程 RSS、失败后执行观察持久化与合并身份保护；主动导出的最近 64 条任务诊断采用字段白名单。Power/background/notification states are visible; no automatic upload or endurance claim.
- 完整程序 26 组 / 4,940 项、页面 616 项、38 原生库 / 16 KiB / 原签名，Lint 0 错误 / 16 警告。Zero complete trained-model downloads/copies/runs, no phone, emulator or virtualization.
- README 中英正文保留历史案例并扩展至 24 个用例 / 26 组检查；修正过时构建与验证说明，20 当前截图 / 4 GIF / 4 MP4；v0.3.2 原始证据与三组媒体按 Git 原字节归档。
- 固定源码复核其余测评 9 条配置 / 8 组家族，明确记录实际原生移植缺口，不把登记或补测视为支持。[编号实现 / 待办与附件 / Numbered delivery](docs/releases/v0.3.3.md)。

## 0.3.2 — 语音与本地生 3D / Speech and local 3D

- 新增 Kokoro INT8、MeloTTS Chinese INT8 / FP32、F5-TTS v1、OmniVoice Q8 / 原版六个可选语音包；匹配 ONNX、原版 safetensors 或 GGUF，不直接执行任意 PyTorch `.pth`。Add matched local workers and external frontend resources; all downloads remain explicit.
- 新增 TRELLIS.2 / Pixal3D 单图 CPU 后端与五个可选包，接通图片、独立参数、预检、草稿、队列、取消、GLB 校验 / 预览 / 导出。Assess all 16 benchmark cases; multiview and other unported pipelines remain explicit limitations.
- 保留原推荐和完整既有范围；44 模板、78 包、14 扩展引擎＋文本。No model weights, voices, tokenizers or dictionaries are bundled; no remote inference or virtualization.
- 新增 173 项专项程序检查与 32 项页面交互；更新原有回归、原生 ARM64、原签名 APK 与全部媒体指纹。No complete-model runs or phone acceptance; F5 Chinese and large 3D resource limits remain documented.
- 保留完整中英 README 并扩展到 22 个场景 / 25 组测试入口；新增双语方案、逐项测评来源、截图 / GIF / MP4、原版 v0.3.1 证据归档及[本轮编号交付 / 待办](docs/releases/v0.3.2.md)。

## v0.3.1 文档维护 — README 完整性修复 / README completeness repair

- 恢复中英 README 正文中的 18 个操作用例、4 组 API 示例、18 组历史案例与 24 组程序测试覆盖表；补回原图、WAV、GIF、MP4、失败对照、精选文本候选、Z20 起步配置及排错。Restore detailed scenarios, integration examples, generated artifacts and explicit test/failure evidence.
- 修正过时的 23 套目录表述：现有 23＋社区 44＝67 套；模板、模型包、引擎计数分别说明。Distinguish current program records, historical host outputs and unperformed phone acceptance.
- 修复程序发行版本的 `check_repository.py --published`：维护文档后按原发布标签逐文件核对源码 ZIP 的 Git blob、SHA256、大小及附件白名单，拒绝篡改或漏项，不覆盖已发布文件。Add 14 isolated audit regressions; no complete models, devices or browsers.
- APK 仍为 v0.3.1/code51，已发布 16 项附件、标签与历史媒体原样保留；[本次双语维护说明](docs/releases/v0.3.1-readme.md)。Documentation/release-audit maintenance only; no new APK.

## 0.3.1 — 社区模型与内容标记 / Community models and content labels

- 新增 14 系列 / 44 个可选 checkpoint（生图 30、视频 14），总登记 67 套；28 个明确 NSFW 来源标记、1 个 HF 敏感标记、15 个未标注。Video counts represent 14 versions of one Wan 1.3B series.
- 独立内容依据、HF 提示与自选配方标签保留；全部 / 搜索 / 本地组合筛选、离线登记目录、来源 / 许可 / 组件详情。Preserve Recommended m08 → m06 → m01 and explicit user-controlled downloads/settings.
- 精确 Range 文件头与固定 API / 模型卡身份，Pony 镜像许可冲突和不适配视频架构明确标记。Reuse local SD1.5/SDXL CPU and Wan 2.1 T2V 1.3B Vulkan routes; no implicit weight downloads or remote inference.
- 24 组 / 4,438 项程序检查，564 项页面回归；原签名 code51、35 原生库、API28 / 16KiB、Lint 0 错误。No complete trained models or physical phones used.
- 双语指南、44 文件列表、10 当前截图、2 GIF / 2 MP4；v0.3.0 程序 / 媒体原样归档；[完整更新说明](docs/releases/v0.3.1.md)。

## 0.3.0 — 本地多模态基座 / Local multimodal foundation

- 完整同版程序集成 F-01–F-12、既有文本、01–14/16/17、MOSS 九子目标及 SD1.5/SDXL LoRA；38 配方、23 模型包、12 扩展引擎。Complete frozen program scope in one release.
- 原始 PixArt F32 T5、原始 SentencePiece、学习型空间放大 / AdaIN、旧 LTX 0.9.8 固定 7+3 阶段与手机 AVC 接入；Google Q5 单尺度保留独立身份。Model-free graph packaging and explicit user-selected dependencies.
- 程序回归 23 组 / 3,590 项，页面 530 项；35 原生库、API28/16KiB、原签名、Lint 0 错误。Program-only validation follows the user's updated policy; zero complete model downloads/copies/runs and no phone/quality/endurance claims.
- 重整双语 README / 文档索引，9 张当前截图、2 GIF / 2 MP4、完整实现矩阵、历史证据归档、源码与可审查验证附件。See [release notes](docs/releases/v0.3.0.md).


## 0.3.0-dev.45 — Sana-Sprint 本地文生图 / Local text-to-image

- 新增具名 Sana-Sprint 0.6B MNN 配方，14 个固定组件 / 约 6.29 GiB 由用户明确选择、下载、导入；APK 不附模型或词表。Separate from Sana Edit/ordinary Sana; preserve original recommendation order and independent user assets.
- 实现同手机 SentencePiece、按行 embedding、四段 Gemma2、SCM / DiT、DC-AE、PNG 与共用任务 / 取消 / 参数快照；1024²、1–4 步等约束分别标明导出和应用来源。Engine-owned input rules hide unsupported negative conditioning and enforce the same restriction at the API boundary.
- 448 项 Sana 程序检查、25 分词用例、10 采样数学步骤、两个微型图；20 组共 2,975 项程序回归。No complete weights downloaded/copied or complete model/image generation executed; no new phone/quality/endurance claims.
- 原签名 dev.45/code49，35 份原生库与 API28 / 16KiB 包核对；新增 4 张当前页面截图、GIF / MP4 和 19 项 Sana UI 交互。Browsers close after checks; historical dev.44 program evidence and dev.42 recordings retain their original identity.
- [中文方案](docs/SANA_SPRINT.md) · [English guide](docs/SANA_SPRINT.en.md) · [本轮实现与完整待办](docs/releases/v0.3.0-dev.45.md)。Sana 匹配移动文生图代码已接入；旧 LTX 官方 PixArt / 多尺度代码阻塞仍在同一个完整 v0.3.0 内处理，后续仅做程序验证。

## 0.3.0-dev.44 — 程序验证与导入取消 / Program validation and import cancellation

- 按 2026-10-31 用户指令，后续仅做程序验证；不再重跑完整模型、ASR 或耗时推理，不将未实现适配或历史失败改为通过。Record the explicit override of older full-model/device gates in a bilingual policy and machine-readable manifest.
- 用原生产代码复现并保留“等待打开文件时暂停仍阻塞队列”的失败；共用 `InputHandle` / Android `DocumentInput` 支持打开前取消、取消信号、读取关闭与迟到资源释放。Cancellation covers bundles, legacy text models and media imports.
- 22 项阻塞模型包输入、15 项实际 Android 桥接源码逻辑、138 项后端、701 项基座检查通过；夹具和 Android 编译分别记账，不运行完整模型。Original failure and historical model/media records remain unchanged.
- 原签名 dev.44/code48；模型仍由用户自主选择、下载、导入和管理；推荐、HF 全部 / 搜索、本地、逐模型参数保留。Unchanged dev.42 page recordings retain their original identity; current UI regression is separate.
- [验证规则 / Policy](docs/PROGRAM_VALIDATION.md) · [English](docs/PROGRAM_VALIDATION.en.md) · [本轮编号实现 / 完整待办](docs/releases/v0.3.0-dev.44.md)。正式 v0.3.0 的未实现代码继续收口，完整模型及手机耐久验证不再列为程序发版前置项。

## 0.3.0-dev.43 — 共用语音引擎修正 / Shared speech corrections

- 官方 Delay 普通提示 7/7、状态机 5/5；修正同一步排空递增、截断帧数和用户参考片段误提取，保留原始失败。Official method parity is scoped separately from trained output and Android acceptance.
- 参考编码完成后释放 CPU 批处理临时缓存；21 项真实分配器检查、7 次实际计算，独立流式图 / 持久权重 / 重复输出保持正确。Allocated buffer bytes are not resident-memory measurements.
- 完整模型执行记录实时事件；530 项 MOSS、306 项 RQ 回归通过。旧 PCM 比较继续记录，提示 / 状态语义修正后不把旧 WAV 字节相同作为新实现正确性条件；正常结束、取消与恢复门槛保留。
- 71 项实际生产 Java 检查 / 4 次运行、2 个 WAV 与直接输出逐字节一致；完整原生 5 个 WAV / 6 项控制保留参考模式 375 步截断及新 ASR 36/2 词错误。Publish original WAVs and actual-host waveform PNG/GIF/audio MP4; original 35/2 failure remains separate.
- 原签名 dev.43/code47；App 不附模型、不自动取得或替换权重，模型继续用户自主选择 / 下载 / 管理。保留 dev.42 的精确页面媒体并检查 UI 逻辑不变；界面 490 项通过，Lint 0 错误 / 17 警告。
- [中文](docs/MOSS_DELAY_FIX.md) · [English](docs/MOSS_DELAY_FIX.en.md) · [本轮实现与完整待办](docs/releases/v0.3.0-dev.43.md)。所有冻结模型、子目标与同手机验收仍属于同一个完整 v0.3.0；本检查点不发布正式 Release。

## 0.3.0-dev.42 — 导入暂停与队列 / Import pause and queue

- 暂停或关闭时关闭实际本地输入，释放阻塞读取与后续队列；防止登记竞态，完整 SHA 接纳、用户显式传输、重启暂停及逐模型设置保留。Pause/shutdown close the actual input and release the queue while retaining full SHA acceptance and user ownership.
- 冻结旧失败；13 项阻塞输入、692 项基座、68 项 API 通过。本地显式重选后重复制未完成组件；HTTP 保留校验续传。Android providers and full-size stream copying remain open.
- 官方提示对照存在额外 audio_start 行；实际候选 1800 秒到 332/375 步，无 WAV、未采用。离线 ASR 两控制通过，原参考 WAV 35/2 词错误；EOS / 文本遵循继续失败。No diagnostic clears quality/Android gates.
- 原签名 dev.42/code46，APK 61,342,218 bytes，SHA `fda9fbe41bcbf6ae4abb6eee6d8c88fe3e2ccab233792f0dab00bb6d974ae79b`。dev.41 的 44 份报告及状态原字节归档；原生 MOSS 不变，87 项 Java 模型运行及实际媒体明确历史。
- [中文使用](docs/MODEL_TRANSFERS.md) · [English](docs/MODEL_TRANSFERS.en.md) · [独立诊断](docs/MOSS_REFERENCE_DIAGNOSTICS.md) · [编号实现与全部待办](docs/releases/v0.3.0-dev.42.md)。完整 v0.3.0 不拆分，本检查点不创建正式 Release。

## 0.3.0-dev.41 — MOSS 本地语音 / Local MOSS speech

- Add an optional, complete pinned MOSS-TTS 1.5 Q8/BF16 pair; explicit user download/import, independent settings and lifecycle. APK remains free of learned assets.
- Report actual sampled steps, EOS versus output-limit truncation, audio decoding and final parameter/seed/audio telemetry.
- Privately map required CPU weight ranges, retain tensor bytes and original user files, and release every mapping with the model. Add real GGML numerical, private-write, >4 GiB offset and cleanup contracts.
- Show an incomplete-output notice when opening a limited result from tasks or artifacts; clear it for natural completion, retain original provenance and require an explicit user retry. Preserve the actual reference-case natural-EOS failure.
- 新增可选完整 MOSS-TTS 1.5 用户资产，接通实际进度、独立参数与结果记录，优化 CPU 权重加载；达到输出上限时提示内容可能不完整。参考模式未自然结束，保留失败与原始产物，不自动重跑或替换用户模型。
- Verify the actual production Java/native flow: 87 checks, five children, three original WAVs, zero network calls, explicit full-SHA existing-file adoption and exact direct/Java outputs. Retain the separate 900-second stream-copy timeout and failed reference natural completion.
- Preserve prior trained and failed-quality evidence; retain all targets in the same complete v0.3.0 scope.
- [中文方案](docs/MOSS_TTS15.md) · [English workflow](docs/MOSS_TTS15.en.md) · [本轮实现与完整待完成事项](docs/releases/v0.3.0-dev.41.md).

## 0.3.0-dev.40 — Per-model video decoding / 视频解码业务收口

- 修复共用原生进度节流丢失快速采样首个完成步骤的问题；新阶段、首个已完成步骤和最终进度及时转发，其余保持节流。Add real child-protocol regressions and repeat actual Java/native sampler cancellation with the production fix.
- Wan 新增空间分块大小和实验性时间分段，补齐配方生成、已有安装 schema、独立设置、不可变任务、原生校验和实际结果链路；默认保留128 / 时间分段关，旧任务精确 SHA 回归。
- Preserve user assets and model-free upgrades. Five retained full-geometry experiments plus unchanged official CPU F32 VAE decoding reproduce later artifacts; preserve original failures and compilation provenance, without a quality/resource/phone pass.
- 同步原签名开发 APK、双语完整操作 / 诊断、全部受影响截图 / GIF / MP4、当前业务回归与 dev.39 原字节归档。所有冻结目标仍归同一完整 v0.3.0，未发布缩减 Release。

[中文](docs/WAN_DECODER.md) · [English](docs/WAN_DECODER.en.md) · [Numbered delivery and full pending scope](docs/releases/v0.3.0-dev.40.md)

## 0.3.0-dev.39 — Local Wan video / 本地视频业务

- 增加完整 Wan 2.1 T2V 1.3B Q4 四组件可选方案，共4,741,874,667字节；全部 / HF / 本地、独立可编辑参数、显式下载 / 导入、共用任务、取消恢复和结果管理沿用基座。App不含权重或分词数据，保留推荐与用户资产。
- Add a distinct pinned Vulkan worker: CPU UMT5/VAE, Vulkan diffusion, a completed non-host GPU matrix-operation check and actual execution provenance. Reject unavailable/mismatched backends; no RPC, external inference or automatic CPU fallback. Production Android uses same-phone MediaCodec; native Windows FFmpeg is a labelled test port only.
- 新增精确四角色 HF 文件建议与量化歧义检查、真实生产页面截图 / GIF / MP4、双语使用 / 复现说明和原签名 ARM64 开发包。具体检查、实际产物和限制见编号交付。
- Preserve exact historical dev.38 and earlier trained reports, including failed LCM/Sana/LTX gates. Host operation and ARM64 compilation do not establish numerical, video quality, physical-phone or complete Release acceptance. All original targets remain in one v0.3.0 scope.

[中文方案](docs/WAN_VIDEO.md) · [English guide](docs/WAN_VIDEO.en.md) · [Numbered implemented / full pending](docs/releases/v0.3.0-dev.39.md)

## 0.3.0-dev.38 — Complete Z-Image business / 完整Z-Image业务

- 新增完整Z-Image-Turbo四组件可选方案（6,349,991,011字节），接入全部/HF/本地、显式下载/导入、独立八步配置、不可变任务、取消恢复与结果管理。原始匹配编码器和完整官方VAE；内容哈希复用不触发自动安装，App仍只交付基座。
- Add six checked suggestion cases for complete roles, explicit application, quantization ambiguity, base/encoder mismatch, FLUX.2 VAE exclusion and incomplete inventory. Preserve all shared lifecycle/settings/queue behavior and exact source attribution.
- 实际原生及生产Java完整训练模型链路，真实PNG/MP4/GIF、八张相关页面截图与十组业务录制、双语完整文档；签名dev.38/code42 APK和既有17项Lint警告如实留证。主机不替代完整数值、画质、资源、手机与Release验收。
- Preserve dev.37 reports/status byte-for-byte and retain all earlier experiments, failures, selected models and full-v0.3.0 gates. No formal Release or scope reduction.
- [完整更新与所有待办 / Changes and full pending scope](docs/releases/v0.3.0-dev.38.md) · [中文方案](docs/ZIMAGE_TURBO.md) · [English](docs/ZIMAGE_TURBO.en.md)。

## 0.3.0-dev.37 — Complete local FLUX flow / 完整本地 FLUX 业务

- 新增 FLUX.2-klein 4B distilled 完整四组件（5,127,452,603 字节）可选目录及 HF 配套建议；全部 / HF / 本地、独立参数与上限归位、不可变任务、真实采样取消 / 恢复、PNG 来源、重启及删除模型后保留结果接通共用业务。App 仍只更新基座，所有资产由用户显式选择取得，不附模型或自动下载。
- Correct the shared Qwen merge-header and NFC handling without changing installed user files or the pinned upstream checkout. Independently compare all 151,643 base IDs, 26 added IDs and 33 multilingual/Unicode inputs across three file representations with the official Rust tokenizer: 117 checks.
- Complete trained native Windows CPU and production Java execution; preserve changed-prompt/step effects, exact recovery, actual child cancellation and the original failed-semantic diagnostic. Source/host evidence does not establish complete numerics, quality, resources or phone acceptance.
- 原签名 dev.37/code41 ARM64 APK、双语完整指南与更新说明、十组业务页面录制和实际 PNG / MP4 / GIF；原字节归档 dev.36 的 39 份记录与状态。推荐 m08→m06→m01、全量冻结范围、既有失败及正式 Release 门槛保持。
- Full details / 完整更新与所有待办：[v0.3.0-dev.37](docs/releases/v0.3.0-dev.37.md) · [中文方案](docs/FLUX2_KLEIN.md) · [English](docs/FLUX2_KLEIN.en.md)。

## 0.3.0-dev.36 — Local image-edit business flow / 本地图片编辑业务闭环

- Correct the matched Sana model's task from generic text-to-image to fixed-style image editing, based on pinned official application sources. Preserve the legacy declarations, files, settings, jobs and failed gray outputs; the original frozen text-to-image target stays pending.
- 完整 15 组件（1,661,730,284 字节），共用素材导入/必选图片/固定提示词/独立参数/不可变任务/实际采样取消/恢复/结果保存及重启读取。无模型数据进入 App，无自动下载或远程推理。
- Bound actual PNG/JPEG bytes/pixels and decoded images; correct Android decode-failure handling. Deliver oversized-upload errors before bounded stream closure, preserving the 256 KiB body limit.
- 双语指南、原始输入和实际结果、带标记 MP4/GIF、更新页面截图、原签名 dev.36/code40 APK；原样归档 dev.35 的 39 份记录及状态。所有原数值失败、冻结范围与手机/正式 Release 门槛保持。

## 0.3.0-dev.35 — Sana real execution / Sana 真实运行

- 使用完整 13 组件（1,505,181,194 字节）执行实际生产 C++ 与 Java 导入 / 独立参数 / 不可变任务 / 采样取消 / 恢复；资产不进入 App。
- 修复固定 batch Qwen 的 CFG 编码、浮点 additive mask、实际完成步回调、单步除零与图像写入状态；主机和 ARM64 使用相同生成源码。
- Publish exact original outputs, labelled MP4/GIF, bilingual guides and original-signed dev.35/code39 APK. Preserve exact dev.34 records and old numerical failures. Observed missing-subject quality, independent reference numerics, physical Android and complete frozen v0.3.0 Release remain open.

## 0.3.0-dev.34 — companion-file review / HF 配套组件确认

- Add generic pinned-revision metadata inventory, filename/sibling-path proposals and explicit confirmation. 35 套配方中 19 套提供 49 条数据提示，不按模型 ID 新增页面或队列分支。
- Keep review, apply, declaration and model download separate; preserve manual choices. 歧义、重复角色与未完整目录不自动选择，不隐式下载或覆盖。
- Add native review tokens, binding fingerprints, stale/cancel/error recovery. Existing model IDs/manifests remain identical when only matching hints change; compared against exact dev.33 templates.
- Add 57 production client/controller/store checks and 16 UI checks; rerun current HF80/backend98 controls and related regressions. 当前 18 套 / 2,634 项检查；元数据 / HTTP 夹具，不代表训练模型或手机推理。
- Update original-signed dev.34/code38 APK, bilingual docs, four screenshots, MP4/GIF. Preserve dev.33 exact29 receipts and older trained/numerical failures; complete single v0.3.0 and phone gates remain open.


## 0.3.0-dev.33 — local voice selection / 本地语音选择闭环

- Add complete optional Nano 100M All profile: eleven pinned files, 717,414,286 bytes, fresh immutable ID. 原导入与设置不变，App 不附模型或预设声音数据。
- Read names/counts from exact local ONNX/Nano metadata without loading weights; Kokoro 54 voices (ID53 em_santa), Nano18, Piper/Matcha numeric fallback. 名称不扩展英文配方的语言范围。
- Add shared editable named numeric suggestions, actual-limit clamping, numeric API/job snapshots and engine schema dispatch. 无按模型 ID 分裂的页面 / 队列流程。
- Add 70 production Java checks including four full-SHA local headers under 48 MiB heap and 20 UI checks; current 15 suites / 2,383 controls. 真实文件检查不是推理，未重复旧训练模型或冒充手机验收。
- Update bilingual READMEs/guides, four labelled screenshots, MP4/GIF and original-signed dev.33/code37 APK. Retain exact dev.32 receipts and older failed numerical evidence; full v0.3.0 scope remains required.


## 0.3.0-dev.32 — explicit diffusion model selection / 生图选择与依赖闭环

- Add six immutable All profiles: SDXL, SD 1.5/SDXL style and LCM LoRAs, SD-Turbo. 六套完整资产逐项固定 revision、URL、字节与 SHA，既有十项清单保持原样。
- Add generic base review, install/transfer state and return navigation in LoRA details and missing-base pairing. 下载与导入始终由用户分别明确选择。
- Bind new SD 1.5 LoRAs to the actual shipped base ID; preserve older imports/settings/jobs through fresh identities. 同时保留旧 SDXL / SD 1.5 导入身份兼容。
- Add 55 production storage/upgrade/pairing checks and 40 UI checks across all four adapters. 上限回填、模型设置独立与冻结队列请求分别验证。
- Verify historical asset locks/receipts by SHA during metadata-only builds; retain dev.31's 28 original records. 本轮未重跑训练模型，历史输出不作为当前 APK / 手机证据。
- Synchronize bilingual guides/READMEs, four labelled screenshots, MP4/GIF and original-signed dev.32 APK. 所有冻结目标、LCM / LTX 原数值失败、Android 与完整 Release 门槛保留。

## 0.3.0-dev.31 — shared runtime resource protection / 共用运行资源保护

- Continuous public Android resource observations cover the load/chat/API/job execution slot; stop on severe thermal status, OS low memory or a 64 MiB storage floor. 公开系统信号约每 2 秒采样，Android 9 温控保持未知，不重复扣除已加载模型内存。
- Exact child ownership, stale-probe rejection and stop/release race handling preserve the shared queue. 多阶段引擎逐次绑定子进程，保留真实停止原因。
- Bounded reports commit atomically with task terminal states and successful artifact provenance; explicit retry retains previous requests and records. 任务与结果保存有界摘要，重试创建新任务。
- Chat preserves partial replies; text stops disable automatic restart; API interruptions do not become successful EOF. 聊天 / API 复用同一保护。
- Tasks and details expose readable reports; bilingual guides, 3 screenshots, recording and GIF document the flow. 当前界面夹具与真实 Android 测量明确区分。
- Current signed APK and regression receipts preserve original signing identity and historical evidence. All frozen targets, numerical/quality failures and Android/full Release gates remain open. 不拆分完整 v0.3.0 范围，不自动下载模型。

## 0.3.0-dev.30 — old-LTX local video business flow / unreleased

- 新增生产旧 LTX 适配器：顺序 T5 / Vulkan 八步 DiT / 九段 VAE / RGB / 手机 MediaCodec，与共享模型租约、队列、取消、结果提交和来源记录整合。Sequential owned local stages share existing lifecycle and artifact services.
- 新生成变体使用独立 ID；旧资产记录与设置不可变，用户明确准备、关联并选择缺失依赖，不自动获取模型。Explicit user-controlled association preserves installed records.
- 新模型配方与独立可编辑参数、超限归位、完整提示词、固定八步及任务快照；Android ARM64 四个组件使用代码与共享库，无模型权重。Model-scoped video forms and model-free native packaging.
- 真实生产队列的成功 / 错误收据 / 错误输出 / 编码失败 / 取消 / 中断检查，完整训练主机链路与 Android 编译分别记录；同步原签名开发包、双语文档、截图 / MP4 / GIF。Original numerical failures, official variants, quality and Android gates remain required in one complete v0.3.0. [中文](docs/LTX098_APP_FLOW.md) / [English](docs/LTX098_APP_FLOW.en.md) / [编号与完整待办](docs/releases/v0.3.0-dev.30.md).


## 0.3.0-dev.29 — incremental audio business flow / unreleased

- MOSS Realtime 非 EOS 编码帧直接进入有状态 codec，逐帧输出 PCM16 并保留完整 WAV；不等待文件完成后再切片。Actual stateful frame decode with final sample agreement.
- 流式试听默认关闭，设置随模型与不可变请求保存；固定增益用于试听及最终文件，整段模式保留原 RMS 处理。Opt-in per-model settings and explicit gain semantics.
- 基座新增有界、连续、校验结束边界的音频通道；私有缓存最多 4 次，成功 / 失败 / 取消 / 中断与真实队列一致，部分音频不发布为成功产物。Bounded previews share the production task lifecycle.
- 鉴权 API 提供游标分页及不可变 PCM，页面明确点击播放、停止 / 关闭 / 后台释放音频资源，生成独立继续。Authenticated cursor-based reads and explicit playback controls.
- 同步 ARM64、原签名开发 APK、当前回归与 3 张新截图 / MP4 / GIF、双语指南；dev.24 / dev.28 历史证据原样留存。完整训练 Realtime / 质量 / Android 及所有冻结目标未完成，不发布为完整 Release。[中文](docs/AUDIO_STREAMING.md) / [English](docs/AUDIO_STREAMING.en.md) / [编号完整待办](docs/releases/v0.3.0-dev.29.md)。


## 0.3.0-dev.28 — LCM user assets through generation / unreleased

- LCM 准备程序注册进 App；用户明确选源、准备、关联、下载依赖和生成，复用共享队列与独立模型记录。Production preparation and association connect to generation without implicit transfers.
- 修复阶段输出预算与磁盘余量混用；Java / C++ 验证来源、基础模型、GGUF 单张量、有限数值、填充与精确结束；原生加载错误停止。Separate native output budgets and strict source-bound condition parsing.
- 固定条件不允许叠加未验证 LoRA，页面明确说明并隐藏低步数不用的负面条件；保留独立 SD1.5 / SDXL LoRA、推荐、HF 搜索、本地与参数归位。Fixed-condition limits remain distinct from independent adapters.
- 完整训练源与实际生产 Java / 原生主机链路、结构拒绝对照、当前回归、原签名 APK、双语文档和四张新截图 / MP4 / GIF 同步。Known pixel failure 8 > 5, quality/device gates and all frozen release targets remain open. [中文](docs/LCM_APP_FLOW.md) / [English](docs/LCM_APP_FLOW.en.md) / [编号实现与完整待办](docs/releases/v0.3.0-dev.28.md).


## 0.3.0-dev.27 — task recovery, history and capacity / unreleased

- 启动对账已提交结果，来源与不可变请求一致才关联 interrupted 任务；保留中断状态，不自动续步。回收有明确归属的未提交生成文件，保留索引结果、续传输入及模型。Startup reconciles committed results and reclaims owned uncommitted output files.
- 终态历史清理先生成精确范围与状态指纹，用户确认后原子删除；过期范围整批拒绝，活动 / 后完成任务、草稿、模型、结果保留。API 共用原生存储与刷新。Reviewed cleanup retains active work and independent assets.
- 任务状态筛选、搜索、20 条分页及 256 历史 / 64 待处理 / 2,048 素材结果容量；UI / API / 入队和结果发布独立复查。Search/filter/pagination and actionable capacity checks.
- 原签名 dev.27 / code31 APK、双语方案与指南、4 张新截图 / MP4 / GIF、受影响媒体和当前检查同步；不提升历史模型实验为新版验收。[中文](docs/TASK_RECOVERY.md) / [English](docs/TASK_RECOVERY.en.md) / [编号实现与完整待办](docs/releases/v0.3.0-dev.27.md)。


## 0.3.0-dev.26 — task preflight and input review / unreleased

- 生成表单与 `POST /v1/jobs/preflight` 共用实际入队解析器，报告模型 / 引擎 / 组件 / LoRA / 素材 / 参数 / 资源与用户确认，检查不创建任务、不下载或更改独立设置。UI and authenticated API share the production submission resolver with read-only diagnostics.
- 文字、参数、素材、LoRA 或用户选项改变使旧结果失效，丢弃修改期间返回的过期检查；素材刷新保留输入，失效引用须重新复核。Edits invalidate readiness; changed references require review before explicit submission.
- 原签名 dev.26 / code30 APK、双语指南、4 张新截图 / MP4 / GIF、刷新工作台媒体及当前检查同步；保留所有历史失败、冻结子目标和同一个完整 v0.3.0 门槛。Signed development APK and matching docs/media/checks; no new model inference or Android acceptance claims. [中文](docs/TASK_PREFLIGHT.md) / [English](docs/TASK_PREFLIGHT.en.md) / [编号实现与完整待办](docs/releases/v0.3.0-dev.26.md).

## 0.3.0-dev.25 — generation workflow / unreleased

- 原生每模型草稿、显式保存 / 恢复 / 删除、空提示词、单调版本号与冲突保护；草稿、参数、LoRA 与参考素材独立于模型设置。Native per-model drafts support explicit persistence, incomplete prompts and revision conflicts without changing model defaults.
- 任务详情直接打开结果、编辑再生成；保留产物可从来源恢复请求，图片 / 音频 / 视频可填入匹配的下一次本机生成。Readable jobs, direct outputs, editable provenance and compatible reference reuse connect the generation workflow.
- UI / API / retry 共用请求重建，移除执行回执并重新检查资产 / 参数；恢复编辑重新确认试运行，缺失 / 改变项目明确提示。Shared sanitized restoration and fresh validation retain immutable old records and disclose missing inputs.
- 新增草稿与可编辑请求 API；修复窄屏预览按钮换行。Added authenticated draft/request routes and wrapped narrow-screen modal actions.
- 原签名 ARM64 开发 APK、当前检查、双语[使用文档](docs/TASK_WORKBENCH.md) / [English](docs/TASK_WORKBENCH.en.md)、五张截图 / 录屏 / GIF 和[编号完整待办](docs/releases/v0.3.0-dev.25.md)。Original-signature APK and labelled UI media; device/model acceptance remains open.
- 当前业务证据与 dev.24 不可变历史实验分开，原 LCM / LTX 失败及 F01–F12 / 01–14 / 16 / 17 全部同版门槛保留，未发布完整 v0.3.0。Current checks and historical experiments have separate applicability; no failed gate is waived or complete Release published.

## 0.3.0-dev.24 — diffusion progress and trained host evidence / unreleased

新增 LCM 原生本地准备程序：流式校验完整原始 F32 UNet，确定性 F16/F64/F32 条件折算，只生成 5,696 字节来源 / 基础模型绑定组件，不含学习参数的程序及数学常量独立构建。24 原生进程 / 105 检查、真实训练源 / 数值、底层小组件出图对照 / 非法 CFG / 采样取消 / 恢复、Android ARM64 编译与五份公开证据分别审计；原始 PNG / GIF / MP4、双语文档与[编号完整待办](docs/releases/v0.3.0-dev.24-lcm-preparation.md)同步。All five execution cases complete, but the new C++ image comparison fails its unchanged max-difference gate (8 > 5; mean0.0838928 <=0.1). The candidate stays rejected. Native program is not yet packaged or integrated into App preparation/routing; source APK inputs/bytes stay unchanged. Image quality, canonical equivalence, phone/background and the complete v0.3.0 remain unaccepted. [中文](docs/LCM_LOCAL_PREPARATION.md) / [English](docs/LCM_LOCAL_PREPARATION.en.md).

新增独立 SD-Turbo / LCM checkpoint 主机验证：10 原生子进程 / 6 PNG，80 项生产 Java / 绑定检查、完整2对象导入、5真实 worker / 3 PNG；LCM 原始687张量 / 859,602,884参数、686转换张量逐值对照、30完整 UNet 前向、仅5120字节偏置的固定引导候选及原生取消恢复。五份公开记录、原始PNG / GIF / MP4、[中文](docs/SD_DISTILLED_TRAINED.md) / [English](docs/SD_DISTILLED_TRAINED.en.md)及[编号完整待办](docs/releases/v0.3.0-dev.24-sd-distilled.md)同步。LCM face/detail quality remains failed; product preparation, canonical pipeline, phone/resource/endurance and full Release remain open. Production sources and APK inputs/bytes are unchanged.

新增完整 SDXL 与 SD1.5 / SDXL 风格 LoRA、LCM-LoRA 的真实训练主机专项：固定五新对象、双 CLIP / UNet / VAE 与适配器完整结构、零强度 / 启用 / LCM 权重反事实 / 组合 / 取消恢复对照；生产 Java 完整导入七唯一对象、模型参数 / 适配器租约 / 快照 / 实际 worker。原始 PNG、联系图、标明范围的 GIF / MP4、独立原始复核、五份公开 JSON、双语文档和[编号完整待办](docs/releases/v0.3.0-dev.24-sd-variants.md)同步。Low-step sample quality is not accepted; actual hash differences do not establish semantic quality. This developer-only follow-up leaves production sources/APK bytes unchanged and does not close SD-Turbo, the separate LCM checkpoint, Android or complete Release gates. [中文](docs/SD_VARIANTS_TRAINED.md) / [English](docs/SD_VARIANTS_TRAINED.en.md).

新增编号11完整Qwen0.6BBase/12Hz codec两GGUF/920MB取得及真实生产源码主机执行：18WAV/12控制涵盖十语言、参考、采样和frame16后取消恢复；94项生产Java检查、6真实worker、2完整对象导入且零网络，145原始文件/31协议/22WAV/2对象独立复核及8项错误范围提升控制。原始音频/波形PNG/GIF/MP4、双语指南/README与[编号完整待办](docs/releases/v0.3.0-dev.24-qwen-tts.md)同步；生产/APK字节不变。The greedy short-text output matches the30-second budget, without a separate EOS/budget reason; quality, voice similarity, Z20 fit, Android endurance and the complete Release remain unaccepted. [中文](docs/QWEN_TTS_TRAINED.md) / [English](docs/QWEN_TTS_TRAINED.en.md).

新增编号10全部三套冻结训练资产/真实生产worker主机验证：Kokoro54音色、Piper Lessac、Matcha LJSpeech/Vocos，共68成功WAV/13控制/82原生进程；157项生产Java检查、完整导入9对象/11引用、独立设置/快照、12真实子进程取消/时长错误/恢复。独立复核394原始文件/82协议/74WAV/9导入对象，拒绝8种错误范围提升。三套原始WAV/波形PNG/GIF/含实际音频MP4、五份公开JSON、双语文档及[编号完整待办](docs/releases/v0.3.0-dev.24-tts.md)同步。Unchanged production C++ uses official sherpa2.0.1/ORT1.28.2 Windows libraries; Android log interposition, speech quality, licenses, every phone/target and full Release remain open. No APK inputs/bytes or user asset policy change. [中文](docs/TTS_TRAINED.md) / [English](docs/TTS_TRAINED.en.md).

新增Nano100M真实训练资产与独立用户导入清单：固定11组件/717,414,286字节、18音色范围，7成功WAV/7控制及40项生产Java→真实worker检查；原始65文件/15协议/9WAV/11对象复核，8种错误提升验收标记被拒绝。三语原始WAV、波形图/GIF/含真实音频MP4、双语指南和[编号完整待办](docs/releases/v0.3.0-dev.24-moss-nano.md)同步。This source/metadata follow-up preserves existing APK bytes. Host ORT1.28.0/API28 differs from Android1.28.2/API28; production neural C++ is unchanged. Model assets remain user-selected and external; speech quality, Android/background, every frozen target and full Release remain pending. [中文](docs/MOSS_NANO_TRAINED.md) / [English](docs/MOSS_NANO_TRAINED.en.md).

修正生产扩散 worker 的 loading/generating 进度，避免把加载/VAE回调都当作采样；原生构建复用 CMake 缓存驱动器。新增固定 SD1.5 真实权重/外部词表、生产源码 CPU 推理、采样取消/恢复和 A/B/A 验证工具与实测媒体；首次错误阶段分类的尝试保留并重新执行。旧 LTX 两次原训练前向观察114调制位置、两次八步原生候选、478文件独立复算；两条B条件仍超冻结门槛。原签名 dev.24/code28 APK、限定回归、68界面截图/录像/GIF、双语文档及编号完整待办同步。

Corrects top-level diffusion progress without changing model math. Adds actual trained SD1.5 production-source host validation and a labelled still-image slideshow, with Windows/Android scopes separated. Old-LTX modulation staging matches all original observed sites but does not repair the failed full sampler gates. The App remains foundation-only, with explicit user-selected assets; all physical-phone, quality/background and complete-release gates remain open. [SD1.5 中文](docs/SD15_TRAINED.md) / [English](docs/SD15_TRAINED.en.md) / [LTX 中文](docs/LTX098_MODULATION.md) / [English](docs/LTX098_MODULATION.en.md) / [Numbered implementation and full pending scope](docs/releases/v0.3.0-dev.24.md).

## 0.3.0-dev.23 source follow-up / 2026-10-29 — original F32 operation staging

实现 F32 RMS 分组归约和 GeGLU 原始运算顺序；72 局部对照、四候选共 12 次真实 T5、三次实际 DiT/VAE/RGB 链路及重复 A 一致性。A 通过，B 三项浮点门槛失败；保留原参考和门槛。复核字段修复后显式恢复首条真实采样，执行与复用如实记录。新双语指南、误差图、真实主机帧/GIF/视频及来源审查同步；App/APK/注册引擎保持原状态。Four isolated T5 variants and actual host A/B/A improve diagnosis without accepting failed floats, Android or Release. [中文](docs/LTX098_STAGING.md) / [English](docs/LTX098_STAGING.en.md) / [编号及完整待办](docs/releases/v0.3.0-dev.23-ltx-staging.md).

补充五次完全相同参考条件的采样器诊断，定位 CPU 激活隐式 F16 转换；显式 F32 输入减少该误差但未关闭完整模型门槛，Vulkan 未改善。所有候选均未注册或打包，公开证据 / 范围标记与双语说明同步。Five fixed-reference sampler diagnostics preserve all failed gates and separate CPU/Vulkan behavior.

## 0.3.0-dev.23 — user-selected runtime model association / unreleased

新增通用签名关联方案、实际环境依赖指纹绑定、`model.assemble`共用任务、排队/运行引用保护、完整验哈希及本地硬链接复用。7个固定候选中新增旧LTX社区Google T5 Q5单尺度运行资产：20个派生组件复用，2项T5依赖由用户随后明确下载/导入，缺失时暂停、未安装。原模型参数和两份记录的独立删除保留。47项核心契约、生产队列/API检查、真实训练文件关联、原签名APK code27、中英说明及截图66–68/录屏/GIF同步。

Signed association plans bind preparation/runtime identities and share jobs, cancellation, explicit retry and storage. No automatic downloads, model bytes in the APK, remote execution or generation-engine availability is introduced. Actual trained asset association is a HOST filesystem check; UI media uses explicit fixtures. Six full-chain float failures, every frozen subtarget and all Android/background gates remain required for one complete v0.3.0. [中文](docs/MODEL_ASSEMBLY.md) / [English](docs/MODEL_ASSEMBLY.en.md) / [Numbered delivery and full pending scope](docs/releases/v0.3.0-dev.23.md).

## 0.3.0-dev.22 — explicit local runtime preparation / unreleased

用户下载/导入固定源模型后明确选择准备；签名方案、两个原生程序、共享任务/执行槽、独立派生存储/恢复/删除、源删除后本地可管理、过热/空间/内存检查。生产Java核心处理完整旧LTX源文件并校验20个结果（6,061,184,991字节），44项生命周期契约通过；两个准备器的Android父进程结束保护及主机/ARM64重编译。原签名APK code26含29原生文件和九份审计无参数图，不含学习模型数据。双语文档、截图62–65、录像/GIF与编号待办同步。

Trusted plans and two native preparers reuse shared jobs and atomic derived-asset storage. Full trained production-core HOST preparation passed; package/host/UI/Android evidence remains separate. Updated APK fingerprints include all preparation code without invalidating unchanged math producers. Android execution, T5 user assets, production video integration and six failed full-chain float gates remain open. No automatic model retrieval, frozen-target deferral or complete Release. [中文](docs/MODEL_PREPARATION.md) / [English](docs/MODEL_PREPARATION.en.md) / [Numbered delivery and full pending scope](docs/releases/v0.3.0-dev.22.md).


## 0.3.0-dev.21 source follow-up / 2026-10-29 — native VAE asset preparation

新增共用原生准备 I/O、旧 VAE 九图无学习数据审计、从原始用户 checkpoint 流式生成九份参数文件及事务提交。18 资产 /2.212 GB 与独立 Python 导出整文件身份一致；243 检查、25 组失败保护、31 原生子进程及四种尺寸的 40 个原始前向解码对照通过。DiT 156 检查与 Windows / ARM64 构建重新通过。

Architecture remains foundation code; learned weights, timestep multiplier and statistics stay user data. Synthetic-latent host decoding is separate from prompt-video quality, App acquisition, Android execution and the six failed complete-chain float gates. Existing APK/UI unchanged; full v0.3.0 scope retained, no new Release. [中文](docs/LTX098_VAE_PREPARE.md) / [English](docs/LTX098_VAE_PREPARE.en.md) / [numbered implementation and complete pending scope](docs/releases/v0.3.0-dev.21-ltx-vae-prepare.md).

## 0.3.0-dev.21 source follow-up / 2026-10-29 — native local asset preparation

旧 LTX safetensors → DiT GGUF 改为独立可移植原生流式组件：完整同流 SHA、F16 / F32 分块转换、旧版结构校验、取消 / 源保留 / 无覆盖提交。156 检查、46 组失败保护、51 原生子进程；6.34 GB 完整训练源与 3.85 GB Python 基线整文件身份一致，主机观测峰值工作集 13.27 MiB。Windows / Android ARM64 API28 /16KiB 编译通过。

Portable Python-free preparation contains no learned data and performs no inference. Production App acquisition, on-phone VAE preparation, six failed full-chain float gates and every frozen v0.3.0/device gate remain open. APK/UI unchanged; no new Release. [中文](docs/LTX098_PREPARE.md) / [English](docs/LTX098_PREPARE.en.md) / [numbered implemented and full pending scope](docs/releases/v0.3.0-dev.21-ltx-prepare.md).

## 0.3.0-dev.21 source follow-up / 2026-10-29 — text precision diagnostics

旧 LTX 真实训练 T5：314 中间张量、628 原始文件哈希 / 误差重算、120 同输入算子对照；原生及原始参考最终 embedding 均保持既有字节身份。新增独立注意力 / 可选线性 F64 候选构建及 A/B/A 复现工具、双语指南、来源图与开发证据审计。

Actual host diagnostics and separately identified precision candidates do not close six failed original full-chain float gates, establish phone execution or change APK. No automatic model retrieval or external inference is added. All frozen v0.3.0 targets remain required. [中文](docs/LTX098_PRECISION.md) / [English](docs/LTX098_PRECISION.en.md) / [numbered implementation and full pending scope](docs/releases/v0.3.0-dev.21-ltx-precision.md).

候选实测：两种实现各完成三次训练T5 A/B/A，重复字节一致；组合候选A / B embedding最大误差2.861e-6 /1.192e-6。两次A原始八步轨迹仍超原0.003门槛（0.003953 /0.003829），证据保持失败及exit 1；候选VAE / B视频 / 完整修复未验收。Six trained candidate text jobs, two failed partial video probes; no gate relaxation.

## 0.3.0-dev.21 source follow-up — real-prompt old-LTX host pipeline / unreleased

新增真实提示词、完整训练 T5、旧版 0.9.8 distilled DiT 八步采样、九段 VAE 与 RGB/MP4 的独立单尺度主机串联。可移植 RNG / 张量还原 / 帧封装组件独立 Android 编译；完整链路参考从原始模型前向传播到 RGB，保留固定精度门槛与实际 A/B/A 任务。基座与模型资产继续分离，没有模型隐式获取或 APK 模型数据。

Real host outputs, separately labelled comparison media, component identities/lifetimes, independent original-forward checks and distinct Android compilation evidence. The explicit Google/community Q5 text variant does not establish official PixArt weight identity or the default multi-scale preset. Quality, production App integration, public user acquisition, phone/endurance and all frozen v0.3.0 gates remain open; APK/UI media remain dev.21 and no Release is created. [中文](docs/LTX098_PIPELINE.md) / [English](docs/LTX098_PIPELINE.en.md) / [numbered implemented and complete pending scope](docs/releases/v0.3.0-dev.21-ltx-pipeline.md).


本次真实主机视频的完整参考验收：163 检查中 157 通过、6 项 float gate 失败；RGB 两组均通过。保留原门槛与 exit 1，并分开记录 executed=true / numeric accepted=false；同 caption 隔离诊断指向文本编码微小误差在采样中的放大。This checkpoint publishes real experimental outputs and the numerical failure, not successful full-chain acceptance or an APK Release.

## 0.3.0-dev.21 source follow-up / 2026-10-29 — trained old-LTX VAE

旧版0.9.8 distilled完整训练VAE：132张量 /552,814,641参数从原始BF16转F32，九段CPU ONNX会话依次装卸；外部图 /数据2,211,661,835字节不进入APK。噪声先在归一化空间混合，原始通道统计 /时间条件 /PixelNorm /时空上采样保留。355检查 /36真实原生子进程 /31防护 /40逐段与最终误差记录通过；独立未修改原始Decoder.forward四组几何参考，44参考文件先核对SHA；最终帧最大误差2.14577e-6，真实ORT计算中取消和无会话泄漏通过。

Full trained decoder host parity, distinct Android ARM64/API28/16KiB compilation and measured host memory are reported separately. No model graphs/statistics enter APK, no implicit model acquisition, no complete prompt-to-video/quality/App/phone claim. APK/UI media stay dev.21; all frozen v0.3.0 targets remain required in one complete release. [中文](docs/LTX098_VAE.md) / [English](docs/LTX098_VAE.en.md) / [numbered implemented/pending handoff](docs/releases/v0.3.0-dev.21-ltx-vae.md).



## dev.21 source follow-up — old LTX T5 / unreleased

新增完整24层T5原生CPU文本编码组件：外部量化存储 /原始tokenizer配置、全部32000学习词条与归一化身份、F32 GELU /临时矩阵解量化、raw embedding /mask、实际计算中取消与输出保护。491检查 /76真实原生子进程 /39防护通过；219张量 /4,762,310,656参数与独立解量化参考对照，训练最大误差3.27826e-6；ARM64/API28/16KiB编译单独核验。

Full trained T5 host execution with three short prompts and a repeated call, original external sentinel definitions,49 independently hashed oracle artifacts, bounded temporary matrix buffers and separate host process-memory counters. No weights/vocabulary or research executable enters APK; no unquantized-weight/prompt quality, full trained256-token completion, VAE/video/App/phone acceptance is claimed. APK/UI media staydev.21; the complete frozenv0.3.0 remains one release. [中文](docs/LTX098_TEXT.md) / [English](docs/LTX098_TEXT.en.md) / [numbered implemented/pending handoff](docs/releases/v0.3.0-dev.21-ltx-text.md).

## dev.21 source follow-up — old LTX trained DiT sampling / unpublished

固定完整旧0.9.8训练检查点，显式下载 /断点 /完整SHA核对，本地逐张量DiT GGUF转换；新增旧坐标 /unpatchify /精确8步RF与逐步事件 /取消。692检查 /58真实原生子进程 /111误差记录通过，含完整715张量 /28层训练Vulkan前向及8步latent官方对照；原有675项回归通过，ARM64 probe /sampler分别编译核验。训练最终latent最大误差3.57628e-6，人工caption embeddings未运行T5 /VAE，不是视频输出或手机验收。

Pinned external checkpoint, explicit acquisition and streaming local conversion; publisher geometry/RF/layout and native CPU/Vulkan trajectories, full trained DiT Vulkan velocity/eight-step latent parity, separate ARM64 compilation and host process-memory counters. No model data or research executable enters APK. APK/UI media stay dev.21; complete video/App/phone/quality and the full frozen v0.3.0 remain unaccepted. See [中文](docs/LTX098_SAMPLING.md) / [English](docs/LTX098_SAMPLING.en.md) / [numbered implemented/pending handoff](docs/releases/v0.3.0-dev.21-ltx-sampling.md).


## dev.21 source follow-up — old LTX native DiT / unpublished

精确LTX-Video2B0.9.8独立原生CPU /Vulkan DiT，全715张量布局核对；675检查 /80原生子进程 /48原始PyTorch数值对照通过，含28层小宽度未训练图、F32 /F16密集权重和31个拒绝用例。固定F32 shader计算、原生Windows /NDK与新版shaderc来源，ARM64/API28/16KiB编译单独记录。双语方案 /复现 /证据与编号待办同步；APK /UI媒体仍dev.21，训练视频 /App /手机 /完整v0.3.0仍未验收，公开Release仍v0.2.0。

Independent exact-old-version CPU/Vulkan transformer component with publisher-forward parity and separate Android compilation; UNTRAINED reduced-width graphs do not establish complete video support. No model data or research executable enters APK. See [中文](docs/LTX098_DIT.md) / [English](docs/LTX098_DIT.en.md) / [numbered implementation and complete pending work](docs/releases/v0.3.0-dev.21-ltx-dit.md).

## 0.3.0-dev.21 — SoulX App foundation / unpublished

- 完整SoulX CPU worker、14份用户资产（含40字节声源权重）、四说话人参考原文、独立联合参数及共用任务 /API接入；无模型数据进入APK。Complete native worker, paired inputs and shared foundation; explicit user assets only.
- 222项Java /C++契约与95项完整训练生产worker检查；两说话人新文字4.84秒WAV、四说话人截断、两次主机阶段强制终止，分别标识无质量 /手机结论。Trained host execution remains separate from complete Android acceptance.
- 582基座 /295UI /80HF回归；34个元数据配方，27原生文件，72份生产Java + 1份生成源码；原签名dev.21 /code25，修正Gradle /应用状态 /UA的旧版本字面量。Consistent version identity; refreshed bilingual docs, screenshots59–61, recording/GIF.
- 共享原生库校验允许严格字节 / SHA256 / API 一致的复用，拒绝冲突；10 项回归与最终 27 文件 APK 校验通过。Exact runtime identity is required for shared dependencies.
- 目标13仍缺完整公开用户下载候选、语音质量和Android；01–14 /16 /17、全部冻结子目标 /后台与完整Release保持同版阻塞。Public release remainsv0.2.0. [方案](docs/SOULX_ENGINE.md) / [English](docs/SOULX_ENGINE.en.md) / [编号交付](docs/releases/v0.3.0-dev.21.md)。


## dev.20 source follow-up — SoulX language and complete trained host pipeline / unpublished

源码后续更新（APK仍dev.20）：[SoulX语言与完整主机链路](docs/SOULX_LANGUAGE.md)已运行全部训练Qwen3 /S3 /CAMPPlus /Flow /HiFT，以两段新文字输出24kHz WAV。语言546项 /20次原生子进程、整链路60项 /5次原生子进程通过；官方与较早社区词表分开验证，实际原始HF logits、RAS /历史和运行中取消均核对。ARM64 /API28 /16KiB编译通过，执行器未进APK。参考PCM为合成输入，没有语音质量、App或手机验收结论；模型与WAV留在忽略目录，完整范围 /Release门槛保留。见[编号实现与完整待办](docs/releases/v0.3.0-dev.20-soulx-language.md)。

Source follow-up (APK remains dev.20): [SoulX language and complete host pipeline](docs/SOULX_LANGUAGE.en.md) execute trained Qwen3/S3/CAMPPlus/Flow/HiFT on fresh texts and write 24 kHz WAV. Language 546 assertions / 20 native children and pipeline 60 assertions/5 native children pass; distinct official/earlier community tokenizers, full original HF logits, RAS/history and actual decode cancellation are checked. ARM64/API28/16KiB compilation passes; executors are outside APK. Synthetic references provide no speech quality, App or phone acceptance. Models/WAVs remain ignored; all complete-scope/Release gates stay open. See [numbered implementation and remaining work](docs/releases/v0.3.0-dev.20-soulx-language.md).

## dev.20 source follow-up — trained SoulX reference/acoustic reconstruction / unpublished

- 新增完整训练S3Tokenizer v2 / CAMPPlus原生参考提取，完整ONNX / tensor身份保持，显式开发权重下载与严格来源锁；145项 /15主机子进程 /10图 /2实际终止。Native trained references with exact publisher identity and explicit asset preparation.
- 使用真实Flow / HiFT和原生训练参考完成253项声学重建、54图 /63阶段 /12隔离比较；定位F0浮点相位差，独立RMSE /SNR门槛，保留未训练244项原阈值。Shared CPU ORT contracts and Android ARM64/API28/16KiB compilation pass.
- [双语方案与复现](docs/SOULX_REFERENCE.md) / [English](docs/SOULX_REFERENCE.en.md) / [编号完成与待办](docs/releases/v0.3.0-dev.20-soulx-reference.md)。目标码来自合成PCM，未运行Qwen3 /完整TTS、未接App、无手机 /质量验收；APK /媒体仍为dev.20，公开Release仍v0.2.0，所有冻结范围保留在同一完整v0.3.0。

## dev.20 source follow-up — full SoulX acoustic networks / unpublished

新增完整 Flow / HiFT四图离线导出与原生 ORT/CPU声学链路、学习源、顺序会话 / 运行中取消，修复参考前缀帧预算。244项限定检查、12次主机子进程、57次完成图执行、1次实际 ORT终止；均为完整结构的未训练参数，不是完整 SoulX语音。ARM64/API28/16KiB编译及 DSP155项检查通过。双语方案、来源许可、独立证据和编号交付同步；APK / UI媒体沿用dev.20，不创建 Release。

Added full-network acoustic export and native execution with sequential ORT/CPU sessions, learned source and actual in-run termination. Scoped host / ARM64 evidence uses UNTRAINED parameters; language/reference models, App integration, trained speech quality and phone gates remain open in the same complete v0.3.0. See [numbered delivery](docs/releases/v0.3.0-dev.20-soulx-acoustic.md), [中文](docs/SOULX_ACOUSTIC.md) / [English](docs/SOULX_ACOUSTIC.en.md).

## dev.20 source follow-up — SoulX DSP / unpublished

新增尚未接入 APK 的 SoulX C++ 音频计算库：独立 S3 / Flow / CAMP 前端、sinc 重采样、CFG Euler、HiFT STFT / ISTFT / NSF，修复长序列半像素相位插值并检查30 / 120秒 F0。153项限定检查、49次主机子进程及 Android ARM64/API28 静态编译；双语文档、固定来源 / 许可和独立证据同步。模型推理 / 音频产物 / 真机仍0，完整执行器待完成，APK / 页面 / 媒体沿用 dev.20，不创建 Release。

Added unregistered SoulX native audio primitives with three distinct frontends, sinc resampling, CFG Euler and HiFT spectral/NSF operations, including long-offset interpolation alignment. 153 scoped checks/49 host children and Android ARM64/API28 static compilation; bilingual docs, pins/licenses and separate receipts. No complete-model/phone evidence; APK/UI/media remain dev.20. Full scope stays in the same v0.3.0. See [numbered delivery](docs/releases/v0.3.0-dev.20-soulx-dsp.md).

## 0.3.0-dev.20 — internal / unpublished

新增 Stable Audio Open Small 同机 LiteRT CPU 基座：顺序 T5 / DiT / 音频解码、四份用户自选组件、HF TFLite 文件识别、每模型可编辑参数与有效 token / 固定长度成本说明。144 项限定检查含实际 LiteRT 微型图和 6 次主机子进程，不是整模型或 Android 推理。

Added a native same-phone Stable Audio pipeline, strict pinned export layouts, isolated worker lifecycle, model-specific bounded settings and receipts. All 33 recipes are metadata; no implicit model transfers. Original-signature development APK, 561 foundation / 287 UI assertions, bilingual docs, screens 56–58 and refreshed recording/GIF. Full frozen scope and phone gates remain in one complete v0.3.0; no new Release. See [numbered notes / 编号交付](docs/releases/v0.3.0-dev.20.md).

## 0.3.0-dev.19 — 2026-10-28 (internal / unpublished)

新增旧 Local / Realtime 的独立原生 RQ 基座，三个用户自选 GGUF、24 kHz 可选参考、独立词表与实际输入预算校验；旧 SoundEffect 按官方模板绑定 Ambient Sound。Added separate native depth architectures and shared model-owned parameters/jobs/leases/cleanup. Realtime currently provides one text request to complete WAV, without incremental streaming or real-time claims.

178 scoped RQ checks include 10 actual host children, 14 GGUF metadata checks and two actual synthetic tiny graphs; openmoss 514 / foundation 550 / UI 280 checks pass. Original-signature APK, 32 metadata-only recipes, 24 native files, bilingual docs, 55 UI FIXTURE screens and refreshed recording/GIF. No complete-model or Android inference/quality/endurance evidence. Every frozen target stays in one complete v0.3.0; no new Release. See [双语说明与编号表 / bilingual numbered notes](docs/releases/v0.3.0-dev.19.md).

## 0.3.0-dev.18 — 2026-10-28 (internal / unpublished)

在现有原生 MOSS worker 中接入 TTS、v1.5、TTSD、VoiceGenerator 四种平级配方；按 32/16-codebook、8B/1.7B 实际 GGUF 几何校验。增加成对 S1/S2 参考、每模型声音描述/语言参数和真实生成网格的 prefill 前预算保护。Added native delay dispatch, explicit paired reference mapping, per-model bounded voice/language hints and a context guard in a generated copy of the pristine pinned source. All model/codec/BPE assets stay user-selected.

459 scoped Java/C++ assertions (18 actual host children), 521 foundation and 265 UI assertions pass. Refreshed original-signature APK, 29 metadata-only templates, bilingual guides, five new screenshots and recording/GIF. No complete model/Android inference, quality or endurance claims; all frozen targets stay in one complete v0.3.0 with no new Release. See [双语说明 / bilingual notes](docs/releases/v0.3.0-dev.18.md).

## 0.3.0-dev.17 — internal / unpublished

Two native CPU MOSS routes now share the foundation: Local-Transformer-v1.5 speech and SoundEffect-v2 flow matching. Users explicitly select matching backbone/extras GGUFs; embedded BPE/codecs remain user assets, with no implicit downloads. Independent editable parameters, optional stereo reference, actual solver/receipt events and isolated child cleanup are integrated. CFG=1 cannot silently ignore a supplied negative prompt; full 30-second latent cost is disclosed.

180 new host/native checks (100 Java / 80 C++, six actual host children), 485 foundation checks, 244 UI checks; original-signature APK with 23 native files and no model weights. Bilingual guides, six new screens, refreshed recording/GIF and numbered implemented/pending tables are included. These are scoped checks/fixtures, not full model or phone inference; all frozen targets remain in the same complete v0.3.0 with no new Release. See [bilingual notes](docs/releases/v0.3.0-dev.17.md).


## 0.3.0-dev.16 — 2026-10-28 (internal / unpublished)

- 新增 MOSS Delay first-class 签名 ARM64 CPU worker、生产 Java 管线、严格组件 / WAV 契约、模型独立采样和实际执行计时。Added a real local BPE/32-channel Delay/codec route with sequential model release.
- 第 23 个显式 HF 配方：主模型和解码器必需；参考编码器仅用户需要时选择，不隐式下载或打包模型数据。Plain TTS does not require reference assets; ordinary MOSS GGUFs and other family architectures remain distinct.
- 176 项新增 Java / C++ 检查包含实际主机子进程及固定上游 Delay 自检；基座 467、UI 228、Lint 0 errors / 13 warnings；更新双语文档、截图 40–41、录屏与 GIF。Fixtures are not generated speech or physical Android acceptance.
- 所有冻结目标、完整家族适配与模型质量 / 资源 / 后台 / 升级门槛保留在同一完整 v0.3.0，无新 Release。See [双语说明](docs/releases/v0.3.0-dev.16.md), [中文](docs/MOSS_DELAY_ENGINE.md), [English](docs/MOSS_DELAY_ENGINE.en.md).

## 0.3.0-dev.15 — 2026-10-28 (internal / unpublished)

- 新增 Qwen3-TTS 12Hz 0.6B Base 的签名 ARM64 CPU worker、生产 Java 适配器、可选本地参考 WAV、独立采样参数、严格 GGUF / 音频检查与实际耗时 / RTF 记录。Added a real same-phone Qwen speech route; model/device output remains untested.
- 两个固定 GGUF 的可选包、22 个 HF 模板和通用内含依赖 `provides`；用户选择下载，App 更新不带权重或默认音色。Pinned optional assets and embedded-role disclosure reuse shared downloads/settings/jobs; no implicit downloads.
- 81 项主机 / 原生检查、固定文件头核对、双语指南及截图 38–39 / 录屏 / GIF；结构 WAV / 界面夹具不代表模型推理。Every frozen target and gate remains part of one complete v0.3.0, without a new Release.
- 同步中英文首页与资产需求核对的当前统计；App 基座更新、用户自主选择模型及独立功能标签的约束一致。Synchronized current documentation counts and the foundation/model ownership assessment.
- [双语说明 / Notes](docs/releases/v0.3.0-dev.15.md) · [中文指南](docs/QWEN_TTS_ENGINE.md) · [English guide](docs/QWEN_TTS_ENGINE.en.md)


## 0.3.0-dev.14 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 实际 MNN Sana 移动端 CPU worker、Qwen3 特征编码与分阶段释放；新增 13 组件配方和 `.mnn` / `.mnn.weight` 用户选择。No bundled model assets, auto-downloads or remote execution.
- 配置白名单 / embedding 范围、独立参数快照、硬链接引用与延迟清理；74 项 Java / C++ 检查。Host protocol bytes are not generated images.
- 445 foundation / 253 recipe-integrity、208 UI、37 张显式 UI FIXTURE 与录屏 / GIF；原签名 APK 和双语文档同步。
- 所有冻结目标与 Android 真实输出、质量 / 资源 / 后台 / 升级门槛仍在同一个完整 v0.3.0，未创建 Release。See [双语 notes](docs/releases/v0.3.0-dev.14.md).

## 0.3.0-dev.13 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 补齐 Z-Image-Turbo、FLUX.2-klein 4B、Qwen-Image 2.1、Wan 2.1 T2V 1.3B 的显式四组件模板与角色校验；总计二十个数据模板，用户自行选择下载，不因 App 更新安装模型。Four complete recipes, without implicit asset downloads.
- 实际绑定采样器 / 调度器 / flowShift、蒸馏任务策略及 Qwen / Wan 几何；本次参数不改写普通基础配置。Actual native bindings and task-scoped policies.
- 174 项扩散、425 项基座与 203 项 UI 主机检查；原签名 APK、双语指南、35 张 UI FIXTURE 截图及录屏 / GIF 已同步。Host/package evidence does not establish Android model generation.
- 全部所选目标和手机离线 / 质量 / 资源 / 后台 / 升级验收保留在同一完整 v0.3.0；无新 Release。See [notes](docs/releases/v0.3.0-dev.13.md).

## 0.3.0-dev.12 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 十六种用户自选数据配方，新增 SD1.5 / SDXL 分离组件、SD-Turbo、LCM checkpoint 与双架构 LCM-LoRA。No weights or automatic model downloads.
- 明确 LCM 配对后固定本次采样 / CFG / 步数，保留模型独立设置；队列计划落盘稳定、运行前重算核对，原生再次验证策略和实际张量架构。Freeze effective sampling without overwriting base settings.
- 83 项新增扩散主机 / C++ 检查、381 项基座和 194 项 UI；原签名 APK、双语指南、32 张标识截图与录屏 / GIF 同步。Host protocol bytes are not generated images.
- 全部冻结模型、真实图像 / 音频 / 视频、物理 Android 质量 / 资源 / 后台 / 升级验收继续要求在同一完整 v0.3.0 完成；没有新 Release。

## 0.3.0-dev.11 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 用户显式导入本地素材，前台服务复制 / 取消，实际结构与 hash 校验；素材和生成结果分别标记、预览、导出、独立管理。Explicit local media import and ownership.
- 新增鉴权有界上传会话、256 KiB 二进制分块、持久偏移、显式续传、全文件 SHA256 / 媒体校验与原子完成对账。Resumable authenticated input uploads without URLs or model downloads.
- 签名引擎声明输入角色；任务固定 ID / hash / 元数据，保护排队和活动输入，执行前复核完整 hash；取消等待实际子进程退出再释放。现有生产配方保持文字输入。Immutable local task references, not new model-input claims.
- 64 项素材 / HTTP、49 项生产调度、182 项 UI 检查；双语输入指南、30 张带标识截图及录屏 / GIF 已同步。原签名和 19 个原生文件保留。
- 全部所选模型的实际管线、Android 媒体 / 后台 / 升级和离线新输入验收仍属于同一完整 v0.3.0；无新 Release。

## 0.3.0-dev.10 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 常驻文本加载、聊天、同步 API 和异步任务共用 FIFO 执行槽，回复结束再自动切换；空闲恢复用户仍希望运行的模型。Share engine scheduling without model downloads.
- 取消等待 / 关闭监听 / 停止文本 / 停止服务保持各自归属；旧进程未退出时保留执行槽、资产与临时文件，有限崩溃恢复继续受调度。Preserve cancellation and actual process-exit ownership.
- 43 项生产调度 / 真实主机子进程 / HTTP 检查及 167 项 UI；双语指南、28 张明确夹具截图与录屏 / GIF 同步。Host evidence does not establish Android or model inference.
- 完整输入产物、全部所选模型与物理设备门槛仍须在同一 v0.3.0 完成，未创建新 Release。Every complete-release requirement remains.

## 0.3.0-dev.9 · 2026-10-28 · internal / 内部检查点

- 文档复核：明确复述基座更新 / 用户模型资产 / 四类功能与依赖标签边界，校正双语指南的旧迁移状态与当前检查数量，README 增加直接入口。Documentation-only audit clarifies asset ownership and tags, corrects stale progress and adds README links.

- 旧文本 / HF / 导入 GGUF 通过本地校验、硬链接和原子 ID 绑定纳入共用资产、参数、任务与版本管理，原推荐 / 标签保留，无重复下载或自动模型选择。Adopt existing assets and retain stable IDs, labels and profiles.
- 旧 / 新管理入口共享传输、设置、删除与进程租约；加载参数变更保持正确重载，API 返回不可变 bundle_id 并合并重复行。Share asset lifecycle and preserve loaded-model configuration behavior.
- 恢复 / 升级不自动续传旧下载，用户明确继续；同步双语指南、26 张带标识截图及录屏 / GIF。Require explicit resume and update bilingual guides/media.
- 69 项新增主机迁移、310 项基座、156 项 UI 检查；仍无物理 Android 或模型推理证据。完整 v0.3.0 全范围与发布门槛不变，未创建新 Release。

## 0.3.0-dev.8 · 2026-10-28 · 内部检查点 / Internal checkpoint

- 新文本 GGUF 包复用签名 llama runtime、共用参数 / 租约 / 队列 / 结果，新增第九种用户自选 HF 配方。Add actual shared text-bundle execution and a ninth explicit HF recipe, without model assets or automatic downloads.
- 读取实际 GGUF 上下文，输出联动回填；有效 schema 与来源分开，模型版本确认绑定实际约束。Inspect limits, enforce dependent bounds and invalidate stale version consent.
- Typed response/reasoning JSON, inert local preview, literal copy/export, bounded SSE and child cleanup. 正文与思考独立保存；受控同源读取，模型 HTML 不执行。
- 310 foundation / 66 new text-host / 147 UI checks, zero Lint errors; original certificate and 19 native files. No model or Android inference evidence.
- 同步[双语指南](docs/TEXT_ENGINE.md)、[更新说明](docs/releases/v0.3.0-dev.8.md)、截图 22–24、录屏 / GIF；旧记录迁移、全部所选模型及真机门槛继续属于同一完整 v0.3.0，没有新 Release。

用户可见行为、验证范围和交付文档在此同步。User-facing behavior, evidence, and delivery documentation are maintained together.

## 0.3.0-dev.7 · 2026-10-28 · 内部检查点 / Internal checkpoint

- User-selected immutable model-version updates, component/license/profile review, separate transfer and activation, retained assets, rollback and bounded history. 通用包独立更新，不随 App 升级下载或替换模型。
- Stale consent, atomic profile/pointer commit, running leases and queued base/LoRA deletion protection; fixed task/API identities. 过期确认与引用保护，旧参数和任务来源保留。
- 302 foundation checks including 62 version assertions; 132 UI checks; zero Lint errors. New [bilingual guide](docs/MODEL_UPDATES.md), [notes](docs/releases/v0.3.0-dev.7.md), screenshots 17–21 and refreshed visible-fixture recording/GIF.
- Complete legacy migration, every selected model and physical Android acceptance remain blockers for the same complete v0.3.0. No new Release; published v0.2.0 remains unchanged.

## 0.3.0-dev.6 · 2026-10-28 · 内部检查点 / Internal checkpoint

- MOSS Nano ARM64 CPU worker with actual SentencePiece/ONNX/codec calls; user-owned tokenizer, voice and external-weight data. 新增 Nano 语音原生路径，模型数据保持用户自选。
- Private leased hardlink workspaces, nested ONNX external-reference guards and identical shared-ORT packaging. 私有工作区、外置数据校验与运行库共用冲突检查。
- Eighth HF component recipe, `.model` / `.data` selection and 190 new native/Java/worker host checks; 240 foundation checks. 第八种组件模板与新增主机验证。
- Bilingual [guide](docs/MOSS_NANO_ENGINE.md), [checkpoint notes](docs/releases/v0.3.0-dev.6.md), visible-fixture screenshots/recording/GIF. No actual MOSS speech/Android acceptance or new Release; complete v0.3.0 scope remains open.

## Earlier development checkpoints / 早前内部检查点

- 2026-10-28：内部 0.3.0-dev.5 / code 9 新增七种显式 HF 组件模板、跨仓库固定版本选择与独立登记 / 下载确认，普通 Git blob 完整性及实际 SHA256 来源回执，兼容旧包。217 基座 / 74 HF / 112 UI 检查；同步[双语指南](docs/HF_RECIPES.md)、[需求核对](docs/ASSET_CONTROL_AUDIT.md)、截图 / MP4 / GIF 与[更新说明](docs/releases/v0.3.0-dev.5.md)。App 只更新基座，模型由用户管理；完整 v0.3.0 与真机门槛未完成，无新 Release。 / Add explicit user-selected component recipes, Git integrity receipts, scoped checks and bilingual media; preserve foundation-only updates and all complete-release gates.

- 2026-10-28：内部 0.3.0-dev.4 / code 8 新增平级 LoRA 包、显式 SD 1.5 / SDXL 基础配对、最多八个独立强度、任务 / API 冻结快照和完整组件引用保护，缺资产不下载。新增 45 项主机适配器检查，总计 130 基座 / 97 UI；同步[双语配对指南](docs/ADAPTERS.md)、[基座与资产核对](docs/ASSET_CONTROL_AUDIT.md)、媒体和[开发记录](docs/releases/v0.3.0-dev.4.md)。尚无手机 LoRA 输出或新增已核对 LoRA 候选，完整 v0.3.0 仍未完成、不创建 Release。Add explicit peer-adapter pairing, frozen strengths/leases, scoped tests and bilingual docs/media; retain all full-release/device gates.

## Unreleased / 后续维护

- 2026-10-28：内部 **0.3.0-dev.3 / code 7** 新增 sherpa_tts ARM64 CPU worker、Kokoro / Piper / Matcha 适配、三套明确由用户下载的完整候选、语音专用表单和独立音色 / 语速设置。扩散与语音共用进程管理；增加参数 / 时长 / WAV 检查、执行来源、固定库依赖 / 许可与原生日志边界。62 项语音主机检查、89 项 UI 检查、18 个原生文件包校验；没有手机语音输出。同步双语 [语音文档](docs/TTS_ENGINE.md)、实施记录和界面媒体；模型许可 / 发音 / 后台等仍待验收，不创建 Release、不缩减完整 v0.3.0。Add the compiled speech worker, three explicit user-owned candidates, speech controls, shared process ownership, WAV guards/provenance and pinned dependencies/notices in dev.3. Host/UI/package evidence stays separate from missing phone inference and full release acceptance.

- 2026-10-27：内部 0.3.0-dev.2 / code 6 新增可在零模型状态独立启停的鉴权接口、持久任务提交 / 幂等 / 事件 / 取消 / 重试、产物元数据与 Range 下载；文本引擎改为独立回环端口和进程密钥，统一接口校验模型独立输出上限并跟踪客户端占用。更新服务页、双语 API / 实施说明和明确标记的界面媒体。模型仍由用户选择，不自动下载；完整引擎 / 模型与真机验收仍待完成，不创建 Release。Add the independent authenticated zero-model gateway, shared durable job/event/artifact routes, private text endpoint and profile/lease enforcement in internal dev.2. Refresh UI, bilingual guides/media and scoped host evidence; full model/device gates remain open.

- 2026-10-27：开始实现同一完整 v0.3.0，内部版本 0.3.0-dev / code 5。新增多组件包、显式下载 / 导入、独立参数与联合约束、持久任务 / 产物、标签 / 表单 / 队列 / 导出界面，以及原生 Windows 构建的 Android ARM64 sd.cpp worker；外置模型专用词表，锁定新原生文件和许可，在“全部”新增一套未实测的固定 SD1.5 候选包元数据，资产仍由用户选择下载，保留推荐及旧文本路径。新增开发截图 / 录屏 / GIF 与[双语实施记录](docs/DEVELOPMENT.md)。完整模型范围、统一 API、真机生成及耐久仍未完成，不创建 Release、不拆版、不默认顺延。Begin the complete v0.3.0 implementation with internal 0.3.0-dev: bundles, explicit transfers/import, per-recipe schemas, durable jobs/artifacts, flat task UI/export and an ARM64 sd.cpp worker built on native Windows. Externalize vocabularies, pin native hashes/notices, preserve recommendations/text. Add labeled development media/evidence; all required model/API/device gates remain open and no Release is created.

- 2026-10-27：明确 App 仅更新基座，01–14 / 16 / 17 是运行支持 / 配方覆盖目标，权重与模型专用资产由用户独立选择、下载、导入、管理和删除。安装 / 升级 / 浏览不触发模型下载，不强制模型更新或静默替换；推荐为元数据，功能标签与安装状态分开。新增 A11 资产分离验收并同步双语文档 / 结构化策略。Clarify foundation-only App updates and explicit user model-asset control; add A11, preserve flat task/dependency tags and single-release coverage. Documentation only; no APK/runtime changes.

- 2026-10-27：按用户最新要求取消分版本工作线路，下一版本 **v0.3.0** 统一交付 F-01–F-12、既有生文、01–14 / 16 / 17 及全部冻结子目标，含 SD 1.5 / SDXL LoRA；新增同版发布门槛与[交付摘要](docs/releases/v0.3.0-plan.md)。撤销默认顺延或缩减预览代替完成；风险保留为本版阻塞。Consolidate the full foundation and selected models into one complete next v0.3.0, without release splitting or automatic deferral; add common release gates and delivery summary.
- 同步双语需求、模型目标版本、结构化范围 schema v2、基座 / 任务 / 研究文档、README / 导航 / 贡献与发布约定。仅文档维护，当前 APK / 公开版本 / 媒体与附件不变。Synchronize bilingual specs, schema v2, model targets and related guides; documentation only, current APK/version/media/assets unchanged.

- 早期提案（已由上述单版要求覆盖）/ Earlier proposal superseded by the single-release scope：按当时范围补齐[双语需求与发版评估](docs/MULTIMODAL_RELEASE_PLAN.md)和[结构化编号 / 标签](docs/proposals/multimodal-release-scope.json)：01–14 / 16 / 17、12 项基座需求、四版拟定范围、子目标与真机验收；所有模型平级，功能 / 基座依赖 / 兼容 / 许可 / 内容标签独立。Complete bilingual requirements, feasibility, 16-group scope, flat tags, foundation requirements, four proposed releases and device acceptance.
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
