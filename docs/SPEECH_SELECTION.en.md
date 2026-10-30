# Local speech models and voice selection

[中文](SPEECH_SELECTION.md) · [English](SPEECH_SELECTION.en.md) · [Documentation](README.md) · [Delivery and complete pending scope](releases/v0.3.0-dev.33.md)

dev.33 adds the complete optional Nano 100M profile to All and derives voice names from the exact files a user downloads. The APK delivers foundation code and catalogue metadata only: no weights, preset voices, learned prompt codes or model voice table. Installation, browsing and upgrades never initiate model downloads.

## User flow

1. Open Models → All → Audio, or search HF. Recommended remains `m08 → m06 → m01`. HF discovery does not establish Android compatibility: format, architecture, components and device resources still matter.
2. Review the license, provenance, complete components and sizes. The new Nano identity `moss_nano_100m_onnx_catalogue_v1` has **11 files totaling 717,414,286 bytes**, including speech, tokenizer, codec and preset prompt data. Downloading requires an explicit selection of that bundle; other models are not fetched.
3. Manage transfers, pause/resume, imports, settings and deletion through Local. Existing matching components may be reused; App updates never silently replace user files. The earlier imported identity `moss_nano_100m_onnx_f52645c_ceff0d0`, its settings and old jobs remain independent of the fresh catalogue identity.
4. Once the relevant local file exists, settings and generation forms show its voice count/names. Choose `ID · name`, enter a numeric ID, or type an exact unique name. Oversized IDs fill back the lower of the actual and recipe ceiling. Missing names keep numeric editing; unreadable metadata explicitly falls back to unverified recipe bounds.
5. Enter text, review per-model parameters and device notices, and submit. The task stores a numeric voice ID and immutable parameter snapshot. Changes to other model settings do not modify queued jobs. The existing shared local queue produces WAV files for playback, export and task management.

| Profile | Voices in the pinned file | Boundary |
|---|---|---|
| Kokoro 82M | 54 names, IDs 0–53; **53 is em_santa** | Respect the actual file order. This recipe's English lexicon does not become multilingual when a different-language voice name is selected |
| Piper Lessac | One voice, ID 0; no names | Numeric display, no invented name |
| Matcha LJS | One voice, ID 0; no names | Numeric display, no invented name |
| MOSS Nano 100M | 18 voices, IDs 0–17, from local manifest `display_name` | Learned prompt codes are never copied into APK data or parameter snapshots; language, quality and phone resource acceptance remain open |
| Qwen3-TTS 0.6B Base | No new named-speaker selector | Existing reference conditioning remains; this is not CustomVoice/VoiceDesign. An output budget does not establish EOS or sentence completion; the historical short-text/long-output quality issue remains open |

Names are file presentation metadata, not additional claims about identity, quality or language support. All models remain peers with separate audio-task, engine/foundation and content tags.

## Foundation design

`LocalEngine.schema(bundle)` provides effective parameters through the shared engine interface. Text and LTX retain existing bounds; speech adapters add local metadata constraints. The UI and queue need no model-ID branches.

The ONNX reader seeks past graph/tensor fields and reads only `n_speakers`, `speaker_names` and `id2speaker`. It bounds field counts, string sizes and voice counts, validates UTF-8 and rejects inconsistent mappings. Viewing voices neither launches inference nor loads the whole model. Nano reads a bounded user-supplied manifest and exposes only display names/counts. A maximum of 32 name/count entries is cached, keyed by canonical path, size and modification time.

Numeric schema `choices` are suggestions, so other in-range numbers remain editable. Names are presentation; saved settings, API values and queued snapshots remain numeric. Duplicate/invalid suggestions, range and alignment are checked. Actual counts can only tighten recipe bounds. Missing or malformed data triggers no transfer or external execution fallback.

## Evidence and limits

Production Java checks cover malformed protobufs, bad/conflicting mappings, cache invalidation, editable numeric suggestions, clamping, isolated settings and old/new Nano coexistence. After full SHA verification, the same Java reader inspects three actual downloaded ONNX files and the Nano manifest with a **48 MiB JVM heap**; the largest ONNX is 325,560,556 bytes. This establishes **metadata parsing, not neural inference or Android memory use**.

[Public metadata checks](../verification/development/speech-voices.json) · [UI checks/media manifest](media/development/speech/manifest.json) · [MP4](media/development/speech/speech-ui.mp4) · [GIF](media/development/speech/speech-ui.gif). Recordings use production pages and an explicitly simulated bridge; download/install/queue states are fixtures. No real download or voice generation occurs. Historical trained audio keeps its original evidence scope and was not rerun this round.

| Optional audio catalogue — UI fixture | Local voice names — UI fixture |
|---|---|
| ![Audio catalogue](media/development/speech/01-audio-catalogue.png) | ![Kokoro file voice names](media/development/speech/02-kokoro-voices.png) |

| Nano settings — UI fixture | Frozen task — UI fixture |
|---|---|
| ![Nano task form](media/development/speech/03-nano-parameters.png) | ![Speech queue](media/development/speech/04-speech-queue.png) |

This remains an internal checkpoint. Every frozen target, actual output quality/resources, three loads per model, 15-minute screen-off, one-hour API and A1–A11/R01–R05 upgrade acceptance remain required for the complete v0.3.0. No physical phone is available; background endurance has not been accepted. All inference and media stages must run on the same no-ROOT Android phone, with no external inference fallback or ComfyUI canvas/user-node/plugin system.
