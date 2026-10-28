# 文本模型与共用基座

[English](TEXT_ENGINE.en.md) · [HF 配方](HF_RECIPES.md) · [模型更新](MODEL_UPDATES.md) · [开发状态](DEVELOPMENT.md)

适用：**0.3.0-dev.10 / code 14，内部检查点，尚未完成或发布完整 v0.3.0**。用户新建文本包及[迁移的已有 GGUF](MODEL_MIGRATION.md)共用参数、任务、产物与模型版本管理。既有推荐、聊天 ID 和常驻 API 保留；[共用自动调度](SCHEDULING.md)已接入；物理设备升级验收仍待完成。

## 选择与使用

1. 在“全部 / 搜索”打开 HF 仓库文件页，选择“构建模型包 / LoRA 配方”，再选择 **文本 GGUF · CPU**。模板只有配方元数据，不包含权重。
2. 为 `text_gguf` 选择一个包含 tokenizer 的完整文本 GGUF，核对固定 revision、字节数、校验、许可与下载计划。加入本地仅登记；下载或文件夹导入须由用户另行操作。拆分 GGUF、视觉 / 音频组件和自定义代码不在这套配方内。
3. 安装完成后在“本地”打开详情与模型设置。文本模型与图像、视频、音频模型平级，使用“生文”及 `llama_text / text_gguf / GGUF / CPU` 等标签。HF 文件扩展名和模板选择不能证明其架构被当前引擎支持。
4. 编辑该模型的线程、上下文、输出上限、采样温度、思考模式和系统提示词。选择“使用”，填写提示词并明确选择尝试未测配方，再提交同一任务队列。任务等待当前回复并自动切换引擎，空闲后恢复用户仍希望运行的文本模型；新任务不改换用户选定的聊天模型。
5. 任务结束后在结果库打开正文，可单独展开思考内容，复制正文、导出原始 JSON 或导出生成记录。达到输出上限会显示相应结束原因；取消、断流或无结束事件不能记为成功。

推荐 `m08 → m06 → m01`、已有权重内容、原 ID 和独立配置保留。App 安装 / 升级 / 浏览不选择、下载或替换模型；本地存储与记录迁移复用已有文件，正在加载 / 运行的旧模型等待退出后再绑定。

## 参数和版本边界

保存设置、提交任务和执行都会校验参数。通用参数 schema 新增 `maximumFrom: {"field":"context","offset":-1}`，表示输出上限同时受上下文约束；前端和原生端均回填合法值，循环或无合法交集会报错。

安装后读取实际 GGUF v2/v3 架构与上下文 metadata，并取配方、模型、CPU 和应用保护值的交集。未知上下文标记为未知，使用 8192 的应用保护值；已知上下文还受当前队列 131072 的分配保护限制。该保护值不是模型质量或内存实测结论。线程不超过可用 CPU；温度 0–2；系统提示词最多 4000 字符，任务提示词最多 16000 字符。

有效 schema 与不可变来源清单分开，既不修改模型来源也不重写权重。不兼容的导入配方单独显示错误，不会使整个模型库不可用。版本差异核对指纹包含两版有效 schema：如果下载后首次发现实际 GGUF 限制，原确认失效，需要取消旧计划并重新核对，保留已下载资产；不会沿用旧确认静默启用。

## 执行、结果和 API

`TextEngine` 复用已锁定的 `libllama-server.so` 与依赖，作为 `LocalEngine` 执行。每个任务使用单独的私有回环端口、随机密钥与固定模型包 ID；密钥在进程环境中，用户提示词经 POST 传入，不进入进程参数或 UI 日志。不跟随推理重定向，不增加外部推理。进程退出后才释放执行所有权。

载入保护时限为五分钟，队列单任务保护为两小时；这些都是应用上限，不是手机速度承诺。取消绑定任务和工作进程。SSE 校验单输出序列、正文 / 思考通道、正常 finish reason 和 `[DONE]`；行、事件、总流和结果分别有大小保护。完整结果保留最多合计一百万个 UTF-16 字符，序列化最多 8 MiB。

结果 MIME 为 `application/vnd.lma.text+json`：

```json
{"schema":"lma.text-result/1","content":"正文","reasoning":"思考内容","finishReason":"stop","usage":{"prompt_tokens":10,"completion_tokens":20,"total_tokens":30}}
```

`finishReason` 为 `stop` 或 `length`；未提供的 token 计数不伪造。原生产物校验后才入库，并保存模型、组件回执、有效参数、引擎及执行来源。UI 仅从自身受控本地产物路径读取 JSON，以纯文本显示正文和思考；内容中的 HTML 不执行。

新模型包通过现有异步任务 API 使用 `type: "text.generate"`，输入 `{"prompt":"..."}`，产物沿用鉴权和 Range 接口。现有 `/v1/chat/completions`、`/v1/completions` 仍服务已加载的旧文本路径，不能据此宣称全部聊天 / API 调度已统一。查看[API 文档](API.md)。

## 当前证据与剩余工作

66 项新增主机检查运行真实生产 Java、文件系统、子进程和鉴权回环 HTTP，使用零 tensor 的 GGUF metadata 与固定文本夹具；覆盖实际参数、版本确认过期、取消、断流、重定向、错误退出、产物和进程清理。它们**没有下载模型、没有运行模型推理，也不是 Android 模拟器**。公开回执见 [text.json](../verification/development/text.json)。

[参数截图](media/development/22-text-model-settings.png) · [任务表单](media/development/23-text-queue-form.png) · [文本结果](media/development/24-text-result.png) · [录屏](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif)。所有媒体保留 UI FIXTURE 标记，正文也是固定测试数据。

本地迁移代码与 69 项主机检查已接入；物理 Android 升级、完整聊天 / API 调度、全部已选模型及离线 / 取消 / 后台 / 资源 / 质量验收继续属于同一 [v0.3.0 完整范围](MULTIMODAL_RELEASE_PLAN.md)。本次不创建新 Release。
