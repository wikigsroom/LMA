# Program-only validation policy

[中文](PROGRAM_VALIDATION.md) · [v0.3.1](releases/v0.3.1.md) · [policy JSON](proposals/program-validation-policy.json)

The user explicitly requested program validation only on 2026-10-31. Do not repeat complete trained-model execution, ASR scoring, physical-phone inference or endurance gates from older documents. Missing program implementation is still required; the frozen scope is not split or deferred.

v0.3.1 retains the complete F-01–F-12 foundation, text and selections 01–14 / 16 / 17, adding 44 optional community checkpoint recipes and independent content provenance. See the [current implementation](IMPLEMENTATION_V031.en.md), [community guide](COMMUNITY_MODELS.en.md) and [current matrix](../catalogue/release-0.3.1-implementation.json).

| Check | Current result |
| --- | --- |
| Program suites | 24 suites / **4,438 assertions**, with current source fingerprints |
| Community metadata / production Java | 814 checks across all 44 optional recipes, labels, independent settings and request planning |
| Full UI | **564 checks**; separate current captures exercise 34 community and 8 workbench interactions |
| Android package | ARM64, API28, 35 native libraries, resolved dependencies, 16 KiB ELF/ZIP alignment, original signer |
| Android Lint | 0 errors / 16 existing warnings |
| Current media | 10 screenshots, 2 GIFs, 2 MP4s, visibly labelled UI FIXTURE |
| Research inputs | 27 source repositories and 45 bounded file headers plus API/card metadata; no complete checkpoints |
| Complete model downloads / copies / executions | Zero |
| Phone / output quality / endurance | Not executed under the user’s policy; no acceptance claim |

[29 current records](../verification/program/status.json) bind this source and APK. All 29 v0.3.0 program files are [archived byte-for-byte](../verification/history/v0.3.0-program-archive.json) and checked against their original Git blobs; its two recordings are preserved under `docs/media/history/v0.3.0/`. Earlier dev.45/dev.44/dev.42 records and complete-model failures retain their original identities.

Explicit desktop Android/media/neural-stage ports exercise production validation, settings, storage, scheduling, process management, downloads and APIs. Actual Android Service, SAF and MediaCodec behavior is covered by compilation/package checks, without a physical-device run. Small bounded random neural fixtures test structure, not trained generation.

`release_ready` means the program-delivery policy passes. It does not establish that a checkpoint runs on Nubia Z20 or any other phone. Header layout checks cannot prove output quality, peak RAM, prediction semantics or driver behavior; source annotations retain these limits.

Principal entry points are `tools/test_backend.py` → `tools/test_community.py`, `node tests/ui-smoke.cjs`, `tools/build.py` → `tools/verify_package.py` → `tools/test_android_lint.py`, and `capture_workbench.cjs community / release-workbench`. Other affected retained suites must also have current evidence; the status record lists their exact sources/fingerprints. Finish with `tools/release_scope.py`, `tools/program_evidence.py --export`, `tools/package_delivery.py`, `tools/check_repository.py` and `tools/prepare_release.py`.

Never manufacture passes by rewriting fingerprints, weakening gates, deleting historical failures or calling unsupported registrations integrated. Do not use `--trained`, obtain complete trained weights, or invoke Docker, WSL, virtual machines or emulators. Close owned browsers in finally. APKs contain no weights or personal credentials; users explicitly select model assets and updates.
