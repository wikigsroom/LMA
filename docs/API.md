# LMA API 接入

[English](API.en.md) · [文档目录](README.md)

下列原有文本接入示例对应公开 **v0.2.0**。内部 **0.3.0-dev.2** 的独立接口、异步任务和产物接口见本文末节；开发包没有完成全部模型或真机验收。

## 地址、鉴权和模型

- 本机默认 Base URL：`http://127.0.0.1:8080/v1`。
- 外部设备：先在“服务”开启局域网，改用界面显示的手机 IP；客户端与手机需要网络可达。
- 请求头：`Authorization: Bearer YOUR_LMA_API_KEY`。密钥从手机界面复制，不是云端 OpenAI 密钥。
- `GET /v1/models` 返回当前加载模型的别名，例如 `m08`。HF 下载模型使用稳定的 `hf_...`，手动添加使用 `custom_...`，不要从文件名猜测 ID。HF 令牌只用于仓库访问，不能代替推理 API 密钥。
- 模型必须已加载且就绪；仅下载文件不足以提供接口。单模型、单推理槽不保证并行吞吐。

这里只承诺所述 OpenAI 兼容 models / chat-completions / SSE 表面，不承诺 Responses、语音、图像、嵌入、工具调用或所有供应商参数。

## curl

```bash
curl http://PHONE_IP:8080/v1/models \
  -H "Authorization: Bearer YOUR_LMA_API_KEY"

curl -N http://PHONE_IP:8080/v1/chat/completions \
  -H "Authorization: Bearer YOUR_LMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"m08","messages":[{"role":"system","content":"请清楚简洁地回答。"},{"role":"user","content":"你好"}],"temperature":0.7,"max_tokens":256,"stream":true}'
```

`PHONE_IP`、密钥和模型 ID 都需替换。`-N` 关闭 curl 输出缓冲。非流式请求使用 `"stream":false`；生成较慢时应适当延长客户端超时。

## Python（仅标准库）

设置 `LMA_BASE_URL` 与 `LMA_API_KEY` 环境变量，密钥不写进仓库或示例文件：

```python
import json
import os
import urllib.request

base = os.environ.get("LMA_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")
headers = {"Authorization": "Bearer " + os.environ["LMA_API_KEY"]}
request = urllib.request.Request(base + "/models", headers=headers)
with urllib.request.urlopen(request, timeout=30) as response:
    model_id = json.load(response)["data"][0]["id"]

payload = {"model": model_id, "messages": [{"role": "user", "content": "你好"}],
           "stream": True, "max_tokens": 256}
request = urllib.request.Request(base + "/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={**headers, "Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=300) as response:
    for raw in response:
        line = raw.decode("utf-8").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        event = json.loads(data)
        choices = event.get("choices", [])
        if choices:
            print(choices[0].get("delta", {}).get("content") or "", end="", flush=True)
print()
```

示例只输出正文；某些模型会通过 `reasoning_content` 或 `reasoning` 给出思考内容，客户端可单独处理。读取 HTTP 行会重组网络字节分片，不应把一次 socket 读取当成一个 token 或完整 SSE 事件。原生 ChatRunner 对生产流另外做 UTF-8、事件长度和错误检查。

## PowerShell 非流式示例

```powershell
$lmaBase = 'http://PHONE_IP:8080/v1'
$lmaHeaders = @{ Authorization = "Bearer $env:LMA_API_KEY" }
$lmaModels = Invoke-RestMethod "$lmaBase/models" -Headers $lmaHeaders
$lmaBody = @{
    model = $lmaModels.data[0].id
    messages = @(@{ role='user'; content='Hello' })
    max_tokens = 128
    stream = $false
} | ConvertTo-Json -Depth 6
Invoke-RestMethod "$lmaBase/chat/completions" -Method Post -Headers $lmaHeaders `
    -ContentType 'application/json; charset=utf-8' -Body $lmaBody -TimeoutSec 300
```

## 参数和边界

“本地”中每个模型独立保存的线程、上下文和思考模式影响其引擎启动；全局服务端口保留在“设置”。每个模型的输出上限、温度、系统提示词用于应用内默认对话。详见[模型参数与约束](MODEL_SETTINGS.md)。外部客户端应显式发送自己的消息、采样参数和输出上限；LMA 不把界面系统提示词强行注入所有外部请求。

生成在 EOS、token 上限、客户端取消或引擎故障时结束。进程停止或重载会打断现有连接。只有实际生成才有 token 输出；“后台接口”不表示无请求时自动无限生成。

局域网为明文 HTTP，未内置 TLS / 公网穿透。默认仅本机；可见 API 密钥和“复制示例”含实际凭据，不要截图或提交。模型下载采用 HTTPS，与推理接口是不同链路。

| 问题 | 核对 |
| --- | --- |
| 无法连接 | 模型就绪、手机 IP、LAN 开关、端口、网络隔离 |
| 鉴权失败 | 当前安装的密钥及 Bearer 请求头 |
| 模型不匹配 | 重新查询 `/v1/models`，切换模型会改变别名 |
| 请求过大 / 上下文不足 | 缩短历史、提示词与输出，或在内存允许时调上下文 |
| 流中断 / 没有结束标记 | 保留已收正文并显示错误，不把它计为完整成功 |

示例依据固定上游接口及桌面协议检查编写；尚未通过手机实际运行的 ARM 引擎作端到端验证。

## 0.3.0-dev.2：独立接口、任务与结果

这是当前开发代码，尚未发布完整 v0.3.0。服务页的“启动接口”无需安装或加载模型；“关闭接口”只关闭客户端入口，文本模型可独立保留。模型选择器中可停止文本模型；通知中的“停止服务”仍停止全部运行工作。安装 / 升级不替用户启动新的模型下载。App 内任务和异步 API 使用同一个 `LocalJobs`、任务 / 产物存储及校验。

所有下列接口均要求 `Authorization: Bearer YOUR_LMA_API_KEY`，包括 `/health`、事件和结果读取。默认绑定手机 `127.0.0.1`；显式开启局域网仅允许客户端向这台手机提交请求，计算仍全部在手机。原生文本引擎使用单独的随机回环端口和独立进程密钥，不能通过公开端口绕过准入与模型设置。

| 方法与路径 | 行为 |
| --- | --- |
| `GET /health` | 接口状态、文本状态、当前任务；零模型也可运行 |
| `GET /v1/models` | 仅列用户已安装的模型，包含 `task_tags`、引擎、配方 / 参数、`loaded`；目录条目不等于安装，安装也不等于设备验证 |
| `GET /v1/engines` | 实际注册的引擎构建元数据；不创建空引擎 |
| `POST /v1/chat/completions`、`POST /v1/completions` | 当前已加载文本模型的纯文本请求，支持原始 SSE；不自动切换 / 下载其他模型 |
| `POST /v1/jobs` | 校验后持久入队，返回 `202` 和任务 ID；不代表已生成成功 |
| `GET /v1/jobs`、`GET /v1/jobs/ID` | 有界任务摘要 / 完整快照、状态、错误与产物 ID |
| `POST /v1/jobs/ID/cancel`、`POST /v1/jobs/ID/retry` | 显式取消；只对失败 / 中断 / 取消记录创建新任务重试 |
| `DELETE /v1/jobs/ID` | 删除终态历史；活动任务须先取消 |
| `GET /v1/events`、`GET /v1/jobs/ID/events` | JSON 游标事件；请求 `Accept: text/event-stream` 获取 SSE |
| `GET /v1/artifacts`、`GET /v1/artifacts/ID` | 结果摘要 / 原始元数据与来源参数 |
| `GET /v1/artifacts/ID/content` | 原始字节，支持一个 `Range` 与 `206 / 416`；`HEAD` 仅返回头 |
| `DELETE /v1/artifacts/ID` | 独立删除未被使用的结果；下载 / 预览 / 导出读取期间有引用保护 |

从已安装的模型包记录（具有 `recipe` 字段）选择对应 `id` 作为 `bundleId`，不要从名称猜测。既有文本记录仍走已加载模型的 chat / completions 接口，完整异步文本适配尚未完成。示例只表示调用结构，所选包、实际引擎与任务能力必须匹配；当前目录中未实测的 SD1.5 候选不能据此称为已支持。只有用户明确同意尝试未测配方时才发送 `allowUnmeasured: true`。

```bash
curl http://PHONE_IP:8080/v1/jobs \
  -H "Authorization: Bearer YOUR_LMA_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-image-request-1" \
  -d '{"bundleId":"USER_SELECTED_BUNDLE_ID","type":"image.generate","input":{"prompt":"A small garden"},"parameters":{"seed":123},"allowUnmeasured":true}'
```

当前任务输入只支持 `prompt` / `negativePrompt` 文本，`parameters` 必须为 JSON 对象、`allowUnmeasured` 必须为布尔值；其他输入不被静默忽略，也不会转为网络获取。输入产物引用尚待接入。参数先应用模型 / 配方独立配置，再执行同样的约束与归位；任务保存不可变有效参数。相同幂等键和相同请求返回原任务；改变请求返回冲突。任务重试产生新 ID，历史不被重写。缺资产、缺引擎、资源不足、未授权尝试未测配方均在本机失败，接口不会触发下载。当前媒体任务还要求先停止已加载的文本模型；完整自动调度统一仍在本版待办。

文本请求采用所选模型的输出 / 温度默认值，输出上限归位到该模型已保存的限制及上下文边界；不注入 App 系统提示词。只接受受支持的纯文本字段，拒绝媒体 URL、工具等未接入字段和多推理槽。外部文本请求占用期间，App 聊天、模型切换和需要重载的参数变更不能越过占用检查。停止或断开文本连接释放其原生连接；断开任务事件订阅不会取消持久任务，取消必须调用对应端点。

事件查询使用 `?after=SEQUENCE` 或 `Last-Event-ID`，两者同时提供须一致。`/v1/events` 还可用 `job_id=ID`。JSON 的 `cursor` 表示已读取到的全局序号；保留 512 条事件，过旧游标返回 `truncated`，SSE 会发送 `reset` 提醒重新读取任务快照。SSE 单连接最长 120 秒、每约 10 秒心跳，客户端按游标重连；同时最多两路事件流，仍可改用 JSON 轮询。

传输限制：请求头 16 KiB、请求体 256 KiB、JSON 嵌套 32 层；POST 要求 `Content-Length`，不接受 chunked / multipart / `Expect` 上传。不提供文件系统路径或远程转发端点。所有响应关闭缓存、启用 `nosniff`；不开放浏览器 CORS，原生客户端和 App 自己的桥接不受此限制。原始产物同时最多三路读取；超出数量返回 `503`，活动读取结束即可重试。明文 HTTP / 无 TLS 的既有限制仍适用。

当前开发证据：67 项接口检查使用实际本机 socket、生产路由 / 存储和显式执行替身；文本后端还检查生产 `ApiHost` 对真实子进程替身的代理与占用释放。它们不是 Android 模型输出或后台耐久证据。完整余项见[实施记录](DEVELOPMENT.md)。

dev.3 的已安装 TTS 候选使用相同异步任务接口，`type: "speech.synthesize"`、`input: {"prompt": "Hello world."}`；参数独立属于模型。输入 1–4000 字符，不接受负面提示词，缺语言组件不会下载 / 转出执行。当前完整配方和限制见[语音基座](TTS_ENGINE.md)；没有手机推理证据。

## dev.4：显式 LoRA 选择

`POST /v1/jobs` 的 `image.generate` 可选 `adapters: [{"bundleId": "本机适配器包ID", "scale": 0.75}]`，最多八个，省略强度时固定各自保存值。基础模型与适配器必须完整安装且声明兼容；重复、自身、路径、未知字段或非生图任务的选择拒绝。缺资产不下载。配对 / 强度 / 来源与验证边界见[LoRA 指南](ADAPTERS.md)；没有真机生成证据。
