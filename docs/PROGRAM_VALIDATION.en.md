# Program-only validation policy · v0.3.11
Current gate coverage: **60 suites / 15,063 assertions, 73 records, 794 UI checks**. Separate physical program acceptance: **23 checks / 60.239 seconds screen-off API health**. Authorized installed-model probes retain exact tested APKs and success/incomplete outcomes in [their own record](../verification/releases/v0.3.11/physical-models.json). Gate counts remain model-free; the optional real-model records are not described as zero inference. [Current inventory](IMPLEMENTATION_V0311.en.md).

## Historical v0.3.7 policy and measurements

**v0.3.11 authorization update, 2026-11-01:** The user permits selected bounded phone/model checks at developer discretion. Use installed models and separate `physical-models.json` evidence; regular gates remain program checks. Full-model quality/endurance is not reinstated as a prerequisite. v0.3.7 figures below are historical.

[中文](PROGRAM_VALIDATION.md) · [Release notes](releases/v0.3.7.md) · [Policy JSON](proposals/program-validation-policy.json) · [Implementation and all suites](IMPLEMENTATION_V037.en.md)

On 2026-10-31 the user requested program validation only. Complete trained-model downloads/copies/runs, ASR, phone inference and endurance are not development or release prerequisites. Missing code must still be implemented; the original scope is preserved.

v0.3.7 implements F01–F12, text, selections 01–14 / 16 / 17 and added P01–P06 adaptations, with 62 recipes, 82 catalogue bundles and 18 extension engines plus text. All models are equal peers. Installation and upgrades deliver the foundation; users select, download, import and manage their models.

| ID | Check | Current result |
| --- | --- | --- |
| V01 | Program coverage | **59 suites / 14,939 assertions**, exact source fingerprints |
| V02 | Foundation / community / shared expansion | 1,226 / 818 / 884 assertions |
| V03 | Full production UI | **748 checks**, explicit desktop bridge |
| V04 | Current evidence | **72 JSON records plus status.json**; 815 historical file identities preserved |
| V05 | APK | ARM64, API28+, original signer, **41 native libraries**, resolved dependencies, 16 KiB ELF/ZIP alignment |
| V06 | Lint | **Zero errors / 16 existing warnings** |
| V07 | Media | **Nine flows / 52 screenshots / nine GIFs / nine MP4s**, UI FIXTURE labels |
| V08 | Complete trained-model downloads / copies / runs | Zero for each |
| V09 | Phone inference / quality / speed / peak RAM / screen-off endurance | Not executed or accepted |
| V10 | Physical program acceptance | **19 checks; 60-second screen-off API health**, no inference/endurance |

[Current fingerprints](../verification/releases/v0.3.7/status.json) and the [pinned source audit](../research/portability/adaptation-current.json) distinguish `all_requested_adaptations_complete=true` / `all_benchmark_architectures_integrated=true` for versioned bounded CPU profiles from `full_benchmark_workflows_reproduced=false`. These flags do not establish support for arbitrary HF architectures, every upstream CUDA configuration, verified public complete-export endpoints or every phone.

Native Windows JVM/HTTP/filesystem/process checks call production code through explicit Android framework ports. Actual source classes, formal-configuration meta construction, bounded random networks and native/upstream numerical comparisons check structure and algorithms, not complete trained generation. UI uses labelled bridge fixtures. Android Service, UI, SQLite and short screen-off API health now have physical records. Complete model execution, SAF picker flows, MediaCodec generation and inference RSS remain unmeasured. Unavailable Windows worker RSS is not reported as measured RAM.

Follow [BUILD](BUILD.en.md) to restore locked sources and compile every enabled native engine; the [complete test inventory](IMPLEMENTATION_V037.en.md#program-checks) links its entry points. Run production-page checks with `node tests/ui-smoke.cjs`; capture all nine flows per [MEDIA](MEDIA.md). Check the APK, signature and Lint, then run `python tools/audit_adaptations.py --require-complete`, `python tools/program_evidence.py --export`, source packaging and release preparation. Reuse passing checks only while exact fingerprints match; rerun affected suites after source changes.

Never fabricate fingerprints, remove failures, call registration a runtime implementation, restore cancelled full-model/device gates, invoke Docker/WSL/VM/emulators or silently acquire models. Close owned browsers in finally. Preserve private signing, existing drive mappings, recommendations `m08 → m06 → m01` and user-controlled assets.

`verification/program/`, `verification/history/` and previous Release assets retain their original identities. Current evidence lives separately in `verification/releases/v0.3.7/`. The old v0.3.5 30-suite / 5,820-assertion result and earlier missing-adapter audits remain historical; original generation results, errors and failures stay discoverable.

[Physical acceptance / 真机专项](DEVICE_ACCEPTANCE.md) · [English](DEVICE_ACCEPTANCE.en.md). Optional physical program evidence is version/APK-bound; it does not restore cancelled model-run prerequisites.
