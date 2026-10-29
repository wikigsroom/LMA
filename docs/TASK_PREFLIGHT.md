# 运行前检查与输入复核

[English](TASK_PREFLIGHT.en.md) · [生成工作台](TASK_WORKBENCH.md) · [API](API.md) · [编号实现与完整待办](releases/v0.3.0-dev.26.md)

内部开发版 **0.3.0-dev.26 / code 30**。在生成表单点击“运行前检查”，先看到本次请求能否加入本机队列，再处理缺失项并主动提交。检查本身不创建任务，不启动推理、不下载文件，不更改模型默认设置，也不启动后台服务或 API。

## 使用逻辑

1. 在模型“本地”选择已安装模型，填写提示词、参考素材、LoRA 与本次参数。推荐原有内容保持不变，其他模型仍由 HF 全部 / 搜索或本地导入添加。
2. 点击“运行前检查”。未确认试运行也可以先查看资源和参数；确认选择仍由用户自己操作。
3. 缺少模型或 LoRA 时，显示模型 ID、缺少组件角色、字节数与需要导入的项目，并可进入本地模型管理。下载 / 续传 / 导入由用户明确选择；有已复用组件也不等于模型已经安装。
4. 素材错误可进入任务页的“素材与结果”处理；参数问题留在当前表单修改。需要离开表单时可先“保存草稿”。从表单导入完成后会刷新可选素材，保留已填写的文字和仍有效的选择。
5. 当前已选素材被删除或不再匹配时，会清除失效引用，显示复核勾选框；用户重新检查当前选择后才能提交。必需的素材仍须重新选择。
6. 修改文字、参数、LoRA、确认选项或素材后，旧检查结果失效；检查过程中修改输入也不会把过期结果显示为就绪。
7. “可加入本机队列”表示当前提交条件通过。用户点击“加入本机队列”才创建任务；实际提交和执行前均重新检查。之后可查看任务、打开结果、恢复请求和复用素材，参见生成工作台。

## 实际检查内容

| 阶段 | 行为 |
|---|---|
| 请求 / 模型 / 引擎 | 支持的生成任务格式、模型能力、本地引擎和配方；LoRA 不能单独运行 |
| 参数 | 当前模型独立默认值加本次覆盖值、超限归位、联合约束与引擎约束；返回有效参数和调整项 |
| 模型组件 | 基础模型与所选 LoRA 的安装记录、必需文件和兼容性，全部明示选择 |
| 参考输入 | 素材存在、媒体类型、大小、尺寸 / 时长与参考原文合同 |
| 资源 | 总共享内存减保留量的排队预算、当前可用内存、峰值估算和 LoRA 附加预算、产物空间 |
| 用户选择 | 未实测配方需要明确试运行确认；检查不会代勾 |

排队预算使用总内存；执行预算使用当时可用内存。当前内存压力可作为排队提示，执行时仍可因低内存、温度或空间不足拒绝启动。未知峰值明确显示“未知”，不会把估算或通过检查写成真机运行成功。检查使用当前存储元数据；执行阶段保留文件完整性复查。任何一次检查都不预留模型或资源，也不保证未来一定能执行。

界面与 API 共用生产 `LocalJobs.GenerationPlan`，提交也调用同一解析器；原有请求幂等性和不可变队列快照保留。运行资产准备 / 关联使用它们自己的已签名方案，此接口只接受生文、生图、生视频、语音合成与音频生成请求，不接收外部执行节点。

## 本地 API

`POST /v1/jobs/preflight` 使用与 `POST /v1/jobs` 相同的生成请求正文及现有 Bearer 鉴权。需要预先明确启动 API；这条请求不会替你开启模型服务。浏览器 Origin、正文长度等现有边界继续生效。

```http
POST /v1/jobs/preflight
Authorization: Bearer YOUR_LMA_API_KEY
Content-Type: application/json

{"bundleId":"YOUR_INSTALLED_BUNDLE_ID","type":"image.generate","input":{"prompt":"a quiet garden"},"parameters":{"steps":20},"allowUnmeasured":true}
```

合法 JSON 检查结果返回 `200`，`canEnqueue` 为 `true` 或 `false`；阻塞条件不是失败任务记录。主要字段：`schema=lma.task-preflight/1`、`checkedAt`、`submissionHash`、`checkedStages`、`issues[{code,message,action}]`、`warnings`、已解析的 `modelAssets` / `effectiveParameters` / `adjustments` / `resources`。未到达阶段的字段可缺省；首次阻塞后停止后续检查，不冒充全面扫描。

处理动作是提示：`manage_models`、`manage_inputs`、`edit_request`。客户端修复后重新检查并明确 `POST /v1/jobs`；`submissionHash` 只标识输入，不是预约、授权或可以跳过重新校验的凭据。未经鉴权返回 `401`，错误方法返回 `405`，非 JSON / 超限正文沿用协议错误；基座未初始化可返回 `503`。

## 验证与媒体

[当前证据](../verification/development/status.json)保留生产校验器、实际桌面存储 / 子进程和 HTTP 的结果，与历史模型实验分开。Android 推理与后台实测仍为 0；没有新增模型通过项。

| 提交条件与资源 | 素材变化复核 |
|---|---|
| ![资源和有效参数](media/development/preflight/02-ready.png) | ![失效引用复核](media/development/preflight/04-input-review.png) |

[录屏 MP4](media/development/preflight/preflight-ui.mp4) · [GIF](media/development/preflight/preflight-ui.gif) · [媒体哈希与页面指纹](media/development/preflight/manifest.json)。这些是带 UI FIXTURE 标记的生产页面操作，使用桌面模拟桥，没有 Android / 模型执行；浏览器资源结束后关闭。
