# LMA API 接入

[English](API.en.md) · [文档目录](README.md)

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
