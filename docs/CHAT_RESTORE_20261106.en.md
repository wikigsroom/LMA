# Restored chat and generation integration · 2026-11-06

[中文](CHAT_RESTORE_20261106.md) · [README](../README.en.md) · [v1.0.1](releases/v1.0.1.md) · [Existing conversation, tool and API contracts](CONVERSATION_V040.en.md)

## 1. Decision and implemented scope

Restore the v0.3.x hierarchy: **model/history/new at the top → messages → compact composer/send**. Retain the accepted UI10 dark/light themes, Logo21, user assets and native jobs. v1.0.1 moves existing generation controls into the optional “+” sheet. Ordinary chat no longer displays a permanent creation form.

Sections 4–6 evaluate further integration. Proposed interactions are not implementation claims. Existing inference engines, model management and queues can be reused; remote inference and ComfyUI wiring remain outside scope.

## 2. Findings and fixes

| ID | Finding | Effect and correction |
| --- | --- | --- |
| P01 | Two selectors, five action buttons and explanatory text stayed above every prompt | Full-row model selection and 48px targets consumed message space; move them into the optional sheet |
| P02 | Header and composer duplicated model selection | Restore one persistent header entry; show a generation-model field inside the sheet only for explicit non-chat tasks |
| P03 | The first option displayed narration while internal mode was chat | Explicitly synchronize the initial control with chat state |
| P04 | The replacement renderer skipped the old header update | Render the actual native text model or selected generation model; follow native text-model changes |
| P05 | Branding replaced useful starter prompts and assistant copy actions disappeared | Restore the original empty state, two prompts and copy; retain branding in the header and About |
| P06 | Discovery capability filters affected chat choices | Select installed compatible models independently of discovery filters |

These findings concern information hierarchy and state synchronization. They do not establish an inference slowdown; idle performance and model speed require separate evidence.

## 3. Current usage

| ID | Action | Behavior |
| --- | --- | --- |
| U01 | Ordinary chat | Pick an installed text model in the header, load and send; Enter adds a newline, Ctrl/Cmd+Enter sends; history is cursor-paged |
| U02 | “+” | Open Chat and creation; choose chat, automatic tools, image/video/speech/music/3D/narration or local composition |
| U03 | Manual creation | Pick a compatible installed model, assign inputs and optional temporary parameters, close the sheet and send; no LLM prerequisite |
| U04 | Non-default operation | Show one small operation summary and a return-to-chat action above the input; the header names the selected task model |
| U05 | Inputs and settings | Access attachments, temporary parameters, templates and visual pairing through “+”; selected references/roles remain visible and model defaults remain independent |
| U06 | Automatic mode | Explicit opt-in lets the LLM propose tools; review before execution; ordinary text never becomes an instruction automatically |
| U07 | Closing or nesting sheets | Preserve the prompt, selected operation and values; reuse modal focus trapping, background isolation and focus restoration |
| U08 | Results and background | Keep original job IDs, real stages/errors, cancel/retry and managed artifacts; leaving chat releases players while native execution remains responsible |

The same `LMAConversation`, production bridge and job store remain in use. A single controls instance moves between its hidden parking area and the modal; parking before replacement prevents destroyed fields and listeners. The default composer has no persistent selector form. Messages retain their 60-row bound, cursor access to older history and lazy media decoding.

## 4. Recommended complete interaction target

| ID | Requirement | Proposed interaction | Feasibility and boundary |
| --- | --- | --- | --- |
| F01 | Chat and all generation tasks | Keep chat as default; expose tasks through “+” and show only the selected operation summary | High; optional access is implemented; a named task grid could replace the long selector |
| F02 | One model entry | Filter local choices by the operation and label capabilities/components/install state; direct missing models to the library | High; one persistent entry is restored; a unified searchable picker remains proposed |
| F03 | Parameters follow each model | Use model defaults; temporary overrides live in a sheet with a changed-count summary; saving defaults is separate | High; defaults and overrides exist; visible override summaries/reset need implementation |
| F04 | Multimodal inputs | Use thumbnails/audio rows, explicit roles and preflight; move GGUF/projector pairing to Local model management | Medium; references, roles and identity checks exist; richer previews, early compatibility feedback and relocation remain proposed |
| F05 | Results in the conversation | One compact card per original job with queue/stage/result; expand details and previews | High; original cards and lazy previews exist; summaries can improve without invented progress or resubmission |
| F06 | Continue from a result | Offer compatible image/video/speech/3D next actions, carry the managed reference and review before send | Medium; reference plumbing exists; capability-specific next actions and complete UI preflight remain proposed |
| F07 | Manual and automatic work together | Manual tasks require no LLM; automatic mode proposes an editable plan for approval and returns results to the stream | Medium; approval/deduplication/continuation contracts exist; small-model tool reliability is not guaranteed |
| F08 | Multi-step requests | W01–W06 use ordered forms with models, inputs, dependencies and failed-step recovery | High; templates and step retry exist; simpler summaries and role forms remain proposed; no node canvas |

Adopt F01–F08 as one coherent target. Only the selected operation, attached inputs, parameter changes and actual job state should enter the main chat surface.

## 5. State and data rules

1. The user chooses the operation explicitly. Keywords must not silently switch mode or download models.
2. Hold stable model/bundle IDs, operation, artifact references/roles, temporary overrides and unapproved tool plans separately. Accepted jobs keep their own configuration when the current chat model changes.
3. Parameter precedence is model defaults → temporary overrides → native bounds. Report unsupported fields, unknown limits and invalid values honestly.
4. Tools still require allowlisting, model/component checks, resources, valid inputs and idempotency. A proposal is distinct from user approval.
5. Chat, Tasks and API share job/artifact identities. Reconnection queries the original job; retry retains its relationship and never erases failures to imply success.
6. Generation capability does not imply understanding. TTS is not ASR; local composition is not an AI model. Visual understanding requires actual compatible components.
7. Inference, codecs and composition execute on the same Android phone. Removing fixed generation deadlines does not remove explicit cancellation, memory/thermal constraints or OS process termination.

## 6. Example flows and acceptance

| ID | Example | Required behavior |
| --- | --- | --- |
| A01 | Ordinary conversation | Original three-part layout, one model selection, streamed response, copy/history/stop |
| A02 | Image without an LLM | Explicit image task and installed image model; no installed language-model prerequisite |
| A03 | Image to video | Reuse the result reference, choose video model/role, target >5 seconds within real frame/rate constraints; never auto-download missing models |
| A04 | Speech/music to composition | Explicit voice/music/visual roles, same-phone composition and actual output/codec errors |
| A05 | Image to 3D | Offer only for a matching input contract; decode GLB on demand and never call an image preview a successful 3D result |
| A06 | Automatic tools | Review model/parameters/inputs, cancel without creating a job, preserve failed plans or original jobs |
| A07 | Sheets and devices | Reopen/nest/back/theme changes preserve the prompt; actions remain reachable on narrow/landscape/IME/large-text layouts |
| A08 | Background/recovery | Native tasks retain ownership; reopening queries real progress, players release resources and no unlimited-background claim is made |

## 7. Evidence and retained limits

Program UI checks use production HTML/CSS/JS with an explicitly labelled simulated bridge: 100 sessions, 1000 messages, 100 assets and manual operations. See the [fixture media manifest](media/conversation-v1.0.1/manifest.json), [version evidence](../verification/releases/v1.0.1/status.json), separate [physical UI record](../verification/releases/v1.0.1/mica-physical-ui.json) and [actual-phone media provenance](media/device/v1.0.1/manifest.json).

No model downloads or complete trained-model runs are required for this restoration. It is not quality acceptance, arbitrary-HF compatibility or long-term background assurance. Existing public projector identity gaps for m03/m09/m16, complete codec output, video/3D quality and endurance limits remain. Proposed additions identified in F01–F08 are not all implemented.
