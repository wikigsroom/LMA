# D08 / D09 — independent specification-side refutation

Date: 2026-10-31. Reviewer: the D10 checker, independently of the D08/D09 report author. Reviewed report: `research/portability/spec-compliance/D08-D09.md`, SHA-256 `a6890fc138f583dfbb07214cf298fd6359b64906d0ce5611e41b3bd12f389a83` at this pass. This record challenges the report's interpretation of the specification; it does not replace independent code-side refutation or implementation tests.

**Outcome: no specification-side refutation of the report's mandatory-stage or incomplete-adaptation finding.** The report correctly distinguishes absent model-specific adapters from existing shared operators, and does not reinstate the user's cancelled full-model/device acceptance gate.

## Authoritative text and precedence

`docs/REMAINING_ADAPTATION.md:L42-L43` requires:

> P03 / D08: mask、MoGe 点图、MoT 结构与布局 / pose、SLAT 与 FlexiCubes、选定输出的几何 / 外观及 GLB
>
> P04 / D09: D08 基础、Depth Anything 3、多相机对齐、权重融合与 MultiDiffusion、首步预热 / 回退重放
>
> 既有四图方案不能代替该模型；不以单图重复执行冒充多视图

These clauses are governed by A01 user-selected assets, A05 all stages on the same phone, A06 preservation of scope, A07 the lightweight task workbench, and A08 program-only validation (`docs/REMAINING_ADAPTATION.md:L11-L18`). The document expressly says waived complete-model validation does not waive missing code, and missing adapters cannot be declared complete from compilation/old tests alone (`L46`).

The updated validation policy independently states that full trained-model downloads/copy/inference, phone inference and long endurance checks are no longer prerequisites, while missing implementation and the frozen scope remain (`docs/PROGRAM_VALIDATION.md:L5`; `docs/MULTIMODAL_RELEASE_PLAN.md:L6`). The original plan's old model/device gates are historical where they conflict with that later instruction. App updates supply the foundation rather than model weights, and all generation stays on one Android phone (`MULTIMODAL_RELEASE_PLAN.md:L19,L28`).

## Attempts to refute the report

| # | Alternate interpretation challenged | Result |
|---|---|---|
| S01 | P03/P04 are optional research notes; listing them need not imply implementation work. | Rejected. The section is explicitly “仍必须实施的模型流程” and includes all five P01–P05 required flows (`REMAINING_ADAPTATION.md:L36-L46`). Therefore `absent` is a development/release-scope gap. The report correctly does not call the document contradictory merely because it openly lists unfinished work. |
| S02 | Program-only validation allows generic sparse primitives/catalog entries to count as adaptation. | Rejected. A08 changes how code is verified, not which networks or orchestration must exist (`L18,L46,L54`). The report's proposed source-class/random-fixture/program integration evidence is consistent with this change. A full trained model or phone run must not be added back as a prerequisite. |
| S03 | Supplying off-phone pointmaps/depth/cameras can replace the neural depth stage. | Rejected for the required baseline. P03 explicitly requires MoGe pointmaps, P04 explicitly adds DA3 and multi-camera alignment, and A05 requires phone-side encoding, sampling, decoding and other computation (`L15,L42-L43`). User-supplied local auxiliary assets can be an additional declared mode; requiring another device to compute every new input would violate A05. The report makes this distinction rather than banning local import. |
| S04 | Four Pixal views or repeated single-view SAM followed by mesh averaging satisfy P04. | Explicitly rejected by the last column of P04 (`L43`). The report's required shared-state, per-step multiview prediction/fusion interpretation is consistent with “MultiDiffusion,” attention weights and warmup/replay. Four entirely completed independent runs do not establish the specified model. |
| S05 | D08 must support every possible mesh/Gaussian representation and optional optimizer before release. | Not demanded by the quoted clause. P03 qualifies the geometry/appearance as **selected output** (`L42`). The report correctly treats exact released mesh/Gaussian output profiles, Gaussian appearance/baking and optional layout optimization conditionally. An explicitly implemented source-backed mesh/vertex-color GLB profile can be valid; claiming default Gaussian-rendered texture equivalence without its renderer cannot. The report does not authorize silently dropping the chosen profile's appearance or GLB stage. |
| S06 | The report requires a full ComfyUI graph/plugin UI for new stages. | Rejected. A07 prohibits that expansion (`L17`). The report's strict component schema, ordered inputs, safe fixed classes and integration with existing task/model management fit the lightweight workbench. Its proposed internal stage graph/export does not mean a user-programmable plugin system. |
| S07 | Exact released YAML or checkpoint metadata being absent from the pinned Git cache justifies stopping all implementation. | Rejected. The specification says missing implementation continues; P07 explicitly supports selected conversion/import while complete public export URLs are unverified (`L46,L53`). The report correctly permits fixed-class/exporter/operator work now and separately leaves released architecture/profile matching unverified. It also correctly avoids inferring a gate/authentication result from a failed HTTP connection. |
| S08 | Model and phone performance limits can remove P03/P04 or defer them automatically. | Rejected. A06 and the shared full scope preserve the required work (`L16,L46`); the user waived performance/phone execution, not adapters. The original plan also never promises all targets run acceptably on a Nubia Z20 (`MULTIMODAL_RELEASE_PLAN.md:L138`). The report's “not measured” limitation is accurate and must not become either a phone-usability claim or an automatic scope waiver. |
| S09 | “首步预热 / 回退重放” demands identical noise handling in SS and SLAT regardless of their implementation. | Not established by that short phrase alone (`L43`). The report separates SS RNG restoration and the source SLAT fresh-main-noise path, rather than flattening both into an invented common rule. Exact source call-chain facts still require independent code-side review; the specification does not refute that distinction. |

## Interpretation limits and actionable wording

The report's request to “decide and document” appearance profiles is an implementation/configuration decision, not a requirement to stop and ask the user for renewed permission. The existing task already authorizes completing all adapters. Implementers should choose an explicit valid profile, carry its required components/tags/limitations, and continue the remaining required work (`REMAINING_ADAPTATION.md:L11-L18,L42-L46`).

“Absent” should remain scoped to complete model-specific production paths. Shared sparse operators and the new typed/multi-output loader are reusable implemented infrastructure, so their existence must not be reported as missing platform capabilities. Conversely, adding another shared export harness alone cannot change P03/P04 to complete (`L42-L46`).

The proof of exact source numerical, RNG, selected-output and decoder dependencies is outside this specification-only pass. No report statement about failed network access was independently re-run, and no claim of gated/unavailable public configs is made here. No source/model execution, protected-file inspection, production edits, browser, emulator, Docker/WSL/VM, downloads or publication were used.

## Record of reads

Read `D08-D09.md` in full across bounded sections; read `docs/REMAINING_ADAPTATION.md`, `docs/PROGRAM_VALIDATION.md`, relevant original frozen-plan/update clauses in `docs/MULTIMODAL_RELEASE_PLAN.md`, and the standing updated policy clauses in `AGENTS.md:L3-L18`. Searches covered SAM/D08/D09, geometry/appearance/GLB, same-phone execution, frozen scope and program-only validation. Historical acceptance language was considered against the later explicit policy; it was not silently used to restore cancelled tests.
