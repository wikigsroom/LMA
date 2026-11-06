# Mica Bento · 30 component and page contracts

> v1.2.0 当前视觉／导航规范已改为 [DSH workspace](DSH_WORKSPACE.md) / [English](DSH_WORKSPACE.en.md)。This document preserves the historical UI10 specification; current user direction takes precedence.

[中文](COMPONENTS.md) · [Design specification](MICA_BENTO.en.md) · [Adaptation and acceptance](RESPONSIVE.en.md) · [Tokens](tokens.json)

**Implemented in v1.0.0.** [Scoped program and physical checks](../MICA_V100.en.md) are separate from these component contracts. Earlier pending wording describes the original specification stage.
**Status: implemented in v1.0.0, with scoped program and phone validation.** Every component must work in dark and light themes. These contracts remain implementation requirements; runtime evidence records actual coverage. Keep C identifiers stable for implementation and review.

v1.0.2: Local model-card footers expose a labelled trash/Delete action beside ordinary controls for text, media and LoRA. Busy transfers retain a disabled “Pause before deleting” action. The existing confirmation/cancel contract applies; controls wrap on narrow/large-text layouts.

## 0. Shared contract

| Concern | Requirement |
| --- | --- |
| Surfaces/colors | Use canvas/surface/raised/inset, text/secondary/muted. Resolve theme tokens in shared components rather than duplicate business logic |
| Metrics | Actions at least 48 × 48 CSS px; icons 20/24px; control radius 8, model card 10, resource 12, dialog 16px. Heights are minima, not text-clipping caps |
| Selection | primarySoft/onPrimarySoft plus a check, outline or explicit label; accessible selected/pressed/current state matches visuals |
| Focus | 2px focus outline, 2px offset; not clipped by containers/bars; logical keyboard and reading order |
| Press/hover | Immediate press feedback without scaling the entire card; primaryPressed for primary actions; hover is optional enhancement |
| Disabled | Block activation and explain why; do not merely gray an active action or fade its explanation into illegibility |
| Loading | Preserve action width and readable wording, prevent duplicate submission, show actual state |
| Failure | Local cause, valid next action and inspectable persistent details; content labels never use failure styling |
| Accessibility | Prefer native semantic HTML; expose name/value/expanded/state; name icon buttons and hide decorative SVGs from accessibility |
| Text/layout | Allow wrapping and `min-width:0`; support 200% text without hiding actions; use logical spacing |
| Themes | Update dynamic overlays and native windows too; preserve original logo/media colors |
| Motion | Press 100ms, state 160ms, overlay 200ms; nonessential maximum 240ms, zero under reduced motion; no per-token announcements |

## C01 · Shell, header and brand

Order: safe area, brand/page actions, optional runtime strip, page, navigation. Header minimum 64px; logo 40px, optionally 36px when narrow; LMA wordmark 20px/700; actions 48px. Move secondary device copy or the full slogan into details rather than squeeze actions. The header enters normal flow on short windows.

Use surface/text in both themes, with matching Android system-bar icons. Never invert/fade the logo. Cold launch, theme changes and rotation must not flash white, reset the catalogue or start a model. Runtime information follows the brand in reading order without stealing focus.

## C02 · Page heading and toolbar

Title 26px/600–700; description 14–16px; title/action gap 12–16px; following section gap 16–24px. Add Model is a named action, not a hidden click on the entire heading. Give each local group one primary emphasis.

Wrap titles and move actions to another row on narrow windows or large text. Do not fix heading height or cover it with error/loading overlays. Use theme primary/onPrimary. Update the page heading accessibly on navigation without announcing it on every background refresh.

## C03 · Mica panels

Opaque surface with raised/inset subregions, normally 16px padding, 12px narrow, 16–24px between groups. Model cards use 10px corners and resources 12px. Avoid three nested layers of outlines/shadows. Noninteractive cards must not look like a single clickable button.

Decorative separators may be subtle; an essential input/selection boundary uses controlBorder or another verified cue. Selection needs a check and primarySoft, not an almost invisible tint. Dark planes brighten with elevation; light uses white cards over blue-gray. Content determines height, not screenshot proportions.

## C04 · Resource bento and runtime strip

Show real memory/storage/local-model fields with 20–24px tabular values, 14px labels, 12–16px padding and 8–12px gaps. Unknown values display “—”, Reading or Unavailable with details; never use the concept’s 8GB/64GB/0 as device data. Distinguish available/total and download size/runtime memory.

Use two columns plus a full-width tile on ordinary phones; three only when text and width permit. Below 360px or at 150%+ text use a column or expandable summary. Keep semantic order. Runtime uses a dot and explicit Not loaded/Loading/Running/Failed text; Stop/Details are separate actions. Avoid full-page polling redraws. Decorative diagonal tints do not cross verified text backings.

## C05 · Model cards and local rows

Order: model/source, capabilities, size/format/quantization/requirements, state/actions. Name 18px/600; metadata 14px; gaps 8–12px. Normal text may use two name lines if Details exposes the full identity; remove clamps for large text. Wrap HF IDs without dropping suffixes.

Offer Download/Load/Resume/Settings from actual state, with 48px targets. Stack actions under content when narrow. Opening settings must not also load the card. Recommended and All use equal semantics; recommendation provenance is separate. Use surface with theme-specific mint download actions, preserving recommendation order.

## C06 · Transfers and recovery

Show file/dependency group, real transferred/total bytes, stage and Pause/Resume/Cancel. A 4–6px progress track needs adjacent 14px text and accurate progress semantics. Unknown totals have no fabricated percentage. Verification/installation stages are distinct from Download 100%.

Retain failures and valid resume/retry paths without automatic full redownload/deletion. Stack into two rows at 320px rather than hide actions in sideways scrolling. Use inset tracks and primary/mint fill in both themes with textual values. Do not announce every percentage change assertively.

## C07 · Catalogue, task and content filters

Keep separate groups: Recommended/Local/Lightweight/Advanced/All; All tasks/Text/Image/Video/Audio/3D; content/source filters. Each has an accessible name. Selection uses primarySoft/onPrimarySoft and a noncolor cue. Wrapping controls retain 48px targets; five fixed columns are not mandatory at 320px.

Prefer wrapping over hidden horizontal options. Use pressed buttons for filters unless implementing real tab behavior. A tablist requires arrow keys, Home/End and correct panel relationships. Preserve search and sensible scroll position. Installation and NSFW states remain independent. Verify text/markers in each theme.

## C08 · Local/HF search

Minimum 48px input, 16px type, 12px padding, 20px search glyph; separate 48px clear action. A visible Search Models label is required; placeholder is supplementary. Expose scope as Local models or HF repositories. Place format/sort controls after search and stack when narrow.

Distinguish searching, no matches, network failure and empty offline library. Late results cannot replace a newer query. Preserve input focus, IME and caret. Enter searches; Escape clears/closes suggestions where appropriate. Announce result counts sparingly. Both themes use inset/controlBorder with explicit focus styling.

## C09 · Actions and icon buttons

Primary uses primary/onPrimary; Download emphasis mint/onMint; ordinary actions surface/text with controlBorder; destructive actions danger text/dangerSoft and explicit Delete. Minimum 48px height, 16px horizontal padding, 8px icon gap, 8px corners. Icon buttons have 48px targets around 20/24px glyphs and names such as “Pause Qwen download”.

Implement default, focus, pressed, disabled and loading. Hover only enhances. Mint press feedback may use the verified mintSoft/onMintSoft combination or an inset marker, not whole-control opacity. Wrap groups and separate destructive actions; targets never overlap.

## C10 · Editable per-model presets

For context, output, threads, temperature: visible label, 48px editable input/dropdown, unit/range/source, local feedback. Preset selection and direct entry write the same field under the same model ID, never a global inference setting.

Support typing, suggestion navigation, Enter and Escape with a working editable combobox/listbox or native alternative. Temporary empty input is permitted. On blur/save parse and clamp against model metadata, shared context/output budget and device/app limits. Explain adjustments and sources; unknown model limits stay unknown. Handle invalid/negative/nonfinite values according to existing rules without saving NaN. Suggestions must remain usable above the IME. Stack descriptions at 320px. Use inset in both themes; distinguish option focus from selection.

## C11 · Fields, units and validation

Visible 14–16px label; input 16px, minimum 48px; 16px field spacing, 12px within related pairs. Units belong in accessible labels/descriptions. Persistent help and local danger text/icons identify errors using invalid/describedby semantics.

Submission focuses the first invalid field and scrolls it into view, without focus theft on each keystroke. Explain required dependencies/ranges in advance. Use two columns only when each field retains at least 240px with wrapping labels; large text/IME falls back to one. Maintain outlines, caret, selection and autofill readability in both themes.

## C12 · Switches, checks and radios

Label and control form a 48px-minimum row; switch graphic may be 44 × 24px and checks/radios approximately 20px. Selected switch uses primary/onPrimary; unselected inset/controlBorder. Expose On/Off or checked state accessibly, not only by color. Prefer native inputs with Space activation.

Switches change immediate preferences, checkboxes select multiple dependencies and radios/selects choose exclusive options. Explain disabled states near labels. Wrap long descriptions instead of clipping rows. LAN/boot copy must describe actual effects rather than claim remote inference. Theme changes preserve values.

## C13 · Model pickers

Trigger minimum 48px, showing model identity, task compatibility and necessary local/readiness state. Options minimum 56px and grow for multiline names. Full IDs distinguish duplicate names; selection has a check and semantics. Disable only for real reasons with explanations; discoverable does not mean runnable.

Support search, keyboard navigation and returning to the current option. Manage focus on open/close. Phone uses an appropriately sized sheet/dialog; wide layouts use a centered dialog rather than a tiny edge popup. Use surface and primarySoft in both themes. Distinguish selected model from currently running model.

## C14 · Five-destination navigation

Models, Chat, Tasks, Server, Settings remain in order. Bottom navigation minimum 64px plus safe inset; 24px icons and 12–14px labels. Every destination has at least a 48px target and a visible label. Selection combines primarySoft/onPrimarySoft, shape and aria-current.

At available width ≥840px, unobstructed layouts may use an 80px rail with identical destinations/state. Use available space, not device brand. Large text allows multiline labels and vertical rail scrolling; extreme narrowness may wrap navigation rows. IME rules must prevent focusable controls being hidden behind the keyboard. Neither theme uses live transparent blur for navigation.

## C15 · Dialogs, sheets and confirmation

Provide title, scrollable content, explicit Close/Cancel and primary action. Corners 16px; padding 16–24px; phone side margins at least 12px, wide dialog normally 480–640px within available space. Long/short-screen forms scroll; title/buttons/IME cannot consume the whole usable height. Put actions in the same scroll flow when necessary.

Use dialog/modal semantics, focus entry, background isolation and focus restoration. Back/Escape closes the active layer without discarding saved jobs. Backdrop clicks never execute destructive actions. Dark scrim 64%, light 40%; opaque surface body. Keep active field and confirmation reachable above the IME. Prefer one main modal rather than nested stacks.

## C16 · Toasts, banners and local feedback

Toast padding at least 12px, 14–16px wrapping text, placed clear of navigation/IME. Brief feedback may disappear after approximately 3–5s, but the only Retry/Undo action must not disappear with it. Decisions and important errors persist in the field/job/banner.

Banners contain cause, next step and optional 48px dismissal. Use corresponding dangerSoft/warningSoft/infoSoft combinations rather than a full red screen. Ordinary announcements are polite; reserve alerts for blocking failures and avoid duplicate announcements. Existing feedback updates with the theme.

## C17 · Empty, loading, offline and unavailable

Use a 24px icon, 20px heading, 16px explanation and one direct action, without a giant illustration. Distinguish no downloaded models, no filter matches, network failure and unsupported engine. Idle/empty screens have no busy animation or fake progress.

Skeletons reflect actual requests, respect reduced motion and do not erase useful local lists. Offer only implemented Retry/Clear filters/All/Import actions. Use static raised/inset placeholders in both themes and wrap content/actions on narrow windows.

## C18 · Messages and streaming

Body 16px/1.5, group spacing 16–24px, text maximum 760px and full available narrow width. Roles use text/position/boundaries rather than bubble color alone. Names/times/actions cannot overlap messages. Code, media and original job cards follow their own contracts; unknown blocks retain readable fallback and identity.

Streaming updates the active text node while preserving selection, scroll and focus. Do not force a reader who scrolled upward to the bottom; offer New content. Retain partial output on failure/cancellation with accurate state. Announce suitable chunks/completion rather than every token. Contain long code/formulas locally. Syntax highlighting must be readable separately on dark and light backings.

## C19 · Composer, attachments and manual modes

2026-11-06 user correction: restore the top model toolbar, message stream and compact composer. Modes, inputs, temporary parameters, templates and visual pairing open through “+”; never keep two selectors and a button grid above every prompt. Non-default tasks add one operation summary and a return-to-chat action; selected inputs/roles appear when present. [Restoration and integration proposal](../CHAT_RESTORE_20261106.en.md). Input minimum 48px grows to about one-third of visible space before internal scrolling. Send has a separate 48px target. Preserve drafts and never submit Enter during CJK composition.

Phone Enter inserts a newline; the Send button remains available. Document physical-keyboard shortcuts without breaking IME input. Manual image/video/audio/3D modes do not require an LLM. Attachments expose role, validity, removal and provenance without silent reinterpretation. Resize around the IME and navigation. Both themes retain inset field boundaries, caret/selection and draft content.

## C20 · Original jobs and queue

Show original job ID/model, real state/stage, parameter/input summary, known progress/elapsed time and valid actions. Distinguish queued, loading, running, finalizing, succeeded, failed and cancelled. Unknown percentages remain stage text. Elapsed time is not a generation deadline or automatic cancellation countdown.

Cancel has a 48px target and distinguishes Requested/Cancelled; deduplicate repeated requests. Retries retain original-job relationships. Expand causes instead of clearing failures to imply success. Stack actions when narrow and allow long-ID copying. Selecting a card does not restart work. Use identical state semantics in both themes; NSFW never means failure. Preserve persistence, recovery and background identities.

## C21 · Image, video, audio and 3D previews

Provide type/name, dimensions/duration/format, implemented save/share/details and provenance. Images preserve aspect ratio; transparency is visible; full-screen has Back. Video/audio are manually played with accessible transport/progress/volume. No simultaneous autoplay in lists. Create 3D viewers on demand; local rotation/zoom must not hijack whole-page scrolling.

Lazy-load previews, pause decoders and release inactive GPU views off page. 3D failures retain file/metadata fallback, not a false success based on a thumbnail. Preserve original media colors in both themes; adapt controls, checkerboard and errors. Show real video duration; looping is not proof of >5-second generation.

## C22 · Artifact picker and provenance

Rows/cards show thumbnail, type, original filename, source job, availability and semantic selection with a 48px target. Expand provenance details, wrap/copy full names and explain deletion impact on references. Respect existing leases/reference guards; removing a visible card does not delete the file.

Filter by required input role; explain incompatible items. An empty library can import without downloading examples. Both themes share metadata and primarySoft selection. Avoid decoding every thumbnail. Phone is one column; wider grids require adequate minimum card width and revert for large text.

## C23 · Sequential templates

W01–W06 use numbered vertical steps, input/output summaries, dependency state and Run. Connecting strokes are decoration, not draggable nodes. Step title 18px, explanation 14–16px, actions 48px; fields use C10/C11. Current/pending/completed/failed/skipped need text.

Phone uses one column; wide layouts may split step list/current details without changing order or model equality. Preserve real missing-input/dependency/cancellation states. Selecting templates never downloads weights or adds a ComfyUI canvas/plugin/graph importer. Opaque panels in both themes; inactive templates do not animate continuously.

## C24 · Local API, published models and secrets

Show Stopped/Running, selected local model and service controls before the actual endpoint, LAN toggle and publishable local models. `http://127.0.0.1:52187/v1` is the default example, not an override for custom configuration. Label downloaded/configured-but-unloaded published models separately from the running model. Capabilities must not imply unimplemented public API input.

Mask keys by default with separate 48px Show/Hide/Copy actions. Screenshots/logs contain no plaintext secrets. URLs/code/logs scroll/copy inside their regions; prose wraps. LAN means clients call this phone, not cloud inference. Both themes retain readable addresses, state, fields and permission notices. Switching themes does not restart the service.

## C25 · Settings and About

Group appearance, downloads/HF, service/background and About. Rows minimum 56px and grow for descriptions. Dark/Light/System are explicit exclusive choices reflecting the resolved theme. New-install defaults do not overwrite stored choices. Protect HF tokens like API keys and exclude them from screenshots.

Do not expose global context/output limits; link to Local model settings. About uses Logo 21, slogan 04, actual version/licenses and no remote fonts. Phone is one column; wide layouts may place whole groups in two columns without interleaving reading order. Returning from native permission/battery settings preserves location.

## C26 · Menus and explanations

Menu items minimum 48px, 12px icon/text gap; explicitly label and separate destructive actions. Fit within available space away from screen edges, keyboard and hinges. Expose expanded state, support keyboard/Back/Escape and restore trigger focus.

Tooltips are never the only source of a name, error or action. Touch has Details/persistent text; long press is optional, not mandatory. Hover and keyboard focus receive equivalent explanations. Use surface and visible boundaries in both themes. At 200% text allow growth/scroll without clipping options.

## C27 · Tables, code, JSON and logs

Prefer key/value lists unless real two-dimensional comparison is useful. Action rows minimum 48px; clear headers; wrap cell prose. Only the table region may scroll sideways, not the page. Preserve/copy code characters in an inset region, normally 14px scalable monospace, not screenshots of examples.

Bound log rendering and expand on demand. Autoscroll respects upward reading. Do not expand unbounded traces/JSON by default or expose credentials. Both themes need readable syntax and text selection. Preserve diagnostic stages while protecting secrets. Tables/scroll regions have accessible names.

## C28 · Capability, engine, content and evidence tags

Separate task/input-output capability, foundation/dependencies, content properties and evidence. Installation/runtime is another state. Tags use 14px text, 4px × 8px padding and 6px corners. Interactive tags still need 48px targets; static metadata is not a pretend button.

Task labels may use primary/mint/info Soft roles but remain explicit equal peers. Content uses contentSoft/content, never danger. Expose unknown/unreviewed status; do not invent tags for ordinary models. Expand “multimodal” into exact input/output and native/adapter boundaries. Wrap on narrow windows. Do not hide critical compatibility behind “+N”; secondary collapsed tags need a full accessible view.

## C29 · HF files, bundles and import

Show full repository/file/format/quantization/size, role and dependencies, plus supported/unknown/incompatible reasons. Users explicitly select bundles and disclosed dependencies. Organize multifile bundles hierarchically rather than check every repository file. Show known total download and space requirements without implying runtime readiness.

Use accessible Android file selection and preserve context on return. Offline import does not trigger HF requests. Wrap/copy paths; searchable file lists scroll while confirmation remains reachable. Coordinate native pickers/permissions with themes where supported, without claiming control of all system UI. Use C06 for transfer/verification and retain failure stages.

## C30 · Image, video, audio and 3D parameter panels

Render from the selected model/recipe schema: prompt, seed, dimensions, steps, voice/language, duration, reference inputs and LoRA only where implemented. Organize Required inputs, Common parameters and expandable Advanced. Expose limit sources and unknown capabilities rather than imply support through decorative controls.

Video targets must exceed 5 seconds. If a backend cannot meet that, report the limitation rather than duplicate frames/clips or alter metadata. Generation has no wall-clock timeout; cancellation/resource errors remain effective, and connection limits must not mark admitted jobs cancelled. Distinguish audio roles, 3D geometry/textures and image references. Preserve failed-form inputs. Phone is one column; at ≥600px use paired fields only when each fits, reverting for large text/IME. Reuse C10/C11/C20 in both themes and add no off-device execution option.

## Page assembly and source anchors

These are existing anchors, **not claims of implementation**. The stack is Java Android with a WebView and native HTML/CSS/JS, not Compose/React or a marketing website. Existing protected-file restrictions continue to apply.

| Page | Components | Existing anchors |
| --- | --- | --- |
| Shell | C01–C04, C14–C17, C26 | `index.html`: `main`, `runtimeName`, `runtimeAction`, `modal`, `toast`, `errorBanner` |
| Models | C05–C13, C28–C29 | `page-models`, `resourceRibbon`, `modelSearch`, `hubControls`, `communityControls`, `modelList` |
| Chat | C13, C18–C22, C28 | `page-chat`, `chatModelPicker`, `messages`, `chatForm`, `chatInput`; existing `conversation.css`/`conversation.js` |
| Tasks | C11, C20–C23, C30 | `page-tasks`, `draftList`, `jobList`, `artifactList`, `runtimeResourceStatus` |
| Server | C09, C12, C24, C27–C28 | `page-server`, `apiUrl`, `serverToggle`, `lanToggle`, `apiKeyDisplay`, `publishedModelList`, `runtimeLogs` |
| Settings | C10–C12, C25, C29 | `page-settings`, `hfTokenForm`, `settingsForm`; per-model settings remain in Local |

Shared styling primarily belongs in existing `app.css`, `conversation.css` and component structure/classes. A visual migration must not reset persistent data or change scheduling. Every page needs default/empty/loading/error coverage in both themes and the adaptive matrix before UI integration can be called complete.
