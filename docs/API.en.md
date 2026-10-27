# LMA API integration

[中文](API.md) · [Documentation](README.md)

The existing text examples below describe public **v0.2.0**. The final section documents internal **0.3.0-dev.2** gateway/jobs/artifacts; complete model support and physical-device acceptance remain unfinished.

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

## 0.3.0-dev.2: independent gateway, jobs and artifacts

This is development code, not a complete v0.3.0 Release. Start the gateway from Service with zero installed/loaded models. Closing the gateway preserves an independently loaded text model; the model picker can stop that model. The notification's Stop service action stops all work. Installation/upgrades never select model downloads. App tasks and asynchronous API requests share the same `LocalJobs`, stores and validation.

Every endpoint below requires `Authorization: Bearer YOUR_LMA_API_KEY`, including health, events and result bytes. The default bind is the phone's `127.0.0.1`; enabling LAN allows clients to submit work to this phone while all computation stays on it. The native text child uses a separate random loopback port and per-process secret. Clients cannot bypass admission/model settings through the public port.

| Method/path | Behavior |
| --- | --- |
| `GET /health` | Gateway/text/current-job status, including an empty library |
| `GET /v1/models` | User-installed models with `task_tags`, engine, recipe/parameters and `loaded`; catalogue metadata is not installation or device validation |
| `GET /v1/engines` | Actual registered engine build metadata, without empty providers |
| `POST /v1/chat/completions`, `POST /v1/completions` | Plain text with the already loaded model and original SSE; no implicit model switch/download |
| `POST /v1/jobs` | Validate and durably queue; `202`/job ID acknowledges submission, not generated output |
| `GET /v1/jobs`, `GET /v1/jobs/ID` | Bounded summaries/full snapshot, state, error and artifact IDs |
| `POST /v1/jobs/ID/cancel`, `POST /v1/jobs/ID/retry` | Explicit cancellation; create a new retry only from failed/interrupted/cancelled history |
| `DELETE /v1/jobs/ID` | Remove terminal history; cancel active work first |
| `GET /v1/events`, `GET /v1/jobs/ID/events` | JSON cursor events or SSE with `Accept: text/event-stream` |
| `GET /v1/artifacts`, `GET /v1/artifacts/ID` | Result summaries/full metadata and provenance |
| `GET /v1/artifacts/ID/content` | Original bytes; one `Range`, `206 / 416`; `HEAD` sends headers only |
| `DELETE /v1/artifacts/ID` | Delete independently while respecting active read/export leases |

Select an installed bundle record's `id` as `bundleId` (it has a `recipe` field). Legacy text records still use the loaded model's chat/completions routes; full asynchronous text adaptation remains unfinished. This example only shows the request structure: the selected bundle, engine and task must match. The unmeasured SD1.5 catalogue candidate is not accepted model support. Send `allowUnmeasured: true` only after explicitly choosing to attempt an unmeasured recipe.

```bash
curl http://PHONE_IP:8080/v1/jobs \
  -H "Authorization: Bearer YOUR_LMA_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-image-request-1" \
  -d '{"bundleId":"USER_SELECTED_BUNDLE_ID","type":"image.generate","input":{"prompt":"A small garden"},"parameters":{"seed":123},"allowUnmeasured":true}'
```

The current task input accepts prompt/negativePrompt text only. Parameters must be an object and allowUnmeasured a boolean. Unsupported inputs are rejected rather than ignored or downloaded; input-artifact references remain unfinished. Apply per-model/recipe settings and the same clamping rules, then persist an immutable effective snapshot. The same idempotency key/request returns the original job; a changed request conflicts. Retries receive new IDs without rewriting history. Missing assets/engines, insufficient resources and an unapproved unmeasured recipe fail locally without downloading. Media jobs currently require stopping the loaded text model first; complete automatic scheduling remains in this release's open scope.

Text requests use the loaded profile's output/temperature defaults and clamp output to its saved ceiling/context. They do not receive the App system prompt. Only supported plain-text fields are accepted; media URLs, unimplemented tools and multiple slots fail explicitly. An external text request also prevents App chat, model switches and settings reloads from bypassing its execution lease. Stopping/disconnecting text releases its native connection. Disconnecting job-event subscriptions leaves durable jobs running; cancel them explicitly.

Resume events with `?after=SEQUENCE` or `Last-Event-ID`; both must agree when supplied together. Global events also accept `job_id=ID`. JSON `cursor` is the global sequence scanned. Keep 512 events; old cursors report `truncated`, and SSE sends `reset` so clients can fetch a fresh job snapshot. SSE connections last up to 120 seconds with approximately ten-second heartbeats; reconnect by cursor. At most two event streams coexist; JSON polling remains available.

Transport limits: 16 KiB headers, 256 KiB request body, JSON depth 32. POST requires Content-Length; chunked/multipart/Expect uploads are not accepted. There are no filesystem-path or remote-forwarding endpoints. Responses use no-store/nosniff; browser CORS is disabled, while native clients and the App bridge work normally. Up to three artifact reads coexist; additional readers receive 503 and can retry after a lease ends. Existing plain-HTTP/no-TLS limitations still apply.

Current evidence: 67 API checks use real host sockets, production routing/storage and explicit execution fixtures; backend checks also exercise the production `ApiHost` proxy against real child-process fixtures and verify lease release. These are not Android inference/endurance evidence. See [remaining development work](DEVELOPMENT.en.md).

dev.3 installed TTS candidates use the same async job API with `type: "speech.synthesize"` and `input: {"prompt": "Hello world."}` plus independent model parameters. Text is 1–4000 characters; negative prompts are rejected. Missing language components never download or execute off-device. See [speech recipes and limits](TTS_ENGINE.en.md); no phone inference has been established.

## dev.4 explicit LoRA selection

`image.generate` on `POST /v1/jobs` accepts optional `adapters: [{"bundleId": "installed_adapter_id", "scale": 0.75}]`, at most eight. Omitted scales freeze saved adapter settings. Require installed compatible bases/adapters; reject duplicate/self selections, paths, unknown fields and non-image adapter requests. Missing assets never download. See [pairing/provenance/evidence](ADAPTERS.en.md); no phone output is claimed.

dev.7 adds `version` metadata to bundle `/v1/models` records (`{}` before a version group exists): `groupId`, `activeBundleId`, `isActive`, `members`, and `pending` when a plan exists. Installed old versions retain their IDs; current preference never redirects requests. Update/review/activation currently use native App commands, without new HTTP update endpoints. See [model updates](MODEL_UPDATES.en.md).
