# Program-only validation policy

[中文](PROGRAM_VALIDATION.md) · [v0.3.3](releases/v0.3.3.md) · [Policy JSON](proposals/program-validation-policy.json)

The user requested program validation only on 2026-10-31. Complete trained-model downloads/copies/runs, ASR, phone inference and endurance are not development/release prerequisites. Missing implementation is not waived, and the complete original frozen scope is preserved.

v0.3.3 retains F-01–F-12, text, selections 01–14 / 16 / 17, community models and speech/single-image 3D; it adds an actual four-view CPU runtime and persistent diagnostics. [Implementation](IMPLEMENTATION_V033.en.md) · [MV/diagnostics](MULTIVIEW_DIAGNOSTICS.en.md).

| Check | Current result |
| --- | --- |
| Program coverage | **26 suites / 4,940 assertions**, current fingerprints |
| Community / shared expansion / MV native | 818 / 288 / 63 assertions |
| Full production UI | **616 checks**, explicit simulated bridge |
| Four current captures | 34 community / 8 workbench / 32 speech/3D / 19 MV checks |
| APK | ARM64, API28+, original signer, **38 libraries**, dependency closure and 16 KiB ELF/ZIP alignment |
| Lint | 0 errors / 16 retained warnings |
| Current media | **20 screenshots / 4 GIFs / 4 MP4s**, UI FIXTURE labels |
| Complete trained-model downloads / copies / runs | Zero |
| Phone / model quality / screen-off endurance | Not executed or accepted |

There are [35 current program records plus status](../verification/program/status.json). The [v0.3.2 archive](../verification/history/v0.3.2-program-archive.json) preserves all 34 prior JSON files byte-for-byte against commit `3f59f2e9f61e72ea3400fe268f85f959c759fc3b`. Its three recordings remain under `docs/media/history/v0.3.2/`. Earlier version archives and original model failures retain their identities.

Native Windows JVM/HTTP/filesystem/process checks exercise production logic with explicit Android framework ports. Bounded random neural graphs test structure, not complete trained generation. UI uses labelled simulated bridges; actual Service, SAF, MediaCodec, power flags and Android process RSS are compiled/package-checked, without phone execution. Windows worker RSS is unavailable rather than simulated as measured RAM.

`release_ready` applies to this program-delivery policy. `full_scope_implementation_complete` is explicitly scoped to original F-01–F-12/text/selected IDs. It is not a universal model claim: current status separately records **all_benchmark_architectures_integrated=false** and D04–D12. [Pinned source audit](../research/portability/audit-v0.3.3.json) identifies actual architecture work. No test can substitute for a missing native port.

Run `tools/run_program_checks.py` (backend first, then three bounded groups), `tools/test_foundation.py`, `tools/test_expansion.py`, `tools/test_multiview.py` and `node tests/ui-smoke.cjs`. Package verification and Lint follow the current APK build. Refresh the four affected `capture_workbench.cjs` groups, then follow [RELEASING](RELEASING.md). Existing passing checks are reused only while their exact fingerprints remain current.

Never edit fingerprints to fabricate passes, delete failures, call a registration integration, restore old trained/device gates, invoke Docker/WSL/VM/emulators, or silently acquire model assets. Close owned browsers in finally. Preserve signing material privately, existing drive mappings, original recommendations and user-controlled model files.
