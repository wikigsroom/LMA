# Text models in the shared foundation

[中文](TEXT_ENGINE.md) · [HF recipes](HF_RECIPES.en.md) · [Model updates](MODEL_UPDATES.en.md) · [Development status](DEVELOPMENT.en.md)

Applies to **0.3.0-dev.10 / code 14, an internal checkpoint, not the completed or published v0.3.0**. User-selected and [migrated existing text GGUFs](MODEL_MIGRATION.en.md) share parameters, jobs, artifacts and model-version management. Existing recommendations, chat IDs and persistent APIs remain; [shared scheduling](SCHEDULING.en.md) is integrated; physical upgrade acceptance remains open.

## Selection and use

1. Open an HF repository's file picker through All/search, choose **构建模型包 / LoRA 配方**, then **文本 GGUF · CPU**. The template contains recipe metadata only, without weights.
2. Bind one complete text GGUF with its tokenizer to `text_gguf`. Review its fixed revision, bytes, integrity, license and transfer plan. Adding to Local only declares a manifest; download or folder import requires a separate user action. This recipe does not accept split GGUF, vision/audio components or custom code.
3. After installation, open details and model settings in Local. Text remains a peer of image/video/audio, tagged text generation and `llama_text / text_gguf / GGUF / CPU`. A filename or template cannot establish architecture compatibility with the packaged engine.
4. Edit independent threads, context, output ceiling, temperature, reasoning and system prompt. Choose Use, enter a prompt, explicitly opt into trying an unmeasured recipe, and submit the shared queue. Jobs wait for active replies, switch engines automatically and restore the text model the user still wants. A job does not change the selected chat model.
5. Open the artifact to read/copy its response, expand reasoning separately, export original JSON or export provenance. Output-limit completion is labeled. Cancellation, truncation and missing completion events cannot become successful results.

Recommended `m08 → m06 → m01`, original weight contents, IDs and per-model profiles are retained. App installation/upgrades/browsing do not select/download/replace models. Local metadata/storage migration reuses existing files; a loading/running legacy model waits for exit before binding.

## Parameters and model versions

Saving, submission and execution validate parameters. Shared schemas add `maximumFrom: {"field":"context","offset":-1}` for the joint output/context bound; UI and native code clamp effective values and reject cycles or impossible intersections.

Installed GGUF v2/v3 architecture/context metadata intersects recipe, model, CPU and application bounds. An unknown context is explicitly unknown, with an 8192 application guard. Known contexts also have the current queue's 131072 allocation guard. These guards do not establish quality or measured RAM. Threads cannot exceed available CPUs; temperature is 0–2; system prompts are at most 4000 characters and task prompts at most 16000.

Effective schemas remain separate from immutable source manifests, without changing provenance or weights. Incompatible imports report a record-specific error instead of disabling the library. Version review hashes include both effective schemas. First discovering GGUF limits after download invalidates an earlier review: cancel that plan and review again while retaining downloaded assets; old consent cannot silently activate a changed model configuration.

## Execution, artifacts and API

`TextEngine` reuses pinned `libllama-server.so` and dependencies through `LocalEngine`. Each job has a private loopback port, random secret and fixed bundle ID. The secret is passed in the child environment, and prompts use POST rather than process arguments or UI logs. Inference redirects are rejected and no off-device execution is added. Execution ownership is released after child exit.

Loading has a five-minute guard and the shared queue has a two-hour per-job guard. Neither is a phone performance promise. Cancellation owns the job/process. SSE validation requires one output sequence, separate response/reasoning channels, a normal finish reason and `[DONE]`, with line/event/stream/result bounds. Results retain at most one million UTF-16 characters combined and 8 MiB serialized.

Result MIME is `application/vnd.lma.text+json`:

```json
{"schema":"lma.text-result/1","content":"Response","reasoning":"Reasoning","finishReason":"stop","usage":{"prompt_tokens":10,"completion_tokens":20,"total_tokens":30}}
```

`finishReason` is `stop` or `length`; absent token counts are not fabricated. Native validation precedes artifact storage, with model/component receipts, effective settings, engine and execution provenance. The UI reads only its own controlled local artifact path and displays inert text; output HTML does not execute.

New bundles use the existing async job API with `type: "text.generate"` and `{"prompt":"..."}` input. Authenticated artifact/Range routes remain shared. Existing `/v1/chat/completions` and `/v1/completions` still serve the loaded legacy text path; this does not establish complete chat/API scheduling unification. See [API documentation](API.en.md).

## Evidence and remaining work

66 added host checks execute production Java, real files, child processes and authenticated loopback HTTP with zero-tensor GGUF metadata and literal text fixtures. They cover actual limits, expired version consent, cancellation, truncated streams, redirects, failed children, artifacts and cleanup. **No weights are downloaded and no model inference or Android emulation is performed.** See [text.json](../verification/development/text.json).

[Settings](media/development/22-text-model-settings.png) · [Task form](media/development/23-text-queue-form.png) · [Text artifact](media/development/24-text-result.png) · [Recording](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif). All media visibly retains UI FIXTURE labels and literal test output.

Local migration code and 69 host checks are in place. Physical-Android upgrades, full chat/API scheduling, every selected model and offline/cancel/background/resource/quality acceptance remain in the same [complete v0.3.0 scope](MULTIMODAL_RELEASE_PLAN.en.md). No new Release is created.
