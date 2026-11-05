# Delete directly from model cards · v1.0.2

[中文](MODEL_DELETE.md) · [User guide](USER_GUIDE.en.md) · [Release notes](releases/v1.0.2.md)

## Operation

1. Open **Models → Local**. Optionally filter by text, image, video, audio or 3D.
2. Select the labelled **trash icon + 删除 (Delete)** at the bottom of the model card. Text GGUF, media bundles and LoRAs expose this outer action without opening details.
3. Review the model name in the confirmation dialog. **确认删除** submits deletion; **取消** or Back cancels without submitting it.
4. During queued, active, verifying or pausing transfers, the visible button reads **暂停后删除 (Pause before deleting)** and remains disabled. Pause and wait for the transfer to stop. The native service independently checks concurrent transfers.

Unselected, undownloaded catalogue candidates do not show a local-file deletion button. Paused/failed or other saved transfer records use the existing deletion flow. The existing detail-dialog action remains available.

## Scope and protection

Text models keep `deleteModel`; bundles keep `bundleRemove → confirmation → deleteBundle`. This patch changes discoverability, retaining storage semantics, confirmation and native protections for running models, active tasks, shared components and leases. A rejected action exposes the actual reason so users can stop the conflicting operation and retry. Bundle deletion preserves its per-model settings by default. Downloads remain explicit user actions.

Phone checks open and cancel confirmation, comparing installed assets and preferences before/after upgrading. Confirmed deletion runs only against program fixtures. Neither check establishes trained-model quality, full inference or sustained background endurance.

| ID | Implementation and verification scope |
| --- | --- |
| D01 | Labelled outer-card deletion for all five output types |
| D02 | Correct target IDs, confirmation/cancel and fixture-only selected-bundle deletion |
| D03 | Visible busy-transfer explanation, paused recovery and native concurrency protection |
| D04 | 320px layout, both UI10 themes, phone cancel/preservation and font checks |
| D05 | Original-signed upgrade, bilingual documentation and versioned phone screenshots/MP4/GIF |

See [current evidence](../verification/releases/v1.0.2/status.json) and [physical UI](../verification/releases/v1.0.2/mica-physical-ui.json). Historical projector/codec, video/3D quality, full-model, physical hinge and endurance limits remain separate. F01–F08 chat-integration proposals are not expanded by this patch.
