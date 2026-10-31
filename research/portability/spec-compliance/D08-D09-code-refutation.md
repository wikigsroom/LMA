## D08 / D09 — independent code-side refutation

**Result: confirm `absent` for both complete production adaptations. Confidence: high.** This pass was performed by the D05 checker, who did not author the SAM/MV-SAM finding. It independently followed current production validators and native entrypoints; it is not a full release or full-network numerical audit.

Target: `research/portability/spec-compliance/D08-D09.md`, reviewed SHA-256 `a6890fc138f583dfbb07214cf298fd6359b64906d0ce5611e41b3bd12f389a83`, 43,208 bytes, 2026-10-31. Source `D08/` means `build/spatial-source-review/repos/D08/`, revision `facebookresearch/sam-3d-objects@f91db411c50efee93d8db7aeb323885650f6f722`; `D09/` means the sibling fixed `devinli123/MV-SAM3D@abb04b5e8af5bc33b0265bdf19937e76bbb6bcdd` source.

---

**Requirements used:**

> mask、MoGe 点图、MoT 结构与布局 / pose、SLAT 与 FlexiCubes、选定输出的几何 / 外观及 GLB
> — `docs/REMAINING_ADAPTATION.md:L42`, P03
>
> D08 基础、Depth Anything 3、多相机对齐、权重融合与 MultiDiffusion、首步预热 / 回退重放
> — `docs/REMAINING_ADAPTATION.md:L43`, P04
>
> 既有四图方案不能代替该模型；不以单图重复执行冒充多视图
> — the same P04 row

---

**Refutation attempts against actual executable paths:**

| # | Possible counterexample | Actual code followed | Result |
| --- | --- | --- | --- |
| R01 | A generic registered Spatial engine may already load SAM graphs under an unrecognized name. | `app/src/main/java/com/lma/app/LocalEngines.java:L45` through `:L48` calls the selected engine's validator. `app/src/main/java/com/lma/app/ExpansionEngine.java:L26` through `:L41` delegates Spatial schemas/inputs/validation to `SpatialSpec`. `app/src/main/java/com/lma/app/core/SpatialSpec.java:L21` through `:L25` permits only explicit UltraTex/Paint branches or the Hunyuan/UltraShape `ultra()` predicate at `:L13` through `:L15`. | Refutation fails. There is no accepted SAM component/schema/input branch at the reachable Java boundary. |
| R02 | Bypassing Java or staging a different ONNX file may reach a hidden native SAM orchestrator. | `native/spatial/worker.cpp:L14` through `:L16` has the same finite UltraTex/Paint/Hunyuan/UltraShape dispatch. The shape branch at `:L30` through `:L41` evaluates image encoding, one shape flow, dense SDF queries and uniform surface extraction. | Refutation fails. No native MoT multi-head/layout stage, SAM SLAT/FlexiCubes or MV-SAM fusion runner is invoked there. Renaming a file supplies neither the missing coordinator nor a source-matched exporter. |
| R03 | Another mesh-family engine may already provide these models. | `app/src/main/java/com/lma/app/core/MeshSpec.java:L10` through `:L25` accepts TRELLIS/Pixal only; `native/mesh/worker.cpp:L11` through `:L17` repeats that guard. `app/src/main/java/com/lma/app/core/RfShapeSpec.java:L17` through `:L24` and `native/rf_shape/worker.cpp:L12` accept TripoSG/PartCrafter only. | Refutation fails. The alternative mesh families are closed routes to different models. |
| R04 | The working four-view route might be MV-SAM under another label. | `app/src/main/java/com/lma/app/core/MultiViewSpec.java:L15` defines fixed front/right/back/left roles; `:L25` through `:L28` requires `pixal3d_mv`. `native/multiview/worker.cpp:L17` rejects other pipelines and `:L64` calls `trellis_run_mv`. By contrast, `D09/sam3d_objects/pipeline/multi_view_utils.py:L135` through `:L166` evaluates actual per-view conditions against the same current state before fusion. | Refutation fails. This is genuine Pixal four-view support, not the required SAM backbone or shared-state MultiDiffusion implementation. |
| R05 | Existing sparse tests could prove the missing SAM networks are implemented. | `tools/test_spatial_sparse.py:L109` extracts only the pinned sparse spatial definitions; `:L118` through `:L126` compares operator policies; `:L153` extracts masked SDPA. `native/spatial/sparse.hpp:L23` through `:L37` implements pooling/subdivision policies. | Refutation fails. These are useful source-based operator checks and must be credited, but none evaluates MoT, pose decoding, SLAT or FlexiCubes as an App-selected model. Clarify denominator wording: for N contributing features, SAM mean is sum/(N+1), not division by an already incremented count plus one again. |
| R06 | New typed IO and `spatial_portable.py` have completed the port during review. | `native/spatial/typed_graph.hpp:L4` through `:L16`, `:L39` through `:L50` implements typed/multi-output IO. `tools/spatial_portable.py:L1` through `:L6` explicitly describes offline bindings; `:L67` through `:L72` selects a source lock and the UniForge/SUPRA prefix. `third_party/portable-sparse-source-lock.json:L5` and `:L409` list D05 and D10, not D08/D09. No Java/native call site imports this Python helper. | Refutation fails. The reusable loader is implemented; the in-progress offline binder is not a complete Android SAM adapter and presently does not source-lock SAM networks. Preserve that distinction as shared work advances. |
| R07 | Stage-one output or a mesh-only upstream switch could already close the promised GLB behavior. | `D08/sam3d_objects/pipeline/inference_pipeline_pointmap.py:L440` through `:L447` returns voxels for `stage1_only`; the normal route at `:L450` through `:L462` still samples/decodes SLAT and postprocesses. `D08/sam3d_objects/pipeline/inference_pipeline.py:L543` through `:L555` unconditionally accesses `outputs["gaussian"][0]` whenever mesh exists. | Refutation fails. The source facts in the original report are correct. An explicitly implemented alternate mesh-only GLB postprocessor could be valid, but toggling decode formats alone is not that implementation. |
| R08 | A simple warmup or repeated independent generation might satisfy the MV replay details. | `D09/sam3d_objects/pipeline/inference_pipeline.py:L1110` through `:L1128` performs SS warmup and restores CPU/CUDA RNG state. Its SLAT main pass at `:L1456` through `:L1468` instead generates fresh noise after warmup. | Refutation fails. The report correctly distinguishes the two stages rather than inventing one generic replay rule. No current native MV route implements these SAM stages. |

---

**Independent searches:**

| Search scope / pattern | Result |
| --- | --- |
| `rg -n -i 'sam3d|sam_3d|sam-3d|MV-SAM|multidiffusion|FlexiCubes|DepthAnything' app/src/main/java native --glob '!*.header.json'` | **0 hits**. This result was corroborated by actual allowlists/dispatch reads; it was not the sole basis of absence. |
| `rg -n -i 'sam3d|sam_3d|sam-3d|MV-SAM|D08|D09|multidiffusion' tools --glob '!*.header.json'` | **12 matching lines**, all audit/scope entries or the two sparse-test extraction calls. None is a full model exporter or App adapter. |
| Explicit `app/src/main/assets/recipe-templates.json` search for SAM/MV-SAM/MultiDiffusion/FlexiCubes/Depth Anything names | **0 hits**. No protected JavaScript catalogue or model-header file was read. |
| `spatial_portable` references in Java/native/tools | **0 call-site hits** at the inspected snapshot; the helper itself and its source lock were read directly. It is in progress, and this check does not claim future changes will remain absent. |

**Conclusion and limits:**

Both implementation gaps survive the independent code-side challenge. The proof is the finite set of executable mesh-family entrypoints combined with the absence of any matched SAM route, not the old audit's missing-target array. Credit shared sparse operations, typed graph loading and lifecycle infrastructure. The original report's static search counts can change during development; they are snapshot evidence and do not override real new production paths.

No trained models, program tests, device/emulator, browser/network calls, Docker/WSL/VM, protected JavaScript/model headers or production edits were used. Only this refutation record was written. Full profile-metadata accessibility, neural export correctness, selected appearance scope and phone capacity remain the original report's open questions; none was assumed resolved by this limited pass.
