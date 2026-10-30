# Program validation for subsequent development

[中文](PROGRAM_VALIDATION.md) · [Full functional scope](MULTIMODAL_RELEASE_PLAN.en.md) · [Machine-readable policy](proposals/program-validation-policy.json) · [This delivery](releases/v0.3.0-dev.45.md)

**From 2026-10-31 the user requires program validation only, without time-consuming complete-model execution.** This supersedes earlier requirements to repeat full-weight inference, model-quality/ASR scoring and phone inference/endurance before subsequent program deliveries or publication. It does not waive missing implementation. F01–F12, existing text, selections 01–14/16/17, every frozen subtarget and both SD1.5/SDXL LoRA remain in the same version scope.

| ID | Checks | Meaning of a pass |
|---|---|---|
| V01 | Android compilation, signature, dependencies, API, alignment and packaged resources | Consistent build and delivery identity; not phone inference |
| V02 | Recommendations, HF All/search, Local, components and recipes | Explicit user-owned selection, download/import, pause/resume, update/delete; no asset downloads on installation or browsing |
| V03 | Independent editable model parameters, bounds and immutable job snapshots | Model-bound settings and controlled limits |
| V04 | Production queue, authenticated API, artifacts, cancel/shutdown/restart recovery | Actual program/file/loopback behavior with clearly identified bounded fixtures |
| V05 | Engine contracts, failures and small algorithm checks | Adapter behavior; synthetic children, fixed logits and small graphs are not complete models |
| V06 | UI regression, screenshots/GIF/MP4, documentation and source auditing | Actual pages with labelled test state; owned browsers always close |

Do not download/copy complete model assets for validation, regenerate complete image/speech/video suites, run ASR scores, three loads per model, 15-minute screen-off inference or one-hour inference APIs. Metadata and small development dependencies remain allowed. Production inference must still execute entirely on the same no-ROOT Android phone, without off-device/virtualized fallback.

“Program integrated/checked” names the actual adapter, business flow and checks. “Model tested” refers only to the exact historical files, model and commit. Phone execution, performance, memory, quality and background endurance remain untested without corresponding records. No phone is available in this conversation; do not request one repeatedly. Preserve historical LCM differences, Sana gray outputs/purpose correction, MOSS reference failures and Wan artifacts without promoting them to passes.

Publication still requires implemented functionality, relevant program checks, consistent version/original signature, exact source/APK identities, bilingual documentation and release notes. Complete-model quality and phone endurance are no longer program-release gates.

dev.45 is a signed program-development checkpoint, not complete frozen feature coverage. [Sana-Sprint 0.6B](SANA_SPRINT.en.md) now implements the matched mobile text-to-image alternative in selection 04, with explicit component and evidence boundaries. Original PixArt/multiscale LTX still differs from the existing Google T5 Q5 single-scale variant; that missing adapter remains in the complete v0.3.0 scope. Waiving model runs does not implement missing code.

Existing model experiments and checkpoints remain in `verification/development/`, `verification/history/` and named research directories. Current program records go to `verification/program/` with checked source fingerprints, without running historical models. Unchanged UI recordings may be reused with their original version explicitly stated and matching page-source hashes.
