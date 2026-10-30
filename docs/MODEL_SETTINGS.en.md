# Per-model settings

dev.33 adds named numeric suggestions. Voice names/counts come from the exact local file; users can select a name or edit the ID, with actual/recipe clamping. Tasks/API remain numeric; unknown metadata has a disclosed recipe fallback. See [speech parameter design](SPEECH_SELECTION.en.md).

[中文](MODEL_SETTINGS.md) · [User guide](USER_GUIDE.en.md) · [Documentation](README.md)

## Open and save

Open **Model library → 本地 / Local → the settings icon on a downloaded model**. Context, CPU threads, reasoning mode, output limit, temperature and system prompt are saved independently by model ID. Built-in, HF and device-imported files share this flow. Incomplete downloads cannot configure inference. The application Settings page retains source/token preferences, auto-load, boot restore, service port and theme.

Numeric controls combine a preset menu with editable text. Custom values such as context `1536` or output `333` are accepted. Blur, preset selection and saving validate values: an excessive number becomes the current maximum, an undersized value becomes the minimum, and integer fields round down. Empty/invalid text restores the field's last valid value. Native validation runs again. A matching success acknowledgement completes saving; errors retain the editable draft.

## Limits

| Parameter | Default | Source and behavior |
| --- | --- | --- |
| Context | 2048 | Reads `general.architecture` and its `[architecture].context_length` from this GGUF; range 2 to that declared value. Defaults are also normalized |
| Output limit | 512 | At most **configured context minus one**, reserving at least one input token. Reducing context adjusts output too. Actual prompts, templates and history can leave fewer tokens available |
| CPU threads | Up to 4 | 1 to Android's available-processor count; a device limit |
| Temperature | 0.7 | Application range 0–2; custom decimals accepted |
| Reasoning | off | off / auto / on sent to the engine; some models may ignore it |
| System prompt | Built-in local-assistant prompt | Editable or empty, at most 4000 characters |

For a GGUF declaring context `8192`, entering `100000` resets to `8192`. With configured context `1024`, entering output `9999` resets to `1023`. This does not guarantee 1023 generated tokens.

GGUF generally declares trained context rather than a universal independent maximum-output field. LMA uses the shared context bound and does not mistake an HF `generation_config.max_length` default for a hard limit. See the [official GGUF format](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md).

If metadata cannot be read, the interface explicitly labels an **application fallback of 8192 tokens**, not a confirmed model limit. No RoPE extrapolation is inferred. A declared maximum does not establish phone RAM capacity; reduce context or model size if loading fails.

## Applying changes

- Saving context, threads or reasoning for the running model reloads it. Stop an active in-app reply before changing these load parameters.
- Output limit, temperature and system prompt apply to the next **in-app chat** without restarting the engine.
- Editing another model does not change the running profile. Model switching, crash recovery and boot restoration read the selected model's profile.
- External API clients provide their own messages, temperature and `max_tokens`. The UI's system prompt and output limit are not injected into external requests. Engine context still comes from the loaded profile.

## Persistence, upgrades and implementation

`Store` atomically writes `profiles` and `metadata` to private `models-state.json`. HF identity includes repository, pinned commit and file path: different quantizations/revisions have different profiles, while selecting the same file reuses its ID. Deleting HF/manual entries removes their profiles; deleting built-in weights preserves their settings for redownload.

Upgrade migration copies legacy global inference preferences to existing models once, preserves profiles already present, writes them durably and removes the old keys. Subsequent new HF/imported models receive independent defaults. Same-signature installation retains data; uninstalling deletes it.

`GgufMetadata` reads little-endian GGUF v2/v3 on download completion, parameter opening and engine load. It bounds the header at 64 MiB, metadata keys at 100000, and array sizes without loading tensors/full tokenizers. File size/mtime invalidate the cache and normalize saved values. This is not a complete GGUF validator. `ModelSettings` enforces native bounds; `EngineHost` and `ChatRunner` select values by explicit model ID.

85 backend assertions include binary fixtures, bounds, persistence, migration and actual child-process arguments/HTTP requests. 66 UI checks include editable presets, clamping and model independence. There was no Android-device test. Media uses explicitly simulated metadata; it does not establish actual bounds for the illustrated weights.

[Settings GIF](media/lma-model-settings.gif) · [Load-parameter screenshot](media/06-settings.png) · [Output-limit screenshot](media/11-model-output.png)

In dev.4, LoRA strengths are saved per adapter bundle, separately from base generation settings. Task edits leave saved settings intact; limits must be within the native `-4…4` range and over-limit input clamps. See [adapter pairing](ADAPTERS.en.md).

dev.7 adds bundle [independent updates/rollback](MODEL_UPDATES.en.md): user-reviewed assets/profiles, separate download and activation consent, retained old files/settings and protected queued/running version references. Current preference never redirects API/existing jobs; legacy unification and device acceptance remain required in this same complete version.

dev.8 [text bundles](TEXT_ENGINE.en.md) use the shared editable form. Installed GGUF metadata constrains context/output at save, submission and execution. Effective schemas remain separate from provenance, with explicit unknown/application bounds. Legacy profiles remain; complete migration is still in scope.

Dev.9 [existing-model migration](MODEL_MIGRATION.en.md) reuses verified local hardlinks, preserves IDs/sources/profiles and exposes shared tasks/versions from original details. Incomplete transfers stay paused until explicit resume. 69 host migration and 156 UI checks pass; physical-Android A11 upgrade acceptance remains open.

Dev.12 LCM-LoRA applies a task sampling policy: LCM sampler/scheduler, CFG=1 and a 1–8-step guard appear after selection; deselection restores form values. Saved ordinary base-model settings stay independent. LCM checkpoints and SD-Turbo have their own recipe bounds. Requested/effective values remain reviewable in the task. See [diffusion](DIFFUSION_ENGINE.en.md).


dev.13 [image/video parameters](ADVANCED_DIFFUSION.en.md) remain per model: Qwen 2.1 dimensions align to 32, Wan frames to 4n+1, and flowShift=0 selects the engine default. Distilled jobs freeze CFG/sampling and record task adjustments without overwriting ordinary base settings.


The SoulX development recipe adds independent context/output/history bounds, RAS/Flow/pause/duration controls; see [profile details](SOULX_ENGINE.en.md#4-parameters-and-execution). Numerical overflow clamps; temperature0 forces effective RAS off with an adjustment record. Reference transcripts are frozen task inputs, not global/model defaults.
