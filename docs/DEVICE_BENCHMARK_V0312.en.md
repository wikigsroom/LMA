# v0.3.12 physical API integration and benchmarks

[中文](DEVICE_BENCHMARK_V0312.md) · [API usage](LOCAL_API_V0312.en.md) · [Release](releases/v0.3.12.md)

## Device and scope

The connected physical device reports **motorola edge plus / burton_vzw**, Android 12/API31, SM8250/Snapdragon 865 and approximately 11.4 GiB system-visible RAM. These are not X30, nubia Z20 or all-Android measurements. Native USB ADB only; no ROOT, emulator, Docker, WSL or off-device inference.

Final **v0.3.12/code62** APK SHA256: `67b20c2a548f7b253db18f938156f44e817fe20fc58332f8912314f40f756140`. The original signer, five installed models and saved parameters are preserved. No model weights were downloaded/copied. Owned cube imagery, text, uploads and test jobs are separate from personal data.

## Final-APK program and real SDK checks

| ID | Execution | Result and scope |
|---|---|---|
| P01 | Physical program checks | **24 passed**: native libraries, UI, SQLite, model management, API authentication/catalogue and short screen-off health |
| P02 | Idle performance with existing models | **8 passed**; snapshot p50 275.88 ms, p95 286.75 ms; maximum main-thread gap 27 ms, zero over 100 ms |
| P03 | OpenAI SDK 2.36.0 and native Go gateway → phone | **28 passed**, using the actual SDK |
| P04 | Real speech on final APK | Gateway-forwarded SDK WAV, 267,308 bytes, approximately 13.76 seconds total request time; matching artifact SHA |
| P05 | Real image on final APK | Direct SDK PNG, 128×128, one step, 27,116 bytes, approximately 23.08 seconds; decodable, quality unaccepted |
| P06 | Screen-off service | At least 60 seconds in program checks; a separate 43.234 seconds in SDK checks; short responsiveness, not endurance |

SDK checks cover list/detail/conditional catalogue, PNG/WAV, durable retries, Alice/Bob isolation, history filtering, Range/If-Range, upload bounds/offset conflict/completion, image-only 3D preflight, explicit cancellation, SSE and gateway restart bindings. Thirty USB-forwarded model-list calls had median **29.11 ms**, p95 **59.79 ms**, including client/transport overhead.

The gateway is the real native Go forwarding implementation; callers use explicit authentication fixtures. Separately, exact pinned upstream Sub2API source compiles and passes route-adapter checks. **Production Sub2API, databases, subscription balances, prices and billing were not deployed/tested.** No installed text/music models were available for phone inference in those two categories.

## Generation and the longer video

**No fixed generation execution deadline remains.** The former two-hour queue and five-minute text-loading ceilings are removed; text reads no longer stop at a fixed socket read timeout. Explicit cancellation, real resource failures and model output bounds remain. The phone's 120-second synchronous PNG/WAV wait and gateway HTTP budgets limit waiting, not admitted async execution; query the job or retry the original key.

The longer video uses existing Wan weights with explicit CPU execution: 128×128, 49 frames, 8 fps, four steps, CFG1, four threads. Both phone artifact metadata and FFprobe must show **more than five seconds**. No interpolation, repeated clip or slowed playback substitutes for generation. Final-APK measurements appear below.

| ID | Final-APK run | Result | Total time |
|---|---|---|---|
| V01 | Wan CPU,128×128,49frames,8fps,4steps,CFG1 | **Succeeded:6.125seconds,200,149bytes**;49frames in both phone metadata and FFprobe;Range/If-Range/SHA verified | **732.170s** |

Actual output:[original MP4](media/benchmarks/v0.3.12/wan-cpu-6s.mp4)/[GIF](media/benchmarks/v0.3.12/wan-cpu-6s.gif). The picture contains blurry colour blocks;**quality is unaccepted**. Twenty API checks passed;all30 post-generation screen-off health requests succeeded over60.465seconds. Battery samples ranged41.5–48.5°C;this is not long-run thermal stability.

| ID | Final-APK 3D diagnostic run | Result | Total time |
|---|---|---|---|
| V02 | TRELLIS.2 CPU,512/one step/guidance1/six threads/geometry only, owned cube input | **Failed:`empty_structure`, no GLB**; actual exit1, no completion event, specific error displayed | **886.846s** |

This uses minimum diagnostic sampling, not quality acceptance with the recommended12 steps/guidance7.5. The actual failure confirms an empty sparse structure; it does not establish whether sampling, guidance, input, seed or a model-computation discrepancy caused it. Suggestions are not verified remedies. Lost diagnostic details are repaired, and the failure is actionable, but **successful3D output is not claimed**. All17 API checks passed; after failure,30 health calls succeeded over60.560seconds with the screen off. Battery samples were44.7–49.7°C. The earlier cancelled Pixal3D attempt also remains incomplete. Normal-sampling GLB, textures and quality remain unaccepted.


## Earlier candidate APK: five-model measurements

These results retain earlier candidate SHA256 `403abc8a1ecd06a4ad88d4743398ebe13d5840e55926c7f3aaedcf4844bff62d`; they are not relabelled as final-APK reruns. Times include protocol checks/retries/polling, not pure kernel execution.

| ID | Model and parameters | Result | Total time |
|---|---|---|---|
| B01 | MeloTTS Chinese INT8, two threads | 44.1 kHz mono WAV, approximately 3.076 seconds, 271,404 bytes | 11.241 s |
| B02 | RealisticVision, 256×256, four steps, CFG4, four threads | 76,901-byte PNG; blurry orange block, quality unaccepted | 155.279 s |
| B03 | Wan CPU, 128×128, five frames, 8 fps, four steps, CFG1 | 23,077-byte MP4, 0.625 seconds/five frames; noisy colour blocks, **does not satisfy the new >5-second requirement** | 193.125 s |
| B04 | Pixal3D, 512, one step, guidance1, six threads, geometry only | Explicitly cancelled by the then 20-minute benchmark budget; no GLB, not an engine crash | 1,201.092 s |
| B05 | TRELLIS.2, same parameters | Old worker exited with a generic error; no GLB; exact cause not established by that message | 896.116 s |

Another candidate, `dd3f87fbcead42135485ea8143f9d39cbb876dac50e679ce94a373698eef9cd5`, produced a 6.125-second/194,549-byte video in720.271seconds; its one-step TRELLIS.2 reproduction failed with a generic error in847.916seconds. These keep their candidate identity and do not replace final-APK results above. Investigation found worker initialization discarded standard error, preventing the earlier drain from seeing actual exceptions. The final APK restores that channel and adds a physical check of the signed worker itself.

## Failure handling and limits

| ID | Failure | Handling | Limit |
|---|---|---|---|
| F01 | Synchronous HTTP 504 | Durable job ID; original-key replay/polling continues the same task, physically checked | A response timeout does not prove generation stopped |
| F02 | Fixed execution timeout | Queue/text-load/read ceilings removed; explicit cancellation retained | Android process reclaim and actual resource failures remain possible |
| F03 | Upload bounds/offset mismatch | Out-of-bounds 400; in-range wrong offset 409; committed offset unchanged, completion SHA checked | Errors are not swallowed as successful uploads |
| F04 | Empty 3D sparse structure | `empty_structure` diagnosis; recommend 12 steps, the model's guidance, a clear input and another seed | A one-step low-guidance probe does not establish normal-sampling quality |
| F05 | Allocation/model-family failure | Separate diagnosis, real exit code and failure retained; no dummy GLB or silent weight switch | Recognising a failure does not establish successful generation |
| F06 | Initial SDK upload interruption | The fixture's complete file at offset1 first exceeded bounds; corrected fixture checks 400 and 409 separately; all28 checks then passed | This was a test-fixture fix, not an invented App offset bug |
| F07 | Lost native 3D exception details | Restore stderr after worker initialization; retain actual exit and private exception metadata; physical signed-worker check passed | Raw detail is restricted to the phone owner; public jobs/gateway omit private paths |

The earlier candidate's precise 3D cause requires fresh worker evidence. Under-sampling is not presented as a confirmed cause without that evidence. No proxy geometry or result from another machine substitutes for phone inference.

After testing,4 owned failed/cancelled fixture jobs were privately backed up and removed using only IDs from these reports. Unrelated history, all5 installed models and saved parameters were checked unchanged. Successful outputs remain.

## Resources and evidence

Resource samples include system MemAvailable/CPU ticks, battery temperature and App PSS. **App PSS excludes native workers and is not model peak RAM.** An independent observation showed the video worker around 3.1 GiB RSS and battery47.2°C; this is not a high-frequency measured peak. The candidate 3D worker was once around600% CPU and2.8 GiB RSS.

Allowlisted records: [physical program](../verification/releases/v0.3.12/physical-device.json), [idle performance](../verification/releases/v0.3.12/ui-performance.json), [SDK and model benchmarks](../verification/releases/v0.3.12/physical-api.json). Actual pages: [GIF](media/device/v0.3.12/physical-walkthrough.gif) / [58-second recording](media/device/v0.3.12/physical-walkthrough.mp4). No API keys, serials, endpoints, personal jobs, private gateway state or lock credentials are published.

These results establish scoped API/file workflows. Image/video quality, all82 bundles, uninstalled text/music models, Z20 capacity and long screen-off endurance remain unaccepted.
