# LMA v1.2.0 · Conversation workspace specification

[中文](DSH_WORKSPACE.md) · [Design index](README.md) · [Release notes](../releases/v1.2.0.md)

The user requested both style and layout to closely follow [Deepseek-Harness-Local-Android](https://github.com/Soodok/Deepseek-Harness-Local-Android) on 2026-11-06. This specification replaces UI10 Mica Bento's visual and navigation rules. Logo 21, slogan 04 and existing LMA model/API functionality remain.

## 01 · Reviewed reference

Review is pinned to `02e89ea7d9a6d211e38777c6a409f6cdf5dc0888`. [Source identities and decision](workspace-decision.json) cover the README, actual interface image, narrow-sidebar/settings plugins, Framer, appearance and settings layout. The Android shell and upstream WebUI form the actual workspace; promotional artwork alone does not define its neutral palette.

| ID | Reference characteristic | LMA implementation |
| --- | --- | --- |
| U01 | Left icon rail, conversation centre | Five destinations in the sidebar; conversation-first home |
| U02 | Expanded narrow sidebar replaces the centre | Full-width drawer, inert background, keyboard focus cycle and Back/Escape |
| U03 | Neutral surfaces and quiet separators | Complete dark/light themes; resource tiles and model grids become compact summaries and lists |
| U04 | Rounded composer with model selection below the prompt | Model selector, plus and send in the composer; history/new remain in the toolbar |
| U05 | Session list and compact runtime status | Bounded 24-row recents, paged full history and a visible runtime manager |
| U06 | Consistent compact settings and lists | Shared components across Models, Tasks, API, Settings and overlays |

LMA uses an original HTML/CSS/JS implementation and its existing Android bridge. No DSH agents, runtime code, cloud endpoints or branding are bundled. Images, video, audio and 3D continue through LMA's same-phone model/queue contracts.

## 02 · Shell and navigation

`index.html` defines the semantic shell; `workspace.css` owns current layout and visuals; `workspace.js` handles navigation expansion and session summaries. Existing `mica.css`/`LMAMica` names remain as compatibility components for controls, native insets, keyboard and text scaling. The current design is defined by this document and [tokens.json](tokens.json).

Phones use a 56 CSS px icon rail; 600–1079 px windows use 64 px. Every icon has an accessible Chinese label. Expanding on narrow screens occupies the full available viewport instead of compressing the conversation. At 1080 px and above, a 256 px labelled sidebar opens by default and can collapse to 64 px. Logo, new conversation, destinations, recent sessions and device information form the hierarchy. Recent sessions scroll independently, preserving Settings and footer reachability.

The top bar contains a page title and runtime capsule. Phones simplify the title while keeping Runtime management visible. Errors occupy their own layout row instead of intercepting controls. Content scrolls independently; modal focus isolation remains in effect.

## 03 · Theme tokens and geometry

| Role | Dark | Light |
| --- | --- | --- |
| Canvas | `#141414` | `#FFFFFF` |
| Sidebar/overlay | `#1C1C1E` | `#F7F7F8` |
| Composer/selection | `#2A2A2D` | `#EEEEF0` |
| Text | `#ECECEE` | `#202024` |
| Secondary | `#C1C1C7` | `#53535C` |
| Muted | `#ADADB5` | `#62626C` |
| Separator | `#333338` | `#E2E2E6` |
| Control border | `#85858F` | `#7A7A85` |
| Primary/focus | `#99B9FF` | `#2C5FCA` |

Dark remains the installation default; Light and System are equally supported, preserving saved preferences. Boot script, Android window, system bars and WebView share backgrounds to prevent an obsolete blue flash. Both themes use the same structure. Error, warning, success and content tags retain semantic text and color, never color alone.

Use system fonts with a 16 px body baseline, 12–14 px secondary information, 24 px page headings and system monospace for code. No font download. Targets are at least 48 px with a visible 2 px focus ring. Controls use 10 px radii, composers 20–22 px, dialogs 20 px and media previews 12 px. Models and jobs are separated rows, not a card dashboard. Decorative separators are distinct from meaningful interactive borders.

`tokens.json` generates `mica-tokens.css` and `mica-design.json`; [contrast calculations](workspace-validation.json) verify the configured pairs. Previous Mica decision/concept records remain historical.

## 04 · Conversation and creation

Empty conversations display the approved LMA logo, a concise welcome and two starter prompts. The rounded composer is centred with limited bottom space in the empty state; short windows and the keyboard remove that space. Existing messages anchor the composer below the scrolling stream. User messages use neutral bubbles; assistant messages use open text. Reasoning, code copy, stop, streaming and cursor history remain available.

Composer controls are plus, current model/dropdown and circular send/stop, followed by a status hint. Long model names truncate with their complete name available in the selector. There is one model picker. Plus opens the existing optional creation sheet: chat, suggestions, image, video, speech, audio, 3D, media composition, attachments, temporary settings, templates and vision pairing. Ordinary chat has no persistent multi-selector form. Temporary values do not overwrite per-model defaults. Manual creation does not require a loaded language model.

Recents mount at most 24 summaries. Full history remains cursor-paged and native `selectSession` remains the persistence contract. Message windows stay bounded to 60 rows, and streamed tokens update their target row. Sidebar updates follow snapshot/navigation events; no new bridge polling, unbounded DOM observer or automatic media decoding is introduced.

## 05 · Other pages and retained operations

| Surface | Required structure and actions |
| --- | --- |
| Models | Heading/Add, compact resource summary, search, Recommended/Local/Light/Advanced/All, task and capability filters, equal-peer model rows |
| Local | Labelled outer Delete, load/unload, per-model settings, pause/resume, versions and dependencies; busy deletion explains the prerequisite |
| Tasks and artifacts | Drafts, recovery/resource status, filters, queue, real errors, cancel/retry and managed results |
| API | Running models/Unload, independent listener, URL/authentication/LAN, published models, examples and logs; port remains 52187 |
| Settings | App preferences, sources, HF token, themes/background and About; inference settings stay per model |

The `m08 → m06 → m01` prefix and multimodal recommendations remain. Task, capability and content tags are independent. Browsing never downloads, loads, unloads or generates automatically. Delete requires confirmation. Unload preserves files, settings and history; the API listener is independent and a subsequent explicit request may reload an installed model.

## 06 · Adaptation, accessibility and performance

240–319 px windows keep navigation and reduce content gutters; below 240 px a recovery message appears. Main controls must remain reachable from 320 px upward without horizontal overflow. Landscape/short windows retain independent scrolling and reduce empty-state decoration. At 130%, 150% and 200% text scale, controls can grow and chat can scroll as a whole page. Names and errors remain readable.

The keyboard removes rail occupancy and uses the existing single native/web inset owner; closing it restores navigation. Test drawer focus cycling, Back/Escape, modal inert state and visible focus. Honor reduced motion. Avoid real-time blur, animated noise, gradients, external fonts and idle animations. Release media when leaving pages. Automated layouts are not device touch, WebView, TalkBack or frame-rate acceptance.

## 07 · Evidence scope

Program verification uses production pages, a 520-layout matrix, bounded conversations/streaming, model and business workflows, signed APK/package checks and Android Lint. Screenshots, MP4 and GIF come from production assets with an explicitly labelled simulated bridge. [Media hashes](../media/workspace-v1.2.0/manifest.json) and [UI checks](../../verification/releases/v1.2.0/workspace-ui.json) are reviewable.

The shared phone is occupied by another task. This round uses no ADB, installation, unlocking or model inference. Fresh Android interaction, TalkBack, the system keyboard and actual frame rate remain pending an available device. Historical phone media retain their exact original version and are not v1.2.0 acceptance.
