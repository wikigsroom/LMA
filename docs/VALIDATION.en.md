# LMA 0.1.2 validation

[中文（含完整修复与警告复核）](VALIDATION.md) · [Documentation](README.md)

## What passed

| Evidence | Result | Scope |
| --- | --- | --- |
| Backend | 54 assertions | Production Java, real TLS and child JVM processes; explicit Android framework adapters |
| Protocol | 25 assertions | Actual protocol core on a host JVM |
| SQLite | 5 assertions | Production SQL on a host SQLite database; not Android SQLiteOpenHelper |
| UI | 31 assertions | Shipped interface, explicit test bridge, headless Edge; no Android runtime |
| Standalone Android Lint | 0 errors, 7 warnings | All 12 production Java files, resources, Manifest |
| APK | Signatures, identity, contents and alignment pass | Package and source-byte inspection |
| Native libraries | 14 checked | Pinned hashes, ELF dependencies, API 28 notes, interpreter, 16KB alignment |
| Runtime configuration | 15 options and 7 CPU kernels statically checked | Pinned upstream code and packaged binaries |
| Model catalogue | 14 pinned candidates | Revisions, sizes, publisher hashes, GGUF byte/architecture probes |
| Uncensored evidence | 14 publisher declarations checked | Pinned author cards and attribution to exact weights; not refusal-rate tests |
| Device acceptance APK | Compiled and signed | **Not executed on a phone** |

There are **115 desktop assertions** in the first four rows. Static/package/audit checks are separate, not additional phone tests. Public records are in [`verification/`](../verification/); records include input fingerprints so a stale passing report cannot silently validate changed inputs.

The shipped APK SHA256 is `e9e3b7103f5e63c86953acdb986387f73cae9e3fb42851f6af1b9fffe6c1cc28`. Source ZIP bytes change when documentation/media change; use that release's SHA256SUMS for its actual digest.

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

Seven screenshots, MP4, and GIFs use the actual packaged UI with simulated native state. Download progress is simulated and replies are scripted. The visible demo banner and [media manifest](media/manifest.json) preserve this distinction. Browser pages and processes are closed after capture.
