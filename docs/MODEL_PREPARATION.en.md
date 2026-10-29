# User-selected local runtime asset preparation

Dev.28 extends this shared foundation to [fixed-condition LCM](LCM_APP_FLOW.en.md): per-stage output budgets stay separate from disk reserves; association and missing dependency transfers remain explicit. The original dev.22 old-LTX flow below retains its own scope.

[中文](MODEL_PREPARATION.md) · [Documentation](README.md) · [Numbered delivery](releases/v0.3.0-dev.22.md)

**dev.22 / code 26 is an internal development checkpoint; complete v0.3.0 remains unpublished.** Existing native preparers now use the App's shared job foundation. Full trained-file preparation passed on Windows. Android installation, SAF, converter execution and background endurance remain untested; no video-generation engine is registered.

## User workflow

1. In Models → All, select the source candidate **LTX-Video 2B 0.9.8 distilled** and review its pinned identity, license and size. Its video tag describes the target task, without asserting generation support.
2. Explicitly download the source, or import the original `ltxv-2b-0.9.8-distilled.safetensors` using the folder/SAF flow. Existing transfer controls preserve failed work and require explicit resume. Installation, upgrades, browsing and missing-asset checks never initiate model downloads.
3. Once the complete source is installed, open its runtime-assets details under Local. Installation itself does not trigger conversion.
4. Review and confirm **6,195,402,719 additional free bytes**: **6,061,184,991 bytes** across 20 runtime files plus 128 MiB reserve. The retained source separately occupies **6,340,744,492 bytes**. Source, outputs and reserve total about **12.54 GB**, before T5, other models or system storage.
5. Explicitly start preparation and manage it in Tasks. It shares the execution slot with text and generation jobs, parks resident text before running, and supports cancellation and explicit retry. Memory, thermal, storage and identity failures are reported locally.
6. Manage derived files separately in model details. Deleting them preserves source weights and settings. Deleting source weights still leaves their derived files visible and manageable under Local.

This candidate supplies only the original checkpoint. dev.23 adds explicit [runtime association](MODEL_ASSEMBLY.en.md) followed by user-selected T5 download/import; the production video adapter remains open. Successful preparation neither enables a missing generator nor downloads additional dependencies. An unrelated checkpoint cannot use this exact conversion contract.

## Foundation structure

| Layer | Implementation and boundary |
| --- | --- |
| Signed plan | App-delivered `asset-preparations.json` pins the source role/size/SHA256, ordered stages, preparers and output identities; clients cannot supply programs, paths or scripts |
| Program registry | `engine-builds.json.preparations` is separate from generation engines; both ARM64/API28/16KiB programs have verified sizes and hashes |
| Data separation | Nine audited model-free ONNX architecture graphs total 402,231 bytes inside APK; all 138 learned parameter inputs remain external user data, including timestep multiplier and channel statistics |
| Immutable request | `model.prepare` binds the selected bundle, plan ID and fingerprint; the server adds source-bundle identity rather than following subsequent UI selection |
| Lifecycle | Reuses `LocalJobs`, `JobStore`, `ExecutionGate` and foreground ownership; source leases, work directories and the slot remain held until process reaping |
| Child ownership | Registered binaries and private paths, bounded messages and receipts; Android parent death terminates the preparer to prevent orphan writes |
| Derived storage | Private `PreparedAssets` directories, exclusive ownership lock, atomic index, read leases and full revalidation on acquisition; recovery removes only owned unfinished work |
| Evidence | Returns a preparation receipt rather than fabricated media; conversion does not establish inference, quality or device acceptance |

The first plan, `ltx098_dit_vae_v1`, requires source SHA256 `76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f`. Stage one writes DiT GGUF. Stage two writes nine graphs, nine parameter files and a manifest. Further architectures require explicit trusted preparers/contracts while sharing model lists, jobs and storage.

The candidate reuses a developer-explicitly acquired checkpoint, its pinned publisher revision and independently measured full-file identity. This update does not claim a fresh official-HF download verification. User downloads and imports must still pass the complete SHA check.

## API

`GET /v1/models` includes installed sources and derived-only local records with `preparation_plans` / `prepared_assets`. `installed` retains its source-component meaning; derived files do not make it true. Preparers are separate from generation engines.

Read the current plan fingerprint, then explicitly submit `POST /v1/jobs`:

```json
{
  "type": "model.prepare",
  "bundleId": "ltx098_source_r8984fa2",
  "preparationId": "ltx098_dit_vae_v1",
  "planFingerprint": "45c36668b83f7ce989720fc4144992cf3d99ab9b3e989ba34345c856a0922131"
}
```

Existing authentication, idempotency, querying, events, cancellation and retry apply. Client filesystem paths, URLs, module names and generation parameters are rejected. After a plan change, review and explicitly select the new fingerprint. Independent prepared-file deletion is currently available in the App; there is no new arbitrary file-deletion API.

## Verification and reproduction

`python tools/test_preparations.py` exercises 44 contracts, including strict requests, corruption, invalid receipts, cancellation, leases, recovery and four actual protocol-fixture children. Those are not model tests. `python tools/test_preparations.py --trained` runs the production Java core with the existing complete checkpoint and two real native host converters. All 20 outputs match the signed plan and the source is retained. This took approximately 1,126 seconds; Java/Android peak memory was not measured. A converter-only host memory figure cannot establish phone requirements.

Separate native checks cover independent output bytes, rejection cases and four actual trained VAE decodes. **Six required full prompt-to-video float gates remain failed.** Passing conversion does not close them. See [DiT preparation](LTX098_PREPARE.en.md), [VAE preparation](LTX098_VAE_PREPARE.en.md) and [full pipeline](LTX098_PIPELINE.en.md).

| Evidence | Scope |
| --- | --- |
| Production host core | One complete trained-file preparation, two native children and 20 verified outputs |
| APK | dev.22, original signing identity and 29 native files; no weights, vocabulary or learned parameters |
| UI | Screenshots 62–65, recording and GIF use shipped pages with an explicit bridge fixture; no model/Android execution |
| Android / complete Release | Unverified; all frozen targets and A1–A11 / R01–R05 remain required within the same v0.3.0 |

![Preparation storage confirmation, UI FIXTURE](media/development/63-preparation-confirm.png)

[Queue screenshot](media/development/64-preparation-queue.png) · [Independent management](media/development/65-preparation-management.png) · [Recording](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif) · [Public trained-preparation evidence](../verification/development/preparation-trained.json)
