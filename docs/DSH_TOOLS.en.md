# DSH and OpenAI function tools · v1.2.1

[m04 repair: bound template, full definitions and physical results](DSH_M04_REPAIR.en.md).

[中文](DSH_TOOLS.md) · [API](API.en.md) · [Running models and unload](MODEL_RUNTIME.en.md) · [Release](releases/v1.1.0.md)

## 1. Problem and connection

v1.0.2/code67 rejected `store:false`, tools, tool_choice and tool messages at its public validation layer. This did not establish a model limitation. v1.1.0/code68 implements declarations, native tool replies, caller execution and multi-turn results without disabling DSH tools or converting the protocol into ordinary chat.

Start the listener in Services. DSH on the same phone uses `http://127.0.0.1:52187/v1`, the key shown by LMA and an installed model ID from `/v1/models`, such as `m15`. Respect a customized port. Other client devices require explicitly enabled LAN access and the phone address; inference still executes on this Android phone.

The listener can run without a resident model. Explicit API requests may load complete, installed, configured and published text models; they never download weights. The calling client executes tools. LMA does not run arbitrary client shell/file/network/agent code or restrict external functions to the App's internal creation tools.

## 2. Contract

| ID | Supported surface | Behavior |
| --- | --- | --- |
| T01 | `tools` | Up to128 uniquely named function declarations, descriptions, parameter schemas and strict |
| T02 | `tool_choice` | auto, none, required or a declared named function |
| T03 | `parallel_tool_calls` | Boolean; multiple tools differ from parallel phone decoding |
| T04 | Assistant tool messages | tool_calls, nullable/omitted content, IDs, names and string arguments |
| T05 | Tool results | role:tool, tool_call_id, string/text-part content; multiple results and subsequent rounds |
| T06 | Text messages | system/developer/user/assistant, strings or text content-part arrays |
| T07 | Caller hints | store:false/null accepted, true rejected; bounded metadata/user/safety_identifier/prompt_cache_key consumed without persistent completion storage |
| T08 | Replies | Nonstream message.tool_calls; SSE indexed delta.tool_calls, IDs/name/argument fragments, tool_calls finish reason, usage and DONE |
| T09 | Sampling | Per-model defaults and ceilings; max_tokens or max_completion_tokens; template-dependent reasoning_effort |
| T10 | response_format | text, json_object and a bounded JSON Schema subset; strict content checked before delivery |

Every call in a historical assistant turn needs exactly one matching result before another non-tool message. Orphan, duplicate and missing results return a specific error.param. Media URLs are not fetched. Responses, legacy functions/function_call, custom tool types and arbitrary vendor fields are outside this contract.

## 3. Native behavior and strict validation

The existing pinned llama.cpp `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` runs with `--jinja`. Its named-object choice falls back to auto. v1.2.1 retains the complete public list and renders every definition via private chat_template_kwargs.tools while native grammar/required limits the selected target. Preflight and generation share that copy, then output is validated. m04 receives a reviewed weight/template-bound repair; other models retain their templates and need actual rendering/parser readiness. Model reliability remains a separate assessment.

The native pin does not fully enforce function.strict. The gateway validates declared function names, IDs, arguments, parallel policy and finish reasons before delivering executable strict tool deltas. Strict tool fragments buffer after the first tool delta until the round validates; earlier real text/reasoning can stream immediately. Invalid arguments produce invalid_model_output. Clients retain execution permission checks.

The subset covers object/properties/required/additionalProperties, arrays, string/numeric bounds, enum/const, anyOf/oneOf/allOf/not, bounded pattern/format, $defs/definitions and local $ref. Complexity/nesting are bounded; external references, unknown keywords and complex regexes are rejected. Strict arguments must be valid JSON, including quoted keys and no trailing commas. This is bounded pre-delivery validation, not a promise of complete JSON Schema or complete native grammar coverage.

## 4. Queue, capacity and context

| Boundary | v1.0.2 | v1.1.0 |
| --- | --- | --- |
| Text admission | Busy409 | Up to9 admitted requests, normally1 running plus8 waiting in the shared FIFO |
| Text body | 256KiB | 4 MiB per request; 16 MiB total admitted serialized JSON |
| Messages | 128 /64,000 UTF-16 units each | 1024 /1MiB UTF-8 each, within the4MiB body |
| Text JSON nesting | 32 | 64, with separate schema-complexity budgets |
| Other JSON/upload chunks | 256KiB | Unchanged;512MiB upload-file ceiling |
| Heavy decoding | One | One; queueing does not duplicate KV caches |

The 16 MiB budget counts compact serialized parsed JSON, not original HTTP bytes or total heap usage; transport/parsing separately remain bounded by nine workers and 4 MiB per request. The Sub2API kit uses the same text limit and preserves tool history and SSE.

Text has dedicated workers, keeping health/catalogue/control requests available. Full admission returns429 and Retry-After:1; clients should back off. Each parent round releases its execution lease before the caller runs tools or child agents.

The actual model's apply-template and tokenize endpoints count the rendered conversation and tools. Input overflow returns context_length_exceeded without truncating history. Effective output is the minimum of requested tokens, the saved model ceiling and remaining context. A4MiB transport limit does not promise a4MiB usable context or unlimited mobile memory.

An admitted stream returnsHTTP200 before queue/load work, with SSE comment keepalives after about2seconds and then about8seconds. These are not generated tokens. Later failures are SSE error objects without a fabricated successful DONE. Nonstream model errors retain HTTP status before headers. X-Request-ID supports diagnosis; X-LMA-Max-Tokens is the admission-time saved output ceiling, which remaining-context preflight can further reduce.

No generation wall-clock deadline is added. Connection establishment, parsing, blocked-write protection and explicit cancellation remain. Stream write/heartbeat failure cancels that request; a disconnected nonstream queued client may only be noticed during later writing. UI unload cancels current/queued text requests while preserving the API listener.

## 5. Complete tool round trip

```python
import json
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:52187/v1", api_key="YOUR_LMA_KEY")
model = "m15"  # Select an actual installed ID from /v1/models.
tools = [{"type": "function", "function": {
    "name": "sum_numbers", "description": "Sum two integers", "strict": True,
    "parameters": {"type": "object", "properties": {
        "a": {"type": "integer"}, "b": {"type": "integer"}},
        "required": ["a", "b"], "additionalProperties": False}}}]
messages = [{"role": "user", "content": "Call sum_numbers with20 and22."}]
reply = client.chat.completions.create(
    model=model, messages=messages, tools=tools, store=False,
    tool_choice={"type": "function", "function": {"name": "sum_numbers"}},
    parallel_tool_calls=False, max_tokens=512)
assistant = reply.choices[0].message
messages.append({"role": "assistant", "content": assistant.content,
                 "tool_calls": [t.model_dump(exclude_none=True) for t in assistant.tool_calls]})
for tool in assistant.tool_calls:
    assert tool.function.name == "sum_numbers"
    args = json.loads(tool.function.arguments)
    messages.append({"role": "tool", "tool_call_id": tool.id,
                     "content": str(args["a"] + args["b"])})
for chunk in client.chat.completions.create(
        model=model, messages=messages, tools=tools, tool_choice="auto",
        store=False, stream=True, stream_options={"include_usage": True}):
    for choice in chunk.choices:
        print(choice.delta.content or "", end="")
```

Production agents must loop over further calls, assemble streaming arguments by index, wait for the finished round before execution, and retain their approval/cancellation/error policy. The example demonstrates one round without reducing DSH functionality.

## 6. Evidence

test_openai_tools checks production validation and concurrent HTTP sockets; test_backend checks a parent, four queued children, result continuation and context overflow; test_scheduler covers shared media/text scheduling, cancellation and resource errors. These use labelled fixtures, not trained models.

[Physical tools evidence](../verification/releases/v1.1.0/physical-tools.json) records the existing m15, actual OpenAI SDK and phone-native engine separately from [program evidence](../verification/releases/v1.1.0/status.json). **The DSH v1.4.76 App itself, arbitrary tool/model quality and sustained agent endurance are not established by those fixtures.** No weights are downloaded and saved model settings remain intact.

A post-release [actual DSH client code audit](DSH_CLIENT_AUDIT.en.md) adds 79 separate checks importing that APK's adapter, Models layer and codec. The 49 tool declaration variants and streamed round trips traverse production Java HTTP/protocol code. It also reproduces DSH's default 300-second idle watchdog: SSE comments do not reset this client timer, so long prefill/queue waits need an appropriate client threshold. Nondefault provider extensions and outstanding App acceptance remain explicit.

References: [Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), [Function calling](https://developers.openai.com/api/docs/guides/function-calling), [pinned llama.cpp tools](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/docs/function-calling.md). Exact LMA boundaries follow this implementation and its evidence.
