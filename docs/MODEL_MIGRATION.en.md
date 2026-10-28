# Existing text models and shared asset migration

[中文](MODEL_MIGRATION.md) · [Text jobs](TEXT_ENGINE.en.md) · [Model versions](MODEL_UPDATES.en.md) · [Full requirements](MULTIMODAL_RELEASE_PLAN.en.md)

Applies to **0.3.0-dev.10 / code 14, an internal checkpoint, not the complete published v0.3.0**. Existing complete text GGUF files can join shared bundles, settings, jobs and version management without downloading again. Migration itself never selects, loads, updates or replaces a model and does not contact a model download service.

## User flow

1. Upgrade while retaining app data. The app checks complete existing files in a background thread. A loading/running legacy model waits until its process exits before another check.
2. Keep using Recommended / All / Local. Recommended stays `m08 → m06 → m01`; original IDs, sources and checked content labels remain. Migration does not add a duplicate model card.
3. Migrated details offer shared task creation and model version management using existing assets. After explicit unmeasured-recipe consent and submission, shared jobs wait for active replies and switch engines, restoring a text model the user still wants when idle. See [scheduling](SCHEDULING.en.md).
4. Legacy and bundle settings access the same per-model defaults. Output defaults apply to subsequent requests; load-parameter changes reload the process and are rejected during an active reply. GGUF, recipe, device and application limits apply together.
5. Incomplete `.part` files remain paused after restart/upgrade. Network transfer resumes only after explicit user action. Device imports retain their origin and gain no fabricated download URL.
6. Users update/delete models independently. Queued jobs, live processes and other installed references protect required assets. App upgrades do not require weight updates.

The app remains usable for browsing without any model. Failed migration preserves manageable original files/records and never triggers redownloads or off-device inference. Physical Android upgrade acceptance has not been performed.

## Data and interruption handling

The legacy `models-state.json` retains catalogue/custom/HF records and profiles, with a new `bindings` map from original IDs to immutable bundle IDs. Each bundle ID binds the original ID and content SHA256. Choosing a preferred model version does not redirect existing API IDs or jobs.

The shared `BundleStore.adoptLocal` primitive accepts complete existing files, validates their pinned identity, stages private hardlinks and verifies actual bytes before publishing CAS objects and installed metadata. It does not rewrite weights or create network transfers. Identical components can share storage. Filesystems that reject hardlinks leave the original files intact with an error.

After CAS publication, migration rechecks files and running state under the request gate, incorporates settings edited during verification, and atomically commits the binding/profile/metadata. Only then can the old private filename be removed. Interrupted commits retain recoverable source files or harmless unreferenced objects. Startup cleans only adoption `.adopt-UUID` links, preserving ordinary resumable `.part` files.

HF selections retain fixed repository/revision/path and publisher digests. An unpinned legacy HF URL does not become a fabricated reproducible source. Custom files without a digest receive a measured SHA256 without being promoted to checked publisher or device evidence. Uncensored / Abliterated declarations are never inherited from a different model.

Persistent text processes hold the shared asset lease until actual exit. A trusted engine owner may edit future defaults; frozen job requests and immutable file manifests remain fixed. Ordinary settings/deletion continue to respect active and queued references.

## API and evidence boundaries

`GET /v1/models` preserves the original text ID and exposes `bundle_id` for asynchronous `text.generate` jobs, without an additional duplicate bundle row. Synchronous chat/completion APIs use the selected text model and can wait for the shared slot; physical-device scheduling acceptance remains open. Job clients explicitly use the returned immutable bundle ID.

This checkpoint adds **69 host checks** covering real files/hardlinks, GGUF metadata, HF/import origins, concurrent profile changes, cancellation/interruption recovery, shared deletion, API IDs and an actual protocol child process with asset leases. UI checks total **156**. Fixtures contain zero tensors and literal protocol content; no model inference occurred. See the [migration receipt](../verification/development/migration.json), [status](DEVELOPMENT.en.md) and [notes](releases/v0.3.0-dev.9.md).

Screenshots 25–26, recording and GIF retain UI FIXTURE labels, without claiming phone migration or generated output. Physical-device installs/upgrades, persistence/timing, every selected model, automatic scheduling, resources and background acceptance remain in the same complete v0.3.0. No new Release is published.
