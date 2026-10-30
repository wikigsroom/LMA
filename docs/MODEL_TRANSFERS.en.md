# Local model imports, pause and recovery

[中文](MODEL_TRANSFERS.md) · [Full release scope](MULTIMODAL_RELEASE_PLAN.md) · [Numbered checkpoint](releases/v0.3.0-dev.44.md) · [Program-only validation](PROGRAM_VALIDATION.en.md)

Users select assets through All/search and manage them through Local. Installation, upgrades and browsing never start downloads; the APK delivers the shared foundation. Text/image/video/audio and dependency tags classify equal model entries. Recommended stays m08→m06→m01.

## User flow

1. Review complete components, license, storage needs and execution status, then explicitly download or select local files. Similar filenames do not authorize replacement weights.
2. Pause persists state, disconnects HTTP, cancels pending document opening and closes readable inputs so the next selected transfer can run. Dev.44 covers bundles, legacy text models and media imports; foundation shutdown also cancels pending opens.
3. HTTP resume validates Range, total size and response boundaries. Document-provider streams need not support random access: after explicit file reselection, an incomplete local component copies from its beginning. Other verified complete components remain. **Local import restart differs from HTTP byte resume.**
4. Acceptance requires exact size and full SHA-256; installation requires every component. Partial bytes never count as an installed model. User pause does not become a transfer failure.
5. Foundation shutdown stops active reads and persists unfinished work as paused. App restoration never restarts transfers automatically. Users explicitly continue/reselect files; originals, installed versions and per-model settings remain independent.

The system document provider receives an opening cancellation signal; provider response can be delayed. Late descriptors cannot become valid inputs. Program checks use bounded data and explicit host ports, without testing Android providers or full-model throughput. Do not copy complete models for subsequent validation. The original timeout copying the 13.43 GB MOSS pair remains a historical failure.

## Implementation and evidence

Shared `InputHandle` registers the source before opening. `DocumentInput` uses Android `CancellationSignal` with `AssetFileDescriptor`. Cancel pending opens and active reads, release late resources, invoke cancellation/close outside manager locks and prevent old operations from closing newer work. Full SHA acceptance, storage reserves and component leases remain enforced.

Blocking fixtures reproduce the [original read stall](../verification/research/bundle-pause-issue/first-run.json) and the [pending-open stall](../verification/research/input-opening-issue/first-run.json), preserving original source, cases, drivers and failed output. Current bundle checks pass 22 assertions across opening/reading × pause/shutdown. The 138-check backend includes eight cases/40 assertions for legacy text and media imports, cancellation and recovery. Actual production `DocumentInput` has six cases/15 assertions for null descriptors, stream-creation failure, early cancellation and late resource cleanup. Foundation passes 701 and API 68. These are native Windows program checks with explicit Android framework ports, not complete-model or physical Android execution.

```powershell
python tools/test_bundle_pause.py
python tools/test_document_input.py
python tools/test_backend.py
python tools/test_foundation.py
python tools/test_api.py
```

[Current program evidence](../verification/program/status.json) · [Historical dev.43](../verification/development/status.json)

No new controls. [Recovery screenshots/GIF/MP4](media/development/recovery/manifest.json) retain the original dev.42 fixture identity with matching page-source hashes. Current pages are checked separately; reused recordings and host ports do not establish Android import behavior.
