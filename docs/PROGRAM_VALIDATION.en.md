# Program-only validation policy

[中文](PROGRAM_VALIDATION.md) · [v0.3.5](releases/v0.3.5.md) · [Policy JSON](proposals/program-validation-policy.json)

The user requested program validation only on 2026-10-31. Complete trained-model downloads/copies/runs, ASR, phone inference and endurance are not development/release prerequisites. Missing implementation is not waived, and the complete original frozen scope is preserved.

v0.3.5 retains F-01–F-12, text, selections 01–14 / 16 / 17, community models and speech/single-image 3D; it adds matched-export Hunyuan3D shape and UltraShape refinement while preserving RF/part geometry, four-view CPU and persistent diagnostics. [Implementation](IMPLEMENTATION_V035.en.md) · [Spatial shape](SPATIAL_SHAPE.en.md).

| Check | Current result |
| --- | --- |
| Program coverage | **30 suites / 5,820 assertions**, current fingerprints |
| Community / shared expansion / MV / RF | 818 / 533 / 63 / 161 assertions |
| Full production UI | **653 checks**, explicit simulated bridge |
| Six current captures | 34 community / 8 workbench / 32 speech/3D / 19 MV / 17 RF Shape / 20 Spatial checks |
| APK | ARM64, API28+, original signer, **40 libraries**, dependency closure and 16 KiB ELF/ZIP alignment |
| Lint | 0 errors / 16 retained warnings |
| Current media | **30 screenshots / 6 GIFs / 6 MP4s**, UI FIXTURE labels |
| Complete trained-model downloads / copies / runs | Zero |
| Phone / model quality / screen-off endurance | Not executed or accepted |

There are [41 current program records plus status](../verification/program/status.json). The [v0.3.2 archive](../verification/history/v0.3.2-program-archive.json) preserves all 34 prior JSON files byte-for-byte against commit `3f59f2e9f61e72ea3400fe268f85f959c759fc3b`. Its three recordings remain under `docs/media/history/v0.3.2/`. Earlier version archives and original model failures retain their identities.

Native Windows JVM/HTTP/filesystem/process checks exercise production logic with explicit Android framework ports. Bounded random neural graphs test structure, not complete trained generation. UI uses labelled simulated bridges; actual Service, SAF, MediaCodec, power flags and Android process RSS are compiled/package-checked, without phone execution. Windows worker RSS is unavailable rather than simulated as measured RAM.

`release_ready` applies to this program-delivery policy. `full_scope_implementation_complete` is explicitly scoped to original F-01–F-12/text/selected IDs. It is not a universal model claim: current status separately records **all_benchmark_architectures_integrated=false** and D04, D05, D07 Paint, D08–D10. [Pinned source audit](../research/portability/audit-v0.3.5.json) identifies actual architecture work. No test can substitute for a missing native port.

Run `tools/run_program_checks.py` (backend first, then three bounded groups), `tools/test_foundation.py`, `tools/test_expansion.py`, `tools/test_multiview.py`, `tools/test_shape.py`, `tools/test_spatial.py`, `tools/test_spatial_shape_graphs.py`, `tools/test_spatial_sparse.py` and `node tests/ui-smoke.cjs`. Package verification and Lint follow the current APK build. Refresh the six affected `capture_workbench.cjs` groups, then follow [RELEASING](RELEASING.md). Existing passing checks are reused only while their exact fingerprints remain current.

Never edit fingerprints to fabricate passes, delete failures, call a registration integration, restore old trained/device gates, invoke Docker/WSL/VM/emulators, or silently acquire model assets. Close owned browsers in finally. Preserve signing material privately, existing drive mappings, original recommendations and user-controlled model files.

The 30 suites / 5,820 assertions include 188 native Spatial, 60 graph, 109 sparse, 161 RF Shape and 653 UI checks. The Android worker compiles; complete trained exports and phone inference were not run. The original frozen scope is retained. [设计](SPATIAL_SHAPE.md) · [Design](SPATIAL_SHAPE.en.md).

The original v0.3.3 36 JSON files and four media groups are preserved by [Git identity](../verification/history/v0.3.3-program-archive.json), separately from current evidence.

## v0.3.5 Spatial evidence / 形状精修证据

Added 188 native/CLI/preprocessing checks, 60 pinned graph comparisons and 109 sparse CPU/ONNX checks. 新增项纳入 30 组 / 5820 项总数，不叠加重复统计。Complete UI: 653; shared expansion: 533; foundation: 995. [完整方案](SPATIAL_SHAPE.md) · [English](SPATIAL_SHAPE.en.md).

`all_requested_adaptations_complete=false` explicitly preserves the missing D04/D05/D07 Paint/D08/D09/D10 ports and experimental F5 Chinese equivalence. 完整模型与真机验证按用户要求不做，不作为这些代码缺口的解释。v0.3.4 的 38 JSON 与 40 媒体文件按[不可变 Git blob](../verification/history/v0.3.4-program-archive.json)归档。
