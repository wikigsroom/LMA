# m04 / DSH full-context follow-up · v1.2.2

[中文](DSH_M04_FOLLOWUP.md) · [Original v1.2.1 repair and failures](DSH_M04_REPAIR.en.md) · [Tool protocol](DSH_TOOLS.en.md)

The [derived-template attribution and complete license](../app/src/main/assets/licenses/chat-template-dolphin3-llama32-NOTICE.txt) ship in the APK. The legacy license script retains its original bytes.

## 1. Reproduced difference

v1.2.1 puts all 41 definitions into actual inference input; this alone does not establish agent quality. The marked actual DSH request contains system instructions, the user's task, a workspace `<system-reminder>`, a runtime snapshot and a time snapshot. The last four messages all use the `user` role. With roughly 19,000 input tokens, m04 can still repeat the final timestamp or invent a runtime summary without requesting a tool.

Earlier short leading/late-system controls did not cover this actual structure. A separate generic late-system reminder also produced a native parsing error; that reminder was not adopted as the repair.

## 2. Program changes

| ID | Change | Preserved constraint |
|---|---|---|
| F01 | The [weight-bound m04 v2 template](../app/src/main/assets/chat-templates/dolphin3-chatml-tools-v2.jinja) recognizes DSH runtime/time snapshots and places appended background before the associated user task or contiguous tool results | Every original message content and every definition remains; real tasks/results retain their order; no promotion to system and no fabricated results |
| F02 | Apply the same placement to historical turns, preserving the established prefix and subsequent task position | No history truncation, DSH configuration/AGENTS edits or conversion of `auto` into `required` |
| F03 | [Input preflight](../app/src/main/java/com/lma/app/ApiHost.java) matches native generation with `add_special=true, parse_special=true` | The vocabulary controls BOS/EOS; output room is calculated after those tokens, without reducing saved context |
| F04 | Explicit native output-format errors become HTTP 502 / `invalid_model_output`, including truthful streamed errors | No incomplete executable calls, false success marker or conversion of ordinary command text into execution |
| F05 | A separate explicitly marked device acceptance observer | Not shipped in the application APK; temporary request/credential files stay private, standard output contains neither prompts nor credentials, and files are removed on completion |
| F06 | Store template source in the native Jinja lexer's retained newline format; compare actual native source with packaged bytes | Keep strict hash verification; fix CRLF/trailing-newline loading failure found in an unpublished candidate |
| F07 | Repair the native parser's comma-only separator between bare JSON function records; accept the newlines/whitespace emitted by the template | Only unwrapped function records change; arrays, delimited sections, disabled parallel calls and invalid parameters remain checked; no renamed tools or fabricated results |
| F08 | Build from pinned b29 source against the core libraries actually retained in the APK; check C++ imports, 217 required exports and 16 KiB alignment | Retain the other 13 text libraries byte-for-byte; distinguish local library provenance from the original archive; preserve weight/template/settings/signature verification |
| F09 | Permit only a missing final outer `}` or dangling comma in an unwrapped canonical name/arguments record; reject unfinished native tool records after generation ends | Argument JSON must already be complete; no inferred names/arguments. Wrapped/array and nonfinal records stay strict; streaming fragments remain incremental only during generation |

The public request/history copy stays unchanged. Background placement occurs only during rendering of the reviewed template bound to the actual weight identity. Tool conversations without recognized DSH context preserve their previous rendering. Ordinary conversations without tools/history remain byte-equivalent to the embedded GGUF template. Unmatched imported weights do not inherit this rule.

## 3. Model and operation

Keep m04 from `bartowski/Dolphin3.0-Llama3.2-1B-GGUF`, revision `617f94be9dfb802a3fa0ec64b12d7d085482a308`, file `Dolphin3.0-Llama3.2-1B-Q4_K_M.gguf`, SHA256 `7ed39ee0638e18d3e47bf12e60e917c792ca5332606a72bd1882ab1f62a13a7a`.

Saved **131072 context**, **131071 output ceiling**, **8 threads**, approximately **0.7 temperature** and **off reasoning** remain. Each request still respects its explicit token ceiling and remaining context; no generation wall-clock deadline is introduced. Users choose model assets; upgrading neither downloads nor replaces weights.

Start LMA's API with the installed m04. DSH standard mode keeps `http://127.0.0.1:52187/v1`, the existing credential and its complete tools. Runtime management displays `dolphin3-chatml-tools-v2` and effective-template verification. This means definitions/parsing are ready, not that complex agent behavior has passed. Labelled Unload controls remain in runtime management, Local cards and the model picker.

## 4. Acceptance scope

Program regression covers the actual native Jinja renderer/grammar/parser, all 41 definitions, `auto/required/named/none`, returned results, historical prefix stability, non-DSH ordering and original-template equivalence. Backend checks cover BOS boundary budgets, actual native HTTP parser failure, streamed errors and recovery. These fixtures execute no trained model.

Read-only inspection of the installed GGUF confirms `llama.context_length=131072`, `llama.rope.freq_base=500000` and a `rope_freqs.weight` descriptor with 32 FP32 frequencies. No tensor data was read, weights changed or saved parameters replaced. No speculative RoPE override was introduced.

The previous unpublished APK is v1.2.2/code71, SHA256 `00b8a94dd35230f4adfcbca9325d448922cf4a2c0112a33ef1c2965ee6e21486`. Its 56 host-native, 21 real m04 SDK/runtime and five Android synthetic-parser checks remain historical evidence of that candidate. With F09, 69 host-native regressions pass, including four final-envelope positives and nine incomplete/invalid-output negatives. The final7688 APK separately passes fresh21 real m04 SDK and14 Android synthetic-parser checks; actual DSH acceptance is in sections4.2/5.1. Synthetic Android parsing executes neither tools nor models. Source/patch/library identities and reproduction are in the [build guide](BUILD.en.md) and [runtime lock](../third_party/runtime-lock.json).

An unpublished intermediate candidate `ad2213fc…` failed to start because its library referenced `std::__ndk1::__hash_memory`, available in newly built dependencies but absent from the retained older core. F08 links against the actual retained libraries and checks C++ imports. Android startup/parser and real-model SDK checks were repeated on the final patched APK; earlier passing records do not substitute.

Physical acceptance uses Motorola Edge Plus / Android 12, the actual LMA API and DSH 1.4.76/code327. The earlier candidate below is v1.2.2/code71, SHA256 `c5b91e858be6854c2ed036f14438295f8ebdaf26ca2391a78dd6a4eade1a2511`. It does not include F07 and cannot establish phone acceptance of the final patched library.

| ID | Actual DSH control | Observed result |
|---|---|---|
| D01 / F1 | New conversation,19131 input tokens, all41 tools,`auto`, command→write→read | Natural stop after36m14s; script and request for manual execution, zero calls, file absent |
| D02 / F1-plugin | Same conversation,19394 input tokens, request DSH-owned dsh-pet installation | Natural stop after2m31s; installation command example only, no execution event |
| D03 / F2 | Explicit native-call format cue in the conversation containing failed examples,19579 input tokens | Natural stop after5m43s; another script, zero calls |
| D04 / G1 | Fresh conversation without those old replies, all41 tools and workspace background retained, explicit first-call format cue | Real bash execution returned a UUID. The model then repeatedly selected read instead of write; the file remained absent. A subsequent nonprogressing generation was explicitly stopped; the loop did not pass |
| D05 / G2 | Corrective user instruction naming write; UUID still supplied only by the real tool result | Native parsing rejected a subsequent newline-separated JSON call; streaming failed and no file was created. A weight-free reproduction confirmed the separator gap. Final-APK F07 acceptance appears below; this historical failure remains unchanged |

Conversation history and prompting affect this model's observed behavior. Earlier failures do not prove the weights have no tool ability; one executed call does not establish the complete loop. HTTP200, code examples and a working screen do not qualify.

Keep the original v1.2.1 zero-call/file-absent failures. Tool protocol, this 1B model's reliability, Android permissions and plugin platform requirements remain separate conclusions. External execution or plugin installation never substitutes for DSH.

The above 00b8 candidate's fresh H1 turn contained19105 actual input tokens. At20-second sampling, decoding first appeared2034.045–2054.058 seconds after submission, approximately34 minutes; this is not an exact network first-token measurement. The model then emitted a result-only JSON object without a function name/arguments. Native parsing correctly surfaced`invalid_model_output`; no bash command executed and that UUID is not treated as a real tool result. A subsequent retry in the same conversation reused19103 input tokens. These are observations on this phone with the complete background and preserved parameters, not general phone performance or accepted agent quality.


The same H1 conversation retried with all41 tools and the original parameters, reusing19103 cached input tokens. After roughly200 generated tokens without a complete delivered call, the tester explicitly used DSH’s Stop control. LMA recorded `request_cancelled`; its queue and native slot subsequently returned idle. No application generation deadline was introduced. This cancelled run establishes neither an accepted workflow nor that the model cannot call tools.

A single read-only `dumpsys` sample during decoding at2026-11-06T20:44:06Z measured native-process PSS5,080,059KiB, RSS3,836,660KiB and Swap PSS1,245,212KiB. This records the observed resource cost of this context configuration; it is neither a peak measurement, a general performance result nor proof that swapping caused the low speed. Saved parameters were unchanged.

The third H1 round contained19536 actual input tokens and ended with server-recorded`invalid_model_output`. The tester pressed Stop near completion, so this is not relabelled as successful cancellation. An independent fresh G4 conversation contained19167 input tokens and naturally ended after34 generated tokens with the correct`bash` name and complete UUID-command arguments, but a missing final outer `}` and dangling comma. F09 addresses this unambiguous envelope boundary; it never manufactures calls from result-only JSON, missing arguments or the wrong selected function.

### 4.1 Actual observations on the final F09 APK

The final APK SHA256 is`7688cfb962a6283cacb99e2b5500be3b36dd9de6b91593cfe1f6db9eb22ee46b`. Its native libraries pass14 weight-free parser checks on the phone. Those checks execute neither models nor tools.

J1 retains41 tools, complete background and saved parameters, with19168 initial input tokens. Twenty-second slot sampling bounds the first observed decoded token to1951.024–1971.048 seconds after the request, about33 minutes. This is not exact network TTFT. With an explicit initial format cue, the model emits`bash`; DSH actually executes the UUID command and returns its result with the matching call ID. The next19321-token request reuses19201 cached tokens, including the previous assistant call.

The autonomous continuation naturally stops but claims a write in ordinary text without any`write/read` calls. Independent read-only verification finds the owned target absent. The task fails despite the real first bash call. Later stepwise format cues retain all41 tools; the accepted chain in section4.2 is marked`guided_stepwise=true` and does not establish unguided general agent reliability.

Ten health requests during this APK's input computation take a median7.491ms, range4.543–17.590ms, without another generation. A single resource sample reportsPSS4,980,132KiB, RSS4,982,056KiB and zero swapped pages. It is not a peak, a controlled comparison or proof of the cause of slow generation. The native slot still has131072 context; saved parameters remain unchanged.

### 4.2 Accepted explicitly guided tool chain

On the same final APK, actual DSH, m04 and saved parameters, explicit stepwise format cues complete this chain. Every round retains41 definitions. The model emits calls, DSH executes them, and ADB only independently reads the owned file.

| Step | Actual call ID and matching result ID | Verified result |
|---|---|---|
| bash | `U4LHCvIMig9MPRK3L3ivmtAtReMJCoTe` | Actually executes`cat /proc/sys/kernel/random/uuid` and returns a fresh UUID |
| write | `5xtTCfrLNWk95P3wKKxSpjGd8YFmWB8H` | DSH creates the owned test file with that UUID. The model omits the requested trailing newline; the actual file is36 bytes |
| read | `lxXeUSLThqM2fqFMdNVaBFW3003njsdp` | DSH independently reads the same file; its result contains the UUID, then the model answers with the actual read value |

The file is`/sdcard/Android/data/app.dsh.mobile/files/lma-m04-j1.txt`. [Actual DSH evidence](../verification/releases/v1.2.2/physical-dsh.json) includes argument JSON, full results/hashes, matching IDs, file hash and answer. The first completed samples for guided write/read occur438.295 and315.828 seconds after sending, with20-second sampling rather than exact network timing. After writing, the model misinterprets the tool's“Created file” confirmation as file content; only after actual read does it correctly answer with the UUID. This distinction remains recorded.

[Phone screenshots, original-speed video and GIF](media/device/v1.2.2/dsh-loop/manifest.json) inspect the completed read entry and answer. They do not record the whole inference run or replace JSON call/file evidence. The chain is explicitly`guided_stepwise=true`. Initial J1 autonomous continuation fails, so guided success does not establish general unguided agent reliability.

A subsequent plugin request in that conversation naturally stops while repeating the UUID task, without an installation call; keep this J4 failure. The fresh plugin conversation separately passes in section5.1; the file chain does not count as plugin installation.

## 5. Android plugin boundaries

Review also covers the[exact DSH v1.4.76 source](https://github.com/Soodok/Deepseek-Harness-Local-Android/tree/93827371ba09a672e431d6fa4fe27bf3f8e92bda). Dependencies and the mount list belong to`$DSH_HOME/profiles/web`. Its plugin center invokes the installed engine's Node entry with`plugin --profile web add`, handling engine compatibility, dependency builds and installation state. Availability of a global`dsh` executable still requires an actual tool check.

`PC2005-cloud/dsh-pet` is the`dsh-pet` web plugin. Android's`@xiaopb/dsh-pet-bridge` floating-pet integration is a separate plugin and cannot substitute for the selected target. Check command completion, real dependency/profile state and activation after engine reload separately; source review does not establish installation. No silent engine-version exemption is written.

ADB supplies test input and independent read-only verification; it never substitutes for DSH tool execution. It does not establish model access to Accessibility, system overlay or other application-control permissions.

### 5.1 Accepted DSH-owned installation and activation

J6 uses a fresh plugin conversation on the final APK, retaining all41 tools, weights and saved parameters. The model emits the real`bash` call`aAG6aDYwd355SkJSNadUsEWnJ5dA2qMY`; DSH executes its own installed Node entry with`plugin --profile web add dsh-pet`. The matching-ID result includes`dependencies: + dsh-pet 0.4.3` and`Done in 11.9s using pnpm v12.16.1`. No ADB/host script or manual Install/Upgrade action installs the package; no compatibility exemption is written. The prompt supplies the command and call format. The user explicitly accepts this process as autonomous installation for this acceptance; that guidance remains disclosed.

Independent inspection of DSH's own Installed page reads actual profile dependencies and package manifests, showing`dsh-pet 0.4.3`. Restarting the engine through DSH's own control returns it to Ready and visibly loads the web pet. [Installed-entry and post-reload screenshots, original-speed MP4/GIF](media/device/v1.2.2/dsh-plugin/manifest.json) bind the same APK; [JSON evidence](../verification/releases/v1.2.2/physical-dsh.json) retains the real call, arguments, result and hashes. DSH's tool result exposes no numeric exit status, so evidence records`exit_code:null` with its source rather than inventing zero. Package-manager completion, actual manifests and visible activation independently support completion.

Earlier J5 emits the correct command and complete arguments but repeats`timeoutMs` at the outer root. Strict parsing returns`invalid_model_output` without execution; keep this failure instead of dropping a field and reporting success. J6 succeeds after another explicit format cue. Its first completed sample is727.416 seconds after sending; the UI reports11m48s, not exact network timing. The model claims “latest”, but the Installed page shows0.4.5 available alongside installed0.4.3. Only0.4.3 installation is verified; no upgrade occurs and model prose never substitutes for version checks.

Acceptance covers the DSH web plugin and visible pet. Android system-overlay bridging, payment/wallet, voice and arbitrary application control are outside this installation scope. Keep J4's zero-install-call result, J5's format failure and earlier candidate failures; successful installation does not erase model-reliability limits.

## 6. Strict-validation and parser acceptance

A positive requires the actual model to emit a declared function with valid arguments and a call ID, followed by a client result carrying that same ID. Selection modes, streamed assembly and continued rounds have separate records. Weight-free parser fixtures and trained-model requests are counted separately.

The final APK also passes direct public-API controls using the complete actual first-turn DSH messages and all41 definitions: `required`, named`bash` and streamed named`bash`, taking156.121,122.333 and156.050 seconds. Each returns real`finish_reason: tool_calls` and valid bash arguments; streaming reassembles indexed IDs, names and arguments. These three controls generate calls without executing commands and are not extra DSH tool executions. Every message and definition remains intact. The diagnostic request ceiling is explicitly192 tokens; saved model settings remain unchanged. Actual DSH`auto` and continued result execution are accepted separately in sections4/5.

Negatives distinguish admission from delivery: the invalid JSON Schema type value`type: "not-a-json-schema-type"` actually returns400 with parameter`tools[0].function.parameters.type`; generated arguments that violate the declaration return502/`invalid_model_output`. Streaming delivers the real error without executable fragments or a successful`[DONE]`. The dedicated latter diagnostic deliberately combines`const: "not-an-email"` with`format: "email"`, an empty intersection. It is not an ordinary client task, and a model correcting a value is not counted as an observed rejection.

Both output negatives actually pass on the final APK: the nonstreamed request returns502 after72.228 seconds; the65.601-second stream has HTTP200 headers but an actual`invalid_model_output` error event. Neither delivers executable fragments or successful`[DONE]`. Keep the corrected test assumption as well: a valid array-root schema is not an invalid type value and is not an observed admission400. It enters generation, with nonmatching arguments rejected by strict delivery validation. All41 DSH definitions remain unchanged; no tool is removed for this diagnostic.

Argument evidence preserves two byte representations: DSH-returned history JSON, and an equivalent whitespace/key-order serialization matched to the recorded server SHA256. Parsed values must be identical; the latter must match the actual server call ID and hash exactly. Its provenance explicitly says hash-matched reconstruction, not a separately captured response body, and actual execution arguments are never rewritten. Counts describe retained acceptance records in each report, not lifetime telemetry for every transport attempt during debugging.

The final[SDK/runtime record](../verification/releases/v1.2.2/physical-tools.json) contains21 checks and six real short-input generations. Two concurrent requests take8.171 seconds, health peaks at25ms, and API reload after actual Unload takes21.153 seconds. These belong to a separate short-input session; they neither replace full-context DSH measurements nor prove a comparable improvement in the33-minute first-decode observation.

F09 recognizes only an already complete canonical argument object and a known function name. It does not repair missing arguments, unfinished strings, inferred names, result-only objects or incomplete wrapped/array records. A wrong but valid model-selected function remains its actual choice for DSH to handle; it is never rewritten to the test's expected function.

