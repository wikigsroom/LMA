# Physical Android program acceptance · v0.3.10

[中文](DEVICE_ACCEPTANCE.md) · [Release](releases/v0.3.10.md) · [23 program checks](../verification/releases/v0.3.10/physical-device.json) · [10 failure probes](../verification/releases/v0.3.10/task-diagnostics.json)

The authorized USB device identifies as **motorola edge plus / burton, Android 12 / API31, SM8250, approximately 11.4 GiB visible RAM**. This is not an X30, Snapdragon 8 Gen 1 or Nubia Z20 result. The computer installs the APK and forwards management requests; the application, API and probes run on the phone, without ROOT or virtualization.

## 1. Current result

The original-signer in-place update is **0.3.10 / code60**. Five failed jobs were privately archived and removed. Both successful jobs, five artifacts/results, five installed models and their settings remain. [Every failure, repair and optional CPU route](TASK_FAILURES.en.md).

| Item | Physical checks | Scope/result |
| --- | --- | --- |
| A01 | Complete 82-bundle catalogue, device state, native bridge and WebView | Existing installed assets retained |
| A02 | Fourteen recommendations, original text prefix, image 3/video 2/audio 3/3D 3; All/Local and navigation | Actual DOM operations; no private user media recorded |
| A03 | Extracted executable permissions, SQLite interruption recovery, service commands | Android framework passes |
| A04 | API continues after instrumentation detaches | Normal foreground service recovers |
| A05 | Incorrect key 401, browser origin 403, management list APIs | HTTP requests reach the phone via ADB |
| A06 | Missing text weights 409 and unchanged model list | No automatic model download |
| A07 | 60.29 seconds screen-off, seven authenticated health/service samples | Short program survival only |

These are **23 program checks**, separate from **ten failure-specific probes**. The latter use a four-byte owned source, seventeen component receipts/sizes and signed `--info`/`--devices` queries. Workspace staging now succeeds; production Wan preflight rejects the unsupported GPU without adding a job. No complete image/video/audio/3D model is executed on the phone.

The key exists only in test-process memory. Public records exclude credentials, serial numbers, Wi-Fi endpoints, personal prompts and media. Raw backups remain in a local ignored directory.

## 2. Reproduction

Use native Windows Android SDK/JDK/Python and an authorized, unlocked phone. Confirm that no job is active because instrumentation installation may restart the target. `SERIAL` is an authorized entry from `adb devices`; wireless pairing still requires connection to the advertised connect port.

```powershell
python tools/build.py
python tools/build_acceptance.py
python tools/device_check.py --serial SERIAL --install --run --program-api --existing-models --minutes 1
```

`--existing-models` preserves installed assets while checking management/API operations; omitting it retains strict zero-install acceptance. **Do not pass `--model`**, the historical full-download/inference option. No alternative CPU bundle is imported or executed.

The separate `com.lma.app.acceptance/com.lma.app.DeviceTaskDiagnostics` instrumentation requires the already installed affected bundles. Missing bundles are unmet prerequisites, not a reason to download full models. It checks metadata, tiny file links and weight-free native queries only. Remove the acceptance APK afterwards; keep the normal app and its data.

## 3. Media and retained repairs

Ten current desktop production-page flows were recaptured: **57 PNG / ten GIF / ten MP4**. Each is labelled UI FIXTURE; owned browser resources close after recording. [Media index](MEDIA.md).

Actual-phone recordings retain their **v0.3.9 identity**: [recommendations](media/device/v0.3.9/01-recommended.png), [video category](media/device/v0.3.9/02-recommended-video.png), [MP4](media/device/v0.3.9/physical-walkthrough.mp4), [GIF](media/device/v0.3.9/physical-walkthrough.gif), [manifest](media/device/v0.3.9/manifest.json). The current phone contains private tasks/media, which are not copied into public recordings. Historical media is not rebound to this APK.

| Item | Retained repair |
| --- | --- |
| D01 | An unprepared legacy LTX form reports its own error without truncating global state |
| D02 | Acceptance resources remain uncompressed/aligned for Android 12 |
| D03 | Relative ADB media paths avoid the earlier non-ASCII absolute-output issue |
| D04 | v0.3.9 moves snapshot assembly to one background worker and reuses definitions/views |

The 4061 → 230 ms snapshot and 4228 → 24 ms main-thread warm measurements belong to **v0.3.9**. Eight current checks preserve relevant sources and immutable evidence; there is no new latency benchmark. [Methodology](PERFORMANCE.en.md). Published artifacts remain unchanged.

## 4. Open boundaries and declared deviation

| Item | Not established | Treatment |
| --- | --- | --- |
| U01 | Repaired complete 3D/Wan CPU output, quality, speed or peak RAM | No complete model reruns on the phone under the requested program-only policy |
| U02 | This phone's Wan GPU driver compatibility | Explicit rejection; requires a compatible driver/device or an explicit user-selected CPU route |
| U03 | Long screen-off inference, thermals, power management or restart recovery | A short health check does not establish endurance |
| U04 | Other devices, arbitrary HF architectures or full publisher workflows | Preserve bounded 62 recipes / 82 bundles / 18 extension engines plus text |

**Declared validation deviation:** a legacy Nano trained-host runner was selected accidentally, using pre-existing host assets, launching three children and producing two output records. The old Qwen runner exited on stale evidence before generation. Neither contributes to program counts or phone acceptance; no complete model was rerun on the phone. Correct bounded fixture tests were completed separately. [Deviation record](../verification/releases/v0.3.10/validation-deviation.json).
