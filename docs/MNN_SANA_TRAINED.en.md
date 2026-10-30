# Sana trained assets and production execution

[中文](MNN_SANA_TRAINED.md) · [Engine and parameters](MNN_SANA_ENGINE.en.md) · [Companion selection](COMPONENT_SUGGESTIONS.en.md) · [Delivery and full pending scope](releases/v0.3.0-dev.35.md)

dev.35 / code 39 advances the matched Sana mobile variant through actual component execution and production Java import, generation, cancellation and recovery checks. Execution here uses native Windows CPU. Android has an ARM64 build from the same generated pipeline, with no physical-device execution. Existing PNGs do not establish prompt fidelity, independent reference numerics or image quality.

## App foundation and user assets

The APK contains foundation code, with no weights, tokenizer, meta queries or other learned data. Users remain free to select other models. Recommended stays `m08 → m06 → m01`; Sana is a peer image model tagged `task:image`, `text_to_image`, `engine:mnn_diffusion`, `pipeline:sana_mnn_v1` and `backend:cpu`.

Development uses all thirteen components from [the pinned MNN-Sana-Edit-V2 revision](https://huggingface.co/taobao-mnn/MNN-Sana-Edit-V2/tree/dd5955b4e63359b5822fa29a3b3711a112212046), totaling **1,505,181,194 bytes**, each verified with its complete SHA-256. The [public identity lock](../research/mnn_trained/assets.json) contains only source, path, size and hash metadata; learned files stay ignored under the build directory. This is not arbitrary original Sana 600M loading, image editing, image-to-image or Sana LoRA support. The model card declares Apache-2.0; users must review the selected revision and component licenses.

## User workflow

1. Open the matching HF repository/revision through Models → All/search and select `Sana mobile · Qwen3 + MNN`.
2. Bind the transformer and use companion review to inspect thirteen roles, sizes and integrity information. Resolve missing or ambiguous choices manually. Suggestions remain unapplied until confirmation.
3. Apply selected components, separately declare the model, review the full download plan and explicitly download; alternatively import existing matching files. Browsing, upgrading, declaring and submitting a task never trigger an implicit download.
4. Manage the model and its independent parameters in Local, select it in the generation workbench and submit. Each job freezes its settings. Later preference edits affect later jobs; cancellation and an explicit retry remain available.
5. Inspect stages, effective settings, failures and the final PNG in task details. Shared asset management provides pause/resume, import, updates and deletion. Download completion does not establish phone compatibility, quality or resource acceptance.

Developer test assets are not user prerequisites. The production App needs no Python, Windows, Termux, ROOT or second device. Encoding, diffusion, VAE decoding and PNG output are designed to execute on the same Android phone, with no external execution fallback.

## Repairs

| Area | Observed problem | Current implementation |
|---|---|---|
| Conditioning | The upstream helper selects an integer mask although this export declares a float attention mask | Float additive causal mask with padding and position handling |
| CFG | The exported Qwen graph fixes its internal batch to one; sending both conditions together fails with actual weights | Fresh sequential encoder instances produce independent finite `[1,256,1024]` features, then concatenate them for diffusion |
| Sampling progress | Upstream accepts the callback without invoking it inside the loop | Report each completed computation step, enabling production Java cancellation during sampling |
| One step | The schedule divides by `steps - 1` | Select the same high-noise starting timestep for one step, avoiding division by zero |
| Output failure | The upstream function returns success unconditionally | Return the actual image-write result and publish no failed artifact |

Both text instances exit before diffusion loads. Installed metadata stays unchanged. Java extracts only approved fields, creates controlled relative-path configuration, supplies temporary hardlinks and removes them after the child exits. Pinned upstream remains clean. One generator supplies both platform builds, whose two generated files have identical hashes. No model-ID-specific UI or queue branches are added.

## Evidence and limitations

Native execution checks cover prompt A/B/A, CFG, different negative conditions, rectangular and single-step output, input budget, missing components, invalid output location, wrong pipeline and recovery. Production Java exercises the actual HF recipe, user file import, complete SHA checks, independent clamping, restart persistence, immutable snapshots, cancellation after an actual sampling step and recovery. Direct and Java execution also compare same-host pixels.

Nonuniform pixels, repeatability and parameter effects are execution controls, **not image-quality metrics or an independent original reference**. Observed non-CFG and CFG 512×512, ten-step examples do not depict the requested subject. This quality problem remains open; passing flow checks cannot close target 04. Receipt timing and memory are desktop measurements and cannot establish Nubia Z20 performance or requirements. Every frozen target and original LCM/LTX numerical failure remains in the same complete v0.3.0 scope.

![Actual Windows model outputs; not Android UI or accepted image quality](media/development/sana-trained/00-contact-sheet.png)

[Output slideshow MP4](media/development/sana-trained/sana-host-outputs.mp4) · [GIF](media/development/sana-trained/sana-host-outputs.gif). These show labelled real artifacts, not phone recordings. See the [public verification index](../verification/development/status.json).

## Developer reproduction

```powershell
python tools/fetch_mnn_trained.py --download
python tools/build_mnn_host.py
python tools/test_mnn_trained.py
python tools/test_mnn_app_host.py
python tools/build_mnn.py
python tools/collect_mnn_notices.py
python tools/test_mnn.py
python tools/export_mnn_evidence.py
python tools/render_mnn_trained.py
```

Only the explicit `--download` command acquires model files; omitting it verifies existing files. A restricted connection may explicitly select `--origin https://hf-mirror.com`, retaining the exact commit, lengths and full SHA checks. Availability through a mirror is not identity evidence. Other commands never download models or run from the App. Tools use native Windows MSVC/NDK with no Docker, WSL, VM or emulator.
