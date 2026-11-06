# DSH 1.4.76 client interoperability audit

[中文](DSH_CLIENT_AUDIT.md) · [Function protocol](DSH_TOOLS.en.md) · [Unload](MODEL_RUNTIME.en.md)

This supplemental audit targets the published **LMA v1.1.0 / code68**. Before the user reported another task using the phone, its installed APK hash was verified against the formal Release. Phone interaction then stopped. All additional checks run on native Windows, without a phone connection, DSH App startup, tool execution or a model.

## 1. Subject and method

The static APK came from the installed **DSH Android v1.4.76 / code327, `app.dsh.mobile`**. [The client lock](../tests/dsh-client-lock.json) pins its identity and runtime hash. The private APK, extracted third-party code and intermediate requests stay under ignored `build/dsh-client-verification/`; LMA does not redistribute them.

The test imports that client's real `@deepseek-ai/dsh-llm-pi-ai`, pi-ai Models, `@earendil-works/pi-ai` Chat Completions codec and OpenAI SDK. Owned synthetic histories traverse actual HTTP sockets and LMA production `LocalHttp`, `LocalApi`, `TextRequest`, `ChatProtocol`, `JsonSchema` and `ToolReply`. Explicit synthetic SSE replaces native model output, including three-byte reads, interleaved arguments, failures and truncation.

Tool plugins only register declarations. No file, web, shell, scheduled job, background job, subagent or tool handler runs. A platform-specific declaration passing protocol validation does not establish that its tool executes on Android. The concurrent case uses two independent client adapters; existing scheduler evidence separately covers the production execution slot and four child-request histories.

## 2. Coverage

| ID | Check | Scope |
| --- | --- | --- |
| D01 | Installed LMA version and APK match the stable release | Checked before phone use stopped; no reinstall |
| D02 | Real tool package names, descriptions and parameter schemas | Includes subagent/control, jobs, files, web, terminal, schedules and workflows; declaration registration only |
| D03 | Default `store:false`, `max_completion_tokens` and `stream_options` | Real request serialization and production LMA validation |
| D04 | Streamed tool calls, reasoning, usage and durable replay | Actual client tool events; no conversion into ordinary chat |
| D05 | `content:null`, `tool_calls`, `role:tool`, matching IDs | Full histories survive two successive tool-result rounds |
| D06 | Interleaving, reordered results, CJK/emoji and tool failure | Production response guard and actual client parser |
| D07 | Dynamic tool changes and long messages/histories | Crosses former 256 KiB / 128 messages / 64,000 character caps; model context remains a separate check |
| D08 | Two clients, capacity errors, output length and native failures | No actual DSH subagents or repeated phone benchmark |
| D09 | Client idle timeout and nondefault compatibility options | Explicit negative checks; not all configurations pass |

**79 supplemental checks passed**, including 25 tool packages, 49 declaration variants and 45 unique tool names. See [client-code.json](../verification/supplemental/v1.1.0/client-code.json) for exact results. These are supplemental program checks. Published release counts, APK/source assets, media and physical evidence retain their original identities.

## 3. Independent DSH timeout

The client defaults `streamIdleTimeoutMs` to **300,000 ms**. It waits for adapter content, tool or terminal events. Its OpenAI codec discards SSE comments, and its adapter does not translate a standalone `start` event into a Harness event. LMA's `: lma keepalive` maintains the connection but cannot reset this client timer.

The fixture reduces the client timer to 120 ms while sending comments every 20 ms and reproduces `TIMEOUT`. This is not a five-minute phone endurance check. LMA has not reinstated a generation deadline and does not fabricate text or reasoning to defeat the client timer.

For template prefill, strict-argument buffering or queue waits beyond the client threshold, increase `streamIdleTimeoutMs` in DSH's advanced provider configuration and account for its cancellation/retry behavior. This client's schema does not accept zero as unlimited. LMA retains real cancellation, full-queue 429, context overflow and resource errors. Adjusting a wait threshold does not disable tools, subagents or change agent mode.

## 4. Compatibility scope and outstanding acceptance

The audited baseline is a custom **OpenAI Chat Completions** provider with the existing API Key, `http://127.0.0.1:52187/v1` and the actual local model ID. DSH retains execution through its existing tool system.

Provider-specific wire extensions are separate capabilities. For example, nondefault `compat.requiresToolResultName:true` adds `role:tool.name`, which LMA v1.1.0 explicitly rejects with 400; the baseline default is false. OpenRouter `reasoning_details`, other vendors' `thinking` / `priority` extensions and Responses API are outside this function-tool contract. Such provider-specific switches are not prerequisites for disabling DSH features.

| ID | Remaining acceptance | State |
| --- | --- | --- |
| P01 | Android DSH App from declaration through real tool execution, result and continuation | Paused at the user's request while another task uses the phone; code interoperability does not establish this result |
| P02 | Actual DSH subagent scheduling, approvals, cancellation and long tasks | Existing program/selected-phone queue evidence remains; App experience needs separate acceptance |
| P03 | Arbitrary-model tool quality, multimodal input and long background endurance | No expanded claim; the text function route does not fetch images or replace separate media APIs |

The existing [21 m15 / OpenAI SDK phone checks](../verification/releases/v1.1.0/physical-tools.json) remain valid and explicitly record `dsh_app_tested:false`. Protocol acceptance and a model choosing the correct tools/arguments are separate outcomes.

## 5. Reproduction

Use a legitimately obtained, matching DSH APK. This test does not download it, use ADB or run models. Native JDK, Python, Node.js 22+ and the build guide's pinned `json-20250517.jar` are required.

```powershell
python tools/test_dsh_client.py --apk build/dsh-client-verification/dsh-installed.apk
```

Output is ignored `build/dsh-client-verification/client-results.json`, with production-source fingerprints and pinned client identity. The base production protocol checks remain `python tools/test_openai_tools.py`. Existing version-matched physical screenshots and recordings remain; no phone media was fabricated for this audit.
