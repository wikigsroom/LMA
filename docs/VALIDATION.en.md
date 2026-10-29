# LMA 0.2.0 validation

Current dev.27 business checks and APK are documented in [numbered delivery](releases/v0.3.0-dev.27.md) and the [evidence index](../verification/development/status.json). Recovery exercises real host processes/files/HTTP; UI uses a labelled bridge fixture. No new Android/model acceptance is claimed.

[中文（含完整修复与警告复核）](VALIDATION.md) · [Documentation](README.md)

## What passed

| Evidence | Result | Scope |
| --- | --- | --- |
| Backend | 85 assertions | Production Java including GGUF/profile bounds, migration/persistence, engine arguments and chat requests; real TLS/child JVMs, explicit framework adapters |
| HF discovery / Local | 45 assertions | Production HubClient, HubCatalog and Store; deterministic API fixtures and framework adapters |
| Protocol | 25 assertions | Actual protocol core on a host JVM |
| SQLite | 5 assertions | Production SQL on a host SQLite database; not Android SQLiteOpenHelper |
| UI | 66 assertions | Shipped interface including editable per-model presets/clamping; explicit test bridge, headless Edge, no Android runtime |
| Standalone Android Lint | 0 errors, 7 warnings | All 16 production Java files, resources, Manifest |
| APK | Signatures, identity, contents and alignment pass | Package and source-byte inspection |
| Native libraries | 14 checked | Pinned hashes, ELF dependencies, API 28 notes, interpreter, 16KB alignment |
| Runtime configuration | 15 options and 7 CPU kernels statically checked | Pinned upstream code and packaged binaries |
| Model catalogue | 14 pinned candidates | Revisions, sizes, publisher hashes, GGUF byte/architecture probes |
| Uncensored evidence | 14 publisher declarations checked | Pinned author cards and attribution to exact weights; not refusal-rate tests |
| Device acceptance APK | Compiled and signed | **Not executed on a phone** |

There are **226 desktop assertions** across backend, HF logic, protocol, SQLite and UI. Five additional live public HF Mirror metadata checks validate searches, pagination, pinned commits and publisher SHA256 without weights/inference. Static/package/audit checks remain separate. Public records are in [`verification/`](../verification/); input fingerprints reject stale passing reports.

The shipped APK SHA256 is `d8c16c7414ce5cc28c55fb3c2375c042e6735d53f73ebb5d4efa8388d7b130c1`. Source ZIP bytes change when documentation/media change; use that release's SHA256SUMS for its actual digest.

Per-model checks include binary GGUF v2/v3 fixtures, uint32/uint64 bounds, metadata order, tokenizer skipping, truncated/untrusted input, unknown-bound fallback, profile independence, persistence and migration. Real child argv/HTTP checks verify the selected profile; UI tests cover manual values, presets, keyboard, clamping, failed saves and model switching. See [model settings](MODEL_SETTINGS.en.md).

## Android Lint warnings

| ID | Reviewed limitation / rationale |
| --- | --- |
| OldTargetApi | targetSdk 35 is intentional for this build; no app-store readiness claim |
| BatteryLife | User-facing optional battery-exemption entry supports foreground serving |
| UseRequiresApi | Newer Back API references are isolated behind API checks and annotations |
| SetJavaScriptEnabled | Offline trusted assets need JavaScript; remote bridge pages are blocked |
| DataExtractionRules | Backup is disabled; no Android 12-specific extraction XML is provided |
| WakelockTimeout | Continuous API service uses explicit lifecycle release instead of a short fixed timeout |
| Recycle | The SAF stream is closed by the subsequent try-with-resources path |

The Chinese audit preserves the full review and fixes. Reviewed warnings are not proof of device behavior.

## What remains unverified

`physical_device_tests = 0`, `phone_inference_tested = false`, `background_endurance_tested = false`, and `fully_usable_on_phone_verified = false`. No physical Android device was available. The user prohibits Docker, WSL, virtual machines, and emulators; none were used as substitutes.

Outstanding acceptance includes APK installation/startup, actual ARM execution, each GGUF's full download/hash/load, useful model output, tokens/s, peak RAM, temperature, real WebView/input methods, Android SQLite/SAF, notification Stop, wake-lock release, LAN from another device, process recovery, reboot restore, and screen-off/vendor power behavior.

No independent model refusal-rate measurement was performed. Publisher claims and architecture probes do not establish zero refusals or compatibility with the nubia Z20.

The acceptance runner supports real-device checks and screen-off streaming workloads, but USB/ADB power can affect results. Compare unplugged battery and vendor settings before making endurance claims. See [device acceptance](DEVICE_ACCEPTANCE.en.md) and the [requirement audit](COMPLETION_AUDIT.md).

## Documentation media

Twelve screenshots, an MP4 and four GIFs use the actual packaged UI with simulated native state. HF metadata/download progress is simulated and replies are scripted. The visible demo banner and [media manifest](media/manifest.json) preserve this distinction. Browser pages and processes are closed after capture.

dev.20: Stable Audio 144 = Java 51 + C++ 93; six actual host children, six real LiteRT ADD/CAST tiny-graph runs and Arm sampler equivalence. Audio is a silent structural WAV fixture; full-model inference/Android tests remain zero. Foundation 561, UI 287, Lint 0 errors/13 warnings. See [evidence limits](STABLE_AUDIO_ENGINE.en.md) and [checkpoint notes](releases/v0.3.0-dev.20.md).

## Old LTX operation-staging source follow-up

See [staging evidence](LTX098_STAGING.en.md): 72 local comparisons, four variants/twelve trained T5 jobs, and three native host chains. Candidate A passes; B fails three float gates. The baseline six failures remain recorded; App/APK are unchanged. Host numbers/media establish no phone, quality, endurance or complete Release acceptance. [Numbered handoff/full pending scope](releases/v0.3.0-dev.23-ltx-staging.md).
