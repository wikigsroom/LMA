# Local input media, task references and uploads

[中文](LOCAL_INPUTS.md) · [Development](DEVELOPMENT.en.md) · [API](API.en.md) · [Scheduling](SCHEDULING.en.md)

Status: **0.3.0-dev.11 / versionCode 15, unpublished internal checkpoint.** Local media management and task input contracts are implemented. Existing production text, diffusion, Sherpa and Nano recipes still accept text only; this does not add image editing, reference-audio cloning or image-to-video execution. Every selected model, required input pipeline and physical Android gate remains in the complete v0.3.0 scope.

## Using media

1. Open Tasks → Media and results → Import media and explicitly choose one document in Android's picker.
2. The foreground service copies it into private storage, inspects the actual format and computes SHA256. Leaving the page does not cancel it. Cancel the import separately or use Stop service in the notification. An interrupted document copy requires explicit reselection; it is not a resumable engine checkpoint.
3. Filter All / Generated / Imported, preview/play, export or delete. Imported bytes carry an Imported source label; they are not model outputs. Older records without an origin field remain compatible generated results.
4. Choose an installed model. Input selectors appear only when its signed engine declares roles for that recipe. Select compatible imports or previous results. The recipe controls MIME, bytes, duration and pixel bounds; required roles cannot be omitted.
5. Submission freezes the selected IDs, actual hashes, bytes and metadata. Queued/running references prevent deletion. Execution rehashes each file before starting the worker. Missing/changed media fails locally without downloading or substituting another file.

Imports accept **PNG/JPEG, uncompressed PCM/float WAV and MP4**, **1 byte–512 MiB** each; empty, corrupt and unsupported structures fail inspection. Other images, compressed audio and containers are not implicitly converted. WAV supports 8–192 kHz, 1–8 channels, 16/24/32-bit integer PCM or 32-bit float; engines may impose stricter bounds. Image sides are limited to 16384; video dimensions, ordered continuous samples and frame-table counts are bounded too. Android image decoding/MP4 probing still need device testing. An MP4 metadata check does not establish playback or model compatibility for every codec.

The selected source is read only for the explicit import. The private copy does not depend on retaining the original URI afterward. Provenance keeps a display name, without exporting paths or `content://` URIs. Model weights, vocabularies and voice packages continue through model-bundle management rather than input uploads.

## Engine contracts and durable references

Signed engine code supplies `InputSpec`: roles, required flags, MIME lists, byte limits and optional duration/pixel bounds. HF metadata and model manifests cannot enable unsupported input operators. Existing modules default to `promptOnly()` and reject undeclared roles. Each future actual pipeline needs its own implementation and evidence.

`TaskInput` accepts only `input.artifacts: [{role, artifactId}]`, up to eight distinct roles. Clients cannot provide paths, remote URLs, trusted receipts or executable scripts. `InputSelection` prepares immutable receipts under the artifact lock, serialized with durable job publication. UI and API use the same production runner.

Nonterminal JobStore requests protect queued inputs across process restarts. Execution leases and rehashes them, exposing controlled private files by role through the engine context. Cancellation/timeouts retain leases until actual child exit. Output provenance includes the frozen receipts. Terminal history retains receipts without permanently pinning media; explicit deletion makes later retries fail for missing inputs.

Previews, API Range reads and system exports also hold read leases. Deleting a job leaves inputs/results intact. Deleting an upload session leaves already imported media intact. Users manage these records independently.

## Upload API

All endpoints use the existing Bearer key. The default listener is phone loopback; an explicitly enabled LAN listener may receive client input bytes while all execution stays on the same phone. Browser Origins/CORS, remote file URLs, arbitrary paths, multipart, HTTP chunked transfer and `Expect: 100-continue` are unsupported.

| Request | Behavior |
| --- | --- |
| `POST /v1/uploads` | Explicit JSON `{name, bytes, sha256}` declaration; returns 202, ID, `received` and `chunkBytes` |
| `GET /v1/uploads` / `GET /v1/uploads/ID` | List/query state and durable offset; HEAD supported |
| `PUT /v1/uploads/ID` | `application/octet-stream`, exact Content-Length and `Upload-Offset: N`; 1–262144 bytes per chunk |
| `POST /v1/uploads/ID/complete` | Empty JSON; full SHA256/media validation and atomic import; repeats return the same artifact ID |
| `DELETE /v1/uploads/ID` | Remove session and its partial bytes, preserving already imported media |

Limits: four active sessions, 1 GiB of pending bytes, 64 history records, and at least 128 MiB of free-space reserve. Each HTTP body remains capped at 256 KiB; the full file is never buffered in Java memory. Declare an integer size and a 64-character lowercase SHA256. Display names contain 1–160 characters without paths/control characters.

Chunks fsync before atomic offset updates. Identical committed chunks can be retried after a lost response. Different bytes, gaps and overlapping committed boundaries conflict. Restart truncates uncommitted tails to the durable offset; short/missing partial files fail and require explicit deletion/recreation. Startup removes unregistered interrupted import/upload staging while preserving registered partial files. If final artifact publication succeeds before session metadata updates, import-ID reconciliation prevents duplicate imports. Clients explicitly query and continue transfers; the App does not resume network uploads automatically.

Request errors use 400, missing authentication 401, Origin 403, unknown IDs 404, conflicts 409, oversized bodies 413 and wrong MIME 415. Full digest/media validation or local-storage failure uses the existing 503 error with a concrete explanation; no valid artifact is published. Delete and recreate an immutable declaration that cannot complete.

The complete [Python example](LOCAL_INPUTS.md#api-分块上传) uploads only the user-specified local WAV. A real recipe must declare a compatible role before accepting `input: {"prompt":"…", "artifacts":[{"role":"reference_audio", "artifactId":"USER_SELECTED_ID"}]}`. That role is a contract example, not a claim that current TTS supports reference audio. Inspect `/v1/models` → `input_schemas`; current production recipes declare no media roles.

## Evidence and remaining gates

`python tools/test_inputs.py` passes **64 assertions** covering actual host files, production WAV validation and HTTP. `python tools/test_scheduler.py` now passes **49**, including production queued references, actual child consumption of selected bytes, provenance, same-size corruption blocking startup, and cancellation cleanup. PCM is synthetic sample data; host image inspection is an explicit port and the fixture child copies bytes. No model inference occurs.

UI regression totals **182 assertions**. Development media includes **30 screenshots plus recording/GIF**, visibly labeled UI FIXTURE. The input form uses an explicit contract fixture, not an adapted voice-cloning model. The Android picker, real image/video codecs, screen-off behavior, upgrades and all frozen models' fresh-input offline outputs still require physical acceptance.

![Imported media library, UI fixture](media/development/29-imported-media-library.png)

[Input form](media/development/30-local-input-role-form.png) · [Recording](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif) · [Receipt](../verification/development/inputs.json) · [Notes](releases/v0.3.0-dev.11.md)
