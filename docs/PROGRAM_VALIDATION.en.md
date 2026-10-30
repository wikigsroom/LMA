# Program-only validation policy

[中文](PROGRAM_VALIDATION.md) · [v0.3.0](releases/v0.3.0.md) · [policy JSON](proposals/program-validation-policy.json)

The user explicitly requested on 2026-10-31: “请你后续内容只做程序验证，不需要走完完整的模型运行验证，太耗费时间了。” This supersedes older release requirements for complete trained-model execution, ASR scoring, phone inference and prolonged endurance. Missing program functionality is not waived, and the frozen scope is not split into later releases.

v0.3.0 closes the original PixArt T5/multiscale LTX program gap and includes the previously integrated Sana-Sprint route. The full F-01–F-12/text/01–14/16/17 program mapping is in the [implementation matrix](IMPLEMENTATION_V030.en.md).

| Validation / 验证 | Current result / 当前结果 |
| --- | --- |
| Program suites / 程序回归 | 23 suites, 3,590 assertions; source fingerprints checked |
| Android package / 安装包 | ARM64, API28, 35 native libraries, resolved dependencies, 16 KiB ELF/ZIP alignment, original signing certificate |
| Android Lint | 0 errors, 16 retained warnings |
| Current UI / 当前界面 | 530 regression checks; 9 screenshots, 2 GIFs and 2 MP4 recordings across two flows |
| Bounded neural fixtures / 有界神经夹具 | Small random T5/upsampler/MNN graphs and reference math; not complete trained models |
| Complete weights / 完整模型 | 0 complete downloads, copies or executions for this validation |
| Phone / quality / endurance | Not tested; not required by updated policy; no quality or phone suitability claims |

Current evidence: [28 records](../verification/program/status.json). Prior dev.45 program records are archived byte-for-byte in [history](../verification/history/dev45-program/status.json); dev.44/dev.42 and complete-model failures retain their identities. A stale model-quality failure is never relabelled as a pass. `release_ready` means readiness under this program-only policy, not verified phone usability.

Tests exercise production validators, stores, scheduling and process ownership using explicit host Android/media/neural ports. Android Service/SAF/MediaCodec execution is compiled and inspected, not physically exercised. UI recordings visibly identify fixture data; browsers close in finally blocks. No Docker, WSL, virtual machine or emulator is used. App updates contain code and metadata only; users retain explicit model acquisition and management.
