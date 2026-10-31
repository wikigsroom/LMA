# LMA user guide

> Current v0.3.5: [Hunyuan shape and UltraShape refinement](SPATIAL_SHAPE.en.md), [full numbered implementation and pending ports](IMPLEMENTATION_V035.en.md). Five CPU sparse operators do not complete SAM/UniForge/SUPRA; Paint remains missing. All prior routes remain. Versioned notes below are historical, not the current support matrix.

> Current v0.3.3: [four calibrated views, verified MV imports, per-model settings, API and explicit diagnostics](MULTIVIEW_DIAGNOSTICS.en.md). All earlier capabilities remain. The historical checkpoint notes below keep their original scope. [Current implementation](IMPLEMENTATION_V033.en.md) / [program-only policy](PROGRAM_VALIDATION.en.md).

> v0.3.2 adds four speech families and single-image 3D. See the [expansion guide](SPEECH_3D_EXPANSION.en.md) for formats, components, workflows, API, builds and program checks. Existing capabilities remain; older checkpoints below retain their original context.

> 当前 / Current: **v0.3.0**. [完整程序集成 / implementation](IMPLEMENTATION_V030.en.md). [仅程序验证策略 / validation](PROGRAM_VALIDATION.md) 优先于下文历史完整模型 / 手机运行门槛；旧检查点与失败记录保留为历史。Original PixArt multiscale LTX is now integrated; quality/device acceptance remains untested. [Release](releases/v0.3.0.md).


dev.34: HF recipes can review companion files from a pinned revision and explicitly apply checked suggestions. This only fills component choices; declaration/download are separate. Existing choices/settings remain. See [component review](COMPONENT_SUGGESTIONS.en.md).

dev.33: explicitly select the complete Nano 100M bundle in All → Audio. Local offers Kokoro/Nano names or editable IDs from downloaded files, with per-model clamping/settings. See [speech usage](SPEECH_SELECTION.en.md); UI fixtures do not establish downloads, inference or phone acceptance.

Current dev.32: [curated diffusion, LoRA dependencies and tasks](CURATED_DIFFUSION.en.md) / [中文](CURATED_DIFFUSION.md). Explicitly choose six pinned profiles in All, review/download LoRA and base separately, then pair them in Local and submit to the shared queue. [Numbered delivery and full pending scope](releases/v0.3.0-dev.32.md). Existing resource, audio and video flows below remain available.

Historical dev.31: [runtime resource protection](RUNTIME_RESOURCES.en.md) / [中文](RUNTIME_RESOURCES.md). Review system resources in Tasks, inspect a saved stop and retry explicitly. Chat keeps partial text; text models require explicit loading again. [Numbered delivery/full pending scope](releases/v0.3.0-dev.31.md). The dev.30 video flow below remains available.

Historical dev.30: [old-LTX local video flow](LTX098_APP_FLOW.en.md) / [中文](LTX098_APP_FLOW.md), with [numbered delivery and complete same-release scope](releases/v0.3.0-dev.30.md). Sequential T5/Vulkan DiT/VAE/phone AVC connects independent settings, the shared queue and artifacts. Existing asset records stay immutable; users explicitly associate the new variant. Official-variant, numerical/quality/Android and complete Release gates remain open.

dev.29 historical checkpoint: [incremental local audio and playback](AUDIO_STREAMING.en.md) / [中文](AUDIO_STREAMING.md), with [numbered delivery and the full same-release scope](releases/v0.3.0-dev.29.md). Model-scoped opt-in streaming, bounded shared previews and verified full WAV publication. Trained Realtime/Android acceptance remains open; historical failures stay recorded.


Earlier dev.28: [LCM user assets through local generation](LCM_APP_FLOW.en.md). Select a source, prepare, explicitly associate and choose missing dependencies before generating. Pixel/quality/device gates remain open; drafts, preflight and recovery remain.

Internal dev.27 adds [output recovery, task filters and history management](TASK_RECOVERY.en.md): inspect recovered results/capacity and review exact terminal records before clearing. Models, media, drafts and active work remain; no automatic rerun.

[中文](USER_GUIDE.md) · [Documentation](README.md)

See the [draft → task → result → another generation workflow](TASK_WORKBENCH.en.md) for per-model persistence, parameter restoration, compatible references and recovery review.

## Installation and first run

Use ARM64 Android 9 or newer; 32-bit Android and x86 are not supported. Device memory and Android/vendor behavior affect model compatibility. Physical-device acceptance has not yet been executed.

Download the APK from the project Release and verify SHA256. Allow the installation source if requested and open LMA. No terminal, ROOT, LMA account, or cloud key is needed. On Android 13+, allow notifications when requested to see foreground work and its stop control.

Start with `m01`, Dolphin Qwen 0.5B, about 398 MB. Verify download, integrity check, loading, and one complete response before trying larger weights. Runtime RAM and Android installation space are additional requirements.

## Model library: select, download, load

Recommended preserves `m08 → m06 → m01`, including order, labels and publisher evidence. Lightweight / Advanced keep the original curated groups. All queries HF by keyword, `owner/model`, or repository URL, with download/like/update sorting. GGUF is the default; All HF formats discovers other repositories. Repository and file lists both paginate; select a quantization before downloading.

The dedicated Local tab collects downloaded built-in, HF and imported models, plus active/interrupted transfers. Its search is offline; load, pause/resume and delete there. Stop a running model before deleting. Typing outside Local switches to HF search; choosing a category resets the query. See [HF and local models](HF_MODELS.en.md).

Curated/local model details show format, path and hashes, plus evidence where checked. Online name/tag hints get a separate Uncensored · metadata label; ordinary models do not receive that label.

1. Tap **下载 / Download**. Transfers run serially; cards show progress and speed.
2. **暂停 / Pause** preserves partial bytes. **继续 / Resume** uses HTTP Range when supported; a full 200 response restarts the file.
3. A full progress bar is followed by verification. Only valid GGUF, length, and known publisher hashes become installed models.
4. **加载 / Load** starts the engine. The persistent runtime strip changes from loading to ready, and the API becomes available.
5. First-completion auto-load is enabled by default only when no model was previously selected; disable it in Settings if desired.
6. Switching models stops the old engine before starting another. Stop a running model before deleting its file. Deletion also removes transfer records, partial bytes, and rejected files.

**添加模型 / Add model** offers HF discovery, an HTTPS GGUF link with optional SHA256, or an Android file-picker import. Manual files never gain a verified uncensored label from their names. Check source, license, architecture and memory. A local hash without an expected publisher hash does not authenticate provenance.

All-format discovery is broader than phone execution. Only compatible single-file text GGUF candidates are downloadable; shards, projectors and unsuitable tasks explain disabled selection. Safetensors / ONNX / MLX sources are discoverable without conversion or a corresponding runtime.

Public models need no token. For gated/private models, accept terms on HF and save an authorized read token in Settings → Hugging Face access. It remains in private app preferences; only its configured state reaches the page. Authenticated requests use the official source, without forwarding tokens to mirrors/CDNs. Clearing is supported. Real-token gated access was not tested in this run.

Automatic source selection tries Hugging Face, then HF Mirror on connection/source failure. Fixed sources are available. Other custom hosts are not rewritten. A single-file limit of 12 GiB and a 64 MiB reserve apply. Interrupted imports restart copying from the beginning.

## Chat, cancellation, and history

After readiness, open **对话 / Chat**. The toolbar shows the current model and lets you select installed models. Send text, expand reasoning if provided, and copy code without Markdown wrappers.

Stopping a reply preserves received text. SQLite persistence happens roughly every 160ms; a crash can lose the final unsaved fragment. History supports selecting/deleting sessions; New chat starts another. Reopening the UI reads native state, without depending on a surviving WebView.

History uses at most 16 recent messages, selected as complete user/assistant pairs within a conservative character budget. Empty failed replies and their user turn are skipped. This is not exact tokenization: oversized current input or system prompts can still exceed engine context. Content plus reasoning is limited to 1 MiB per response.

## Local and LAN serving

A loaded model exposes `http://127.0.0.1:8080/v1` by default. Loopback is for clients on the same phone. Enable **允许局域网访问 / Allow LAN** to listen on all interfaces. Another device must use the phone's displayed IP, not that client's own `127.0.0.1`.

Copy the API key or connection example. Each installation creates a random key; switching models does not rotate it. LAN uses HTTP, without built-in TLS, public tunneling, or multiple-user permissions. See [API integration](API.en.md).

Export runtime logs for troubleshooting. Exports redact the active key and exclude the chat database; filenames and device runtime details may still appear.

## Background work, screen off, and boot restore

A native `specialUse` foreground service, visible notification, and CPU / Wi-Fi locks maintain background work. Open battery settings from Server and allow exemption if desired. Vendor ROMs may also require background activity, network, autostart, or recent-app protection; menu names vary.

Leaving the app does not intentionally stop generation. Force-stop, low memory, thermal management, vendor policies, and network loss can still interrupt it. Real screen-off endurance is untested. Streaming is not infinite: EOS, output limits, and cancellation end requests.

The notification's **停止服务 / Stop service** stops the model and current transfer. Reopen to resume or load again. Boot restore is off by default and only attempts a previously enabled model with an existing file. If Android blocks startup, reopen the app. First downloads and system settings are not silently bypassed.

## Per-model settings and application preferences

Open Model library → 本地 / Local → the downloaded model’s settings icon. Context, output limit, threads, temperature, reasoning and system prompt are stored separately by model ID. Choose a preset or type custom numbers. Above-limit values reset automatically: GGUF metadata bounds context, output is at most configured context minus one, threads use the available processor count and temperature supports 0–2. Input/history can reduce actual output capacity further. Unknown GGUF bounds are explicitly labeled with an application fallback of 8192. See [per-model settings](MODEL_SETTINGS.en.md).

Context, threads and reasoning changes reload the running model; stop an active reply before changing them. Generation parameters apply to the next in-app reply. Editing another model leaves the active profile alone. Legacy global preferences migrate to existing models; new models receive independent defaults. Global Settings retains source/token, startup, port and theme preferences.

| Setting | Default | Effect |
| --- | --- | --- |
| Threads | Up to 4 | More threads may increase heat without improving speed |
| Context | 2048 | Larger contexts generally require more RAM |
| Output limit | 512 | In-app default; external clients set their own |
| Temperature | 0.7 | Sampling randomness |
| Port | 8080 | 1024–65535; must be available |
| Reasoning | off | Passed to the engine; some models may ignore it |
| First-download auto-load | on | Only when no model was previously selected |
| Boot restore | off | Optional and subject to Android restrictions |
| Source | auto | HF, then mirror on failure |
| Theme | system | System / light / dark |

Edit or clear the system prompt freely. No extra keyword moderation is added. Saving completes only after its native acknowledgement. Other state updates do not erase unsaved settings or a rejected-send draft.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Installation fails | Check ARM64, Android 9+, and APK hash. A different signer conflicts with an installed package; uninstalling removes private data |
| Download fails / stalls | Try a fixed mirror; check storage, network, source link; pause/resume and inspect the native error |
| Hash mismatch | The file is rejected. Check the pinned source/revision and download again; do not bypass verification |
| Loading fails / insufficient RAM | Try `m01`, reduce context to 1024 / 512, close large apps, and inspect logs |
| Connection refused | Confirm readiness, port, LAN setting, same-network reachability, and absence of access-point client isolation |
| 401 / auth failure | Copy the key from this installation and use `Authorization: Bearer ...` |
| Background work stops | Check notification, battery, and vendor settings; record OS, power, model, and timing. Permanent survival is not guaranteed |
| Refusals / ineffective reasoning toggle | Confirm the exact variant, publisher evidence, and prompt. Publisher claims do not imply zero refusals; some models ignore reasoning settings |

Uninstalling deletes models and chats. Model migration and chat backup/import are not implemented; exported logs are not a full backup. Reports should include version, phone/Android, model ID/hash, parameters, reproduction steps, and sanitized logs.

For Sana, select `Sana mobile · Qwen3 + MNN` in All/search, choose the 13 matching graph/weight/tokenizer components, review the plan and separately confirm downloading. Local manages that model and its dimensions/CFG/input tokens/threads. This matched mobile text-to-image recipe does not automatically support original Sana, editing or LoRA. No assets are bundled or implicitly fetched. Compilation/host checks exist; phone output remains unverified. See the [Sana guide](MNN_SANA_ENGINE.en.md).


On development dev.21, open an installed SoulX model's local task, choose contiguous S1–S4 reference audio and actual transcripts, then enter target text. Plain text uses S1; multiple utterances use one `[S1] text` marker per line. Edit defaults independently under Local; task overrides affect only that request. See the [SoulX guide](SOULX_ENGINE.en.md) for all fourteen assets, formats/profiles/API and the still-missing complete verified public download candidate. Public v0.2.0 does not include this development feature.

## dev.22: separate source and runtime assets

[Full workflow and storage requirements](MODEL_PREPARATION.en.md): select the pinned source under All, explicitly download or folder-import it, then review preparation in Local. Retain the source and review approximately 6.20GB additional free space before starting. Manage progress/cancellation/explicit retry in Tasks. Derived files can be deleted independently and remain under Local after source deletion. Installation/upgrades/browsing initiate neither downloads nor preparation. Successful preparation does not establish current video-generation support; the Android flow remains untested.

## dev.23: associate runtime assets and choose remaining dependencies

After preparation, use Local → Runtime assets → Review association, check the target and missing components, then explicitly start the shared job. Twenty verified existing files are reused without another copy/download. Missing T5 remains paused and uninstalled until you choose download or folder import in the runtime model details. Prepared and runtime records have independent deletion; settings survive and generation-engine availability is separate. See the [complete workflow](MODEL_ASSEMBLY.en.md) and [numbered implemented/pending handoff](releases/v0.3.0-dev.23.md). Android, six old-LTX numerical failures and complete Release gates remain open.

## Community image and video models

Models → All now includes an offline Registered recipes source and independent content filters. The 44 additional checkpoint variants include 28 sourced NSFW entries. Source, license and exact supported architecture are shown before downloading; only the selected model and disclosed dependencies are obtained. Local retains the same labels for downloads and unfinished transfers. [Full guide](COMMUNITY_MODELS.en.md).

## v0.3.4 RF Shape / 部件几何

TripoSG / PartCrafter object / scene are optional matched FP32 ONNX recipes. No public complete matching download package is verified; explicit local export/import and compatible HF component selection reuse existing model management. 用户自主转换 / 导入，模型仍平级；PNG → 本机 CPU → 独立部件 GLB，独立参数、草稿、预检、队列、取消与导出均复用基座。[中文完整操作](RF_SHAPE.md) · [English workflow](RF_SHAPE.en.md)。Full checkpoint conversion and phone quality remain untested.
