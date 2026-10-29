# 用户选择的运行模型关联

dev.28 新增 [LCM 条件组件关联](LCM_APP_FLOW.md)，复用相同的角色、指纹、私有租约与暂停依赖流程；关联不会自动下载，完整安装后才允许用户明确提交生成。

[English](MODEL_ASSEMBLY.en.md) · [源模型准备](MODEL_PREPARATION.md) · [完整发版范围](MULTIMODAL_RELEASE_PLAN.md) · [本轮编号交付](releases/v0.3.0-dev.23.md)

dev.23 增加通用 `model.assemble` 任务。App 交付关联方案、存储和执行基座；用户选择源模型、准备资产、运行模型及后续依赖。安装、升级、浏览、缺少资产的请求都不触发模型下载。关联资产不代表生成引擎已经支持该模型。

## 使用逻辑

1. 在“全部”选择源模型，主动下载或从文件夹导入。已有“推荐”顺序和标记不变。
2. 在“本地 → 运行资产”查看准备方案，明确确认空间要求后启动准备；源模型及设置保留。
3. 准备完成后点击“查看关联方案”，核对目标模型、复用组件及仍缺少的依赖。浏览此页不转换、不下载。
4. 点击“开始关联”，进入共用任务队列。App 完整校验本地准备文件，将选定组件关联到独立运行模型记录。
5. 在“本地”管理该运行模型。缺少的依赖保持暂停、未安装，由用户再次明确选择“下载所选模型包”或“从文件夹导入”；已校验的组件复用。
6. 完整安装与引擎可用是两个条件。只有存在实际已登记的生成引擎及合法参数/输入时才能尝试生成，设备状态仍按证据展示。

## 首个固定候选

`ltx098_runtime_google_q5_v1` 是**旧 LTX-Video 2B 0.9.8 distilled + 社区 Google T5 Q5 单尺度**运行资产候选。它不是官方 PixArt 编码器、多尺度/放大/提示词增强默认配方，不将不同权重或配方的证据混用。

| 组件 | 来源及身份 | 大小 | 由谁决定取得 |
| --- | --- | ---: | --- |
| DiT GGUF、9 个 VAE ONNX 图、9 个外部权重文件及清单，共 20 项 | 既有 `ltx098_dit_vae_v1` 方案；路径/角色/字节数/SHA-256 与准备结果完全绑定 | 6,061,184,991 B | 用户先下载/导入源模型，再明确准备及关联 |
| `t5-v1_1-xxl-encoder-Q5_K_M.gguf` | `city96/t5-v1_1-xxl-encoder-gguf`，revision `005a6ea51a7d0b84d677b3e633bb52a8c85a83d9` | 3,386,856,640 B | 用户明确下载或导入 |
| `tokenizer_config.json` | `google/t5-v1_1-xxl`，revision `3db67ab1af984cf10548a73467f0e5bca2aaaeb2` | 1,857 B | 用户明确下载或导入 |

保留原始源模型、准备文件及两项 T5 共占 15,788,787,980 字节模型数据；硬链接不会再增加一份 6.06GB 副本，另需准备/下载保留空间及其他模型/系统空间。

22 项完整身份见 [固定清单](../catalogue/model-bundles.json) 及 [关联方案](../catalogue/model-assemblies.json)。以上身份复用已经实测的训练组件与固定来源记录，不能称为本轮重新在线验证 HF。20 个派生文件没有下载 URL；它们必须来自正确的本地准备结果或用户的显式文件夹导入。尚未关联派生组件时，依赖不完整的下载按钮禁用。

当前候选标签为 `video`、`runtime_assets`、`derived_assets`、`community_google_t5_q5`、`single_scale`，状态 `runtime_assets_only`、`generationSupported=false`。它与生文、生图、生音频模型平级。`ltx098_native` 生成引擎仍未登记；关联任务不启用“生成”按钮。

## 通用基座契约

| 编号 | 实现 | 约束 |
| --- | --- | --- |
| A01 | APK 签名保护的 `lma.model-assembly/1` 描述符 | 只含源/目标 ID、准备方案 ID、角色映射；不接收用户程序、路径或 URL |
| A02 | 在实际运行环境绑定准备方案及目标清单指纹 | 源输出与目标组件必须具有相同字节数和 SHA-256；映射唯一，不能偷换模型 |
| A03 | `TaskInput`、`JobStore`、`LocalJobs`、执行槽 | 请求不可变、幂等键、重复活动目标保护、文本让位、两小时任务保护、取消/明确重试共用 |
| A04 | `PreparedAssets` 完整 SHA 校验及读取租约 | 排队/运行的引用保护准备记录；目标模型也受任务引用保护 |
| A05 | `BundleStore.adoptAvailableLocal` | 已拥有的文件在同一私有文件系统内硬链接复用，不额外复制模型，不调用下载器；文件系统不支持时明确失败并保留原文件 |
| A06 | 组件对象及元数据原子提交 | 缺少组件时为 `paused`、`installed=false`、空传输 token；保留原模型参数，不自动生成 |
| A07 | 独立管理 | 删除准备资产后运行记录仍保留其硬链接；删除运行资产后准备文件仍保留；删除任何一份记录不保证另一份仍引用的磁盘字节立即释放 |
| A08 | 取消及重启 | 提交前取消不发布安装；原子提交后与取消竞争时可以保留已校验的关联（缺少依赖时仍暂停），任务仍为取消，无成功媒体；重启不自动恢复下载，受损文件下次租约完整验哈希后拒绝 |
| A09 | API 与结果 | `/v1/models` 展示已选择的部分运行模型及真实 `installed/reusable_bytes/remaining_bytes`；准备记录含 `assemblyPlans`；任务返回关联收据，不伪造媒体产物 |

手机上的前台服务、唤醒锁及执行槽属于既有基座。这里没有 ROOT、外部执行节点、远程推理或 ComfyUI 连线/插件系统；不能据源码推断厂商系统一定允许长期后台运行。

## API

先从模型列表的 `prepared_assets[].assemblyPlans[]` 读取当前 App 计算的方案指纹，再显式提交：

```json
{
  "type": "model.assemble",
  "bundleId": "ltx098_runtime_google_q5_v1",
  "preparedAssetsId": "prep_<当前记录中的32位十六进制ID>",
  "assemblyId": "ltx098_google_q5_runtime_v1",
  "assemblyFingerprint": "<当前方案指纹>"
}
```

通过既有 `POST /v1/tasks` 提交及任务接口查看/取消。`assemblySourceFingerprint` 由服务在提交时冻结，客户端不得填入；重试重新校验当前来源。该任务不会调用模型接口、取得 T5、运行编码器或生成视频。

## 验证边界与完整交付

47 项生产 Java 核心契约覆盖严格输入、身份变更、文件篡改、硬链接、参数保留、排队/运行引用、取消、原子状态、独立删除及重启。完整训练文件的主机组装验证还逐项校验 20 个实际硬链接及剩余 3,386,858,497 B T5 依赖。共用队列/API 测试使用宿主 Android 框架替身；页面截图、MP4 和 GIF 明确标为 UI FIXTURE。

这些检查不是 Android 安装、SAF/私有文件系统关联、真实生成、画质、资源或后台耐久证据。此前完整旧 LTX 主机链路的 **6 项浮点门槛仍失败**。F-01–F-12、既有文本、01–14/16/17 全部冻结子目标、3 次加载卸载、15 分钟锁屏、1 小时交替 API、升级保留及 A1–A11/R01–R05 均属于同一个完整 v0.3.0；没有缩减或拆成后续版本。没有可用真机，正式 Release 尚未发布。

![关联确认，UI FIXTURE](media/development/66-assembly-review.png)

![仍缺依赖，UI FIXTURE](media/development/68-assembly-dependencies.png)

[录屏](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif) · [验证记录](../verification/development/status.json)
