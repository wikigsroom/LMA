# SoulX-Podcast local audio engine

[中文](SOULX_ENGINE.md) · [Development status](DEVELOPMENT.en.md) · [Numbered handoff](releases/v0.3.0-dev.21.md) · [Local inputs](LOCAL_INPUTS.en.md)

## 1. Delivery boundary

0.3.0-dev.21 integrates a complete native SoulX worker with the existing model bundles, independent profiles, input library, shared queue, authenticated API and artifacts. `soulx_native / soulx_podcast_cpu_v1 / cpu` resolves to compiled App code. No weights, vocabularies, voices, example audio or learned source constants enter the APK. SoulX remains a peer in the flat model pool, tagged audio / TTS / multiple speakers / reference transcripts, independently of format, backend, dependencies, installation and evidence.

**This does not complete v0.3.0 or accept target13.** The production native worker executes complete trained models on the developer host. Physical Android, intelligibility, voice similarity, Z20 resources/performance and background endurance remain untested. Synthetic reference PCM has no valid speech/transcript relationship: the test text probes the protocol and is not a voice-quality demonstration.

**A verified complete public download candidate is still missing.** The recipe supports explicit component selection/download/import/management, but no checked HF entry currently supplies every converted component. Original `flow.pt / hift.pt` cannot run as these graphs. Developer conversion tools are not ordinary-user installation prerequisites and do not complete target13's search/download/use flow. Matching complete bundles can be imported; final delivery still needs reviewable user asset sources and download acceptance.

## 2. Fourteen user assets

The worker uses these execution names. Selected HF files may have other source paths: the engine creates private filename-preserving hardlinks to leased, verified content. It never duplicates multi-gigabyte weights for execution or accepts executable code from model data.

| Role | Execution file | Format |
| --- | --- | --- |
| `language` | `language.gguf` | Complete SoulX Qwen3 GGUF, including its tokenizer |
| `s3` | `reference-s3.onnx` | S3v2 graph |
| `s3_data` | `reference-s3.onnx.data` | Matching external weights |
| `speaker` | `reference-speaker.onnx` | CAMPPlus graph |
| `speaker_data` | `reference-speaker.onnx.data` | Matching external weights |
| `flow_encoder` | `flow-encoder.onnx` | Flow encoder graph |
| `flow_encoder_data` | `flow-encoder.onnx.data` | Matching external weights |
| `flow_estimator` | `flow-estimator.onnx` | Flow estimator graph |
| `flow_estimator_data` | `flow-estimator.onnx.data` | Matching external weights |
| `hift_f0` | `hift-f0.onnx` | F0 graph |
| `hift_f0_data` | `hift-f0.onnx.data` | Matching external weights |
| `hift_spectrum` | `hift-spectrum.onnx` | Spectrum graph |
| `hift_spectrum_data` | `hift-spectrum.onnx.data` | Matching external weights |
| `hift_source` | `hift-source.f32` | Ten learned float32 source-merge coefficients, exactly40 bytes |

Those40 bytes are weights too. They are never substituted with constants or embedded in the APK. HF identifies `.f32` as a binary data component. Every asset has a pinned source/size/integrity identity. An ONNX graph may reference only its adjacent same-name `.data`; graph protobufs are bounded at128MiB. Arbitrary Qwen/ONNX files and original PyTorch checkpoints do not automatically match this contract.

Users still choose All/search → recipe → individual components → complete plan → explicit download, or import a manifest/folder. Local provides independent pause/resume/delete/settings/updates. Declaration, browsing, missing components and App upgrades initiate no model transfer. Interrupted downloads restore paused; Recommended remains m08 → m06 → m01.

## 3. Inputs and form

Choose1–4 reference WAVs:24kHz mono, PCM16 or float32,1–15seconds, at most1,536,000bytes, finite normalized samples in[-1,1]. Other formats require an explicit user conversion; the worker does not silently resample/downmix. S1 is required; S2–S4 must be contiguous. Each selected recording requires **the words actually spoken in it**. Audio-only, text-only, missing-speaker and dangling transcript selections fail. Compatible imported media and previous WAV results share the picker.

Plain target text uses S1. For multiple utterances, use one marker per line:

```text
[S1] The first speaker's opening.
[S2] 第二位说话人在本地回答。
[S1] The first speaker continues.
```

At most64 utterances and4000 UTF-16 units of target text; each reference transcript is bounded at4000. Internal SoulX control markers are rejected. Audio identity and transcripts are frozen with the job: later profile/form edits do not change queued requests. Library refresh retains unsaved paired selections/text. Deselecting optional audio disables its transcript field.

## 4. Parameters and execution

| Parameter | Default / range | Behavior |
| --- | --- | --- |
| context |4096 /256–8192 | Application guard; actual GGUF limits still apply |
| maxNewTokens / minNewTokens |512 /8; maxima3000 /2999 | Output≤context−64; minimum<output maximum |
| temperature / useRas |0.6 /true | Temperature0 forces effective RAS=false with a recorded adjustment |
| repetitionPenalty / topK / topP |1.25 /100 /0.9 | Native processors; RAS may restore raw logits, including EOS |
| rasWindow / rasTau |25 /0.2 |1–256 /0.0001–1 |
| maxHistoryTurns / historyTurns / textHistoryTurns |10 /2 /2 |5–64 /1–8 /0–16; complete history≤maxHistoryTurns−4, reserving four references |
| historyThreshold |4096 /128–8192 |≤context; required reference/history/target/output overflow fails explicitly |
| steps / cfg |15 /0.7 |1–100 Flow Euler steps; CFG0–10 |
| seed / threads |−1 /4 |−1 becomes a recorded concrete seed;1–32 CPU threads |
| pauseMs / maxOutputSeconds |200 /120 |0–2000ms between turns;1–960seconds including pauses |

Editable presets clamp in UI/Java; the native worker rejects out-of-range snapshots again. Most maxima are application/export guards, not device capacity guarantees. Each semantic code produces40ms, with at most24000 total codes. Duration is checked before synthesis and after writing. Actual speech EOS, output caps and history-only delimiters are recorded separately; generic Qwen EOS is never used for speech stopping.

One App-owned child runs reference DSP/S3/CAMPPlus → complete Qwen3 semantic generation → language-model unload → per-turn Flow encoding/Euler/HiFT F0/spectrum/DSP →24kHz mono PCM16 WAV. ORT permits only one model session at a time; compact features/codes remain between stages, rather than retaining all model weights. llama uses the adjacent packaged baseline CPU backend; ORT uses the existing CPU runtime. No user code/plugins or off-device inference stages are added.

Only a private temporary WAV exists until successful output commit. Java owns the child, leases and workspace; errors/cancellation terminate/reap the process before cleanup. Android source routes SIGTERM to ORT termination/llama abort callbacks, with shared forced termination as fallback. Host checks actually terminate two production stages, **without establishing Android cooperative cancellation or screen-off behavior**. Receipts record concrete seeds, per-turn codes/EOS, graph/model lifetimes, durations and RTF; host timings are not Z20 performance.

## 5. Shared authenticated API

Obtain artifact IDs through App import or [local input uploads](LOCAL_INPUTS.en.md), then use the existing Bearer-authenticated `POST /v1/jobs` and optional idempotency key:

```json
{
  "bundleId": "YOUR_INSTALLED_SOULX_BUNDLE_ID",
  "type": "speech.synthesize",
  "input": {
    "prompt": "[S1] The first speaker.\n[S2] 第二位说话人。",
    "artifacts": [
      {"role": "reference_s1", "artifactId": "YOUR_FIRST_ARTIFACT_ID"},
      {"role": "reference_s2", "artifactId": "YOUR_SECOND_ARTIFACT_ID"}
    ],
    "transcripts": {
      "reference_s1": "The words actually spoken in reference one.",
      "reference_s2": "第二段参考音频实际说出的原文。"
    }
  },
  "parameters": {"maxNewTokens": 160, "steps": 15},
  "allowUnmeasured": true
}
```

202 means queued. Follow job/events, then preview/Range-read/export the resulting artifact. Arbitrary paths, URLs, client receipts and external execution addresses are rejected. Omitted parameters use the model's saved profile and freeze effective values for this job; request overrides do not save defaults. No new OpenAI speech-endpoint compatibility is claimed.

## 6. Reproduction and outstanding gates

Explicit developer asset preparation follows the [reference/acoustic](SOULX_REFERENCE.en.md) and [language](SOULX_LANGUAGE.en.md) guides. These build/check commands do not download models:

```powershell
python tools/build_soulx.py
python tools/build_soulx.py --android
python tools/collect_soulx_notices.py
python tools/test_soulx.py
python tools/test_soulx_worker_trained.py
python tools/build.py
python tools/verify_package.py
```

222 scoped assertions cover146 Java/76 C++ checks and6 actual protocol children; their WAVs are structural fixtures.95 trained-worker assertions execute14 real model assets in4 production children: fresh two-speaker text, four speakers with explicit caps, and two forced host terminations during language/acoustic stages. Complete trained outputs remain ignored developer files, outside Git/APK/Release, without voice-quality claims.

The ARM64 worker is472,400bytes, SHA256 `424d609440603a4c93238d5130b316e384d0ead58613a53e5fdbe3608b4963bf`, API28/16KiB aligned, reusing five existing runtime libraries. Four SoulX source locks plus the trained asset lock retain exact identities. Full Apache/MIT/KISS FFT/Snake/ORT dependency notices ship in the App.

Target13 still needs a verified user download candidate, actual speech-reference/quality/speaker evaluation, and physical Android resources/cancellation/load-unload/background/upgrade evidence. All frozen01–14/16/17 targets, nine MOSS variants, both LoRA families and old LTX retain the same complete v0.3.0 release gates.


Shared-runtime verification permits reuse only when names, sizes, SHA256 and Android API requirements match exactly, and rejects workers aliasing base libraries. `python tools/test_native_payload.py` passes 10 regression checks; `verify_package.py` verifies the final 27-file APK.
