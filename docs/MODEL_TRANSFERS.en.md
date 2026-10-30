# Local model imports, pause and recovery

[中文](MODEL_TRANSFERS.md) · [Full release scope](MULTIMODAL_RELEASE_PLAN.md) · [Numbered checkpoint](releases/v0.3.0-dev.42.md)

Users select assets through All/search and manage them through Local. Installation, upgrades and browsing never start downloads; the APK delivers the shared foundation. Text/image/video/audio and dependency tags classify equal model entries. Recommended stays m08→m06→m01.

## User flow

1. Review complete components, license, storage needs and execution status, then explicitly download or select local files. Similar filenames do not authorize replacement weights.
2. Pause persists state and disconnects HTTP. Dev.42 also closes the active local input so the next previously selected transfer can run.
3. HTTP resume validates Range, total size and response boundaries. Document-provider streams need not support random access: after explicit file reselection, an incomplete local component copies from its beginning. Other verified complete components remain. **Local import restart differs from HTTP byte resume.**
4. Acceptance requires exact size and full SHA-256; installation requires every component. Partial bytes never count as an installed model. User pause does not become a transfer failure.
5. Foundation shutdown stops active reads and persists unfinished work as paused. App restoration never restarts transfers automatically. Users explicitly continue/reselect files; originals, installed versions and per-model settings remain independent.

The implementation closes the actual input, but Android document-provider behavior is untested. Large-model copying, Android file selection and every target's lifecycle remain open. Existing-file full-SHA adoption, stream copying and Android file selection are separate evidence. The original 900-second timeout importing the 13.43 GB MOSS pair remains failed.

## Implementation and evidence

Shared `BundleTransfers` prevents further reads before detaching and closing the input. Registration and pause share the task monitor; closing occurs outside it. An exiting operation only removes its own stream reference. Full SHA acceptance and component leases remain enforced.

A real blocking input first reproduced the old queue stall. The [original failure](../verification/research/bundle-pause-issue/first-run.json) retains source, case, driver and output. Thirteen passing checks cover blocked-read release, queue continuation, durable pause, explicit full re-import/SHA, active-stream shutdown and unopened queued inputs. They are included in the 692-check foundation suite; the API passes 68 checks. These are production Java checks on native Windows, without network requests, model inference or Android execution.

```powershell
python tools/test_bundle_pause.py
python tools/test_foundation.py
python tools/test_api.py
```

[Current pause checks](../verification/development/bundle-pause.json) · [Foundation](../verification/development/foundation.json) · [API](../verification/development/api.json)

No new controls are added. [Recovery screenshots/GIF/MP4](media/development/recovery/manifest.json) are refreshed for the current version and label the simulated bridge; they do not establish Android import behavior.
