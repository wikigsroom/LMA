# Physical task-failure diagnosis · v0.3.10

**Follow-up v0.3.11:** [Explicit CPU video now generates on the phone; shared native 3D path repair](ON_DEVICE_MODEL_REPAIR.en.md). The five-case cleanup and diagnostics below are the preserved v0.3.10 investigation.

[中文](TASK_FAILURES.md) · [User guide](USER_GUIDE.en.md) · [Release notes](releases/v0.3.10.md) · [Public diagnostic record](../verification/releases/v0.3.10/task-diagnostics.json)

The connected phone identifies as **motorola edge plus / burton, Android 12 / API31, SM8250**. Its history contained seven jobs: five failed and two successful, with none active. Diagnosis used original timestamps, installation receipts, tiny owned files and native startup queries under the actual application identity. No complete trained model was rerun. Times below are 2026-11-01, UTC+8.

## 1. Each failed record

| Case | Time / model | Duration | Cause | Repair and disposition |
| --- | --- | ---: | --- | --- |
| T01 | 13:10:07 / TRELLIS.2 pbr512 | 19 ms | Android denied a hardlink in the private workspace with `EACCES`; the model files exist | Fixed staging with a verified private symbolic-link fallback. A four-byte physical probe passes; full 3D generation was not rerun |
| T02 | 13:10:24 / TRELLIS.2 pbr512 | 19 ms | Same filesystem restriction as T01 | Covered by the shared workspace fix. No replacement model download is needed for this failure; the old job was privately archived and removed |
| T03 | 13:19:35 / Wan 2.1 1.3B Q4 GPU | 339 ms | The signed engine requires Vulkan 1.2; its device query exposes only CPU. Merged native stderr corrupted JSON event framing and hid the explanation | Fixed diagnostic transport and GPU preflight. This driver cannot run that GPU recipe; users may explicitly import a CPU recipe, whose full output and performance remain untested |
| T04 | 13:19:45 / Wan 2.1 1.3B Q4 GPU | 189 ms | Same backend failure as T03, previously reduced to a generic error | Preflight now explains the mismatch and adds no doomed job. Retrying or reducing resolution cannot supply missing Vulkan capability |
| T05 | 13:29:24 / Pixal3D geometry512 | 23 ms | The same shared hardlink staging path was denied | Covered by the symbolic-link fallback; original files and settings remain. Full 3D generation was not rerun |

These were startup/staging failures. The original records lack sufficient resource samples to establish an out-of-memory cause. Fixing the identified startup failure does not establish successful complete generation.

## 2. Implementation

`EngineWorkspace` first attempts a hardlink. If unavailable, it requires an ordinary, non-symlink source and an absent destination, creates a private symbolic link, and verifies that both resolve to the same source. The model lease retains that source throughout execution. Cleanup removes workspace entries without following them. Existing destinations, symlink sources or failure of both link methods produce an explicit failure; no large weight copy or overwrite is attempted.

`NativeWorker` reads structured events separately from stderr, drains stderr continuously to prevent pipe blockage and retains only bounded, allowlisted diagnostic codes. Task execution details retain effective parameters, completion state, exit code and diagnostic code. Structured native errors take precedence. Raw prompts and private paths are not published. Earlier MNN/Sana-Sprint, MOSS delay and Qwen TTS metadata also survives completion reporting.

Wan GPU validation runs the signed engine's bounded `--devices` query before enqueue and execution, without weights. Positive capability results are cached; catalogue snapshots and idle UI updates do not invoke the probe. Unsupported hardware is rejected explicitly, without an automatic CPU switch. This phone reports `Vulkan 1.2 required` and CPU only. An APK update cannot change its driver capability.

## 3. Optional, explicit Wan CPU import

The [CPU import descriptor](examples/wan21_13b_q4_cpu_phone.json) contains metadata only. Its ID is `wan21_13b_q4_cpu_manual_v1`, using the signed `sd_cpp` CPU engine and `wan21_13b_split_cpu_v1` recipe.

1. Download the JSON yourself and select “导入模型包清单” (import model-bundle manifest) in local model management.
2. Review the CPU tag, four components, pinned sources, licenses and transfer plan; explicitly choose installation.
3. Existing objects with the same verified identities can be reused. Missing components download only after confirmation. CPU/GPU identities and per-model settings remain separate.
4. Explicitly select the CPU bundle when creating a task. Complete CPU output, speed and resource requirements were not tested this turn.

The diagnostic session did not import, download or execute this optional bundle. It does not alter the default 82 bundles, fourteen recommendations or the installed GPU bundle, and is not a promise of successful full CPU video generation.

## 4. Exact cleanup

Original jobs, model settings, artifact identities and diagnostic results were backed up privately under ignored `build/device-task-audit/`. Each failed terminal job was reread and matched before deleting its exact ID. Subsequent checks confirmed:

| Item | Result |
| --- | --- |
| P01 | All five failed jobs privately archived, then removed from history |
| P02 | Both successful job records remain identical |
| P03 | All five artifacts/inputs/results remain identical |
| P04 | Five installed models, installation flags and per-model settings remain; drafts were not cleaned |
| P05 | All seventeen relevant components exist, match expected sizes and retain valid installation receipts |

Private backups, prompts, personal media, API credentials and connection information are excluded from Git and release assets. The [public JSON](../verification/releases/v0.3.10/task-diagnostics.json) contains only case numbers, bundle identities, timings, causes and check conclusions.

## 5. Verification and open boundaries

Physical checks cover the four-byte link fixture, seventeen component receipts/sizes, native `--info`/`--devices`, and production preflight rejecting the GPU route without changing history. Separate UI/SQLite/API checks include approximately sixty seconds of screen-off foreground-service health. Host production-class fixtures cover separate stderr, diagnostics without a newline, structured errors, nonzero exits, retained execution parameters and the CPU descriptor.

| Item | Not established | Treatment |
| --- | --- | --- |
| U01 | Complete repaired TRELLIS.2/Pixal3D output, quality or peak RAM | The diagnosed staging failure is repaired; full models remain outside the requested program-only validation |
| U02 | Complete Wan CPU output or runtime | Available as an explicit user-selected route; not executed for the user |
| U03 | Compatibility of this phone with the selected Wan GPU engine | Currently incompatible; requires a driver/device satisfying the engine, not retries or an application-only patch |
| U04 | Long inference and screen-off endurance | A sixty-second health check establishes only short program survival |

The v0.3.9 latency measurements retain their original identity. This release checks preservation of relevant performance sources and historical evidence, without claiming a new latency benchmark. [Performance](PERFORMANCE.en.md) · [Physical acceptance](DEVICE_ACCEPTANCE.en.md)
