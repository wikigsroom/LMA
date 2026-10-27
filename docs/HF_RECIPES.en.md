# HF components and local recipes

[中文](HF_RECIPES.md) · [HF discovery](HF_MODELS.en.md) · [Development status](DEVELOPMENT.en.md) · [Asset-control audit](ASSET_CONTROL_AUDIT.en.md)

Applies to **0.3.0-dev.6 / code 10, an internal checkpoint, not a Release**. The App supplies code and recipe metadata; users select and manage model assets. This workflow does not establish Android support for arbitrary HF weights. Architecture, language, matching components, licensing and device resources still need verification.

## User workflow

1. Search HF or use All, open a repository's file picker, then choose **构建模型包 / LoRA 配方**. The existing single-file GGUF text route is preserved.
2. Explicitly select a recipe. Seven signed-App data templates cover complete SD 1.5 / SDXL checkpoints, their respective LoRAs, and Kokoro / Piper VITS / Matcha + vocoder using the disclosed English lexicon. A template cannot install an engine, convert weights or verify runtime compatibility.
3. Select each required role, such as `model`, `voices`, `tokens` or `vocoder`. Enter another `owner/repository` and paginate when necessary. Existing choices retain their own repository and frozen commit. Extensions validate role formats only; they do not identify architecture or language. Changing templates clears choices; closing/restarting may lose an undeclared draft.
4. Inspect every chosen file and fixed dependency, source, revision, size and integrity type. Checkpoint templates disclose CLIP merges; speech templates disclose the English lexicon. Other languages, separate diffusion weights and LCM / LCM-LoRA need their own correct complete recipes.
5. **加入本地并查看下载计划** registers an immutable manifest and **does not download**. Review the full size, verified reuse, remaining transfer and engine status, then explicitly download. Missing engines/assets or incompatibility fail locally with an explanation; no off-device inference or implicit dependency download is added.
6. Manage pause/resume, folder imports, independent settings and asset deletion in Local. LoRAs remain peer entries and require an explicitly chosen compatible base. Jobs execute on the same phone; Recommended remains `m08 → m06 → m01`.

## Data and integrity

The bundled `lma.recipe-catalogue/1` contains templates, parameters, roles and dependency metadata only. Generated `lma.model-bundle/2` manifests contain data components, without Python, SO files, scripts, arbitrary commands or user plugins.

| Source | Pinned expected integrity | After explicit transfer/import |
| --- | --- | --- |
| HF LFS weights and other large files | Published metadata SHA256 and full length | Compute and compare content SHA256 |
| Ordinary small Git files | Frozen commit, Git blob SHA-1 and full length | Verify the Git object ID over `blob <length>\0` plus file bytes; separately record actual content SHA256 |

A Git blob ID is neither raw-file SHA-1 nor publisher SHA256. The UI does not invent expected SHA256 when ordinary Git metadata lacks one. A namespaced storage key is not a content-hash claim. Job provenance keeps both the expected algorithm/digest and the measured SHA256. Integrity checks cannot establish trustworthy authorship, license permission or model quality.

Existing `lma.model-bundle/1` SHA256 objects/receipts remain compatible. Schema 2 requires exactly one expected digest per component. Recipe imports separate roles, e.g. `model/model.onnx` and `vocoder/model.onnx`, avoiding cross-repository filename collisions; consult the exact paths in the download plan. Runtime leases protect complete base/adapter groups, and deleting another model preserves shared objects.

Native selection accepts files from the current frozen repository page only. Changed templates, repositories or pagination invalidate stale commands. WebView cannot invent unlisted downloads or supply executable engines. Repeating the same template/component selection reuses its ID; changed pinned sources or recipes create distinct immutable records. Independent model version updates and complete legacy migration remain unfinished work in the same release.

## Verification and media

240 foundation/storage checks include 110 new recipe/Git-integrity assertions. Separate HF/controller and browser checks are recorded in [development evidence](../verification/development/status.json). Host checks use arbitrary bytes or explicitly simulated native state, without test weights; they are not model outputs, Android installation or screen-off endurance evidence.

![Explicit UI fixture: HF component choices](media/development/12-hf-components.png)

![Explicit UI fixture: component files and digest types](media/development/13-hf-component-files.png)

Complete v0.3.0 still requires F-01–F-12, every frozen subtarget in 01–14/16/17, and A1–A11. This feature does not reduce, split or defer that scope. The public APK remains v0.2.0.

Metadata fields were checked on 2026-10-28 against the [official HF SDK `RepoFile` parser](https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/hf_api.py) and [file-tree API documentation](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api#huggingface_hub.HfApi.list_repo_tree): ordinary-file `oid` and LFS `oid` have different meanings. New controller tests use deterministic metadata fixtures. Direct HF requests timed out and the mirror returned 403 in this run; no new live tree acceptance or weight download is claimed.

![Explicit download plan after registration, UI fixture](media/development/14-hf-download-plan.png)

## Nano external-data recipe

The eighth template covers only MOSS-TTS-Nano browser ONNX with its full codec. `.model` SentencePiece data and `.data` external ONNX weights are separate user choices. Eight core roles are required; every data file referenced by a graph is also required at execution. Registration does not transfer anything. See [Nano roles, guards, build and evidence](MOSS_NANO_ENGINE.en.md).
