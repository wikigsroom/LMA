# v0.4.0 · Conversations and local creation

[中文](CONVERSATION_V040.md) · [Frozen 20261102 plan](UPDATE_DIRECTION_20261102.en.md) · [Release notes](releases/v0.4.0.md)

D01–D12 ship as one program delivery. LMA remains a foundation: users choose, download or import every model; inference, preprocessing and composition run on the same Android phone. The original recommendation order, 62 recipes, 82 bundles, 18 extension engines plus text, port 52187, signing identity and existing assets remain.

Program implementation does not establish successful phone inference for every model. No ADB device is currently available and this round does not download complete models. Android visual preprocessing/MediaCodec output, current phone latency and screen-off endurance have no new physical results. Previous benchmarks retain their original APK identity; historical `empty_structure` and video-quality failures remain failures.

## Everyday operation

| ID | Action | Behavior |
| --- | --- | --- |
| U01 | Recommended / All HF / Local | Combine input/output/tool/evidence/local-state filters. Preserve recommendations and bounded HF pagination, explicit searches and offline cache. Unknown differs from unsupported. |
| U02 | Choose image, video, speech, music or 3D mode | Select an installed compatible model and submit directly. A language model is optional. |
| U03 | Attach managed assets | Import or select indexed results and assign their visual/voice/music role. Ambiguous choices require explicit selection. |
| U04 | Open a job card | Query the same job ID as the workbench/API; inspect stages, cancel, open results or edit a failed attempt. |
| U05 | Retry edited input | Restore the original request, preflight a new attempt and retain its parent task. Never overwrite previous failures or files. |
| U06 | Change temporary parameters | Edit numbers/JSON, clamp to model bounds in UI/native checks and preserve saved model defaults. Save defaults separately under Local model settings. |
| U07 | Browse history | Sessions page in batches of 40 and messages in batches of at most 60 using durable cursors. Paging does not regenerate anything. |
| U08 | Set a theme | Fresh/missing/invalid preferences default to dark, including a light system theme. Preserve valid dark/light/system selections and coordinate native/startup/WebView colors. |

Messages retain managed references rather than media bytes. Viewers open only on demand and release media when leaving. Chat references, active jobs, sequences and leases protect shared inputs. Deleting a conversation releases its references without deleting shared artifacts or models.

## Capability evidence and visual pairing

The fourteen exact language variants retain repository/revision/file identities and separate native declarations, LMA operations, composed behavior and evidence. Gemma 3 1B, ordinary Qwen2.5 and text Llama 3.2 do not inherit other vision variants. NSFW/Uncensored/Abliterated remain independent content labels.

The packaged llama.cpp server/mtmd bridge explicitly loads a main GGUF and matching projector. Images become actual `image_url` content blocks; filenames are not substitutes for visual inputs. Projectors are components and never independently advertised chat models.

1. Stop the resident model, select the exact compatible variant and open Visual Pairing.
2. Review main SHA256, architecture and projector repository, fixed revision, SHA256, size, URL and license. Saving only declares the component.
3. Explicitly download it in model management or import its exact manifest/files from a phone folder; load the main model afterward.
4. Select an image and send. Missing components, hash mismatches, text-only variants and unsupported inputs are rejected explicitly.
5. Stop before changing the pair. Unbind before removing its component; other shared references/leases still apply.

The built-in **m15 Qwen3.5 4B HauhauCS** preset pins main `79e28e…62741`, projector `a1e32e…a0f22`, 675,568,768 bytes, revision `c09cdbcdb1fefad6d335809d445621b5f5ba0c6e`, Apache-2.0. Sources: [publisher's fixed file](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/blob/c09cdbcdb1fefad6d335809d445621b5f5ba0c6e/mmproj-Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-BF16.gguf), [LFS identity pointer](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/raw/c09cdbcdb1fefad6d335809d445621b5f5ba0c6e/mmproj-Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-BF16.gguf). This is pairing provenance, not phone/quality acceptance. Fixed projector identities for m03/m09/m16 remain unresolved; a user may supply a fully reviewed manifest. No substitute model is silently selected.

Visual inputs accept 1–4 managed images/videos. Images resize to a 768-pixel maximum edge, source images are bounded to 4096² pixels and aggregate JPEG input to 4 MiB. Videos are limited to 30 seconds, at most three timestamped frames per clip and four total frames, also constrained by text/context/output budgets. Sampled-frame understanding is composed image input, not native video understanding. Actual server token limits remain authoritative; conservative estimates do not prove arbitrary tokenizer compatibility. Native audio, transcription, specialized OCR and 3D understanding remain unintegrated. See [llama.cpp multimodal interface](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md).

## Auto mode and controlled tools

Auto requires a deliberately loaded local language model and compatible template; small-model planning reliability is unknown. The program separately receives text, reasoning and streamed `tool_calls`, merges indexed fragments, checks strict JSON/unique IDs/whitelisted operations/models/assets/parameters, then persists an editable draft. Ordinary prose or code never becomes an executable command.

Tools: `image_generate`, `video_generate`, `speech_synthesize`, `audio_generate`, `mesh_generate`, `media_compose`, `task_status`, `asset_select`. Users review/edit before admission; unmeasured installed recipes require explicit consent. There are no implicit download, delete, arbitrary path, shell or external inference tools.

Plans allow at most eight automatic steps and one explicitly requested format repair. Invalid calls remain recorded. Calls/results retain matching IDs; terminal results can continue the language-model response. Newer user messages prevent an old plan from inserting an automatic continuation. Interrupted continuation requires explicit recovery. Media work uses the same heavy execution slot and existing resident suspension/restoration.

## Sequential templates and composition

| ID | Template | Requirements |
| --- | --- | --- |
| W01 | Prompt → image | Explicit image generator; optional planner. |
| W02 | Image → short video | A route that actually accepts image conditioning; explicit upstream artifact binding; generated motion must exceed five seconds. |
| W03 | Prompt → narration → TTS | Text and speech models, or skip the text step when narration already exists. |
| W04 | Image → geometry → optional material | Compatible mesh/material operations; reuse the existing GLB viewer. |
| W05 | Visual + voice/music → movie | Built-in `media.compose`, no AI-model download. |
| W06 | Asset understanding → answer | Use an integrated understanding route; a generation/TTS model is not an understanding model. |

Each editable step has an operation, model, prompt, temporary parameters and managed inputs. Future inputs bind `step`/`output`/`role` to declared earlier dependencies. At most eight controlled steps; no canvas, plugins, arbitrary scripts or external node graphs.

Sequences persist before admission and use stable step/attempt keys in the original queue. Failed dependencies block children; cancellation reaches active work and prevents new admissions. Successful predecessors are reused. Explicit step retries retain earlier attempts. SQLite outbox reconciliation survives either side of the chat/job commit window without duplicate generation.

`media.compose` accepts one PNG/JPEG/MP4 visual and at least one WAV track. Voice/music gains are 0–2, with linear resampling, mixing and saturation. Trim long audio and silence-pad short audio. Selected audio replaces original video audio. Short source video is rejected rather than looped/padded. Still-image presentations are explicitly labeled and limited to 15 seconds; video compositions to 60 seconds. Requested duration is 5.1–60 seconds and output validation requires an actual duration over five seconds and a real AAC track. Motion-generation guards retain their original rules. Originals remain; cancellation/corrupt inputs clean only temporary files.

## API contract

Use `http://127.0.0.1:52187/v1`, or the phone IP after explicitly enabling LAN access. Existing authentication, caching, publication eligibility, jobs/events/uploads remain. `/v1/models` lists complete, configured AI models; `x_lma.native_capabilities` describes evidence independently of executable operations.

`/v1/capabilities` separately describes built-in composition, sequences and `chat_input_types: ["text"]`. **Public OpenAI chat remains a text subset.** App visual attachments use internally constructed managed content, not arbitrary public URL fetching, image/audio inputs or unrestricted `image_url`. Standard image/speech endpoints still return PNG/WAV; video/music/3D/composition/sequences use explicit LMA asynchronous extensions. Sub2API clients route according to those declarations.

Example `POST /v1/lma/jobs`, after `/v1/lma/jobs/preflight`, with Bearer authentication and a stable `Idempotency-Key`:

```json
{"model":"builtin_media","type":"media.compose","input":{"prompt":"Local edit","artifacts":[{"role":"visual","artifactId":"REPLACE_WITH_REAL_VISUAL_ID"},{"role":"voice","artifactId":"REPLACE_WITH_REAL_WAV_ID"}]},"parameters":{"durationSeconds":6,"voiceGain":1,"musicGain":0.25}}
```

The built-in tool is absent from the AI model list. Create a sequence with `POST /v1/lma/chains`, `{ "template": "W02", "steps": [...] }`. Each step uses a public `model` in `request`, optional `dependsOn: [0]` and `bindings: [{"step":0,"output":0,"role":"ACTUAL_ENGINE_ROLE"}]`. Query `GET .../{id}`, cancel `POST .../{id}/cancel`, retry `POST .../{id}/retry` with `{"step":1}`. Repeating the same key/payload returns the original sequence; conflicts fail. Private session IDs and saved private prompts are omitted.

No fixed total generation deadline. Synchronous waits, SSE connection lifetimes and codec no-progress detection are distinct. Query the existing job after a client timeout before considering another submission.

## Implementation and validation

| ID | Implemented | Evidence boundary |
| --- | --- | --- |
| D01 | Exact variants, declarations, independent filters | Metadata/pair/API checks; unknown capabilities remain closed. |
| D02 | mtmd loading, component management, image/frame bridge | Android compilation and fixed-pair/negative cases; no new physical visual output. |
| D03 | SQLite v2, legacy bytes, cursors and outbox | Real host SQLite 100 sessions/1000 messages and rollback, not Android framework execution. |
| D04 | Unified direct modes, attachments, temporary parameters | Direct generation without a language model and two-layer constraints. |
| D05 | Original durable job cards, revision parent | Crash-window/idempotency/edit/cancel/retry checks. |
| D06 | Tool fragments, strict JSON, confirmation, continuation | Whitelist/duplicates/privilege/budget/format negatives; model reliability unknown. |
| D07 | References, lineage and deletion protection | Original/shared assets preserved; missing legacy sources are explicitly recorded. |
| D08 | Dependencies, templates, reuse and parent cancellation | Production state machine, durable reopening and commit/crash tests. |
| D09 | Local PCM mix, encoding and composition | Actual PCM/corrupt WAV/gain/resampling/silence checks; Android codec output still needs a phone. |
| D10 | Dark startup, incremental blocks, lazy media, scoped state | 1000 mixed messages mount 60; streamed updates change only their target; no new phone benchmark. |
| D11 | Discovery contract and tool/chain API | Actual host HTTP auth/bindings/idempotency/query/cancel; public chat inputs explicitly text. |
| D12 | Frozen regression, bilingual docs/media and stable delivery | Signed package/source fingerprints and stable-release checks; no recycled phone conclusions. |

See [version-bound evidence](../verification/releases/v0.4.0/status.json) and the [A01–A33 implementation map](../catalogue/conversation-20261102-implementation.json). Program verification, Android compilation and unavailable device checks are separate statuses.

UI artifacts: [blocks](media/conversation-v040/01-block-chat.png), [direct jobs](media/conversation-v040/02-direct-generation.png), [explicit audio roles](media/conversation-v040/03-explicit-composition.png), [ordered templates](media/conversation-v040/04-sequential-template.png), [recording](media/conversation-v040/walkthrough.mp4), [GIF](media/conversation-v040/walkthrough.gif). These capture production HTML/CSS/JS with an explicitly simulated native bridge, not a physical phone or generated model outputs.

OpenAPI: [v0.4.0](proposals/sub2api-openai.openapi.json). 新增链和内置合成直接调用手机服务；当前 Sub2API 源码网关保留既有媒体路由，不转发这两个新增工具。New chain/composition tools use the phone endpoint directly; the current opt-in Sub2API source gateway retains its existing media routes and does not forward them.
