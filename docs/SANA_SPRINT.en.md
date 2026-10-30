# Local Sana-Sprint 0.6B text-to-image

> 当前 / Current: **v0.3.0**. [完整程序集成 / implementation](IMPLEMENTATION_V030.en.md). [仅程序验证策略 / validation](PROGRAM_VALIDATION.md) 优先于下文历史完整模型 / 手机运行门槛；旧检查点与失败记录保留为历史。Original PixArt multiscale LTX is now integrated; quality/device acceptance remains untested. [Release](releases/v0.3.0.md).


[中文](SANA_SPRINT.md) · [Delivery](releases/v0.3.0-dev.45.md) · [Validation policy](PROGRAM_VALIDATION.en.md)

dev.45 adds a named **Sana-Sprint 0.6B MNN** text-to-image adapter, using the matched mobile-recipe alternative allowed by selection 04. Every execution stage stays on the same phone and uses the shared library, Local management, per-model settings, queue and PNG artifacts. Sana Edit, ordinary Sana 600M and 1.6B remain separate component contracts; the historical Edit gray-image failure is retained.

This update validates programs, without complete-model execution, generated model images or phone performance measurements. Publisher mobile demonstrations are not LMA device evidence. **No claim is made that the nubia Z20 can run these approximately 6.29 GiB of assets.** Encoder chunks are released sequentially, but peak memory is unknown; asset size is not runtime memory.

## User flow

1. Open **Models → All → Image**, select **Sana-Sprint 0.6B**, and review all components, total size, purpose and terms. Recommended remains m08 → m06 → m01.
2. Download only after explicitly confirming this bundle and its fourteen disclosed dependencies, or obtain and import the components yourself. Installing/upgrading LMA, browsing and opening settings never fetch weights. Other HF files require their matching recipe; filename suggestions do not prove compatibility.
3. In Local, pause/resume transfers, manage installed assets and save this model's editable settings. Values above its declared bounds return to the applicable maximum. Other models retain their own settings.
4. Once complete, choose Use, enter a positive prompt and confirm local execution. The engine-owned input rule hides and disables negative conditioning; the API rejects nonempty negatives as well. This recipe accepts neither image inputs nor LoRAs.
5. Submission freezes the selected model and task parameters, then uses the common queue, cancellation, resource checks, errors and artifact management. Temporary task edits do not replace saved model settings. Private workspaces are released after the child exits; failures remain local.

## Exact component contract

The conversion is pinned to [simota1987/Sana_Sprint](https://huggingface.co/simota1987/Sana_Sprint), revision `c7b846e1cec3ec9ec7ae456cf7d3ceb36742d656`. The original model is [Sana Sprint 0.6B](https://huggingface.co/Efficient-Large-Model/Sana_Sprint_0.6B_1024px_diffusers). The [bundle catalogue](../catalogue/model-bundles.json) records each immutable URL, size and SHA-256. The [source audit](../catalogue/sana-sprint-evidence.json) separates repository metadata, small graph structure and bounded partial VAE metadata reads.

| Count | Roles | Purpose |
|---|---|---|
| 2 | `diffusion` / `diffusion_data` | DiT graph and its external `.weight` |
| 8 | `gemma0`–`gemma3` and their `_data` | Four Gemma2 graph chunks and external weights |
| 1 | `embeddings` | FP16 256000×2304 table, read by selected row |
| 1 | `encoder_config` | Six fixed layout values; additional config paths rejected |
| 1 | `tokenizer` | Matched SentencePiece vocabulary checked against public HF tokenizer data |
| 1 | `vae` | Matched DC-AE, with input `latent` and output `image` |

Total: **6,754,581,137 bytes / 6.2907 GiB**. SentencePiece is pinned to the Sana 600M tokenizer revision `28f3af7689de15f3883d5863059a2fca0aa9b829`; matching tokenizer identity does not make ordinary 600M neural components interchangeable with Sprint. None of these models, vocabularies or embeddings ship in the APK. Sana/DC-AE and Gemma2 have separate terms; **Gemma Terms are not overridden by a blanket Apache-2.0 declaration**. Users review and obtain assets independently.

| Parameter | Default | Current bound and source |
|---|---|---|
| Width / height | 1024 / 1024 | Fixed matched export; entering smaller numbers cannot reduce this graph's resources |
| SCM steps | 2 | 1–4, application guard, not a universal theoretical model limit |
| Embedded guidance | 4.5 | 1–30, application guard; multiplied by 0.1 for DiT; no dual-branch CFG |
| CPU threads | 4 | 1–32, application guard |
| Seed | -1 | Automatic at -1; otherwise 0–2147483647; actual seed recorded |

Selections remain editable and offer presets. UI, Java preparation and the native process enforce their corresponding bounds. Settings distinguish fixed export constraints from application-selected limits.

## Execution

`positive prompt → lowercase / trim → fixed instruction + SentencePiece → row-wise embeddings → four Gemma2 chunks → 300 selected features and mask → SCM / DiT → DC-AE → PNG`

The encoder uses a fixed 506-position sequence and reports truncation for longer input. The diffusion condition selects BOS plus the last 299 positions with its mask. This is the named converted MNN profile, not a claim of equivalence with every ordinary Sana full-sequence pipeline. Encoder sessions are destroyed between chunks, and CPU output is materialized before proceeding. Pinned MNN/SentencePiece sources, process ownership and verified user components reuse the foundation without external inference services or a public node system.

## Program evidence and reproduction

**448 checks:** 57 Java contracts, 389 native tokenizer/math/small-graph checks and two production-process protocol checks. Twenty-five tokenizer cases cover control tokens, whitespace, Unicode and truncation. Ten sampling steps compare with unmodified Diffusers 0.35.1 `SCMScheduler.step`. Two tiny constant/addition graphs exercise the actual MNN graph loader; they do not execute Gemma, DiT or complete image generation.

An additional **19 current UI checks** cover selection, component review, explicit download, pause, settings and queue submission. Android ARM64/API28/16KiB compilation, dependency and signing audits are separate. See [program results](../verification/program/sana-sprint.json) and [Android native receipt](../verification/program/mnn-android.json), both fingerprinted. Complete-model/phone inference, image quality, speed and background endurance remain untested and are not reintroduced as subsequent program-publication gates.

The native Windows developer environment requires MSVC, JDK, cached pinned MNN/SentencePiece sources, CPU Torch and HF tokenizers. Install the reference package separately. Only about 37 MiB of tokenizer/config data is fetched below, without complete neural weights:

```powershell
python -m pip install --no-deps --target build/sana-reference-python diffusers==0.35.1
python tools/fetch_sana_program_inputs.py
python tools/test_sana_sprint.py
# Native NDK compilation and packaging; no model execution
python tools/build_mnn.py
python tools/collect_mnn_notices.py
python tools/build.py
node tools/capture_workbench.cjs sana
```

Current-page recordings use an explicitly simulated installation/queue bridge; no placeholder generated image is presented. Browser resources close in `finally`.

![Per-model Sana-Sprint settings; desktop UI fixture](media/development/sana/02-sana-settings.png)

![Selection, confirmation, settings and queue; no model execution](media/development/sana/sana-ui.gif)

[MP4](media/development/sana/sana-ui.mp4) · [Fourteen components](media/development/sana/01-sana-components.png) · [Task form](media/development/sana/03-sana-task.png) · [Queue](media/development/sana/04-sana-queue.png) · [Media identity and checks](media/development/sana/manifest.json)
