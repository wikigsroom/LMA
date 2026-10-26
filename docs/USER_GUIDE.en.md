# LMA user guide

[中文](USER_GUIDE.md) · [Documentation](README.md)

## Installation and first run

Use ARM64 Android 9 or newer; 32-bit Android and x86 are not supported. Device memory and Android/vendor behavior affect model compatibility. Physical-device acceptance has not yet been executed.

Download the APK from the project Release and verify SHA256. Allow the installation source if requested and open LMA. No terminal, ROOT, LMA account, or cloud key is needed. On Android 13+, allow notifications when requested to see foreground work and its stop control.

Start with `m01`, Dolphin Qwen 0.5B, about 398 MB. Verify download, integrity check, loading, and one complete response before trying larger weights. Runtime RAM and Android installation space are additional requirements.

## Model library: select, download, load

The recommended list starts with `m08`, `m06`, and `m01`. Filters cover lightweight, advanced, installed, and all entries. Search names, families, or tags. Tap a model name to inspect the format, filename, hashes, uncensoring method, and pinned author evidence. The author-card link and GGUF source link are separate.

1. Tap **下载 / Download**. Transfers run serially; cards show progress and speed.
2. **暂停 / Pause** preserves partial bytes. **继续 / Resume** uses HTTP Range when supported; a full 200 response restarts the file.
3. A full progress bar is followed by verification. Only valid GGUF, length, and known publisher hashes become installed models.
4. **加载 / Load** starts the engine. The persistent runtime strip changes from loading to ready, and the API becomes available.
5. First-completion auto-load is enabled by default only when no model was previously selected; disable it in Settings if desired.
6. Switching models stops the old engine before starting another. Stop a running model before deleting its file. Deletion also removes transfer records, partial bytes, and rejected files.

**添加模型 / Add model** accepts an HTTPS GGUF link with optional SHA256 or an Android file-picker import. Custom files display **属性未核对 / Unverified attribute**. Check source, uncensored variant, license, architecture, and memory yourself. A locally calculated hash without an expected publisher hash does not authenticate provenance.

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

## Settings and starting values

| Setting | Default | Effect |
| --- | --- | --- |
| Threads | 4 | More threads may increase heat without improving speed |
| Context | 2048 | Larger contexts generally require more RAM |
| Output limit | 512 | In-app default; external clients set their own |
| Temperature | 0.7 | Sampling randomness |
| Port | 8080 | 1024–65535; must be available |
| Reasoning | off | Passed to the engine; some models may ignore it |
| First-download auto-load | on | Only when no model was previously selected |
| Boot restore | off | Optional and subject to Android restrictions |
| Source | auto | HF, then mirror on failure |
| Theme | system | System / light / dark |

Edit or clear the system prompt freely. No extra keyword moderation is added. Runtime changes reload the model; save completes only after its native acknowledgement. Other state updates do not erase unsaved settings or a rejected-send draft.

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
