# Local FLUX.2-klein 4B text-to-image

[中文](FLUX2_KLEIN.md) · [Project](../README.en.md) · [Checkpoint](releases/v0.3.0-dev.37.md) · [Local API](API.en.md)

LMA connects the distilled FLUX.2-klein 4B model to its existing model, download, settings, task and output management. App updates deliver foundation code only. Users explicitly choose and download/import four matched components; tokenization, text encoding, diffusion and image decoding all execute on the local CPU. There is no remote-inference route.

This checkpoint supplies complete trained Windows CPU execution, production Java/native calls, an independent tokenizer comparison and Android ARM64 compilation. **These are separate from physical Android execution, image quality, complete model numerics and full v0.3.0 acceptance.** Frozen target 07 still requires those gates. The separate Sana Edit capability does not replace frozen Sana text-to-image target 04.

## 1. Choose and acquire

1. Open **Models → All**, filter images, and choose **FLUX.2-klein 4B · Q4_0**. Recommended remains `m08 → m06 → m01`.
2. Review every component, total size and device status. Browsing, App installation, API startup and missing-file checks start no download.
3. Explicitly download or import the complete local files. The plan contains only this model's four components. A partial model cannot execute.
4. Pause/resume transfers and verify whole-file SHA-256. Use **Local** for installed models. Removing a model, deleting outputs and clearing task history are independent operations.

HF search can also compose a matching split-component recipe. Filename suggestions require confirmation and do not establish architecture compatibility. Multiple quantizations remain a user choice. The base checkpoint, 9B variants and a different Qwen encoder are not silently selected for this distilled recipe.

| Component | Pinned source | Complete bytes |
|---|---|---:|
| Q4_0 diffusion | [leejet/FLUX.2-klein-4B-GGUF](https://huggingface.co/leejet/FLUX.2-klein-4B-GGUF/tree/3b1f5a9dc3abb32238b053aeb3d823c30afdacbd) | 2,460,378,560 |
| Qwen3-4B Q4_K_M text encoder | [unsloth/Qwen3-4B-GGUF](https://huggingface.co/unsloth/Qwen3-4B-GGUF/tree/22c9fc8a8c7700b76a1789366280a6a5a1ad1120) | 2,497,281,312 |
| Original full FLUX.2 VAE | [Official klein 4B VAE](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/tree/e7b7dc27f91deacad38e78976d1f2b499d76a294/vae) | 168,120,878 |
| Matching Qwen merges | [Official tokenizer data](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/blob/e7b7dc27f91deacad38e78976d1f2b499d76a294/tokenizer/merges.txt) | 1,671,853 |
| **Total** | Four runtime components; none is packaged in the APK | **5,127,452,603** |

The [asset lock](../research/flux2_trained/assets.json) provides exact paths, revisions and full-file SHA-256. This recipe uses the original full VAE, not a substituted small decoder. Its catalogue ID is `flux2_klein4b_q4_0_catalogue_v1`; HF selections receive independent `hfb_…` identities. Both use the shared business flow and preserve older models and jobs.

## 2. Settings belong to the model

Open **Local → Model details → Model settings**. Editable selection fields accept presets or custom values and clamp excess values to this model's declared ceiling. Saved changes affect later jobs. Submitted jobs retain their original model, prompt, parameters and execution plan.

| Parameter | Recipe contract | Source of restriction |
|---|---|---|
| Width / height | Default 1024; 64–2048, aligned to 16 | Application guard and pipeline alignment; not acceptance of every size/quality/memory combination |
| Steps | 1–4, default 4 | Distilled sampling policy |
| CFG | Fixed 1 | This recipe disables CFG |
| Negative prompt | Unsupported; disabled in UI and nonempty submissions rejected | No silent loss of user instructions |
| Sampler / scheduler | `euler` / `flux2` | Matching fixed policy |
| CPU threads | 1–64, default 4 | Application guard, not a phone performance promise |
| Seed | `-1` random, or 0–2,147,483,647 | Random seed fixed and recorded at execution |
| flowShift | 0 automatic, or 0–32 | Automatic value resolved by the matching engine |
| VAE tiling | Enabled by default | Local decoding still requires full resource evaluation |

This is text-to-image. It does not reuse Sana Edit's source image or fixed style prompt. FLUX.2-klein base, 9B, FLUX.1 and alternative encoders need their own matching recipes.

## 3. Submit, cancel and manage results

Choose an installed model, enter a prompt, review the device resource status and add a local task. The shared queue waits for the active model call to finish and does not acquire missing components. Existing foreground-service, notification, API, cancellation, error and restart handling apply.

Completed PNGs are inspected before publication to the output library, with immutable model identity, original input and effective parameters. A failed or cancelled run publishes no partial image. Retrying is an explicit new execution. Removing the model preserves completed outputs and retained model settings and does not fetch a replacement.

Use the shared [task API](API.en.md), [preflight API](TASK_PREFLIGHT.en.md) and [recovery flow](TASK_RECOVERY.en.md). Starting the local API neither downloads nor loads an arbitrary model; callers use the same locally prepared models and queue.

## 4. Shared tokenizer correction

The first complete-weight probe produced a poster unrelated to the prompt. The HF `merges.txt` version header was treated as a merge by the upstream reader, shifting later token IDs. LMA now removes that header only in memory, handles BOM/CRLF and preserves the installed source bytes and SHA. Unknown/duplicate version headers, bare CR and empty rules fail explicitly.

Qwen pipelines also perform NFC before BPE splitting, matching official behavior for combining characters. Android and native host use the same helpers; the pinned upstream Git checkout remains unchanged.

Independent validation uses the explicitly acquired official `tokenizer.json` and Rust `tokenizers`: all **151,643 base vocabulary IDs, 26 added/special IDs, 33 text cases and three file representations**, for **117 checks**. This additional developer reference is not part of the four-component runtime package and is not bundled in the App. Tokenizer agreement does not establish full model floating-point or image-quality acceptance.

## 5. Evidence and reproduction

The actual native Windows CPU runs used six threads, 512×512 and seed 42. Complete four-step execution took approximately **373–524 seconds**; 20 ms process samples observed peak working sets around **4.58 GB (4.26 GiB)**. These observations include concurrent-test effects and are not Android speed, minimum RAM or GPU measurements. The four downloads total about 5.13 GB; file size alone does not establish runtime memory. Nubia Z20 loading, available memory, thermal behavior and sustained background execution remain unverified.

- [Independent tokenizer comparison](../verification/development/qwen-tokenizer.json): full vocabulary IDs, combining characters and malformed-file failures.
- [Actual native runs](../verification/development/flux2-trained.json): prompt/step changes, cancellation after real sampling, errors, deterministic recovery and observed Windows process memory.
- [Production Java/native flow](../verification/development/flux2-app-host.json): complete offline imports, HF composition, independent settings, immutable jobs, leases, actual generation/cancel/recovery, output publication, restart and model removal.
- [Actual output media](media/development/flux2-trained/manifest.json); [UI interaction recordings](media/development/curated/manifest.json) use visibly labelled bridge fixtures.

![Actual host output slideshow; not Android footage](media/development/flux2-trained/flux2-trained.gif)

GIF/MP4 files display actual images; **they do not represent generation speed or Android recordings**. The original failed-semantic image is retained as a diagnostic, not accepted quality. Full numerics, quality, resources and same-phone load/screen-off/API/upgrade tests remain independent requirements.

Run on native Windows, keeping all files in this project; no Docker, WSL or emulator:

```powershell
python tools/fetch_flux2_trained.py --download --reference-tokenizer
python tools/test_qwen_tokenizer.py
python tools/test_flux2_trained.py
python tools/test_flux2_app_host.py
python tools/render_flux2_trained.py
```

Without `--download`, acquisition only verifies existing files. Tests/inference cannot download. `--execute-only` saves a nonaccepting Java capture; `--verify-run build/flux2-app-host-tests/run-…` later checks source, native build, raw report and direct-output identities without rerunning inference. Developer builds may reuse only an owned unaccepted cache and publish separate immutable executables; accepted builds are never overwritten as mutable caches.

See the [official Apache-2.0 model license](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/blob/e7b7dc27f91deacad38e78976d1f2b499d76a294/LICENSE.md). App/engine and selected-model licenses are independent.
