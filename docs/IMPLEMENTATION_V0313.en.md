# v0.3.13 implementation and verification

[中文](IMPLEMENTATION_V0313.md) · [Port behavior](API_PORT.en.md) · [Release notes](releases/v0.3.13.md)

This update changes the public API default and performs a one-time preference migration. Shared `ApiPort` rules define 52187. Application startup migrates preferences before services start; listener startup, settings, advertised URLs and internal HTTP requests use the shared default. The production UI fallback, initial HTML URL and development fixtures agree.

| No. | Check | Result and scope |
| --- | --- | --- |
| 1 | Fresh install, former default, custom ports, one-time migration, invalid historical values | Five new backend groups, including 1024/65535 boundaries |
| 2 | Production loopback and LAN UI URLs | Two new checks; all 796 UI checks pass |
| 3 | Program and build evidence | 62 suites, 15,122 assertions and 75 current records |
| 4 | APK and static analysis | ARM64 / Android 9+, original signer, 41 native libraries, 16 KiB alignment, zero lint errors; existing warnings disclosed |
| 5 | Physical program and idle performance | 24 program checks and 8 performance checks; installed models retained, no inference counted as a program gate |
| 6 | Physical direct LAN requests | Separate current evidence verifies the signed upgrade, old-listener closure, preserved user settings, actual PNG/WAV and media protocols |
| 7 | Documentation and media | Both READMEs/guides, ten development UI flows, five physical screenshots and a recording/GIF |

Affected backend, community, pause, document input, API/publication, workbench, recovery, text, migration, scheduler, preparation, assembly, diffusion, MNN, HF, recipe suggestion, voice, Sana and LTX program checks were rerun. Unchanged native-component records were checked against current source fingerprints, without rerunning complete trained models.

The phone is a motorola edge plus, Android 12/API31. This does not establish Z20 or X30 acceptance. New-port inference results belong to the separate [LAN report](../verification/supplemental/v0.3.13/lan-http.json). The old video receives transfer checks only and retains its [v0.3.12 benchmark identity](DEVICE_BENCHMARK_V0312.en.md).

All 62 recipes, 82 bundles, 18 extension engines plus text, and 14 recommendations retain their scope and ordering. The APK carries only the foundation. Valid 3D outputs, all-model phone quality and long background endurance remain separate acceptance work.
