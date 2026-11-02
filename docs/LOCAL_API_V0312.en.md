# Local multimodal API and Sub2API integration

[中文](LOCAL_API_V0312.md) · [Physical benchmark](DEVICE_BENCHMARK_V0312.en.md) · [Full contract](SUB2API_OPENAI.en.md) · [OpenAPI](proposals/sub2api-openai.openapi.json)

v0.3.12/code62 adds standard discovery, image/speech facades and a shared asynchronous extension for video, music and 3D. APK upgrades deliver the foundation. Users choose, download/import and configure model assets in Models → Local. All 14 recommendations, content labels and unrestricted HF discovery remain available.

## Installation and use

1. Install the stable APK and explicitly select/download or import complete model components.
2. Save settings for each model in Local. Request overrides apply only to that task; model constraints clamp effective values without rewriting saved defaults.
3. Start API in Service. The new published-model panel shows actual IDs, task labels and state. LAN listening remains an explicit user choice; loopback belongs to the phone.
4. Connect to the reachable phone's `/v1` with its Bearer key. Complete, configured models with an available runner are published automatically, including unloaded models.
5. Read `/v1/models/{id}` and its `x_lma` operations, input roles and parameter schema before submission. Busy/unloaded models stay visible. Incomplete assets, invalid settings and standalone LoRA do not become generators.

The phone key is an owner credential. Native phone endpoints do not provide separate user accounts; use the gateway below for multiple callers and protect the upstream key. Public recordings exclude keys, private chats and personal task history.

## Endpoints and scope

| ID | Endpoint | Implemented behavior |
| --- | --- | --- |
| 01 | `GET/HEAD /v1/models`, `/v1/models/{id}` | Standard model objects, persistent IDs/created time/instance, revision and ETag/304; additional `x_lma` capabilities/settings |
| 02 | `GET/HEAD /v1/capabilities`, `/v1/lma/capabilities` | The same snapshot, task/foundation/content labels, roles, schemas, backends and limits |
| 03 | `POST /v1/chat/completions`, `/v1/completions` | Explicitly select/load installed GGUF under the common execution slot; JSON/SSE subset |
| 04 | `POST /v1/images/generations` | One PNG, `n=1`, `b64_json`; standard 200 only after a real valid artifact |
| 05 | `POST /v1/audio/speech` | Explicit WAV binary output; `default` or an advertised model speaker |
| 06 | `/v1/lma/jobs`, `/preflight`, `/{id}`, `/cancel`, `/retry`, `/events`, `/audio` | Six peer operations: text/image/video/speech/music/mesh; async 202 followed by owned artifacts |
| 07 | `/v1/lma/uploads`, `/{id}`, `/{id}/complete` | Explicit destination model, offset chunks, SHA256 and local inputs; no arbitrary host paths |
| 08 | `/v1/lma/artifacts`, `/{id}`, `/{id}/content` | Metadata and authenticated media, genuine Range/If-Range/ETag semantics |
| 09 | Image edits, Responses, Videos, Realtime compatibility | Not enabled; explicit errors. Image-conditioned generation uses declared local job roles |

Stage events are not image tokens. Chunked WAV delivery is not incremental speech; generic `incremental_pcm` remains false. Existing engine-specific preview contracts are separate. Omitting the speech format requests MP3 and fails until an encoder exists; WAV is never mislabeled. Unsupported voices, quality, transparency, masks, batches and stream modes are rejected before admission.

## Actual SDK use

Set variables yourself; the repository contains no live credentials. Use IDs returned by discovery, without impersonating GPT models. `allow_unmeasured` explicitly permits execution with incomplete device estimates; it does not download assets, enable remote inference or accept quality.

```python
import os, base64
from openai import OpenAI
client = OpenAI(base_url=os.environ["LMA_BASE_URL"],
                api_key=os.environ["LMA_API_KEY"], timeout=150, max_retries=0)
for model in client.models.list():
    print(model.id, model.x_lma["operations"])
audio = client.audio.speech.create(
    model=os.environ["LMA_SPEECH_MODEL"], input="Hello from the local phone.",
    voice="default", response_format="wav",
    extra_headers={"Idempotency-Key": "my-speech-request-001"},
    extra_body={"lma": {"allow_unmeasured": True}})
audio.write_to_file("speech.wav")
```

```python
import base64, hashlib, json, time
from urllib.request import Request, urlopen
from openai import APIStatusError

api_root = os.environ["LMA_BASE_URL"].rstrip("/")
assert api_root.endswith("/v1")
api_root = api_root[:-3]
def local_bytes(path):
    assert path.startswith("/v1/lma/")
    req = Request(api_root + path,
                  headers={"Authorization": "Bearer " + os.environ["LMA_API_KEY"]})
    with urlopen(req, timeout=30) as response:
        return response.read()

try:
    result = client.images.generate(
        model=os.environ["LMA_IMAGE_MODEL"], prompt="An orange cube on white.",
        n=1, size="256x256", response_format="b64_json",
        extra_headers={"Idempotency-Key": "my-image-request-001"},
        extra_body={"lma": {"allow_unmeasured": True,
                             "parameters": {"steps": 4, "threads": 4}}})
    png = base64.b64decode(result.data[0].b64_json)
except APIStatusError as error:
    if error.status_code != 504:
        raise
    job_id = error.response.headers.get("X-LMA-Job-ID")
    if not job_id:
        raise
    while True:
        job = json.loads(local_bytes("/v1/lma/jobs/" + job_id))
        if job["state"] in ("failed", "cancelled", "interrupted"):
            raise RuntimeError(job["error"])
        if job["state"] == "succeeded":
            output = job["outputs"][0]
            png = local_bytes(output["content_path"])
            assert hashlib.sha256(png).hexdigest() == output["sha256"]
            break
        time.sleep(2)
open("image.png", "wb").write(png)
```

The phone facade waits at most 120 seconds, with three synchronous wait slots and one heavy generation slot. Prefer async jobs for slow models. A 504 carries `X-LMA-Job-ID` and `x_lma.job_id`; work may continue. Retry only the original body/key or query that job, never create another request merely because a connection timed out.

```json
{
  "model": "<INSTALLED_VIDEO_MODEL_ID>", "type": "video.generate",
  "input": {"prompt": "An orange cube on a white background."},
  "parameters": {"width": 128, "height": 128, "frames": 49, "fps": 8,
                 "steps": 4, "threads": 4, "executionBackend": "cpu"},
  "allowUnmeasured": true
}
```

POST the body to `/v1/lma/jobs` with an independent idempotency key. Poll `GET /v1/lma/jobs/{id}` and download `outputs[].content_path` after success. **POST `/{id}/cancel` cancels**; DELETE removes terminal history. Explicit `/retry` creates a new job and needs a new key. Image-only 3D uses the declared role, e.g. `reference_image`, without invented user text. Speech/music/multiview inputs follow each selected schema.

Model loading and generation have no fixed execution deadline. The previous two-hour queue and five-minute text-load ceilings are removed, and text generation reads wait continuously. A 49-frame video at 8 fps targets 6.125 seconds. Explicit cancellation, output-size bounds, actual resource protections and separate HTTP waits remain; an HTTP timeout does not cancel an admitted async job.

Historical `/retry` keeps the original parameters. To change steps, guidance or inputs, edit the model in Local and create a new task with a new idempotency key. The 3D defaults recommend 12 steps/guidance7.5; this is not a guarantee of phone quality or successful GLB output.

## Persistence and idle performance

Discovery uses asset/configuration revision caches. Repeated reads do not hash weights, launch probes, download or load models. Actual installation/configuration/deletion invalidates the cache. Public defaults omit private prompts, paths and credentials; internal configuration revisions still reflect changes.

Both phone and gateway persist intent before forwarding. Lookup is caller/endpoint/key first, then immutable body comparison; changed bodies return 409. Defaults freeze on first admission. History deletion retains tombstones for at least 24 hours after terminal state; a removed job returns 410 rather than rerunning. Interrupted phone tasks retain records, not neural computation checkpoints.

Gateway chat/text requests use a separate transport without the ordinary response-header deadline; control requests retain their network budgets. A real HTTP regression check verifies delayed text headers outlive a shortened ordinary network wait.

## Native Sub2API source extension

The source kit is in [integrations/sub2api](../integrations/sub2api/README.md), pinned to official **v0.2.19 / dece26153621959ccd7635814f4b2d08304e681a**. Its opt-in capability middleware runs after existing authentication/group allowlists and before provider-family checks. Real local names do not have to masquerade as GPT models.

An unchanged upstream installation cannot enable this merely by setting an OpenAI base URL. Apply with `python tools/apply_sub2api.py --source <isolated-upstream-source>` and compile natively. The tool requires the audited upstream route bytes and rejects unknown versions. No production deployment/database was changed for this release.

`SUB2API_LMA_CONFIG` points to a private JSON file; upstream credentials come only from environment variables:

```json
{"state_file":"/private/lma-state.json","accounts":[{
  "account_id":1,"group_id":2,"base_url":"http://PHONE_ADDRESS:8080",
  "key_env":"LMA_PHONE_KEY","expected_instance_id":"<FROM_PHONE_CATALOGUE>",
  "aliases":{"my-local-speech":"<ACTUAL_INSTALLED_MODEL_ID>"}}]}
```

`account_id` identifies a phone in the extension's private registry. `group_id` selects an existing dedicated Sub2API group. **No database account/model mapping rows are created or overwritten.** Model/alias collisions reject the entire incoming snapshot and preserve the last valid one. Use distinct groups for phones with conflicting names. Unconfigured groups retain their original routes.

Conditional sync runs around 30 seconds (±20% jitter), connect timeout 3 seconds/read 5 seconds, exponential failure backoff at most 300 seconds. First unknown catalogue returns 503. Entries older than 90 seconds remain visible but admit no new jobs. An unexpected instance change is rejected. Caller/resource/instance bindings persist atomically; raw shared phone history never reaches ordinary users.

One bounded JSON event cache per phone fans out downstream SSE, retaining at most 1024 events and 64 simultaneous subscribers. Truncated cursors reset. Direct native phone SSE remains limited to two streams/120 seconds. Media forwarding uses bounded buffers and preserves Range/If-Range/ETag. All inference stays on the same phone without cloud fallback.

Native gateway contracts, pinned source compilation, real-phone forwarding and live production authentication/billing are distinct evidence. This release does not validate a production DB, balance debit or price mapping, and does not invent token usage or prices.

## Verification

```text
python tools/test_api_publication.py
python tools/test_sub2api_gateway.py
python tools/device_check.py --serial SERIAL --run --install --existing-models --program-api --minutes 1
python tools/profile_device.py --serial SERIAL --label optimized --existing-models
python tools/device_sdk_integration.py --serial SERIAL
```

The last three require an authorized phone. SDK checks use installed speech/image models and owned fixtures/tasks. See the [physical benchmark](DEVICE_BENCHMARK_V0312.en.md) for exact APK identities, settings, durations, failures and temperature. Valid media files do not establish acceptable quality, all-model coverage or long background endurance.

## Direct LAN HTTP supplement

Enable LAN in Service and use the phone Wi-Fi address. Native PC HTTP can access models and jobs directly. See the [57-check / 128-request LAN guide](LAN_HTTP_TEST.en.md) for measured results, environment variables and curl examples. ADB operates the UI only; the data path uses neither port forwarding nor a proxy.
