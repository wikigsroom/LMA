# m04 / DSH complete function tools: repair assessment · 2026-11-06

[中文](DSH_M04_TOOL_TEMPLATE_ASSESSMENT_20261106.md) · [API contract](DSH_TOOLS.en.md) · [Client audit](DSH_CLIENT_AUDIT.en.md) · [Source/render evidence](../verification/research/dsh-m04-template/assessment.json)

## 1. Conclusion and affected versions

Treat this as a repairable template-path defect. Pinned GGUF repository metadata, the upstream tokenizer and LMA source corroborate a missing tool-aware template: m04's published GGUF template renders ordinary role/content messages but not tool declarations or assistant call history. LMA enables Jinja without selecting a reviewed override or checking the effective template. Parameter count alone does not establish that the 1B weights lack tool capability.

The customer reports Motorola Edge Plus / Android 12, LMA 1.1.0/code68 and DSH 1.4.76/code327. Current published LMA is 1.2.0/code69. EngineHost, ApiHost, TextRequest, ChatProtocol, ToolReply and GgufMetadata are unchanged between those releases. The newer UI release therefore still needs this m04 repair.

This delivery is an assessment, not a production patch: no runtime code changes, new APK, new release or phone access. The phone remains occupied by another task under the user's earlier code-review-only instruction. Customer token measurements and task results remain customer evidence, not a new measurement by this review. A possible repair version is 1.2.1/code70, subject to checking availability when implementing; never replace existing published assets.

## 2. Confirmed findings and open boundaries

| ID | Finding | Evidence / limit |
| --- | --- | --- |
| E01 | Catalogue identity matches the reported m04 source | [models.json](../app/src/main/assets/models.json): 807,697,440 bytes; SHA256 `7ed39ee0638e18d3e47bf12e60e917c792ca5332606a72bd1882ab1f62a13a7a`. Pinned LFS metadata agrees; the actual phone file has not been checked |
| E02 | Published GGUF metadata contains an ordinary-message-only template | Revision `617f94be9dfb802a3fa0ec64b12d7d085482a308`; template SHA256 `58c1a1f04baa7adaeaba1f90267c3d57d9396f0c1f0129bdde9e76d3c6784af7`; no tools or assistant.tool_calls branches |
| E03 | Upstream pinned tokenizer contains tool declarations, calls and responses | Revision `e753b6ebd7adf87036eb6a3e6de68acca5850e2f`; template SHA256 `0067535d4b21c9be3ab1da0d2b99aa71a158711a485da6c5c8a30a6d2227363f`; configuration Git blob identity agrees |
| E04 | GGUF metadata predates the upstream template update | Repository lastModified values are 2025-01-05 and 2025-04-25, consistent with an unsynchronized later template update; this is not a weights-quality measurement |
| E05 | The auto/required API path retains and forwards tools | [TextRequest](../app/src/main/java/com/lma/app/core/TextRequest.java) and [ApiHost](../app/src/main/java/com/lma/app/ApiHost.java) send normalized definitions to both apply-template and inference |
| E06 | Jinja is enabled without template readiness checks | [EngineHost](../app/src/main/java/com/lma/app/EngineHost.java) supplies no reviewed template profile; [GgufMetadata](../app/src/main/java/com/lma/app/GgufMetadata.java) can return after finding context metadata |
| E07 | The reported required502 comes from output validation | [ToolReply](../app/src/main/java/com/lma/app/core/ToolReply.java) rejects a missing required call using the reported message. Keep this protection and improve failure classification |
| E08 | Named choice currently narrows engine-visible definitions | [ChatProtocol](../app/src/main/java/com/lma/app/core/ChatProtocol.java) replaces tools with the selected function and required to accommodate the old native server; the new full41-definition acceptance requires separating visibility from allowed output |
| E09 | Historical m15 evidence does not establish m04 acceptance | [SDK record](../verification/releases/v1.1.0/physical-tools.json): m15, six generations, DSH App untested. The customer's additional m15 bash/write/read result is not relabelled as our own device test |

Direct HF retrieval failed during this review. Public pinned configurations and API metadata were obtained through hf-mirror; primary URLs, transport, hashes and blobId are recorded separately. No GGUF or tensors were downloaded. The GGUF template came from repository API metadata, not a new binary-header extraction or phone-file inspection. Actual loaded-file identity and effective /props still require device verification.

## 3. Bounded source-template reproduction

The exact retrieved templates were rendered with Python Jinja2 and a fixed message. The 41 declarations are explicitly synthetic, not the customer's DSH tool set. These are prompt character counts, not native token counts.

| Fixture | Published GGUF template | Upstream candidate |
| --- | ---: | ---: |
| No tools | 106 | 207 |
| One tool | 106 | 823 |
| One expanded description | 106 | 35,640 |
| Forty-one synthetic tools | 106 | 10,277 |

The old outputs have identical SHA256 values; definitions do not enter that template's rendering. The candidate renders declarations, and a separate history fixture retains the function call and dedicated tool-response markup. See the [machine evidence](../verification/research/dsh-m04-template/assessment.json).

This independently supports the template diagnosis without executing a model, minja, native decoding or Android. The candidate also changes the no-system ordinary-chat default. Review system/developer messages, special tokens/BOS/EOS, null content, object/string arguments and ordinary chat before adopting it. Do not globally replace templates by architecture or parameter count.

## 4. Numbered repair work

P0 is required before complete-tool acceptance. P1 covers regression, observability and plugin work in the same repair delivery; it does not authorize omission.

| ID | Priority | Required change | Location / acceptance |
| --- | --- | --- | --- |
| R01 | P0 | Establish actual model/file/effective-template identity | Store/BundleStore, GgufMetadata, template resolver and EngineHost diagnostics. Record loaded-file identity, approved digest, template source/version/hash, native revision, tokens and caps. Avoid repeatedly hashing807 MB on the UI thread |
| R02 | P0 | Introduce versioned, identity-bound tool-template profiles | Shared TemplateProfiles layer and asset manifest, EngineHost and TextEngine. Supply approved template-file/tool_use behavior alongside Jinja; retain weights and selection |
| R03 | P0 | Add effective-template and tool admission checks | Readiness and ApiHost.openText. Use actual props/rendering to establish that definitions enter the prompt. Source substring checks alone are insufficient; do not rerun a 41-tool self-test per request |
| R04 | P0 | Align native tool parsing with the selected format | Locked common/chat, Jinja/autoparser and ToolReply. Validate actual tool_calls, argument normalization, null content, special characters and finish reasons. Never turn ordinary code blocks into calls |
| R05 | P0 | Preserve all 41 visible declarations for named choice | ChatProtocol, native selection/grammar adaptation and output guard. Separate full visible definitions from the permitted output function. Do not merely remove narrowing and fall back to auto; evaluate a native patch or controlled rendering/allowed-set separation |
| R06 | P0 | Render complete call/result history and preserve IDs | ChatProtocol.messages, profile and native parser. Retain assistant calls, role:tool, tool_call_id, failed results and continued calls; reject orphan/duplicate/missing results |
| R07 | P0 | Correct stream and strict delivery | ToolReply, JsonSchema and API/client regression. Assemble index/id/name/arguments; validate finish reasons and both schema success/failure. Invalid strict calls must not reach execution; retain the documented bounded schema subset |
| R08 | P0 | Preserve settings and accurate context/load identity | ModelSettings, apply-template/tokenize and EngineHost/execution slot. Keep m04/context 131072/all saved parameters; count the complete rendered request; reject overflow rather than truncating. Safely reload the same file after a profile change |
| R09 | P1 | Expose precise capability states and failure categories | ModelCapabilities, publication, runtime diagnostics and docs. Distinguish upstream declaration, template readiness, parsing, phone verification and reliability. Global function_tools:true is not per-model acceptance; keep private prompts/keys out of public logs |
| R10 | P0 | Add real-template regression gates | Native weight-free rendering/parsing, API and versioned evidence. Old-template negative case, candidate positive case, 0/1/expanded/41 definitions, history/named/SSE/strict. A fake engine returning predetermined calls cannot establish this |
| R11 | P0 | Run actual m04 + full41 tools + DSH App task loop | Command execution, write, independent read and result-grounded answer; preserve IDs/results/file evidence. No external substitute execution or HTTP200-only acceptance |
| R12 | P1 | Separately validate plugin installation and Android presentation | DSH plugin manager/commands, Node/Cordis/WebUI and any plugin adaptation. DSH must perform the installation; verify profile/version/dependencies, enable/reload and actual page behavior |

R01–R12 form one repair delivery, ordered by identity/template, native parsing/protocol, program regression and physical tasks/plugin checks. The integration defect is repairable; complex-task reliability with m04 and41 tools requires measurements after that repair.

## 5. Implementation constraints

The native revision is `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`. Its apply-template and chat routes use the same oaicompat_chat_params_parse. Current preflight can accurately count a prompt that has already lost its tools; add readiness validation while retaining context accounting.

This revision includes specialized handling and a differential autoparser. Validate the effective template and object arguments using that exact runtime rather than assuming a handler name in older documentation guarantees support. If a template override is insufficient, use a minimal native patch or a regression-tested upgrade and include other-model impact.

Context 131072 is an allowed window, not evidence that every request prefills 131072 tokens. Once 37 KB of definitions are rendered, actual input tokens, prefill time, cache use and remaining output budget will change. Report resource errors separately; do not silently shorten saved context, replace weights/model or change saved sampling. Retain explicit cancellation, token output bounds and real resource protection.

The [DSH audit](DSH_CLIENT_AUDIT.en.md) documents a default 300-second idle timeout that SSE comments do not reset. Large-prefill/strict-buffering behavior needs measurement and appropriate waiting configuration. Do not emit fake content/reasoning to reset it, disable agents or restore a generation wall-clock cap.

## 6. Device acceptance

Record APK/hash, versions, native revision, actual model/template identity, complete41-definition identity and saved context/sampling for every device run. Keep necessary full traces privately; remove credentials and unrelated private paths/content from public evidence.

| ID | Scenario | Required evidence |
| --- | --- | --- |
| A01 | Same installed m04/settings and actual template | File/process/endpoint identity, props/profile hash and upgrade settings comparison |
| A02 | No/one/expanded/actual41 definitions | Native rendering or verifiable digest, complete tool identity/count and input token comparison with cache semantics checked |
| A03 | Auto | All41 declarations, real calls or actual non-selection; repeat task outcomes instead of implying reliability from one success |
| A04 | Required/named/none | Required call, exact named function and no forbidden none call; all 41 declarations remain visible |
| A05 | Streaming | Indexed real IDs/name/arguments across fragments and Unicode/quotes/newlines; correct finish/usage or actual error |
| A06 | Continued calls/results | Matching IDs, at least three independent tool events and final answer; failure results continue or are honestly reported |
| A07 | Strict success/failure | Valid object accepted; missing/wrong-type/extra-key/invalid JSON rejected. Label controlled negative injection separately from actual model output |
| A08 | Lifecycle/error regression | Orphan/duplicate results, overflow, length, cancellation, resource stop, 429, unload/reload; no false DONE/task success |
| A09 | DSH command→write→independent read→answer | DSH executes a command producing an unpredictable test value, writes a unique test file, independently reads it and answers from the result; authorized read-only device/file inspection confirms it; external observers do not write/execute the task |
| A10 | Plugin install | DSH-originated installation call, exit/log/version/profile, enable/reload and actual page result; no manual/external substitute installation |
| A11 | Android/permissions | DSH-UID-accessible paths, real Node/dependency/host APIs, WebView media support and optional permissions; diagnose separately from absent calls |
| A12 | Model capability benchmark | Repeat a fixed full41-tool task set and report selection/argument/task success, timings/cancellation/resource failures and all failures without silently changing the model/settings |

A07 includes real generated strict responses and separately labelled injected failures against the real gateway; do not combine these into model-inference success. Auto can legally return no call, but a task requiring actual execution then remains incomplete.

## 7. Plugin and permission boundaries

Pinned [dsh-pet commit 60bb2eb](https://github.com/PC2005-cloud/dsh-pet/tree/60bb2eb4113eca92b2636ab906f8e6c9c934ae13) declares Node >=22.12.0, DSH/Cordis host dependencies and a Web client. DSH Android wrapper version 1.4.76 alone does not establish those runtime requirements.

A browser overlay is a plausible Android integration path. The [desktop helper](https://github.com/PC2005-cloud/dsh-pet/blob/60bb2eb4113eca92b2636ab906f8e6c9c934ae13/dsh-pet/src/host/plugin/desktop/spawn.ts) and [Electron downloader](https://github.com/PC2005-cloud/dsh-pet/blob/60bb2eb4113eca92b2636ab906f8e6c9c934ae13/dsh-pet/scripts/ensure-electron.mjs) target desktop environments; no Android desktop-helper implementation was identified. In-WebView presentation, Android cross-app floating windows and desktop Electron behavior are separate acceptance targets. An installation directory does not establish all three. No Docker/WSL/virtualization workaround is proposed.

DSH commands run with DSH's own Android UID and accessible paths. LMA inference does not grant root or ADB privileges. Workspace file I/O and global app control require separate checks; the latter may need explicitly granted accessibility, screen-capture or other relevant permissions. Optional pet chat/TTS must also be checked for local endpoints before claiming all inference remains on the phone.

## 8. Completed and outstanding

| ID | This assessment completed | Evidence scope |
| --- | --- | --- |
| C01 | Compared load/normalization/preflight/parser/guard paths across 1.1/1.2 | Source review |
| C02 | Checked pinned HF identity/templates/timestamps and function-training references | Public metadata/config, mirror transport disclosed |
| C03 | Four-way definition and call-history rendering contrast | Jinja2 only, no native/model/device execution |
| C04 | Reviewed pinned plugin host/Node/Web/Electron boundaries | Source only, no installation |
| C05 | R01–R12 repair plan, A01–A12 acceptance and bilingual known-issue docs | Assessment delivery |

| ID | Remaining | Status |
| --- | --- | --- |
| P01 | R01–R10 production template/native/API fixes and regression | Not implemented by this assessment |
| P02 | R11/A01–A09/A12 actual file/native API/DSH 41-tool loop and benchmarking | Await available device; customer reports/historical m15 do not replace m04 acceptance |
| P03 | R12/A10–A11 DSH-installed plugin and Android presentation/permissions | Keep plugin failures separate from protocol/model failures |
| P04 | New signed APK/version evidence/stable release | After repair and corresponding acceptance; preserve signing, weights/settings and existing published assets |

Retain the complete existing multimodal/model scope and regress shared queues, Delete/Unload and media operations. This assessment makes no additional model-quality or background-endurance claim.

Sources: [pinned GGUF](https://huggingface.co/bartowski/Dolphin3.0-Llama3.2-1B-GGUF/tree/617f94be9dfb802a3fa0ec64b12d7d085482a308), [pinned tokenizer](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-1B/blob/e753b6ebd7adf87036eb6a3e6de68acca5850e2f/tokenizer_config.json), [model card](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-1B/blob/e753b6ebd7adf87036eb6a3e6de68acca5850e2f/README.md), [locked function-calling documentation](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/docs/function-calling.md).
