## P02 / D05 — independent specification-side refutation

**Disposition:** retain the checker's **absent** verdict for the complete UniForge3D production path. No specification-side refutation overturns that result. Narrow the interpretation of preprocessing, exact backend parity and implementation-plan choices as described below; they are not additional standalone P02 requirements.

Reviewed report: `research/portability/spec-compliance/D05.md`, SHA-256 `7b881e04ed72934270dd510986a923c2ebaa6e411e17661ea88c8d4028c44cd2`, 33,999 bytes at the reviewed snapshot, 2026-10-31. This pass was performed by the D08/D09 checker, who did not author the D05 finding. It is a specification-side refutation, not the separate independent code-side refutation or a full release audit. Production source was read, not changed.

`U/` below means the fixed source `build/spatial-source-review/repos/D05/`, revision `xibushu/UniForge3D@8b6094780e202b8a6b1d239e0997552e18547026`. Fixed local pipeline/model sources were reread directly; the report's remote dependency/API observations were not accepted as newly independently verified evidence by this pass.

---

**Requirement reread verbatim:**

> "联合 VGGT / DiT、DINOv3、多视图 anchor 与联合特征、稀疏结构 / SLAT 采样、FDG / 材质解码及 GLB"
> — `docs/REMAINING_ADAPTATION.md:L41`, P02
>
> "卷积、池化 / 细分、packed attention；不以 TRELLIS 或普通四图替代联合网络"
> — the same row's existing-but-insufficient foundation column

The header calls these “仍必须实施的模型流程” (`docs/REMAINING_ADAPTATION.md:L36`), and `L46` says the model paths are genuine unfinished development requirements. They are a required next-development scope, not a claim that the published v0.3.5 APK already includes them (`L5`). The checker correctly reports an implementation gap; it must not be reframed as an undisclosed defect in an earlier published binary.

Relevant product constraints remain part of the interpretation: user-selected assets (`L11`), all runtime stages on the same phone (`L15`), equal model status (`L12`), per-model parameters (`L14`), program-only checks without complete trained-model or phone runs (`L18`, `L54`). Neither physical-phone testing nor downloading a complete model is necessary to establish this source-code gap.

---

**Refutation attempts and results:**

| # | Attempt to overturn or narrow the finding | Direct evidence reread | Result |
| --- | --- | --- | --- |
| R01 | The row might be only an optional research roadmap, making `absent` irrelevant. | Section title `docs/REMAINING_ADAPTATION.md:L36`; P02 `L41`; explicit missing-code statement `L46`; published-version boundary `L5`. | Rejected as a refutation: this is explicitly required development. Retain absent, scoped to development completion rather than published-version guarantees. |
| R02 | “联合 VGGT / DiT” might permit a one-time VGGT embedding plus an unrelated shape generator. | `U/uniforge3d/models/joint_dit_vggt_stage1.py:L232-L255` selects the anchor DINO input and enters `forward_joint_with_fusion`; `L326-L372` alternates VGGT processing, learned fused DiT conditions and a writeback from completed DiT state to the VGGT stream. `U/uniforge3d/pipelines/sparse_structure.py:L45-L54` calls this conditional predictor at sampling evaluations, with a separate DiT-only negative branch. | Rejected: the cited publisher model contains actual bidirectional learned coupling. A cached one-way encoder or existing TRELLIS/four-view family does not implement the named joint network. Exact layer counts are model-profile facts, not newly authored product features. |
| R03 | The checker invented the shape512 → mesh → shape1024 → texture cascade because P02 does not literally enumerate those numbers. | Publisher production `U/uniforge3d/pipelines/uniforge3d_image_to_3d.py:L360-L380` unconditionally calls structure, shape512, actual mesh-to-coordinates handoff, shape1024, texture, then GLB export. `_generate_shape512` decodes its latent (`L244-L258`); `_shape512_to_coords64` consumes that decoded/postprocessed mesh, not initial structure coordinates (`L285-L293`). | Rejected for the cited complete publisher route. The dependency order is source-grounded interpretation of the named model, not an extra hypothetical architecture. A disclosed alternate source profile could be assessed separately; relabelling a smaller unrelated route is insufficient. |
| R04 | Material/texture and shared decoder guides are optional embellishments beyond “FDG / 材质解码及 GLB”. | P02 explicitly names material decoding. `U/uniforge3d/pipelines/texture.py:L108-L109` passes shape subdivisions into the texture decoder; `L123-L140` exports base color, metallic, roughness and alpha material channels through the GLB path. `U/uniforge3d/models/vaes/flexi_dual_grid.py:L52-L66` interprets seven decoder channels before actual FDG extraction. | Rejected: FDG and source material decode/output are core to this requested route. The shader/GLB implementation may be adapted to CPU, but a bare SDF mesh without these neural/material stages cannot count as complete P02. |
| R05 | Automatic background removal must block all P02 completion even when users supply correct masked RGBA inputs. | Checker `D05.md:L41`, `L62`; source `U/uniforge3d/utils/preprocessing.py:L118-L125` calls the remover only for non-RGBA or entirely opaque alpha. Nonopaque RGBA bypasses it. `docs/REMAINING_ADAPTATION.md:L52` separately identifies automatic masking outside disclosed subsets. | **Narrowed.** The remover is a conditional dependency for the cited opaque-input path, not a universal unconditional dependency for every P02 task. An explicitly constrained RGBA-input profile can exercise the actual D05 core without it; that limitation must stay visible and cannot be called full original input coverage. Removing this ancillary demand does not supply the missing joint/SLAT/FDG/material path or overturn absent. |
| R06 | P02 might require bit-identical CUDA results, fixed CuMesh internals, default sampling counts, or one specific export architecture, so the checker is testing a stronger requirement. | P02 `docs/REMAINING_ADAPTATION.md:L41` does not specify bit identity or hardcode default runtime settings. Per-model editable settings are required at `L14`; CPU differences are explicitly disclosed at `L34`; program-only validation is at `L18`, `L54`. The checker itself describes FP32 CPU adaptation and does not claim full-output parity (`D05.md:L117`, `L128`, `L136`). | **Narrowed interpretation.** Preserving actual learned stages, conditioning, material meaning and geometric handoff is required to support this named route. Exact CUDA scheduling, original RNG implementation, identical simplification numerics and literal default step counts are not independent normative requirements. Reasoned CPU replacements and truthful declared limits can be acceptable. This does not permit deleting the mesh-dependent handoff or replacing FDG with an unrelated extractor while claiming exact source behavior. |
| R07 | D05 only appears absent because the report assumes the foundation cannot carry int64 coordinates or multiple graph outputs. | Current `native/spatial/typed_graph.hpp:L9-L11` creates int64 tensors; `L25-L31` validates explicit input/output signatures; `L39-L45` loads typed multi-output graphs; `L48-L50` runs and validates multiple outputs. The checker already acknowledges these at `D05.md:L30`, `L103`. | Rejected: typed graph infrastructure exists and must be reused. No global typed-loader absence is a valid reason for this finding. The remaining gap is the D05-specific graphs and their actual ordered runner/validator integration. |
| R08 | Missing or gated external weights/configuration prove development impossible and justify treating the requirement as undecidable rather than absent. | Checker `D05.md:L143-L146` explicitly marks concrete decoder JSON inspection and trained-asset accessibility unverified after HTTP timeouts; it does not claim a gating response. Available publisher source includes the concrete pipeline/topology just reread. Program-only development does not require complete trained weights (`docs/REMAINING_ADAPTATION.md:L18`, `L54`). | Rejected: source-code implementation remains directly checkable and can proceed with fixed-class construction and random programs. Actual published-profile metadata is an open compatibility item, not evidence of source implementation, global impossibility, or a reason to erase the gap. |
| R09 | Source locks, proposed graph filenames, unmerged-LoRA-first development, B=1/FP32 choices and every proposed fixture are all additional mandatory product requirements. | These occur under “Minimal concrete same-phone export/runtime plan” (`D05.md:L52-L58`, `L86-L103`, `L130-L134`), explicitly labelled a proposal. P02 names the model behavior rather than these internal construction choices. Source topology also allows conditioned modules to be built into different equivalent export boundaries. | **Narrowed.** Treat those entries as one actionable remediation design and evidence plan. Equivalent implementations can satisfy P02. Retain strict identity/compatibility checks as engineering controls, without asserting that every proposed file boundary or development sequence is itself a quoted requirement. |

---

**Mandatory scope versus grounded source interpretation:**

| Category | What belongs here | What it does not establish |
| --- | --- | --- |
| Explicit P02 requirements | Joint VGGT/DiT, DINOv3, actual multiview anchor/joint features, sparse structure/SLAT sampling, FDG, material decoding, GLB; no substitution by a different TRELLIS or four-view model. | P02 alone does not dictate graph filenames, host conversion layout, CPU thread counts or bit-identical backend numerics. |
| Source-grounded necessary dependencies of the reviewed full profile | Bidirectional joint evaluations, routed learned conditioning, distinct shape512/shape1024/texture state, actual decoded shape mesh as the later coordinate source, shared guide subdivisions, source material channels. | Their existence in the fixed publisher path does not require support for every possible future architecture or every training-time branch. |
| Conditional/source-profile coverage | Opaque-image background removal, view-count/capacity range, exact selected resolution/profile, postprocessing choices. | A scoped input/capacity limitation cannot be silently hidden; a conditionally unused module does not by itself prove that every supported task is absent. |
| Implementation/evidence proposals | Source lock expansion, safe local state loading, typed graph boundaries, FP32 CPU export, selected fixture inventory. | These are not extra product requirements simply because the checker proposes them. Other faithful, reviewable solutions remain possible. |
| Explicitly unverified | Actual trained-model quality, phone RAM/heat/throughput/background longevity, unresolved external decoder JSON contents and component download permissions. | They cannot be reported as passed or failed by this source review, or used to demand excluded complete-model/phone validation. |

---

**Why the absent verdict survives the narrowed scope:**

Even after excluding automatic masking, bit identity and every optional export-design choice, there is no reachable D05 joint/SLAT/FDG/material runner. Current Java `SpatialSpec.ultra` accepts only the Hunyuan and UltraShape shape families after the explicit UltraTex/Paint cases (`app/src/main/java/com/lma/app/core/SpatialSpec.java:L13-L25`). The native worker's corresponding fallback explicitly rejects unknown spatial architectures (`native/spatial/worker.cpp:L14-L16`); its source identity checks also cover only those two shape profiles (`L23-L24`). These boundaries do not become a UniForge adapter because `TypedGraph` exists. This independently reread dispatch evidence supports the narrow decisive claim already made in `D05.md:L5`.

Supplemental searches were rerun with `foundation.js`, `license.js` and `*.header.json` excluded:

| Search | Result at refutation snapshot |
| --- | --- |
| `rg -n 'UniForge\|uniforge\|D05\|VGGT' native app/src/main/java tools catalogue` | **15 matching lines**: audit/scope/catalogue records, shared sparse comment, sparse tests; **0 Java D05 implementations**, no native joint/SLAT/FDG model route. The decisive Java/native validators were then read directly. |
| `rg -n 'UniForge\|uniforge\|D05\|VGGT' tools -g '*export*.py'` | **0 matches**, exit 1. This supports, but does not alone establish, absence; dispatch/source-path review above supplies the actual evidence. |
| Source-specific reads | Main publisher run/handoff/texture, joint positive and negative paths, conditioning, occupancy coordinate generation, RGBA bypass and FDG interpretation were reread with line numbers. No complete model was imported or executed. |

No browser UI, trained-model download/inference, emulator, phone, Docker, WSL, VM, token access, publishing or production edits were used. The only file authored by this refutation pass is this report.

**Parent action:** retain the implementation gap with the core P02 wording; carry R05/R06/R09 as scope clarifications. Do not add a missing-global-loader finding, treat network timeout as gating, or require full-model/device testing. An independent code-side refutation is a separate workflow item and is not supplied by this specification-side pass.

| # | Completed item | Pending item |
| --- | --- | --- |
| 1 | Re-read exact requirement, product constraints and relevant fixed publisher topology | None for this specification-side review |
| 2 | Attempted nine refutations, retained core absent result and narrowed three ancillary interpretations | Parent aggregation should apply the clarifications |
| 3 | Confirmed existing typed/multi-output loader is usable infrastructure | Actual D05 exporter and production integration remain development work |
| 4 | Recorded precise sources and search results in this report | Independent code-side refutation remains outside this pass |
