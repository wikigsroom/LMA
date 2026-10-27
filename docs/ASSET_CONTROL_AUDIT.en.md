# Foundation updates and user-controlled model assets: audit

[中文](ASSET_CONTROL_AUDIT.md) · [Full requirements](MULTIMODAL_RELEASE_PLAN.en.md) · [Release summary](releases/v0.3.0-plan.md) · [Actual progress](DEVELOPMENT.en.md)

Reviewed 2026-10-28. **Current requirements match foundation-only App updates with user-selected/downloaded/managed model assets.** Document compliance does not establish completed implementation or Android acceptance.

| Requirement | Document rule | Implementation / evidence |
| --- | --- | --- |
| APK updates deliver the foundation | Asset-separation section, F-02 / A11 | Package checks exclude weights, model-specific vocabularies and voices; engine code belongs in the App |
| Users select models and dependencies | Explicit selected bundle plus previously disclosed required components; no mandatory installation of all supported targets | Bundle details, explicit transfers and folder import exist; eight explicit HF component templates do not download on registration; other architectures still need adaptations |
| Install/upgrade/browse never downloads models | Structured `model_asset_policy` forbids implicit selection/download/replacement | Host storage/transfer/UI checks cover declaration, browsing and missing-asset failure; physical install/upgrade still needs evidence |
| Independent management | Local pause/resume/settings/import/update/delete, with upgrade preservation | dev.7 implements bundle update/review/explicit activation/rollback; dev.9 adds existing-GGUF migration/shared management; physical Android upgrades remain unverified |
| Text/image/video/audio tags | One flat pool; independent capability and engine/architecture/format/component/backend/evidence labels | Four output filters are implemented; labels do not establish execution support |
| User-controlled adapters | Peer adapters with explicit compatible base dependencies; A1 / A11 | dev.4 adds LoRA bundles, pairing, strengths and task leases; no phone effect acceptance |
| Future models | Existing architectures may gain separate asset recipes; new architectures need signed foundation updates | Actual text, diffusion and speech code exists, without arbitrary-HF execution claims |
| Same-phone execution and one next release | F-01–F-12 plus 01–14/16/17 share the complete v0.3.0 gate | No external inference scheme; full targets/device acceptance are unfinished, with no new Release |

The [Chinese requirements](MULTIMODAL_RELEASE_PLAN.md), [English requirements](MULTIMODAL_RELEASE_PLAN.en.md), [summary](releases/v0.3.0-plan.md), [structured policy](proposals/multimodal-release-scope.json), [repository instructions](../AGENTS.md) and [release workflow](RELEASING.md) agree. None require end users to download every supported model.

A11 still requires zero-model install/upgrade, no downloads during browsing, explicit selection boundaries, independent asset updates, preservation and shared-object deletion checks. The document baseline is consistent; implementation and device evidence remain open. Catalogue counts, successful downloads and desktop UI demonstrations are not counts of models accepted on a phone.

Dev.6 adds the Nano signed worker and eighth explicit HF recipe. Tokenizers, voice-prompt codes and external `.data` remain user-owned components; temporary execution workspaces use leased hardlinks and do not install/update model data. [Nano details](MOSS_NANO_ENGINE.en.md).

dev.7 [independent updates](MODEL_UPDATES.en.md) add 62 host assertions covering explicit selection, failure preservation, stale consent, atomic activation and rollback. App updates do not trigger these operations, and old API IDs never redirect to new weights. Physical install/upgrade evidence for A11 remains missing.

dev.8 adds [user-selected text bundles](TEXT_ENGINE.en.md) using shared jobs/artifacts, without selecting/migrating old weights or downloading text models on App upgrade. 66 added text-host checks and 147 UI checks do not replace A11 physical install/upgrade evidence.

Dev.9 [existing-model migration](MODEL_MIGRATION.en.md) reuses verified local hardlinks, preserves IDs/sources/profiles and exposes shared tasks/versions from original details. Incomplete transfers stay paused until explicit resume. 69 host migration and 156 UI checks pass; physical-Android A11 upgrade acceptance remains open.
