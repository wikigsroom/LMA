# Incremental local audio and playback

[中文](AUDIO_STREAMING.md) · [Native layouts](MOSS_RQ_ENGINE.en.md) · [Delivery and full pending scope](releases/v0.3.0-dev.29.md)

Internal **0.3.0-dev.29 / code 33** connects MOSS Realtime frame decoding to production tasks, API access and playback. A request still contains the complete text. Incremental text sessions and real-time throughput are not implemented promises. Full trained speech quality, phone resources and Android execution remain unaccepted.

## 1. User flow

1. In All/search, select the matching `moss_realtime_rq_cpu_v1` recipe. Explicitly select/download/import its backbone, 24 kHz codec and BPE tokenizer GGUFs. Installation, upgrades and browsing never retrieve model data.
2. Open Local → model details → model settings and enable **流式试听 / streaming preview**. It defaults to off and is saved per model. Already queued requests retain their immutable settings. Other recipes, including old Local, do not inherit the option.
3. Enter the complete text, optionally choose an imported 1–10-second 24 kHz mono reference WAV, and explicitly submit. The model's generation budget still applies, with at most 750 code steps including a stop step.
4. Once the first block arrives, open Tasks → incremental playback → Play. Playback starts from the beginning. Opening the panel never autoplays. Stop, closing the panel or backgrounding releases page audio resources while the foreground-service job continues until completion, cancellation, failure or service interruption.
5. A successful job publishes a complete PCM16 WAV through the existing result preview/export/provenance/reuse flow. Partial previews never become successful results.

| Model setting | Playback before the final file (synthetic protocol data) |
|---|---|
| ![Opt-in setting](media/development/audio/01-model-setting.png) | ![Incremental playback](media/development/audio/02-incremental-playback.png) |

[Recording](media/development/audio/audio-ui.mp4) · [GIF](media/development/audio/audio-ui.gif) · [Manifest](media/development/audio/manifest.json). These are production pages with a labelled simulated bridge and synthetic PCM; they demonstrate neither model inference nor Android execution.

## 2. Same-phone pipeline

```text
User-selected assets and per-model settings
  → shared task queue, execution gate and asset/input leases
  → App-owned Android native Realtime child
  → each non-EOS code frame → one stateful codec → PCM16 block
  → private preview cache → local page / authenticated client
  → final WAV format, sample count and PCM SHA256 agree with the stream
  → existing artifact commit → successful full result
```

The implementation uses the stateful codec at pinned `mudler/moss-tts.cpp` revision `ee722b8e9205ee9b1b1c398a4e87e4e393e9be41`. Reviewed generated build copies expose its methods without modifying the upstream checkout or loading a second codec. Each non-stop frame supplies 16 codes and decodes to 1,920 mono samples: **80 ms of audio content**, irrespective of compute time. Per-stage KV windows remain bounded; the decoder does not recompute the entire prefix. No remote execution or slicing a completed WAV is involved.

Whole-file mode keeps upstream whole-clip RMS adjustment, bounded to ±3 dB. Streaming mode uses unity gain for both blocks and the final file, with identical finite checks, clipping and PCM16 quantization. It cannot apply a later gain to already heard samples. Output levels can therefore differ between modes; streaming is an explicit setting.

## 3. Shared protocol, storage and failures

`lma.audio-stream/1` provides a bounded foundation transport. Its current production provider is MOSS Realtime. The generic transport allows 8–48 kHz, one or two channels, PCM16, at most 120 seconds / 24 MiB / 4,096 chunks, and 4,800 sample frames per chunk. Those transport bounds do not establish support for additional models. Realtime narrows them to 24 kHz mono, 1,920 frames per chunk and the selected generation budget.

Sequence numbers and sample offsets start at zero and remain contiguous. Changed formats, oversized/truncated/noncanonical payloads, duplicate/late chunks and absent final boundaries fail the task. After a normal child exit, the final WAV format, sample count and PCM SHA256 must agree before artifact publication. PCM never enters job JSON, job events or logs.

Private storage retains at most **four** previews with one active writer. Starting another preview evicts the oldest terminal entry. App startup removes stale previews without restarting inference, and Android may also clear cache data. Durable results, models, downloads and settings remain independent. Failed/cancelled/interrupted previews are partial and have no full-result ID. Stopping playback never cancels the model. If the cache is unavailable, users can disable streaming in model settings and generate a whole file.

## 4. API

Use the existing Bearer key and same-phone queue. Preflight if desired, then submit to `POST /v1/jobs`:

```json
{
  "bundleId": "YOUR_INSTALLED_REALTIME_BUNDLE",
  "type": "speech.synthesize",
  "input": {"prompt": "Complete user-provided text"},
  "parameters": {"streamAudio": true, "maxNewTokens": 375},
  "allowUnmeasured": true
}
```

`allowUnmeasured` explicitly accepts the request's unmeasured resource condition; it does not bypass component or parameter validation.

| Request | Behavior |
|---|---|
| `GET /v1/jobs/{id}/audio?after=0` | Format, state, total `nextSequence`, sample-frame count, full artifact ID, and up to 32 descriptors; `cursor` is the page end |
| `GET /v1/jobs/{id}/audio/{sequence}` | Immutable interleaved little-endian PCM16 bytes, `application/octet-stream`, `X-Audio-Format: pcm_s16le` |
| `HEAD` on either path | Corresponding status/length without a body |

Read chunks in sequence and continue with `cursor`. While `state=streaming`, a page can contain no new chunks. Only `succeeded` with `artifactId` identifies a separately committed complete WAV; other terminal states describe partial audio. Missing/expired previews are unavailable resources; invalid cursors return 400. Preview access never downloads a model. The page uses private same-origin routes; the public API retains its browser-Origin rejection. There is no new WebSocket, remote inference endpoint or arbitrary execution hook.

## 5. Evidence boundaries

- Production `NativeWorker`, storage and authenticated sockets: eight actual host children, six observed before the final WAV existed, with order/rate/missing or duplicate end/late data/content mismatch/cancellation controls.
- Production `LocalJobs`: success, failure, cancellation and service interruption; only committed full results acquire artifact IDs, without audio payloads in durable job records.
- Real GGML codec graphs: the pinned **untrained tiny stereo fixture**, full/partial codebooks and ten frames across sliding windows. Stream-versus-batch maximum error is about `5.59e-8` against `1e-3`. This is not quality verification of the complete trained 16-of-32-codebook 24 kHz codec.
- Production pages: model-scoped settings, no autoplay, real Web Audio scheduling, ordered playback, stop/close cleanup, expired cache and invalid order handling, without actual model retrieval or inference.

ARM64 compilation, the original signing identity, current regressions and media have separate receipts. Complete trained Realtime speech, first-audio latency, throughput/RTF, memory, phone background operation and all frozen release targets remain required. This checkpoint is not a complete v0.3.0 release.
