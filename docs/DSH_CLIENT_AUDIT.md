# DSH 1.4.76 客户端代码互操作复核

**后续 v1.2.1：** 该客户端程序复核已针对修复后的生产核心重跑，并纳入本版门禁；实际手机／41工具任务另见[m04修复记录](DSH_M04_REPAIR.md)。下文手机暂停与v1.1.0结论保留原时间点含义。


[English](DSH_CLIENT_AUDIT.en.md) · [工具协议](DSH_TOOLS.md) · [卸载模型](MODEL_RUNTIME.md)

本次复核针对已发布的 **LMA v1.1.0 / code68**。在用户告知手机另有任务使用前，已核对安装包 SHA256 与正式 Release 一致；随后停止操作手机。下述新增检查全部在 Windows 原生环境中运行，不连接手机、不启动 DSH App、不执行其工具，也不加载模型。

## 1. 检查对象与方法

检查对象来自已安装的 **DSH Android v1.4.76 / code327，`app.dsh.mobile`** 的静态 APK。版本、包哈希和运行包哈希锁定在 [client lock](../tests/dsh-client-lock.json)。DSH APK、运行包、第三方代码及中间请求仅保存在被 Git 忽略的 `build/dsh-client-verification/`，不随 LMA 分发。

测试导入该包中真正的 `@deepseek-ai/dsh-llm-pi-ai`、pi-ai Models、`@earendil-works/pi-ai` Chat Completions 编解码器和 OpenAI SDK，使用自有合成消息。其 HTTP 请求经过 LMA 生产 `LocalHttp`、`LocalApi`、`TextRequest`、`ChatProtocol`、`JsonSchema` 和 `ToolReply`。原生模型输出由明确标记的 SSE 夹具代替；包括三字节读取、交错参数、错误和断流。

工具插件只向测试注册表提交声明；文件、网络、终端、定时任务、后台任务、子代理及工具处理函数均不执行。平台专用工具的 schema 可通过协议，不代表这些工具能在 Android 上执行。并发检查使用两份独立客户端适配器；真实执行槽和四子请求回传另见既有程序证据。

## 2. 覆盖项目

| 编号 | 检查内容 | 验证边界 |
| --- | --- | --- |
| D01 | 已安装 LMA 的版本、APK 哈希与正式版一致 | 在本轮暂停手机操作前核对；不是重装 |
| D02 | DSH 实际工具包的函数名称、描述与参数 schema | 含子代理／控制、后台任务、文件、网页、终端、定时、工作流等；只注册声明 |
| D03 | 默认 `store:false`、`max_completion_tokens`、`stream_options` | 经过真实客户端请求组装和 LMA 校验 |
| D04 | 流式工具调用、思考字段、usage、客户端持久化回放 | 执行能力来自客户端事件，不把工具改写成聊天 |
| D05 | `content:null`、`tool_calls`、`role:tool`、ID 对应 | 保留完整两轮工具结果回传及继续生成 |
| D06 | 多调用交错、乱序回传、中文／emoji、工具失败 | 生产响应守卫和实际客户端解析器共同验证 |
| D07 | 会话中的工具增减、长消息和长历史 | 超过旧 256 KiB／128 消息／64,000 字符限制；模型上下文仍独立预检 |
| D08 | 两份客户端并发、超量请求、输出上限和原生错误 | 非 DSH 真子代理、非新一轮手机调度测评 |
| D09 | 客户端空闲超时、非默认兼容选项 | 负向检查明确拒绝，不能写成全部配置通过 |

**79 项补充检查通过**，包括25个工具包、49份声明变体、45个工具名。完整结果见 [client-code.json](../verification/supplemental/v1.1.0/client-code.json)。这是补充程序证据，原 Release 的程序数量、APK、源码包、媒体和真机记录保持原有身份。

## 3. DSH 的独立超时

该客户端 `streamIdleTimeoutMs` 默认 **300,000 毫秒**。它等待适配器产生内容、工具或结束等事件。OpenAI 编解码器忽略 SSE 注释，DSH 也不将单独的 `start` 转成可见事件，因此 LMA 的 `: lma keepalive` 能保持连接，却不能重置 DSH 的这个计时器。

补充测试把客户端计时值缩为 120 毫秒，并在夹具中每 20 毫秒发送注释，复现其 `TIMEOUT`。这不是五分钟真机耐久测试。LMA 本身没有新增或恢复生成总时限，也不会发送假的模型文字／思考来骗过客户端计时器。

若手机上的真实模板预填充、严格参数缓冲或队列等待超过客户端容忍时间，需要在 DSH 提供商高级配置中增大 `streamIdleTimeoutMs`，并结合其重试与取消策略处理；该包的配置 schema 不允许用 0 表示无限。LMA 侧仍保留真实取消、满队 429、上下文溢出和资源不足错误。改变等待阈值不会关闭工具、子代理或改写代理模式。

## 4. 兼容范围与待验项目

默认 **OpenAI Chat Completions** 自定义提供商是本次对象。请使用原有 API Key、`http://127.0.0.1:52187/v1` 和实际本地模型 ID。DSH 通过其原工具系统执行任务。

特定远端提供商的额外线协议不自动成为本地接口能力。例如非默认 `compat.requiresToolResultName:true` 会额外发送 `role:tool.name`，LMA v1.1.0 会明确返回 400；默认配置为 false。OpenRouter 的 `reasoning_details`、其他供应商的 `thinking`／`priority` 等扩展及 Responses API 也不属于本次函数工具兼容承诺。不要把这些提供商专用开关当作关闭 DSH 功能的接入前提。

| 编号 | 尚需验证 | 当前状态 |
| --- | --- | --- |
| P01 | 在 Android 的 DSH App 内，从工具声明到真实工具执行、回传和续答 | 手机被其他任务使用，按用户要求暂停；本次代码互操作不冒充这一结果 |
| P02 | DSH 真子代理调度、审批／取消和长任务的端到端体验 | 生产队列已有程序／手机选定证据；DSH App 体验仍待单独验收 |
| P03 | 任意模型的工具选择正确率、多模态输入和长期后台耐久 | 未因此扩大验证范围；文本函数接口不会抓取图片或替代独立媒体 API |

既有 [m15 真机／OpenAI SDK 21 项记录](../verification/releases/v1.1.0/physical-tools.json)继续有效，并明确 `dsh_app_tested:false`。模型正确选工具、正确生成参数与协议被接受是分别评估的事项。

## 5. 复现

从合法取得的同版 DSH APK 运行以下命令。测试不下载 APK，不调用 ADB，不运行模型，要求原生 JDK、Python、Node.js 22+，以及构建指南中锁定的 `json-20250517.jar`。

```powershell
python tools/test_dsh_client.py --apk build/dsh-client-verification/dsh-installed.apk
```

结果写入忽略目录 `build/dsh-client-verification/client-results.json`；源码指纹和客户端版本哈希都纳入结果。重新运行基础生产协议检查可使用 `python tools/test_openai_tools.py`。截图和录屏沿用该正式版对应的真实媒体，本轮未伪造新的手机画面。
