# v0.3.3 implementation and remaining scope

[中文](IMPLEMENTATION_V033.md) · [Complete design](MULTIVIEW_DIAGNOSTICS.en.md) · [Machine matrix](../catalogue/release-0.3.3-implementation.json)

F-01–F-12, existing text, selections 01–14 / 16 / 17 and all nine frozen MOSS subtargets remain. The [v0.3.0 foundation](IMPLEMENTATION_V030.en.md), [community expansion](IMPLEMENTATION_V031.en.md) and [speech / single-image 3D](IMPLEMENTATION_V032.en.md) are preserved. There are 45 templates, 82 bundles and 15 extension engines plus text; users choose and manage all model assets independently.

| ID | Production implementation | Program coverage |
| --- | --- | --- |
| 01 | `MultiViewSpec / ExpansionEngine / native/multiview`, actual Pixal3D MV CPU / ARM64 | Four inputs, cameras, components, hard limits, upstream projection and native rejection |
| 02 | Four F16 / Q8_0 geometry / PBR import choices and generic MV recipe | Pinned manifests, seven/nine roles, no unverified download URL, imports and independent settings |
| 03 | Four-view UI, camera editor, drafts, preflight and explicit submission | 19 additional UI checks, preserved recommendations, no automatic asset downloads |
| 04 | Stage timing, supported workers' RSS and merged persistent execution observations | Failure/restart, retained identity, aggregate limit and independent copies |
| 05 | System restriction states and explicit diagnostic export | Latest 64 jobs, whitelisted fields, private-prompt/key exclusion fixtures |
| 06 | Current checks, package/signature, bilingual documentation and four media groups | Original signer, 38 ELF files / 16 KiB, immutable Git-identity v0.3.2 archive |

“Complete” in the frozen matrix applies specifically to F-01–F-12, text and the original selection IDs. It does not claim every subsequently researched architecture is integrated. Current evidence separately records `all_benchmark_architectures_integrated=false` and D04–D12.

| ID | Remaining | Meaning |
| --- | --- | --- |
| 07 | UltraTex, UniForge3D, UltraShape, Hunyuan3D 2.1, SAM 3D / MV-SAM3D, SUPRA-Tex, TripoSG, PartCrafter | Nine configurations / eight groups need actual Android ports; [concrete work](MULTIVIEW_DIAGNOSTICS.en.md#7-remaining-benchmark-architecture-work) |
| 08 | Verified public endpoint for complete matching MV weights | Import and custom-recipe paths exist; no invented one-click download source |
| 09 | Full-model quality, exact official F5 Chinese segmentation/sandhi equivalence, phone performance and endurance | Omitted under the user's program-only policy, never recorded as passes |

Inference stays on the same phone. No external execution, ComfyUI wiring/canvas or public plugin system is added. Faster program validation does not waive missing architecture implementation.
