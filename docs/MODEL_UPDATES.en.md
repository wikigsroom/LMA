# Independent model updates and rollback

[中文](MODEL_UPDATES.md) · [HF component recipes](HF_RECIPES.en.md) · [Development status](DEVELOPMENT.en.md) · [Asset-control audit](ASSET_CONTROL_AUDIT.en.md)

Applies to **0.3.0-dev.9 / code 13, an internal checkpoint, not the complete v0.3.0 Release**. App updates supply the foundation; users separately manage model versions. This workflow covers generic `ModelBundle` records. Unifying legacy standalone GGUF records with bundles remains required within this same version; this does not establish complete update support for every model.

## Workflow

1. Use All/search and HF file recipes to select and register the new version's pinned components, or import a bundle manifest with a new ID. Registration, browsing and review transfer no assets, and do not automatically discover or accept new versions.
2. Open the existing model in Local and choose **版本管理 / 独立更新**. Select the target and settings policy. Candidates preserve engine, architecture, pipeline, backend, output tasks and LoRA base constraints. Other models can still be added as independent peers.
3. Review added/removed/changed components, provenance-only changes, pinned repository revisions, paths, formats, sizes and expected digests. The review also shows full size, verified reuse, remaining transfer, available storage, licensing and capability changes. Users specify the relationship; it is not a verified publisher release lineage.
4. Explicitly confirm the target download or folder import. Only the selected bundle and disclosed components are processed. Old files remain during transfer. Insufficient storage fails locally without automatically deleting old versions or invoking off-device inference. Pause/resume reuse the shared component transfer manager; restart/App upgrade does not resume downloads implicitly.
5. Successful verification/installation still leaves the old version current. Review again and confirm activation separately. Activation starts no inference and changes no existing task. Old assets and profiles remain until users explicitly clean them up.
6. To roll back, select a retained version, normally with the policy that keeps the target's existing settings/defaults, then confirm. Deleted assets require explicit download/import and verification; they are not fetched automatically. History retains the latest 64 switches.

Versions remain flat peers that can be inspected and used independently. “Current version” is a persistent user preference, not an alias redirecting a fixed ID to different weights. Library/settings remain usable with zero installed models.

## Settings and consent

Copying the current profile migrates compatible fields and clamps numeric values to the target schema. Removed fields are excluded and new fields use target defaults. Type changes, invalid enum options and text exceeding new limits disclose their reset reasons. Incompatible compiled shapes reset only the joint dimensions to a valid default combination; other parameters continue through target validation.

Keeping the target profile/defaults preserves an already customized target or a rollback profile. Both policies preview their effective values; the source profile remains intact. Bounds come from recipe schemas. Unknown device/model limits still require engine and device admission; migration is not proof of verified hardware/model maxima.

The native confirmation fingerprint binds both immutable manifests, effective profiles, version-group generation and policy. Subsequent settings/current-version changes invalidate earlier consent. Cancel an existing stale plan and review again. Transfer progress does not invalidate consent; successful download never substitutes for activation consent.

## Failures, jobs and storage

- Integrity/download failure, pause or interruption leaves the current version/profile untouched. Cancelling a plan pauses its active target transfer and retains acquired assets for explicit cleanup; unrelated transfers are unaffected.
- Installation, activation and deletion are separate operations. One AtomicFile metadata commit changes preference, target settings and history. Activation does not rename/move weights or delete old files.
- A running lease on either version prevents profile replacement during activation. Queued/running jobs protect their base and LoRA assets from deletion. Submission and protected deletion share the store monitor to prevent a check/use race.
- Submitted jobs retain their original bundle/adapter IDs, parameter snapshots and integrity receipts. `/v1/models` lists installed fixed versions with `version` metadata; old API IDs never redirect silently.
- Existing `lma.bundle-store/1` metadata gains an optional `versions` index without rewriting manifests, object paths or profiles. Shared-reference protection retains files needed by another installed version.
- Target provenance, license, capabilities and content tags come from its manifest; old device-verification/checked-uncensored status is not inherited. Update declarations do not verify runtime compatibility.

## Evidence and delivery limits

62 new Java host assertions use real files, arbitrary bytes, the production transfer manager and write failures to cover explicit asset control, integrity failure, restart, stale consent, leases, queued references, atomic activation, sharing and rollback. They are part of 310 foundation checks. The 147 UI checks include the version flow through an explicitly simulated bridge, not model output or Android upgrade acceptance.

[Version choice](media/development/17-model-version-choice.png) · [Component differences](media/development/18-model-version-components.png) · [Settings migration](media/development/19-model-version-settings.png) · [Waiting for activation](media/development/20-model-version-ready.png) · [History](media/development/21-model-version-history.png) · [Recording](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif). Every frame is labeled UI FIXTURE, not phone execution or model output.

Complete legacy migration, actual integration of all selected targets, and physical Android A5–A8/A11 acceptance remain unfinished under the same [complete v0.3.0 gates](MULTIMODAL_RELEASE_PLAN.en.md). No new Release has been created.

dev.8 text-bundle reviews also bind effective parameter schemas. First discovering GGUF limits after download invalidates earlier consent; cancel/review again while retaining assets rather than silently activating. 66 text-host checks cover this path; complete legacy migration remains open. See [text bundles](TEXT_ENGINE.en.md).

Dev.9 adopts existing complete text/HF/import GGUFs into the same assets/settings/jobs/version protocol without downloading again. Its 69 host checks do not establish Android upgrade acceptance. See [migration](MODEL_MIGRATION.en.md).
