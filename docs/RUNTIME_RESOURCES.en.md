# Runtime resource protection

[中文](RUNTIME_RESOURCES.md) · [User guide](USER_GUIDE.en.md) · [Numbered delivery and full pending scope](releases/v0.3.0-dev.31.md)

dev.31 adds continuous resource observations to the shared execution slot. Generation, asset preparation/association, text loading, chat and the local API use the same mechanism. Users continue to select and manage every model; installation, resource review and retry never retrieve or replace model data automatically.

## User flow

1. Select an installed model in Local, edit its own settings, review preflight and explicitly submit a task.
2. Open Tasks. During execution, review minimum system-available RAM, minimum free storage and maximum system thermal status. Queue time is excluded from runtime observations.
3. Severe thermal status, OS low memory or storage below the reserve stops the current execution. Generation becomes failed and incomplete files are not successful artifacts. Chat preserves received text and displays the cause.
4. After freeing resources, explicitly retry to create a new task while preserving the original record, or edit and generate again. Text requires explicit loading again; a resource stop disables automatic recovery.
5. Task details retain the bounded report. Successful artifacts preserve the same finished report in provenance. Saved task reports survive reopening the App.

The recent-stop banner lasts for the current App process lifetime, including service restarts; it does not survive process termination. Chat/API slot reports and the last-stop summary are memory-only, not a persistent diagnostic history. Terminal generation, preparation and association reports are stored with tasks. Observations are not written on every sample; abrupt process termination can leave an interrupted task without a resource report. Protection does not change model files, per-model defaults or immutable requests.

## Policy

| Signal | Stop condition | Source and limits |
|---|---|---|
| System thermal status | Level ≥ 3, severe | Public PowerManager API on Android 10+; a status level, not degrees Celsius |
| System low memory | `MemoryInfo.lowMemory=true` | OS signal; loaded model RAM is not charged again against the entire admission estimate |
| Available storage | App volume < 64 MiB | Runtime floor, independent of the complete output-space estimate at admission |
| Observation interval | Approximately every 2 seconds during execution | Scheduling and system restrictions can delay observations; no real-time guarantee |
| Unavailable values | Count failures without invented measurements | Android 9 thermal status stays unknown; no ROOT, hidden API or desktop substitution |

Reports contain bounded counts, start/end times, system minima, maximum thermal status and the first stop cause. They have no growing sample history. System-available RAM does not establish model peak memory, power consumption, speed or screen-off endurance.

## Foundation and API

`DeviceResourceProbe` reads public Android signals. `ExecutionGate` scopes observations to the current owner and binds its actual native child. OS reads happen outside the lock; both owner identity and monitor generation are checked again before applying a result. Old observations cannot stop a later task. Stop delivery and actual child exit retain slot ownership before the next operation starts.

Sequential engines bind each child. A stage launched across a resource stop is rejected and reaped. The resource cause takes precedence over generic child-exit errors. Token-checked task completion atomically saves the report and terminal state without modifying the request. Successful generation freezes observations before publishing artifacts, preventing late observations from contradicting committed success.

Newly loaded and reused text processes also bind to the current slot. A resource stop disables automatic recovery before terminating that process. Chat preserves partial text. API streams check the owner before and after reads, so resource interruption cannot become a successful EOF. An HTTP/SSE response already in progress may end with a connection error; clients must check its completion marker before accepting a complete result.

Authenticated `GET /health` exposes `scheduler`, including active `runtimeResources`, `resourceMonitoringEnabled` and `lastResourceStop`. The App exposes the same scheduler under `foundation.execution`. Task details return persisted `runtimeResources`; successful artifact `provenance` contains the same summary. The report explicitly declares `scope=shared_system_availability_not_model_peak_memory`.

Idle resident models and waiting tickets do not receive execution observations. Service shutdown closes the observer. OS termination, OEM background restrictions or kernel process termination can precede this mechanism; existing task reconciliation still applies. This feature does not establish Android screen-off acceptance.

## Validation and media

Production queue/text/HTTP host controls use real child processes and exercise stop, retry, partial chat, API failure, stale observations and ownership races. Controlled OS inputs and literal protocol outputs provide business regression evidence, **not Android measurements or model inference acceptance**. The trained old-LTX host chain is checked separately; original numerical failures and model quality/phone gates remain open.

[Running](media/development/resources/01-running.png) · [Stopped details](media/development/resources/02-stopped-detail.png) · [Explicit retry](media/development/resources/03-explicit-retry.png) · [Recording](media/development/resources/resources-ui.mp4) · [GIF](media/development/resources/resources-ui.gif) · [Media provenance](media/development/resources/manifest.json)

![Desktop UI fixture: saved stop details, not Android measurement](media/development/resources/02-stopped-detail.png)

Every frozen target remains required in the same v0.3.0. See the [complete numbered scope](releases/v0.3.0-dev.31.md).
