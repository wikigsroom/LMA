# Default API port 52187

[中文](API_PORT.md) · [API guide](API.en.md) · [v0.3.13 release notes](releases/v0.3.13.md)

v0.3.13 / code63 changes the public model API default from 8080 to **52187**. On-phone clients use `http://127.0.0.1:52187/v1`. After enabling LAN access on the Service page, a computer on the same network uses `http://PHONE_IP:52187/v1`. Follow the actual address displayed by the app. Requests continue to require the existing Bearer API key.

## Installation and upgrade behavior

| No. | Case | Result |
| --- | --- | --- |
| 1 | New installation without a saved port | Use 52187 |
| 2 | Upgrade using the former default 8080 | Move to 52187 at first launch and save a one-time migration marker |
| 3 | Upgrade using another valid custom port | Preserve it, including the 1024 and 65535 boundaries |
| 4 | Explicitly edit the port after migration | Preserve the choice on subsequent launches |
| 5 | Invalid saved port outside 1024–65535 | Recover to 52187 |
| 6 | Requested port already occupied | Report the bind failure and restore the previous listener when possible; private text execution remains independent |

Migration runs during application startup before service creation. Listener startup, settings, LAN addresses, the internal HTTP client and the empty-library page share the default. Users may still enter valid ports from 1024 to 65535. Private model-engine loopback ports remain independently allocated.

An in-place upgrade preserves model files, per-model settings, task history and API credentials. It never downloads or replaces weights. Connected clients must update their base URL if they previously used the default 8080. Clients using a preserved custom port continue to use that port.

## Client examples

Use loopback on the phone and the displayed phone address from a LAN client. Obtain `lma_key` through your own secure input or environment; never commit a real key.

```python
from openai import OpenAI
client = OpenAI(base_url="http://PHONE_IP:52187/v1", api_key=lma_key)
models = client.models.list()
```

```powershell
$lmaBase = 'http://PHONE_IP:52187'
Invoke-RestMethod "$lmaBase/health" -Headers @{ Authorization = "Bearer $lmaKey" }
Invoke-RestMethod "$lmaBase/v1/models" -Headers @{ Authorization = "Bearer $lmaKey" }
```

## Verification

Final APK SHA256: `ed89eda6b88cf005cd839eb67e4b5219a8a191f58af0d2aeea1e401e39106158`. **63 LAN checks pass across 128 HTTP requests**. The screen remains asleep for 111.600 seconds, with 30 health requests after generation. Catalogue median latency is 32.90 ms and p95 is 229.72 ms, including client, physical-network and phone scheduling overhead.

Program regressions cover first installation, the former default, custom-port boundaries, one-time migration, invalid saved values, and the actual UI's loopback/LAN addresses. The phone receives an upgrade from v0.3.12 signed by the original key. A private baseline records its old port, model configurations and history identities; the upgrade test verifies port migration and preservation of model settings, history and the API credential.

Direct LAN checks bind to the PC's physical adapter and connect to phone Wi-Fi. They cover port 52187, refusal on the old 8080 listener, authentication, model publication, settings, jobs, idempotency, cancellation, uploads, SSE, artifacts and ranges. Existing phone models generate one new PNG and two WAV files. No proxy, ADB forwarding, virtualization or off-device inference is involved.

[Current LAN evidence](../verification/supplemental/v0.3.13/lan-http.json) · [Program evidence](../verification/releases/v0.3.13/status.json) · [Physical UI media](media/device/v0.3.13/manifest.json) · [LAN outputs](media/tests/lan-http-v0313/manifest.json)

The earlier 6.125-second video receives a transfer check only. Its generation, previous SDK checks and 3D attempts retain their v0.3.12 APK identity. The `empty_structure` 3D failure, media quality, all-model phone execution and long background endurance remain separately unaccepted.
