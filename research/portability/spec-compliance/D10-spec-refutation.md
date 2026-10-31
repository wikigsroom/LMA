## D10 / P05 — independent specification-side refutation

**Result: confirm the `absent` production-adaptation verdict, with a scope correction for conditional frontend roles. Confidence: high.** This pass was performed by the D05 checker, who did not author the D10 finding. It does not replace the separate code-side refutation or certify a release.

Target: `research/portability/spec-compliance/D10.md`, reviewed SHA-256 `6af4f4810aacafd04bfb36e639d2b88770fd43cb61741a8741eac61a3cf2c64e`, 31,853 bytes, 2026-10-31. `UP/` below means `build/spatial-source-review/repos/D10/`, fixed revision `Supra-3D/SUPRA-Tex@cee4435652d0f23737bd28d5704e0fae9830b411`.

---

**Requirement reread verbatim:**

> | P05 | D10 SUPRA-Tex | 本机 Qwen 材质前端、几何 / 观察 latent、交错 completion 网络与 SCVAE、PBR 光栅 / 烘焙 | 共用 sparse 与材质基座；禁止接入外部背面图或其他远端推理服务 |
> — `docs/REMAINING_ADAPTATION.md:L44`, section 3

The section explicitly describes still-required development (`docs/REMAINING_ADAPTATION.md:L36`, `:L46`), not features already included in the published v0.3.5 (`:L5`). User-selected model assets (`:L11`), same-phone runtime (`:L15`) and program-only validation without full models/device requests (`:L18`, `:L54`) remain binding. The original numbered matrix also names material prediction, observed latent, completion and baking, and excludes external back-view services (`docs/IMPLEMENTATION_V035.md:L26`; `docs/MULTIVIEW_DIAGNOSTICS.md:L127`).

---

**Refutation attempts:**

| # | Attempt to overturn or narrow the original finding | Direct evidence reread | Result |
| --- | --- | --- | --- |
| R01 | P05 might be an optional research note, so missing code would not block requested completion. | `docs/REMAINING_ADAPTATION.md:L36`, `:L44`, `:L46`; its program-only exemption at `:L54` explicitly does not excuse missing code. | Rejected. The actual port remains required; full-model execution is not required to establish the gap. |
| R02 | Generic material baking or an ordinary Qwen image generator could satisfy the named model. | P05 explicitly includes the Qwen material frontend, geometry/observation latents, interleaved completion and SCVAE. `UP/supratex/inference/pipeline.py:L252` calls the actual shape encoder after FDG construction; `:L305` through `:L346` builds/encodes visible material observations; `:L467` through `:L489` uses shape decoder guides and the six-channel material decoder. `UP/supratex/models/interleaved_flow_transformer.py:L323` through `:L339` retains static observations while updating generated features. | Rejected. Generic images, imported example latents or an image-view baker omit required learned stages. Shared kernels are enabling code, not the selected model's implementation. |
| R03 | A valid SUPRA route must generate a back view through the source's external workflow. | `UP/supratex/inference/pipeline.py:L654` makes `back_view_dir=None` the default; `:L673` through `:L677` directly runs single-view completion. P05 explicitly excludes external back-view services. | Rejected. A real local single-view route is a valid minimal choice. Omitting that optional outside service is consistent with the requested all-local design. |
| R04 | Pixal3D geometry, NAF/DINO geometry conditioning and MoGe camera estimation are unconditional P05 dependencies for every input mode. | The report's N06 says the automatic mode remains mandatory work (`D10.md:L96`), while its own plan permits supplied mesh/camera (`:L112`, `:L113`). `UP/README.md:L47` through `:L48` explicitly supports texturing an existing mesh. `UP/supratex/frontend/pipeline.py:L181` conditions geometry generation on `geometry_package is not None`; `UP/supratex/inference/pipeline.py:L181` through `:L218` accepts supplied geometry and canonical camera, with optional image depth. Neither P05 nor the older D10 matrix literally requires Pixal/MoGe for every task. | **Narrow the mandatory-role wording.** These are dependencies of the automatic image-to-geometry/camera frontend, not of every legitimate mesh-texturing task. A declared local mesh/camera input profile must still run actual local Qwen material prediction and all required observation/completion/SCVAE/baking stages. It cannot require off-device latent computation. This does not remove any independently frozen automatic-frontend work from other requested scope. |
| R05 | Background removal must block every task even with correct input alpha. | `UP/supratex/frontend/preprocess.py:L82` through `:L97` preserves nonopaque RGBA; only absent alpha requires an explicit segmentation model. The checker already qualifies N05 (`D10.md:L95`). | Rejected as a universal blocker. Retain conditional dependencies and disclose the accepted input profile. An alpha-input route does not prove automatic opaque-image segmentation. |
| R06 | CPU substitutions or developer-side export inherently violate same-phone execution. | `docs/REMAINING_ADAPTATION.md:L15` requires runtime encoding, sampling, decoding, rasterization and synthesis on the phone; `:L11` permits explicit selected assets. `D10.md:L108` through `:L145` proposes local prepared graphs and a signed native runner, not remote runtime inference. | Rejected. CPU adaptation and offline asset preparation are permitted; actual graphs, source semantics and runtime integration still need implementation. No universal Android impossibility follows from the upstream CUDA entrypoint. |
| R07 | “Absent” ignores newly implemented shared source bindings or typed graph IO. | `tools/spatial_portable.py:L1` through `:L6` declares offline CPU source bindings; `native/spatial/typed_graph.hpp:L39` through `:L50` supplies actual typed/multiple-output loading. `D10.md:L83` scopes absence to the complete SUPRA execution chain. Actual Spatial dispatch remains closed at `app/src/main/java/com/lma/app/core/SpatialSpec.java:L21` through `:L25` and `native/spatial/worker.cpp:L14` through `:L16`. | Rejected as an overturning argument. Credit those reusable components and refresh old search counts, but they are not the missing accepted recipe/orchestrator. |

---

**Searched and paths walked:**

Reread P05 and A01/A05/A08/P08; checked older D10 matrix rows to distinguish the required core from a particular automatic input mode. Followed fixed-source frontend preprocessing → conditional geometry → material-map prediction, then completion case loading → FDG/shape encoding → visible-observation encoding → single-view completion → guide-coupled decoders. Searches for `geometry_package`, `camera`, `run_completion`, `back_view_dir`, `encoder` and `decoder` found the conditional branches and actual learned-stage calls cited above. Existing-mesh support in the README is corroborated by executable input loading, not accepted only as marketing text. No browser or network requests were made in this pass.

**Conclusion and remaining questions:**

The missing matched P05 production route survives the specification-side challenge. Correct the original report's inventory to label frontend roles by input mode rather than treating automatic Pixal/NAF/MoGe as unconditional task prerequisites. Keep the complete core pipeline and user-selected local assets mandatory. Whether the final release promises both automatic generation and existing-mesh modes must be stated in its concrete model profile; this refutation does not authorize silently deleting frozen work.

No trained models, device/emulator, virtualization, protected JavaScript/model headers or production edits were used. Only this refutation record was written; the original report was not changed.
