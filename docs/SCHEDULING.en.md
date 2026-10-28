# Shared execution slot, text residency and task switching

[中文](SCHEDULING.md) · [Development](DEVELOPMENT.en.md) · [Task design](WORKFLOWS.en.md) · [API](API.en.md) · [Asset boundaries](ASSET_CONTROL_AUDIT.en.md)

Applies to **0.3.0-dev.10 / code 14, an internal checkpoint**. Resident text loading, in-app chat, synchronous text APIs and asynchronous generation use the same `ExecutionGate`. Every complete v0.3.0 model and physical-Android requirement remains applicable.

## User flow

1. Download/import your chosen models and load an installed text model in Local. The App can start and manage its library with no model installed.
2. Submit an installed model's generation task while text is streaming. The task waits for the local execution slot while the current reply continues.
3. At its turn, the foundation temporarily unloads idle text residency, confirms process exit, checks resources again and starts the selected task engine. The job retains its submitted model, adapters and effective settings.
4. While text is suspended, a chat or synchronous API request can wait for the same slot. At its turn, the previously selected text model loads. The UI distinguishes a waiting reply from active generation and retains cancellation.
5. An idle job queue restores a text model the user still wants running. Stopping text revokes restoration without stopping an independent task. Selecting another installed text model during a task queues the user's new selection.

This uses existing user assets. It neither selects new models, downloads missing components, replaces weights nor executes elsewhere. APK updates supply foundation code, engines and scheduling; users independently select, download and manage model assets.

## Ordering, identity and profiles

`JobStore` claims persistent asynchronous jobs in queue order. Claimed jobs, loading, chat and HTTP requests request the execution slot in **slot-request FIFO order**. Their combined order follows actual slot requests. Automatic restoration atomically reserves an idle slot only when no owner or waiter exists, so it cannot overtake requests or change a generation preparing for a reply.

An idle text process may remain resident. Actual chat/HTTP replies retain the slot through completion, cancellation or response-stream closure. Other engines reap the old process before starting. The foundation permits one large engine process, regardless of which signed native module implements a model.

Original text IDs, immutable `bundle_id` values, recommendations, tags and profiles remain intact. API requests normalize against the selected model/profile before waiting; waiting does not replace their target. Chat similarly freezes its request and history. With an in-app or synchronous text reply active or waiting, another interactive text request reports busy. Asynchronous jobs can still queue independently.

## Cancellation, stopping and child exit

| Action | Result |
| --- | --- |
| Cancel a waiting asynchronous job | Remove its ticket without starting an engine or stopping active text |
| Cancel waiting chat/API | Release its ticket; chat saves a stopped status; independent jobs continue |
| Stop text | Revoke pending loading/restoration and terminate that resident; independent jobs continue |
| Close API listener | Close connections and cancel waiting text requests; asynchronous jobs continue |
| Stop the whole service | Cancel text, terminate job workers and record interrupted jobs; retain weights, profiles and results |

Tickets and process generations isolate ownership. Late cleanup from an old response cannot release a new request. Listener shutdown and server-side connection timeouts interrupt the owning handler to wake waiters. A client's own timeout can occur before phone-side waiting ends; use asynchronous jobs for durable background results.

Shutdown first requests normal exit, then forces exit if needed, waiting up to three seconds for each step. If the OS has not reaped a worker, the slot reports `reaping` and retains model leases and temporary files. Actual exit releases ownership. Later operations wait instead of launching a second large engine. Resident text asset leases also remain until actual child exit.

Unexpected text exits retain bounded recovery of at most three retries, each scheduled through the same slot. Stopped, replaced or cancelled generations cannot restart.

## Resources and lifecycle

Submission checks known capacity against total memory with a reserve, component/profile constraints and output storage. Current text residency is reclaimable. After acquiring the slot and reaping the previous engine, execution rechecks available shared memory, low-memory and thermal state against the recipe budget. Unknown estimates still require explicit user consent; measured device resource profiles are unfinished.

The two-hour single-job guard starts after slot acquisition, old-engine cleanup and asset leases, covering execution rather than waiting. Text loading has a five-minute guard. Screen-off operation depends on the native foreground service and OS policy; this checkpoint adds no phone-endurance guarantee.

Asynchronous jobs persist requests, effective profiles, state, events and artifacts. Chat preserves SQLite history and received fragments. Interrupted jobs without checkpoints require explicit retry after process restart. Interrupted downloads remain paused until user resume.

## Implementation and evidence

`ExecutionGate`/`ProcessControl` own slot and exit boundaries; `EngineHost` owns residency/recovery; `LocalJobs`, `ChatRunner` and `ApiHost` share the slot. Native starts also check `nativeProcessLock` and actual child liveness. `/health.scheduler` and App `foundation.execution` expose ownership and waiting state.

`python tools/test_scheduler.py` verifies **43 host assertions** using production queue/chat/API code, real children and loopback HTTP, cancellation, deferred reaping, independent service stopping, admission and retained profiles. Framework/resource/media inspectors are explicit host ports. GGUF fixtures contain zero tensors; output is arbitrary test bytes or literal protocol text. No model inference or Android execution is established.

[Model waiting](media/development/27-scheduler-model-waiting.png) · [Chat waiting](media/development/28-scheduler-chat-waiting.png) · [Recording](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif) remain visibly labeled UI FIXTURE. Input artifacts, every selected pipeline and physical-device resources/quality/background/upgrades remain required in the same complete v0.3.0. No new Release is created.
