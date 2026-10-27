# HF discovery and local models

[中文](HF_MODELS.md) · [Documentation](README.md)

LMA 0.2.0 is a local-model workbench. It preserves the existing recommendations and adds HF discovery and a dedicated Local manager. General models are eligible; uncensored variants carry separate evidence-based labels.

## Development component selection

0.3.0-dev.5 adds explicit component recipes: frozen revisions, roles selected across repositories, and separate registration/download confirmation. See [recipes and integrity](HF_RECIPES.en.md). These signed-App templates do not make every HF architecture runnable. The v0.2.0 GGUF workflow below remains available.

## Workflow

Recommended still displays `m08 → m06 → m01`, preserving names, order, labels, pinned weights and author evidence. Lightweight / Advanced retain the original 14 curated entries. Online discovery does not overwrite them.

1. Select **全部 / All**, or enter a keyword, `owner/model`, or `https://huggingface.co/owner/model`. Except within Local, typing queries HF after about 550ms; Enter searches immediately.
2. GGUF and download-count sorting are defaults. Select **HF 全部格式 / All HF formats**, likes, or latest updates as needed. Search pages contain at most 24 repositories with backward/forward navigation.
3. Select a repository's files. Native code rereads repository metadata, pins the 40-character commit, and paginates its recursive tree. Each request reads at most 100 tree entries and displays only `.gguf` files from that page.
4. Choose a quantization/file after checking bytes, task and unsupported reasons. A page without GGUF files may still have a next page. Open the original repository to find a GGUF conversion repository if necessary. No conversion runs in LMA.
5. Download opens **本地 / Local**. The native foreground service queues, downloads/resumes, verifies and stores the file. Re-selecting the same repository, commit and path does not duplicate records.
6. Local collects downloaded built-in, HF and imported models, plus unfinished transfers. Its search stays offline. Load after download; stop a running model before deleting it.

HF search reflects the API's currently visible results and permissions, rather than an offline snapshot of the entire Hub. Retry metadata failures; recommendations and installed models remain available offline. Metadata browsing does not start the inference foreground service or interrupt a running model.

## Discovery, download and runtime compatibility

| Object | Current behavior |
| --- | --- |
| HF repositories | Keyword, exact-name, URL, sorting and paginated discovery; public or authorized visibility |
| Ordinary / Uncensored / Abliterated GGUF | Same download flow, without a curated-list or special-label requirement |
| Single-file text GGUF | Download candidate; actual loading depends on engine architecture, quantization, template and available RAM |
| Split GGUF | Explained and disabled; shard merging/group management is not implemented |
| `mmproj` / projector | Explained and disabled as a standalone text model |
| Declared speech, embedding or other tasks | File selection disabled; unknown task metadata still needs user review and actual loading |
| Safetensors / PyTorch / ONNX / MLX | Discover repositories with All HF formats and inspect sources; not downloadable/loadable runtime inputs in this version; no conversion |
| Gated / private repositories | Need actual HF permission, optional token, accepted terms and connectivity |

A `.gguf` extension does not prove compatibility. The fixed llama.cpp v0.4.1 runtime is CPU / ARM64 / Android 9+. Single files are limited to 12 GiB with a 64 MiB storage reserve. Download bytes are not RAM usage. Start small with a short context on a Z20-class phone; phone compatibility and tokens/s remain unmeasured.

The workflow follows LM Studio-style discovery, quantization selection, downloads, local management, chat and API serving. Full multimodal/multiple-runtime support, conversion, split files and every desktop feature are not implemented. See [LM Studio's model-download guide](https://lmstudio.ai/docs/app/basics/download-model) and [HF's GGUF documentation](https://huggingface.co/docs/hub/en/gguf) for the source format/runtime distinctions.

## Revisions, integrity and local identity

Repository metadata fixes a commit SHA; tree pages and `resolve/{sha}/{path}` use that same revision. LFS SHA256 is checked after downloading when provided. Without an expected hash, only GGUF, transfer length and a local hash are verified, without a publisher-match claim.

HF local IDs are `hf_` plus the first 40 SHA256 hex characters of repository, commit and file path. Remote paths are encoded segment by segment; local filenames use only a safe ID. Deletion removes the installed/partial/rejected files and durable HF metadata. Uninstall removes all private models/history; same-signature upgrades preserve existing IDs and records.

WebView selection sends only repository, commit and path. Native code must match an entry on the current file page; the UI cannot supply a substitute URL, size or hash. Pagination accepts only trusted HF HTTPS hosts and the expected API path.

## Individual local-model settings

A downloaded model’s settings icon opens its own context, output, threads, temperature, reasoning and system prompt. Editable presets and automatic clamping use per-model bounds. Different HF revisions/quantizations have separate IDs; selecting the same pinned file reuses its profile. See [per-model settings](MODEL_SETTINGS.en.md).

## HF token and network source

Public models need no token. Automatic source selection tries HF, then the independent HF Mirror service. Fixed official/mirror options are available. When a publisher hash exists, complete weights are checked against it after download.

For gated/private repositories, accept the terms on HF and obtain read permission, then save an `hf_…` token in Settings → Hugging Face access. There is no browser login flow. A token remains optional for public models.

Tokens reside in private SharedPreferences with app backup disabled; hardware encryption is not claimed. Only a boolean reaches the page, and saving clears the password field. Model records, log exports and release assets exclude the token. Authenticated HF requests use the official source. Redirects recheck the host and send Authorization only to `huggingface.co` on the default HTTPS port, never to mirrors, CDNs or custom hosts. If the official source is unreachable, clear the token to use public mirror access.

401/403 point to authorization/terms; 404 may also mean insufficient permission; retry 429 later. No real account token or gated/private repository was tested in this run.

## Separate uncensored tags

| Label | Basis |
| --- | --- |
| 无审查 / Uncensored | Preserved curated entries with checked publisher claims, pinned author cards and exact weight attribution |
| 无审查 · 元数据 / Uncensored · metadata | Online name/tag hints such as uncensored, abliterated or Dolphin; no individual author-card verification |
| No tag | No such evidence/hint; not an independent refusal measurement |

Manual imports never gain verified status from names alone. Labels do not promise zero refusals, accuracy, performance or phone compatibility. LMA does not add prompt/response filtering. See [publisher evidence](UNCENSORED_MODELS.en.md).

## Evidence and demonstrations

45 production-Java HF checks cover pagination, path/URL validation, format restrictions, pinned hashes, deduplication, persistence/deletion, stale queries, token destinations and native selection. Five live checks use the production client against public HF Mirror metadata: GGUF/all-format search, pagination, commit and publisher SHA256. No weights or inference are involved. See [hub.json](../verification/hub.json) and [hub-live.json](../verification/hub-live.json). Browser tests use an explicit native fixture.

<p><img src="media/lma-hf-local.gif" width="320" alt="HF and Local management; explicitly simulated UI demonstration"></p>

[Media provenance](MEDIA.md) · [Validation boundaries](VALIDATION.en.md) · [Architecture](ARCHITECTURE.en.md)
