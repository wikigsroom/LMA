# Native MOSS speech, dialogue, voice design and sound effects

[中文](OPENMOSS_ENGINE.md) · [Complete scope](MULTIMODAL_RELEASE_PLAN.en.md) · [Development evidence](DEVELOPMENT.en.md)

Internal checkpoint **0.3.0-dev.18 / code 22** extends the ARM64 CPU `openmoss_native` worker and production Java adapter to six equal-peer recipes. It links native graphs, tokenization, sampling and codecs; it invokes no Python, Termux, external inference or upstream HTTP server. **No full model or physical Android inference has been run.** This does not establish phone support. All frozen targets remain in the same complete v0.3.0; no new Release exists.

## Four added delay layouts

| ID / Recipe | Validated layout | Capability and input |
| --- | --- | --- |
| D18-01 `moss_tts_openmoss_cpu_v1` | MOSS-TTS: 32 codebooks, Qwen3-8B / hidden 4096 | Audio / TTS; text, voice instruction, language, optional single reference |
| D18-02 `moss_tts_v15_openmoss_cpu_v1` | MOSS-TTS-v1.5: 32 codebooks, Qwen3-8B / hidden 4096 | Audio / TTS; same input types, independent record/settings |
| D18-03 `moss_ttsd_openmoss_cpu_v1` | MOSS-TTSD-v1.0: 16 codebooks, Qwen3-8B / hidden 4096 | Audio / multi-speaker TTS; text needs `[S1]` and `[S2]`, paired references or none |
| D18-04 `moss_voicegen_openmoss_cpu_v1` | MOSS-VoiceGenerator: 16 codebooks, Qwen3-1.7B / hidden 2048 | Audio / voice design; required voice instruction, no reference control |

All four use the v1 codec and produce 24 kHz mono PCM16 WAV. Native checks cover GGUF architecture, codebooks, backbone layers/attention heads/width, 1025-row audio heads/embeddings, codec and BPE dependencies. TTS v1.0/v1.5 have identical geometry: **geometry cannot authenticate checkpoint provenance**. Users must check repository, pinned revision, hashes and matching conversion provenance. These layouts are incompatible with first-class Delay, Nano, Local and SoundEffect files.

The [publisher audit](../catalogue/evidence/openmoss-delay-publishers.json) records pinned config/processor/modeling/README revisions, hashes and sources. Only metadata/source files were read; no weights were downloaded and no remote Python ran. The native community implementation remains pinned below. v1.5 template/geometry compatibility is source-level assessment; full-weight execution and quality remain unverified.

In All/search, select matching converted files, explicitly choose the recipe and both backbone/extras files, inspect the manifest, then confirm downloading. Importing a complete self-provided bundle also works. Installation, upgrades, registration and browsing never start model transfers. After downloading, open that model in Local, edit its settings or task overrides, choose imported references, then submit the task. Models remain peers in the same list.

Each delay model has the original nine sampling fields plus `voiceInstruction` (1000 characters) and `language` (64); blank hints become the publisher template's `None`. VoiceGenerator requires an instruction. The input budget defaults to 1024 and caps at 2048 **actual formatted positions**; generation defaults to 375 steps, caps at 1500, and includes delay flush, so it is not an exact duration control. Numeric values clamp; oversized hints/template markers fail. Saved defaults belong to the model; task overrides do not alter saved settings or another model. No ignored TTSD duration-hint field is exposed.

References require 24 kHz mono PCM16 or finite normalized float32 WAV, 1–10 seconds, each at most 1 MiB, without automatic resampling. TTSD maps explicit role IDs to `[S1]`/`[S2]` even when the input array is reversed. A lone reference, duplicate or unsupported role fails before spawning. References encode individually; TTSD concatenates codes by codebook for its continuation prefix, then trims that prefix at sample level after decoding. This community path can differ at reference boundaries from concatenating WAVs and re-encoding them; voice consistency still needs acceptance.

The context guard runs on the **actual generation grid**, after all reference/prefix construction and before prefill. The build tool inserts one check into a generated copy of the pinned pipeline; the checkout stays pristine. Build receipts hash that copy and source notices disclose the modification. Exceeding the selected input budget or `prompt + steps + 8 > 4096` fails instead of allowing upstream warning-only shortening. Runtime receipts contain actual formatted positions, reference/prefix frames, sampler/codec timings and RTF; no measurements are invented without execution.

All components stay resident on CPU; large backbones and codecs may exceed Z20 resources. There is no Z20 success or speed claim. Shared queues, cancellation, leases, private hardlinks and child lifetimes are reused. Every inference stage stays on the same phone, with no off-device fallback.

## 1. Separate pipelines

| Recipe | Same-phone pipeline | Output | Task |
| --- | --- | --- | --- |
| `moss_local_v15_cpu_v1` | Text → embedded BPE → Qwen3-4B backbone → 12-channel per-frame Local Transformer → v2 codec; an optional reference WAV first passes through the native encoder | 48 kHz stereo PCM16 WAV | `speech.synthesize` |
| `moss_soundeffect_v2_cpu_v1` | Prompt / optional negative prompt → Qwen3-1.7B encoder → 30-block DiT / flow matching → DAC VAE decoding and crop | 48 kHz mono PCM16 WAV | `audio.generate` |

These layouts target **Local-Transformer-v1.5** and **SoundEffect-v2.0** separately. Older Local/SoundEffect, Realtime, plain text GGUFs, Nano and first-class Delay files are incompatible. There is no transcript continuation, multi-speaker selector or training UI. These routes cannot satisfy acceptance of all nine MOSS subtargets. Existing [Delay](MOSS_DELAY_ENGINE.en.md) and [Nano](MOSS_NANO_ENGINE.en.md) engines remain available.

## 2. Users select assets; App updates supply runtime code

Each bundle needs **two matching GGUFs from the same conversion**:

| Physical role | Contents | Bundled in APK? |
| --- | --- | --- |
| `backbone` | Matching Qwen3 backbone and BPE | No |
| Local `extras` | Audio embeddings, Local Transformer and v2 codec encoder/decoder | No |
| SoundEffect `extras` | DiT and DAC VAE decoder | No |

The `provides` declaration discloses embedded dependencies and creates tags without duplicate tokenizer/codec downloads. Local's conversion includes the reference encoder inside extras, so it cannot be omitted as a separate download; the user's reference WAV remains optional.

In All/search, open HF files, select the recipe and bind both components. Review fixed sources, revisions, licenses, sizes and reuse; register, then explicitly download. A compatible bundle folder can also be imported. After verification, Local manages and runs the bundle. Registration, browsing, App installation/upgrades and missing-asset tasks never download or replace models. This checkpoint adds no unreviewed pinned candidate weights.

Original filenames remain intact. Leased private hardlinks use `models/model.gguf` and `models/model.extras.gguf` for the native sidecar convention. Workspaces release after the actual child exits on completion, failure or cancellation. Parent death signals the child with `SIGKILL`; an interrupted task does not invent a resumable compute checkpoint.

## 3. Flat tags and independent parameters

Both models are peers tagged Audio, with separate `text_to_speech` / `text_to_audio`, engine, architecture, pipeline, CPU, GGUF, dependency and unmeasured-evidence tags. Recommended `m08 → m06 → m01` retains its content, order and labels. Uncensored remains a separate content tag, never inferred from an engine, import or audio capability.

Local → model settings saves that model's defaults. The task form edits only its immutable task snapshot. Editable presets clamp out-of-range values; Java and native enforce their own bounds.

| Parameter | Default | Editable bounds | Applies to |
| --- | --- | --- | --- |
| CPU threads | 4 | 1–32 | Both backbone and auxiliary CPU graphs |
| Seed | -1 | -1 or 0–2147483647 | Both; -1 resolves to a recorded actual seed |
| Formatted input limit | 512 | 1–2048 | Local, including wrapper/reference frames |
| Generation frame limit | 250 | 1–750 | Local, 80 ms per frame, at most 60 s |
| Continue/stop head temperature | 1 | 0–3 | Local; inert text top-p/top-k are omitted |
| Audio temperature | 1.7 | 0–3 | Local |
| Audio top-p / top-k | 0.8 / 25 | 0.01–1 / 1–1024 | Local |
| Audio repetition penalty | 1 | 1–2 | Local |
| Output seconds | 5 | 1–30 | SoundEffect |
| Denoising steps | 50 | 1–100 | SoundEffect |
| CFG / sigma shift | 4 / 5 | Each 1–10 | SoundEffect |

Local's formatted input + generation + 8 must fit both the training context and the App's 4096 ceiling. Oversized input fails instead of silent truncation. Each formatted SoundEffect prompt is limited to 512 BPE tokens; the wrapper rejects overflow instead of inheriting upstream truncation. Only SoundEffect offers a negative prompt. At CFG=1, a supplied negative prompt fails explicitly with a request to increase CFG or clear it, instead of being silently ignored.

Local references must be complete RIFF WAVs: **48 kHz stereo, PCM16 or finite normalized float32, 1–10 s, ≤4 MiB**. No implicit resampling occurs. Native encoding uses upstream loudness normalization, with reference codes limited to that task process. SoundEffect accepts no reference.

## 4. Resources, execution and API

CPU is the only backend here. Backbone and extras remain loaded together; staged unloading is not implemented. **SoundEffect denoises the full 30-second latent before cropping, so shorter output does not proportionally reduce DiT memory or sampling work.** LMA has no measured throughput, peak memory or quality figures; Z20 compatibility and real-time generation are unproven.

Before allocation, GGUF architecture, BPE, dimensions, codec version, sample rate/channels and required tensors are checked. Layout checks do not authenticate arbitrary custom checkpoints or prove quality. The two routes use distinct encoder widths, codecs and parameters.

Use authenticated `POST /v1/jobs` with the task above. Both reuse FIFO scheduling, process ownership, cancellation, input leases and artifact reads. No new `/v1/audio/speech` compatibility or external inference endpoint is claimed. SoundEffect progress comes from actual solver steps; Local reports stages without fabricated percentages. Receipts record actual seeds, model loading/encoding/sampling/decoding times, duration, RTF and stop boundaries. Desktop benchmark numbers are not phone results.

## 5. Pinned sources and build

The community [pwilkin/openmoss source](https://github.com/pwilkin/openmoss/tree/bfb1f465e0a86fb5a52bbf93e67ceba4b7d0b4e1) is pinned under Apache-2.0, with MIT llama.cpp `050ee92d04c2e1f639025786dea701c70e7d4204`. See the [source lock](../third_party/openmoss-source-lock.json) and [notices](../third_party/notices/openmoss-sources.json). This is not official OpenMOSS Android acceptance.

Model/codec licenses are independent of engine licenses. Conversion uses upstream offline tools; Android never runs conversion/download scripts. The APK links neither the upstream CLI/HTTP server nor its WAV implementation.

```powershell
python tools/fetch_openmoss.py
python tools/build_openmoss.py
python tools/collect_openmoss_notices.py
python tools/build_recipe_templates.py
python tools/test_openmoss.py
python tools/build.py
```

The native Windows build uses NDK r30, API 28, `armv8-a` and static C++, without virtualization. GPU/dynamic backends, OpenMP and CURL are disabled. Build guards inspect 16 KiB alignment and absence of networking, shell/exec and logcat imports. Android foreground service, memory and vendor power policies still require device testing.

## 6. Evidence and remaining work

459 scoped checks comprise 349 production-Java checks with 18 actual host child processes and 110 C++ assertions executing pinned upstream speech prompt and sound formatting/noise/sigma functions plus budget/WAV boundaries. They cover paired role mapping, instruction forwarding, failures and asset cleanup. WAVs are structural fixtures; no tensors, neural inference or Android execution run. See [verification](../verification/development/openmoss.json) and the [bilingual checkpoint notes](releases/v0.3.0-dev.18.md).

Production UI screenshots, recording and GIF use **UI FIXTURE** installed state and show no actual model output:

![Local-v1.5 parameters and reference](media/development/43-moss-local-parameters.png)

![SoundEffect-v2 parameters](media/development/45-moss-sound-parameters.png)

[Local components](media/development/42-moss-local-components.png) · [Sound components](media/development/44-moss-sound-components.png) · [Recording](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif)

[Optional stereo-reference form](media/development/46-moss-local-reference.png) · [Sound prompt form](media/development/47-moss-sound-prompt.png)

| ID | Implemented this turn | Evidence boundary |
| --- | --- | --- |
| D18-05 | Four delay recipes added to the existing worker | Compilation/packaging and host protocol; no full model execution |
| D18-06 | Paired reference mapping, voice instructions and model settings | Production Java, actual host children and UI fixtures |
| D18-07 | Actual generation-grid input/context guard | Pinned source build copy and native boundary checks |

| ID | Remaining in the same complete v0.3.0 |
| --- | --- |
| P18-01 | Pinned acceptance assets, fresh-input offline outputs, quality and resources for all six recipes |
| P18-02 | Old Local/SoundEffect, Realtime, SoulX, Stable Audio, old LTX and all other required adaptation/acceptance |
| P18-03 | Physical Android load/unload, cross-modal lifecycle, background/screen-off/API endurance, upgrades and A11 for all routes |
| P18-04 | Complete F-01–F-12, 01–14/16/17 and all frozen subtargets passing the shared gates before full v0.3.0 Release |

[TTSD paired-reference form](media/development/51-moss-ttsd-speakers.png) · [VoiceGenerator instruction](media/development/52-moss-voicegen-instruction.png) · [TTS components](media/development/48-moss_tts-components.png) · [v1.5 components](media/development/50-moss_tts_v15-components.png) · [TTS settings](media/development/49-moss-tts-parameters.png)
