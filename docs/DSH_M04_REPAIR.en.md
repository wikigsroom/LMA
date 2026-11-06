# m04 tool-template and DSH repair · v1.2.1

[中文](DSH_M04_REPAIR.md) · [Protocol](DSH_TOOLS.en.md) · [Pre-repair assessment](DSH_M04_TOOL_TEMPLATE_ASSESSMENT_20261106.en.md) · [Release](releases/v1.2.1.md)

## 1. What changed

The reported template defect is confirmed. The pinned GGUF embeds a 291-character ordinary-message template. Supplying `tools` and enabling `--jinja` cannot make that template render function definitions. Unchanged prompt-token counts therefore identified an input defect, without establishing that the weights lack tool training.

v1.2.1/code70 repairs loading, effective-template verification, named choice, native parsing and history. It preserves the installed m04 weights, saved 131072 context, 131071 output ceiling, eight threads and sampling settings. DSH keeps its full tool set and executes tools itself. Template/protocol correctness and reliable 1B-agent behavior are assessed separately.

## 2. Two observed defects

1. **Outdated embedded metadata.** The pinned upstream tokenizer includes tools, assistant calls and results; the GGUF template omits them. A reviewed profile binds the repair to actual file identity rather than guessing from a Dolphin/Llama name.
2. **An XML-only replacement was insufficient.** An initial physical candidate rendered tools, but m04 produced bare function JSON, which the XML parser treated as text. Forced requests could exhaust their output budget waiting for the XML structure. The final derived profile keeps upstream definitions/history, explicitly describes structured function JSON and uses the pinned native autoparser. No command-text extraction or fabricated execution is involved.

Ordinary conversations without tools/history retain the exact original rendering. Historical assistant calls and `<tool_response>` still render when current definitions are omitted. Parallel result blocks are ordered by call ID in the private native copy; public content and IDs remain intact.

## 3. Identity and provenance

| Item | Pinned identity |
| --- | --- |
| Repository | `bartowski/Dolphin3.0-Llama3.2-1B-GGUF` |
| Revision | `617f94be9dfb802a3fa0ec64b12d7d085482a308` |
| File | `Dolphin3.0-Llama3.2-1B-Q4_K_M.gguf`, 807697440 bytes |
| Weight SHA256 | `7ed39ee0638e18d3e47bf12e60e917c792ca5332606a72bd1882ab1f62a13a7a` |
| Embedded template SHA256 | `58c1a1f04baa7adaeaba1f90267c3d57d9396f0c1f0129bdde9e76d3c6784af7` |
| Upstream tokenizer revision | `e753b6ebd7adf87036eb6a3e6de68acca5850e2f` |
| Upstream template SHA256 | `0067535d4b21c9be3ab1da0d2b99aa71a158711a485da6c5c8a30a6d2227363f` |
| Profile | `dolphin3-chatml-tools-v1`, with derivations disclosed |
| Effective template SHA256 | `59cae1fe1315e4b081877ebdfdec8d2ac433ba402f24ae68d8ba8a76928d7705` |
| llama.cpp | `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` |

[Manifest](../app/src/main/assets/chat-template-profiles.json) · [Template](../app/src/main/assets/chat-templates/dolphin3-chatml-tools-v1.jinja) · [Pinned upstream configuration](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-1B/blob/e753b6ebd7adf87036eb6a3e6de68acca5850e2f/tokenizer_config.json). Fixed upstream configuration was retrieved through an HF mirror and content-checked; no weights were downloaded or replaced. Source retrieval is distinct from physical evidence.

## 4. Implementation

| ID | Component | Behavior |
| --- | --- | --- |
| R01 | `GgufMetadata` / `TemplateProfiles` | Bounded metadata scan; match actual weight hash, size, architecture and embedded-template hash |
| R02 | `EngineHost` / `TextEngine` | Shared resolution and explicit native template file, without changing weights/settings/download state |
| R03 | Native props and rendering | Verify the actual effective hash, rendered sentinel definition and native tool-call parser capability |
| R04 | `NativeToolRequest` | Keep every public definition for named choice; target-only native grammar with complete template kwargs; reject client-injected private kwargs |
| R05 | `ApiHost` | Same native copy for context accounting and generation; count tool definitions without truncation |
| R06 | `ToolReply` | Validate IDs, declarations, named target, parallel policy, strict JSON/schema and termination before executable delivery |
| R07 | Runtime and model metadata | Publish effective template state separately from unverified model reliability |
| R08 | Authenticated `/health` | At most12 in-memory traces with tool names/count, definition hash, input tokens, call IDs/argument hashes, result IDs and delivery state; no full prompts, arguments, results or credentials |

Unknown weights keep their own templates. Tool requests without a working renderer/parser return `422 tool_template_unavailable`; ordinary chat can continue. An ineffective reviewed override fails loading explicitly. Original signing, port52187, bounded FIFO, cancellation, Delete and Unload remain.

## 5. Physical and program evidence

Motorola Edge Plus / Android12, DSH1.4.76/code327, same installed m04 and saved settings. [Exact final APK and 21 SDK checks](../verification/releases/v1.2.1/physical-tools.json).

| Test | Result and scope |
| --- | --- |
| Native program gate | 17 weight-free checks against the actual pinned Jinja renderer, grammar and parser: all41 definitions in auto/required/named modes, long descriptions, history and unchanged plain chat |
| Final APK / OpenAI SDK | 21 physical checks; strict named calls, result round trip, SSE, two queued requests, UI unload and API reload; six actual generations |
| Strict named call | 18.858s, 298 input /24 output tokens, including first load/prefill; not decode throughput |
| Resume / SSE | 5.700s /2.895s; 14 streamed events with checked IDs, arguments, finish and usage |
| Two requests | 6.523s combined, peak admission2, longest health request26ms |
| Actual DSH long task | All41 tools,19309 input tokens; no completed execution after14m4s, explicitly cancelled. Native logs showed over700 generated tokens at about1.4token/s. This is not an accepted tool loop |
| DSH B1, cancelled observation | All41 tools and19050 input tokens; stopped in DSH after9m56s, with underlying computation briefly still active until upgrade. This may have remained in prefill, so it is not evidence of absent tool ability or a final-APK pass |
| DSH C1, natural completion | Candidate `d1cdd364…`, all41 tools and19058 input tokens. Finished with stop after19m57s, repeated runtime context and produced no tool_calls. Prefill reached97% at about17min; total waiting time is not decode time. No protocol422/502 occurred; the tool loop failed |
| DSH D1, final APK natural completion | Final `2dbc586b…` APK, all41 tools,19132 input tokens and17m16s. Stopped with time/timezone text and no calls/results; independent read confirmed the owned target file absent. The bash/write/read loop failed |
| Final APK direct API | Auto, required and named modes returned genuine lma_sum calls; streaming reassembled IDs/JSON. A matching-ID client result43 produced an answer using43. Invalid strict schema returned400 with its field. These small requests do not substitute for DSH acceptance |
| Runtime-message position controls | Two small requests place the same system context before/after the task; both return correct native calls in3.886/4.050s. Failure cannot be generalized to all later environment messages; long system prompts,41 tools and task reliability remain separate boundaries |

Actual DSH short-task/file/plugin results are recorded separately in [physical DSH evidence](../verification/releases/v1.2.1/physical-dsh.json). Injected negative fixtures demonstrate guards, not a model naturally producing every negative case. Initial XML-candidate and input-method failures remain distinct from final-APK passes.

A1/B1 remain earlier-candidate observations in `earlier_unbound_trials`: their complete APK digests were not retained for public binding, so no digest is guessed and they do not count as final-APK acceptance. C1 and final-package D1 have exact APK identities.

The final APK has14 completed generations: six SDK, seven direct/control probes and one DSH D1. D1 failed its task; natural generation completion does not count as tool-task success. Other-candidate C1, cancelled earlier trials and pre-inference negative validation are excluded from those14.

### Customer acceptance mapping

| ID | Constraint | Evidence and boundary |
| --- | --- | --- |
| A01 | Preserve m04, weights,131072 context and settings | Complete physical weight SHA256 plus before/after settings, assets and LMA history comparisons passed |
| A02 | Retain all41 tools and actual agents | Real DSH requests carry41 definitions and render over19000 input tokens; full names and definition hashes retained |
| A03 | Auto, required, named and SSE | Final-APK direct API returns genuine calls in every mode; separate full-DSH auto failures are not replaced by these small requests |
| A04 | IDs, tool results and continuation | Real SDK/direct round trips pass; the DSH three-step command/file loop has not passed |
| A05 | Strict success and failure | Physical integer calls pass; invalid schema returns400 on the phone; invalid model arguments and502/SSE guards use labelled production fixtures |
| A06 | Actual bash, write, independent read and answer | Not accepted; repeated instructions, code and HTTP200 are not execution, and ADB does not create the output file for DSH |
| A07 | DSH installs dsh-pet itself | Installation is unconfirmed without its own tool event/result; platform constraints are separate below |
| A08 | Concurrency and capacity | Two physical requests queue successfully;4MiB bodies,1024 messages and1MiB content boundaries are program checks, not arbitrary-agent throughput |
| A09 | No new generation deadline | Native generation keeps unlimited read duration; explicit test cancellation and natural stop remain separate; saved output limits are unchanged |
| A10 | m15 and other models | Shared code has program regression coverage; no switch to m15 substitutes for m04 acceptance and historical m15 passes are not moved into this release |

## 6. Usage and limits

Upgrade with the original signer and load the installed model once. Runtime management shows tool-template readiness; `/v1/models` exposes `capabilities.lma.toolTemplate`, and authenticated `/health` provides diagnostic state. Readiness confirms template/parser behavior, not successful arbitrary-agent execution.

Keep DSH's phone-loopback base URL `http://127.0.0.1:52187/v1`, existing credential, m04 and all tools. Verify actual tool events and matching IDs, then independently inspect file contents. Code examples are not execution.

For `tool_template_unavailable`, inspect identity/profile/native capability. For `invalid_model_output`, inspect schema, chosen function and finish state. Distinguish prefill, active decoding and client waiting before diagnosing a long request. No generation wall-clock limit is added. The unchanged131071-token saved ceiling allows a model that fails to finish to keep generating; users may choose smaller per-model limits themselves.

DSH acts under its Android UID. Its own app-files need no ROOT; application-wide controls may require accessibility or other Android permissions. LMA grants none of those permissions.

`PC2005-cloud/dsh-pet` additionally requires compatible Node/Cordis/WebUI hosting. Its browser overlay, desktop Electron Helper and native Android cross-app overlay are separate capabilities. Installation counts only when DSH itself executes the installation tool and returns evidence; external/manual installation is not substituted.

Source review pins [plugin commit60bb2eb](https://github.com/PC2005-cloud/dsh-pet/tree/60bb2eb4113eca92b2636ab906f8e6c9c934ae13). Its package requires Node `>=22.12.0`; INSTALL's `dsh plugin --profile web add dsh-pet` is an upstream CLI example, not verified Android-App installation. Browser presentation, Electron pets and Android cross-app overlays require separate acceptance; source inspection establishes neither installed state nor phone compatibility.

This release delivers the template/protocol repair and measured boundaries. **It does not claim reliable completion of all41-tool m04 agent tasks, plugin installation or arbitrary Android app control.** Additional weight identities need separately reviewed profiles and verification.

## 8. Template attribution and terms

The derived configuration retains its upstream provenance, modifications and publisher-declared `llama3.2` terms. **Built with Llama**. Complete attribution and license ship in the APK and sources as `chat-template-dolphin3-llama32-NOTICE.txt`; see [third-party notices](../THIRD_PARTY_NOTICES.md). No trained weights or tokenizer vocabulary are bundled. LMA's own MIT license does not relicense third-party materials.
