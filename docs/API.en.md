# LMA API integration

[中文](API.md) · [Documentation](README.md)

## Endpoint, authentication, and model ID

- Default local Base URL: `http://127.0.0.1:8080/v1`.
- For another device, enable LAN on Server and use the phone's displayed IP. Both devices need network reachability.
- Send `Authorization: Bearer YOUR_LMA_API_KEY`. Copy the key from the phone; it is not a cloud OpenAI key.
- `GET /v1/models` returns the loaded alias, such as `m08`. HF downloads use stable `hf_...` IDs, while manual imports use `custom_...`; do not infer IDs from filenames. An HF access token is separate from the inference API key.
- The model must be loaded and ready, not merely downloaded. One model and one inference slot do not promise parallel throughput.

The documented compatibility surface is models, chat completions, and SSE. Responses, audio, images, embeddings, tool calling, and all vendor parameters are not promised.

## curl

```bash
curl http://PHONE_IP:8080/v1/models \
  -H "Authorization: Bearer YOUR_LMA_API_KEY"

curl -N http://PHONE_IP:8080/v1/chat/completions \
  -H "Authorization: Bearer YOUR_LMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"m08","messages":[{"role":"system","content":"Answer clearly and briefly."},{"role":"user","content":"Hello"}],"temperature":0.7,"max_tokens":256,"stream":true}'
```

Replace the IP, key, and model ID. `-N` disables curl output buffering. Set `"stream":false` for one JSON result, and allow a longer timeout for slower generation.

## Python, standard library only

Set `LMA_BASE_URL` and `LMA_API_KEY` in your environment; do not put real keys in example files or Git.

```python
import json
import os
import urllib.request

base = os.environ.get("LMA_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")
headers = {"Authorization": "Bearer " + os.environ["LMA_API_KEY"]}
request = urllib.request.Request(base + "/models", headers=headers)
with urllib.request.urlopen(request, timeout=30) as response:
    model_id = json.load(response)["data"][0]["id"]

payload = {"model": model_id, "messages": [{"role": "user", "content": "Hello"}],
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

This example prints content only. Models may emit reasoning through `reasoning_content` or `reasoning`; clients can handle that separately. HTTP line reading reassembles byte fragments: one socket read is not necessarily one token or SSE event. Production ChatRunner additionally validates UTF-8, event size, and stream errors.

## PowerShell, non-streaming

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

## Parameters and limits

Each model’s independent threads, context and reasoning settings affect its engine startup; the service port remains global. Per-model output limit, temperature and system prompt are defaults for in-app chat. See [profile limits](MODEL_SETTINGS.en.md). External clients send their own messages and generation parameters; the UI's system prompt is not injected into every external request.

EOS, token limits, cancellation, or engine failure end generation. Stopping or reloading the process interrupts existing connections. Background serving does not mean unlimited generation without requests.

LAN is plain HTTP without built-in TLS or public tunneling. Localhost is the default. Revealed keys and copied examples contain actual credentials: do not publish them in screenshots or Git. Model downloads use a separate HTTPS path.

| Problem | Check |
| --- | --- |
| Cannot connect | Model readiness, phone IP, LAN switch, port, network isolation |
| Auth failure | This installation's key and Bearer header |
| Wrong model | Query `/v1/models` again after switching |
| Oversized request / context | Reduce history, prompt, and output, or increase context if RAM permits |
| Broken stream / missing completion | Preserve received content and report an interruption, not full success |

Examples follow the pinned upstream API and desktop protocol checks. End-to-end requests to a phone's actual ARM engine remain untested.
