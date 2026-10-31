# v0.3.2 program implementation and expansion

> This page records v0.3.2. v0.3.3 additionally integrates the actual D03 Pixal3D MV subset; see [the current guide and remaining architecture work](MULTIVIEW_DIAGNOSTICS.en.md). Old counts/evidence below retain their release context.

[中文](IMPLEMENTATION_V032.md) · [Full expansion guide](SPEECH_3D_EXPANSION.en.md) · [Machine matrix](../catalogue/release-0.3.2-implementation.json)

F-01–F-12, existing text, selections 01–14 / 16 / 17 and all nine MOSS subtargets remain. No prior required implementation is moved to a later version. The original [foundation](IMPLEMENTATION_V030.en.md) and [community additions](IMPLEMENTATION_V031.en.md) remain; this release extends them.

| Number | Implementation | Production behavior |
| --- | --- | --- |
| 01 | Four speech families, six optional bundles | Kokoro INT8, Chinese Melo INT8 / FP32, F5 v1, Omni GGUF / original; separate components and terms |
| 02 | New speech worker | `AudioCppSpec / ExpansionEngine / native/speech_extra`; actual CPU audio.cpp libraries, external F5 Chinese frontend, complete WAV |
| 03 | Chinese Melo frontend | `TtsSpec / native/tts`; phrase phones / tones and four FSTs; existing Kokoro / Piper / Matcha preserved |
| 04 | Single-image 3D, five bundles | `MeshSpec / ExpansionEngine / native/mesh`; TRELLIS.2 / Pixal3D CPU geometry, optional textures and GLB |
| 05 | Shared lifecycle | `mesh.generate`, jobs / drafts / resource checks / cancellation / artifacts / API; explicit user downloads and submissions |
| 06 | 3D settings and results | `expansion.js / glb-preview.js / GlbFile`; independent settings, hard clamping, bounded geometry preview and GLB / provenance export |
| 07 | Reviewable delivery | 16-case benchmark audit, 11-bundle evidence, native licenses, program checks, bilingual docs, original signing, screenshots / GIF / MP4 |

Current counts: **44 templates, 78 bundles, 14 extension engine families plus text**. Models remain peers, with independent task, engine, dependency, content-source and installation tags. Recommended remains `m08 → m06 → m01`.

Only single-image subsets of TRELLIS.2 / Pixal3D from the benchmark enter this APK. Other configurations need the ports described in [D01–D16](SPEECH_3D_EXPANSION.en.md#2-audit-of-the-requested-rtx-3080-3d-collection); catalogue registration is not treated as execution support. Current evidence is program verification, not complete-model, physical Android or quality acceptance.
