# Foundation updates and user-controlled model assets: audit

[中文](ASSET_CONTROL_AUDIT.md) · [Full requirements](MULTIMODAL_RELEASE_PLAN.en.md) · [Release summary](releases/v0.3.0-plan.md) · [Actual progress](DEVELOPMENT.en.md)

Reviewed 2026-10-28. **Current requirements match foundation-only App updates with user-selected/downloaded/managed model assets.** Document compliance does not establish completed implementation or Android acceptance.

The requirements restated:

1. **The App is the shared foundation.** Updates deliver UI, engines, jobs, background services, APIs and recipe/catalogue metadata, without weights, model-specific vocabularies or voice data in the APK.
2. **Users install models on demand.** They choose a model/quantization/recipe, review its complete dependencies and explicitly download or import it. Installation, upgrades, browsing and tasks with missing assets do not fetch models implicitly; installing every supported model is never required.
3. **Users manage assets independently.** Local offers pause/resume, per-model settings, updates and deletion. App upgrades preserve existing assets/profiles without silently replacing weights; deleting a model retains the foundation and protects shared components.
4. **Models are peers with independent tags.** Text/image/video/audio output tags can be combined. Engine/pipeline/format/component/backend requirements, installation and device evidence remain separate. Uncensored is an independent content label, not compatibility evidence.
5. **Preserve discovery and same-phone execution.** Keep existing Recommended entries, order and labels; choose other HF models through All/search. Coverage describes foundation adaptations, not arbitrary-HF execution. All generation executes on the same Android phone.

| Requirement | Document rule | Implementation / evidence |
| --- | --- | --- |
| APK updates deliver the foundation | Asset-separation section, F-02 / A11 | Package checks exclude weights, model-specific vocabularies and voices; engine code belongs in the App |
| Users select models and dependencies | Explicit selected bundle plus previously disclosed required components; no mandatory installation of all supported targets | Bundle details, explicit transfers and folder import exist; twenty-three explicit HF component templates do not download on registration; other architectures still need adaptations |
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

Dev.10 [shared execution](SCHEDULING.en.md) unifies resident text, chat/API and jobs under the same process/cancellation boundary. 43 host assertions cover user-asset reuse, switching and retained stop intent, without model downloads or complete model/device acceptance.

Dev.11 [input media](LOCAL_INPUTS.en.md) is explicitly imported/uploaded independently of model assets. These actions never download, load or replace a model. Production recipes remain prompt-only. 64 input, 49 scheduler and 182 UI assertions do not replace physical A11 acceptance.

Dev.12 [diffusion](DIFFUSION_ENGINE.en.md) updates signed runtime code, recipes and policy only. SDXL encoders/VAE, Turbo/LCM weights and LoRA remain explicit user choices. Sixteen templates initiate no download; LCM task parameters preserve saved base settings. 83 diffusion-host and 194 UI checks do not replace A11 device acceptance.


dev.13 [Z-Image/FLUX/Qwen/Wan bindings](ADVANCED_DIFFUSION.en.md) add four user-selected component recipes, strict roles, actual sampler/scheduler/flowShift bindings and Qwen/Wan geometry constraints. Diffusion 174 (Java 117/C++ 57), foundation 425 (recipe/integrity 233) and UI 203 assertions pass; 35 screenshots plus recording/GIF are explicit UI FIXTUREs. Family checks do not prove scale or distillation; no model/Android outputs exist. The App updates only the foundation; twenty templates never download implicitly. Every target/device gate remains in the same complete v0.3.0, without a new Release.

dev.14 adds the [Sana mobile / MNN pipeline](MNN_SANA_ENGINE.en.md): a real ARM64 CPU worker, 13 user-selected components, whitelisted Qwen3 metadata, encoder release before diffusion, per-model CFG/token/thread controls and immutable job plans. Its 74 host/C++ checks perform no model inference. All 21 templates remain metadata with separately confirmed downloads. Foundation 445 and UI 208 checks pass; 37 screenshots and recording/GIF are explicit UI FIXTUREs. No Android image/endurance evidence exists. Every frozen target and release gate remains in the same complete v0.3.0, without a new Release.

Earlier internal checkpoint (**0.3.0-dev.15 / code 19**, unpublished): [Qwen3-TTS 0.6B Base](QWEN_TTS_ENGINE.en.md) adds a real ARM64 CPU worker, a complete two-GGUF local speech pipeline, optional reference WAV, independent sampling settings and actual timing/RTF recording. Shared `provides` discloses embedded tokenizer/predictor/speaker dependencies without duplicate downloads. Its 81 Java/C++ host checks exercise protocols and structural WAV only; pinned optional assets have header review, without model inference. All 22 templates remain metadata and never implicitly download models. Screenshots 38–39 and development recording/GIF remain UI FIXTUREs. App updates deliver the foundation; every full v0.3.0 target, real-output/quality/background gate remains, with no new Release. See [bilingual notes](releases/v0.3.0-dev.15.md).

Internal checkpoint (**0.3.0-dev.16 / code 20**, unpublished): the [MOSS Delay native CPU pipeline](MOSS_DELAY_ENGINE.en.md) adds a user-selected first-class backbone/decoder, optional reference encoder, independent text/audio sampling and shared jobs. Its 176 Java/C++ host checks include the pinned upstream Delay self-test; structural WAVs are not generated speech. All 23 recipes are metadata; APKs carry no model assets or implicit downloads. Screenshots 40–41 and recording/GIF remain UI FIXTUREs. Every complete v0.3.0 target and physical-device gate remains, without a new Release. See [bilingual notes](releases/v0.3.0-dev.16.md).
