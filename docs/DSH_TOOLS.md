# DSH 与 OpenAI 工具调用 · v1.1.0

**m04已知模板缺口，修复待完成：** v1.1.0/v1.2.0使用的固定Dolphin1B GGUF发布默认模板未渲染工具。实际生效模板与DSH任务闭环待真机核对；[来源、修复项与完整41工具验收](DSH_M04_TOOL_TEMPLATE_ASSESSMENT_20261106.md)已单独记录。

[English](DSH_TOOLS.en.md) · [API](API.md) · [运行与卸载](MODEL_RUNTIME.md) · [版本说明](releases/v1.1.0.md)

## 1. 解决的问题与连接方式

v1.0.2/code67 的入口白名单先拒绝了 DSH 的 `store:false`、`tools`、`tool_choice` 和工具消息。这是接口实现缺失，不能据此判断 Qwen 3.5 的工具能力。v1.1.0/code68 将函数声明、模型原生工具输出、客户端执行和结果回传接成完整协议，不通过关闭工具或改写成普通聊天绕过问题。

手机安装本版后，打开“服务”并启动接口。在同一手机上的 DSH 设置 OpenAI 兼容地址 `http://127.0.0.1:52187/v1`，使用 LMA 显示的密钥，从模型列表选择完整安装的模型，例如 `m15`。端口以用户实际设置为准；其他设备上的客户端需要显式开启内网访问并填写手机地址。推理仍由这台 Android 手机执行。

模型无需常驻才能启动接口。API 仅能按需加载目录中已完整安装、已配置且被发布的文本模型；不会下载权重。工具由 DSH 或调用客户端执行，LMA 不执行外部请求中的 shell、文件、网络或代理工具。它也不把任意客户端函数限制为 App 内置的创作工具集合。

## 2. 请求和响应合同

| 编号 | 支持内容 | 行为 |
| --- | --- | --- |
| T01 | `tools` 函数声明 | 最多128个不重名函数；保留名称、描述、参数 schema 和 `strict` |
| T02 | `tool_choice` | `auto`、`none`、`required`、具名函数对象；指定名称必须存在 |
| T03 | `parallel_tool_calls` | 支持布尔值；工具调用并行与手机推理解码并行是不同概念 |
| T04 | 助手工具消息 | 接受 `tool_calls`，其 `content` 可为 null 或省略；保留调用ID、名称及字符串参数 |
| T05 | 工具结果 | 接受 `role:tool`、`tool_call_id` 和字符串／文本分块内容；支持一轮多个结果及后续多轮 |
| T06 | 普通消息 | system、developer、user、assistant；文本字符串或 `[{"type":"text","text":"…"}]` |
| T07 | `store` 与调用提示 | `false`／null兼容；true明确拒绝，不提供完成记录查询。metadata、user、safety_identifier、prompt_cache_key 经边界检查后消费，不用于存储或对外执行 |
| T08 | 输出 | 非流式 `message.tool_calls`；SSE `delta.tool_calls[index]`、ID／函数名／arguments 分片、`finish_reason:tool_calls`、usage 与 `[DONE]` |
| T09 | 输出配置 | 保留逐模型温度、上下文、输出限制；接受 max_tokens 或 max_completion_tokens，不能同时传；支持模型模板解释的 reasoning_effort |
| T10 | `response_format` | text、json_object、受支持 JSON Schema 子集；strict结构化输出在交付前检查 |

工具历史的每个调用都必须收到恰好一次匹配结果，之后才能继续下一条非工具消息。孤立、重复或缺失结果会给出 `error.param`。不执行媒体URL读取；Responses、旧 `functions/function_call`、自定义工具类型、任意供应商参数及所有 OpenAI 产品能力不在本合同内。

## 3. 原生模板、具名选择和 strict

继续使用锁定的 llama.cpp `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` 与 `--jinja`，没有把函数协议拼成普通聊天。该版本具名对象会落回 auto，因此网关把本次允许函数集合收窄为指定函数并传原生 `required`，再检查实际输出。模型自己的 GGUF 模板必须支持工具；接口兼容不能把所有模型变成可靠代理。

原生版本未完整执行 `function.strict`。网关校验完整参数、声明函数、调用ID、并行限制和结束原因；strict 参数不合格则返回 `invalid_model_output`，不交付可执行工具分片。strict 流在实际工具分片出现后缓冲至该轮校验通过；之前的真实文本／推理仍可流出。客户端仍须校验工具权限和执行结果。

支持 object/properties/required/additionalProperties、数组、字符串／数值边界、enum/const、anyOf/oneOf/allOf/not、受限 pattern/format、$defs／definitions 和本地 `$ref`。限制复杂度和嵌套；外部引用、未知关键字及高复杂度正则明确拒绝。严格参数必须是合法 JSON，不能使用单引号、裸键或尾逗号。这是有边界的子集及交付前校验，不声称完整 JSON Schema 或所有 schema 都由原生解码语法约束。

## 4. 并发、容量与上下文

| 边界 | v1.0.2 | v1.1.0 |
| --- | --- | --- |
| 文本并发入口 | 文本忙时409 | 最多9个已接纳请求，通常1个执行＋8个等待；共用FIFO执行槽 |
| 文本请求正文 | 256 KiB | 4 MiB；已接纳请求序列化JSON合计16 MiB |
| 消息 | 128条／单条64,000 UTF-16单位 | 1024条／单条1 MiB UTF-8；请求总量仍受4 MiB限制 |
| 文本JSON嵌套 | 32 | 64；schema校验另有复杂度预算 |
| 其他JSON／上传块 | 256 KiB | 保持256 KiB；上传文件上限512 MiB |
| 推理解码 | 1路 | 保持1路，排队不会增加KV缓存副本 |

16 MiB预算按解析后紧凑序列化的JSON计算，不等于原始HTTP字节或总堆内存；传输／解析另受9路线程和单请求4 MiB边界约束。Sub2API配套转发器同步采用4 MiB文本上限，工具历史和SSE原样转发。

专用文本工作线程与健康／目录／取消等控制请求分离。队满返回429及 `Retry-After: 1`，客户端应退避；并发请求在父回合返回后释放执行槽，不持有它等待 DSH 执行工具或子代理。

推理前用实际 GGUF 的 `/apply-template` 和 `/tokenize` 计算包括函数定义的输入。超过所选上下文返回 `context_length_exceeded`，不截断历史；输出预算取“请求值、该模型保存的上限、上下文剩余量”的最小值。4 MiB入口不代表手机能处理同样长的上下文；也没有无限并发或无限内存承诺。

流式请求通过校验和准入后先返回HTTP200，加载／排队时每约8秒发送SSE注释保活，首次约2秒；这些不算模型token。后续失败以 `data: {"error":…}` 交付且不补造成功 `[DONE]`。非流式模型错误在响应头前返回对应HTTP状态。strict失败、模板错误、上下文、取消和资源停止分别保留错误信息。`X-Request-ID` 便于定位，`X-LMA-Max-Tokens` 为准入时逐模型输出上限，实际剩余上下文可能进一步降低输出预算。

不增加生成总耗时上限。保留连接建立、请求解析、阻塞写入保护及显式取消。流式客户端断开会通过写入／保活失败取消对应请求；非流式排队连接断开可能到后续写入才被检测。用户在运行管理卸载会取消当前及排队文本请求，API监听继续运行。

## 5. 完整调用示例

```python
import json
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:52187/v1", api_key="YOUR_LMA_KEY")
model = "m15"  # 换成 /v1/models 中已安装的实际ID
tools = [{"type": "function", "function": {
    "name": "sum_numbers", "description": "计算两个整数的和",
    "strict": True,
    "parameters": {"type": "object", "properties": {
        "a": {"type": "integer"}, "b": {"type": "integer"}},
        "required": ["a", "b"], "additionalProperties": False}}}]
messages = [{"role": "user", "content": "请调用工具计算20加22。"}]
reply = client.chat.completions.create(
    model=model, messages=messages, tools=tools, store=False,
    tool_choice={"type": "function", "function": {"name": "sum_numbers"}},
    parallel_tool_calls=False, max_tokens=512)
assistant = reply.choices[0].message
messages.append({"role": "assistant", "content": assistant.content,
                 "tool_calls": [t.model_dump(exclude_none=True) for t in assistant.tool_calls]})
for tool in assistant.tool_calls:
    assert tool.function.name == "sum_numbers"
    args = json.loads(tool.function.arguments)
    result = args["a"] + args["b"]  # 由调用方执行
    messages.append({"role": "tool", "tool_call_id": tool.id, "content": str(result)})
for chunk in client.chat.completions.create(
        model=model, messages=messages, tools=tools, tool_choice="auto",
        store=False, stream=True, stream_options={"include_usage": True}):
    for choice in chunk.choices:
        print(choice.delta.content or "", end="")
```

实际代理应循环处理后续工具调用，按index拼接流式参数，等待该轮完成后再执行，并保留客户端自己的审批、取消和错误策略。上例只展示一次工具往返，不要求 DSH 缩减能力。

## 6. 验证范围与复现

`tools/test_openai_tools.py` 验证生产协议、严格校验和实际并发HTTP socket；`test_backend.py` 覆盖父回合、四个并发子请求、回传结果和上下文溢出；`test_scheduler.py` 覆盖与媒体共用执行槽、取消及资源错误。它们使用明确夹具，不算模型推理。

选择性真机结果见[本版 physical-tools.json](../verification/releases/v1.1.0/physical-tools.json)，与[程序证据](../verification/releases/v1.1.0/status.json)分开。测试使用已装 m15、真实 OpenAI SDK 与手机原生引擎。**DSH v1.4.76 App 本身的完整交互、任意工具／模型质量和长期代理耐久不据此宣告通过。** 保留现有模型和参数，不下载模型。

发布后增加[实际DSH客户端代码复核](DSH_CLIENT_AUDIT.md)：79项补充检查直接导入该安装包的适配器、Models层和编解码器，经生产Java HTTP／协议层验证49份工具声明变体及多轮流式回传。另复现DSH默认300秒空闲计时：SSE保活注释不能重置这一客户端计时，长预填充／排队应单独配置等待阈值。非默认提供商专用字段与App实机待验项在该文档中明确罗列。

官方依据：[Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)、[Function calling](https://developers.openai.com/api/docs/guides/function-calling)、[锁定 llama.cpp 工具说明](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/docs/function-calling.md)。本指南的具体边界以本版实现和证据为准。
