# Mica Bento · Adaptive screens, themes and acceptance

[中文](RESPONSIVE.md) · [Design](MICA_BENTO.en.md) · [Components](COMPONENTS.en.md) · [Tokens](tokens.json) · [Pending matrix](acceptance.json)

**These are required behaviors, not completed device tests.** The minimum usable continuous width is 240px; smaller windows show a recoverable resize/rotate prompt without starting work. Dimensions describe the available WebView viewport in CSS pixels. Native insets/hit targets use Android units with verified mapping. A physical 1080px screen is not a 1080-CSS-pixel layout; do not hardcode Z20/X30/tablet classifications.

## 1. Layout inputs

Use the continuous available window after native system-bar/cutout handling, plus actual WebView layout width, visible height, text scale and any reliable folding obstruction information. `W` is available continuous width after native-owned insets. After choosing navigation, content width is `C = W - rail - 2 × gutter`. IME visibility also changes usable height.

Width bands set maximum columns. Minimum card/field width, text scaling, short height and obstructions can reduce them. Fit takes priority over a nominal two-column breakpoint. Fill fluidly between boundaries rather than scale the whole screenshot. Window changes must preserve page, filters, drafts, parameters, jobs and service state.

These are LMA project breakpoints, not universal Android pixel categories. The principle of available-window rather than hardware classification follows [Android window size classes](https://developer.android.com/develop/ui/views/layout/use-window-size-classes).

## 2. R00–R06 width bands

| ID | W range | Gutter / section gap | Maximum model columns | Navigation | Adaptation |
| --- | --- | --- | --- | --- | --- |
| R00 | <320 | 8 / 8 | 1 | Bottom, wrapping if needed | Extreme split window; all actions reachable, targets never shrunk |
| R01 | 320–359 | 12 / 12 | 1 | Bottom | Stack actions/resources, wrap filters/tags, retain every destination |
| R02 | 360–479 | 16 / 12 | 1 | Bottom | Ordinary phone; resources 2+1, or three only when text fits |
| R03 | 480–599 | 20 / 16 | 1 | Bottom | Wide phone/fold pane; improve readability rather than squeeze in another model |
| R04 | 600–839 | 24 / 16 | 1 | Bottom | Three resource tiles; paired form fields only with at least 240px each |
| R05 | 840–1199 | 24 / 16 | 2 | 80px rail | Reduce columns for minimum widths/short windows |
| R06 | ≥1200 | 32 / 16 | 3 | 80px rail | Center content, maximum 1200; never stretch messages indefinitely |

Multicolumn model cards require at least 320px each, preferably 560px at 200% text, with 16px gaps. Use the lower of the band maximum and `floor((C + gap)/(minCard + gap))`, minimum one. Content maximum 1200 excludes the rail. Chat text maximum is 760; grids, forms and previews do not blindly share one maximum.

Check 319/320, 359/360, 479/480, 599/600, 839/840 and 1199/1200 with no gaps or ambiguous rules. Use Grid/Flex, `minmax(0, 1fr)`, `min-width:0` and logical padding. Do not implement adaptation by scaling the whole page. Reference tokens are not a complete layout stylesheet.

## 3. Homepage reflow

| Region | Narrow/large text | Ordinary phone | Wide window |
| --- | --- | --- | --- |
| Brand/device | Logo, LMA, essential actions; secondary copy moves to details | Secondary copy may wrap independently | No promotional banner replacing tools |
| Runtime | Two-line state; actions may stack | Same row if it fits | Identical semantics and cancellation/details |
| Resources | Column/summary below 360 or at ≥150% text | 2+1 or three only with actual fit | Three grouped tiles; no invented statistics |
| Search | Full width; separate clear target | Same | Search and filters still precede results |
| Five catalogue choices | Wrap; no unlabeled mini-icons | One row only if it fits | Local is not hidden in More |
| Six task filters | Visible wrapping rows | Content-based wrapping | Keep task/source/content independent |
| Models | Name, tags, metadata, stacked actions | One column; inline actions when adequate | Two/three columns only at valid minimum widths; row-major order |

Business order is independent of tile size. Preserve the recommendation prefix. Unequal bento geometry is resource decoration, not a hierarchy among tasks/models. Full identities and quantization suffixes remain inspectable; errors/actions must not be clipped.

## 4. Page adaptation

| Page | <600 | 600–839 | ≥840 when sufficient space |
| --- | --- | --- | --- |
| Models/Local | Single cards, stacked actions | Still one model column; compact filter grouping allowed | Maximum two/three columns with complete management actions |
| Chat | Vertical role/media/job blocks; composer may use two rows | Comfortable text width | Text maximum 760; existing details may become auxiliary, not a fabricated feature |
| Tasks | Grouped or switchable jobs/artifacts; separate detail layer | Paired form fields where adequate | Existing list/step and detail panes only when both fit; short height falls back |
| Server | State, controls, URL, LAN/key, models/examples | Group independent information | Primary status plus secondary API/log region may split; retain real address/secrets controls |
| Settings | Whole groups stacked | Pair related fields when they fit | Whole groups may split; never separate a label/value across unrelated columns |
| Model/generation forms | Label, input, source/error stacked | Two columns only with ≥240px fields | Bound form width; settings remain model-scoped |

Insufficient side-pane space falls back to a full-page/modal detail with a return path. Sideways scrolling belongs only to intrinsically two-dimensional code/tables/media controls, not body prose, ordinary forms/cards or the page.

## 5. Text scaling, language and long content

Cover **100%, 130%, 150% and 200%** text, plus actual window changes from Android Display size. Body is 16px at 100%. Determine text scale from native configuration/actual rendering, not `devicePixelRatio`. Avoid applying native and Web text scaling twice. Do not hide overflow by disabling accessibility scaling in viewport settings.

At ≥150% prefer single-column resources/fields, stacked actions, no critical name/error clamps and fewer inline metadata groups. Titles must not auto-shrink to preserve one line. Navigation icons may stay 24px but labels/targets grow; never remove all labels. At 200% users still save parameters, cancel, send, navigate and close dialogs.

Test Chinese, long English words, mixed versions, `org/repo`, GGUF filenames and quantization suffixes. Wrap prose and long IDs, with Details/Copy for full identity. Code/hashes/logs may scroll in a named local region; do not insert characters that corrupt copied values. Screenshots exclude keys, passwords and personal filenames.

See [W3C 320 CSS px reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) and [200% text resizing](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html). These are usability targets, not a declaration of complete WCAG certification.

## 6. Short height, landscape and insets

Visible height **≤480px** activates short-window behavior in either orientation. Put the header, runtime strip and resources in normal scrolling flow. Retain only essential anchored input/navigation; do not pin three toolbars over most of the screen. Dialog actions may join the scroll flow. Each page needs one clear main vertical scroller; necessary message/editor scrollers need explicit boundaries and must not trap the user.

Landscape also handles left/right cutouts, rounded corners, status bars, gesture edges and three-button navigation. Choose one owner for each native `WindowInsets`/CSS `env(safe-area-inset-*)` contribution. If native code already shrinks the WebView, do not add the same inset again in CSS. When drawing behind bars, move interactive content into safe bounds. See [Android edge-to-edge/insets](https://developer.android.com/develop/ui/views/layout/edge-to-edge).

Bottom navigation is 64px content height plus safe inset. Rails scroll when short; destinations must not sit under gesture areas. Avoid precision gestures at system edges. System Back takes precedence over 3D rotation/custom gestures. Observe actual bars, icon appearance and platform scrims in both themes rather than capture only the WebView interior.

## 7. IME, keyboard and visible height

Test chat, presets, search, secrets and generation forms. Configure native resize/insets correctly, then progressively enhance with `100dvh` and VisualViewport if needed. Legacy `100vh` is not always keyboard-visible height. One owner handles keyboard space; native resize plus another full subtraction is incorrect. Older WebViews need a verified container/visible-height fallback, not a new frontend framework.

Focus, caret, local error and Send/Save must remain reachable above the IME. Bottom navigation may temporarily hide to free space, but hidden entries leave pointer/keyboard focus order and restore afterwards. Preserve chat draft/scroll; suggestions fit above the IME; landscape numeric keyboards cannot hide Save.

Theme/IME changes never reload models. CJK composition must not send messages. Support Tab/Shift+Tab, Enter, Space and Escape where appropriate. Phone chat Enter inserts a newline, with explicit Send. Dialog focus follows C15. Do not fix overlap by globally forbidding scrolling or jumping to page top on every focus.

## 8. Foldables, split windows and resizing

Recompute from the current continuous region during folding/splitting, not a cached boot-time screen size. Hinges/occlusions/gaps cannot intersect fields, buttons, messages or important images. Where native obstruction information is available, pass it through a controlled layout bridge. Otherwise prefer the continuous region provided by the system; CSS width alone cannot detect a hinge.

Default to a complete page in one safe continuous region. Cross-hinge dual pages are not mandatory. Use an existing list/detail split only if both regions meet minimum width/height and actual implementation supports it. Preserve models/jobs/page/search/drafts and sensible focus through folding, rotation and resizing; never redownload/cancel jobs. A larger display does not imply more model memory or capabilities.

## 9. Viewport and state matrix

These are **18 pending acceptance targets**, not emulator results. Virtualization is prohibited. Subsequent checks use allowed native tools/WebViews/physical devices, not Android emulators, Docker or WSL.

| Target | Example CSS viewport | Purpose |
| --- | --- | --- |
| V01 | 320 × 480 | Narrow and short; all actions reachable |
| V02 | 320 × 568 | Five catalogue choices wrap |
| V03 | 360 × 640 | Compact ordinary phone |
| V04 | 360 × 740 | Tall narrow phone |
| V05 | 375 × 667 | Short-middle window, long names |
| V06 | 390 × 844 | Common middle-width window |
| V07 | 393 × 873 | Irregular width/fractional scaling |
| V08 | 412 × 915 | Wide phone, all task labels |
| V09 | 430 × 932 | Wider phone; still one model column |
| V10 | 480 × 960 | R03 boundary |
| V11 | 568 × 320 | Very short landscape, input/confirmation |
| V12 | 640 × 360 | Landscape, IME and lateral insets |
| V13 | 800 × 360 | Wide but short; avoid forced panes |
| V14 | 600 × 960 | R04, paired fields |
| V15 | 840 × 1180 | R05, navigation rail transition |
| V16 | 1024 × 768 | Wide cards/dialogs |
| V17 | 1280 × 800 | Content maximum/three-column ceiling |
| V18 | Actual continuous fold/split regions | Occlusion, reflow, persistent state |

Each target covers dark/light × 100/150/200% text. Also check 130% on main pages and both sides of all breakpoints. Fixture states include 0/1/50 models, long HF IDs, five output tasks plus All and existing input/recognition labels, long errors, offline, transfer/loading/cancellation, clamped parameters and no artifacts. Add key combinations of IME, TalkBack, hardware keyboard, gesture/three-button navigation and reduced motion. Weight-free fixed UI data is sufficient; full model generation is not required for this design matrix.

Name screenshots by page/theme/viewport/text/state and APK/commit identity, separate from concepts. Record cold-launch/overlay theme switches. Performance comparisons identify device, Android/WebView and data size. Unexecuted entries stay pending; static contrast checks do not close them.

## 10. A01–A20 acceptance

| ID | Pass condition | Evidence |
| --- | --- | --- |
| A01 | UI10 with approved Logo21/Slogan04, consistent across all pages | Page/overlay comparison captures |
| A02 | Complete semantic tokens in both themes, no isolated hardcoded palette | Source/token review |
| A03 | Body ≥4.5:1, meaningful nontext ≥3:1 in actual composites | Final colors; image/tint regions checked separately |
| A04 | Default dark, stored preference retained, System resolved, no flash | Cold-launch/switch recordings and restored settings |
| A05 | R00–R06 and boundaries have no whole-page overflow/lost actions | Matrix/boundary/long-content captures |
| A06 | Main flows remain usable at 200% without critical clipping | Text matrix and parameter/job interactions |
| A07 | 48px/48dp targets, focus, names and group semantics | Measurements, keyboard and TalkBack |
| A08 | Stable five-destination order and reachable bottom/rail/large-text labels | 840 boundary, short rail and keyboard |
| A09 | IME does not hide field, error, Send or Save | Chat/search/preset/generation checks |
| A10 | Correct cutouts, gestures, three-button/landscape insets, no double padding | Device captures including system bars |
| A11 | Dialog scrolling, closing, focus management/restoration | Short-window/IME/Back interaction |
| A12 | Accurate readable filters, full identities, quantization and independent labels | Long-name/all-task/multidimensional fixtures |
| A13 | Streaming preserves draft/selection/scroll without whole-thread redraw | Program scenarios and WebView observation |
| A14 | Lazy media, no autoplay, inactive viewers released | Preview lifecycle records |
| A15 | Empty/error/unknown-progress/cancel never imply success | Failure/cancel/offline fixtures |
| A16 | No live blur/decorative loops or idle/scroll regression | Same-device/data resource and latency comparison |
| A17 | Theme changes preserve models/jobs/API/configuration | IDs, drafts and service states before/after |
| A18 | Fold/split/rotation preserve state and avoid occlusions | Actual window/continuous-region evidence |
| A19 | Frozen behavior retained: local inference, explicit downloads, recommendations, model-scoped settings, HF/Local, precise output/input tags, queue/API/templates | B01–B08, [frozen scope](../MULTIMODAL_RELEASE_PLAN.md), [v0.4.0](../CONVERSATION_V040.en.md) |
| A20 | Bilingual docs/media/notes match implementation and preserve older evidence identities | Documentation/release identity and outstanding-work list |

This round defines specifications/tokens and checks static documentation/colors/provenance. All runtime entries in [acceptance.json](acceptance.json) remain pending implementation/acceptance. [validation.json](validation.json) records only checks actually performed. Existing model-quality and device-endurance gaps stay open.
