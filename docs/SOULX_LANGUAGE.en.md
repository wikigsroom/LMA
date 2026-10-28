# SoulX language model and complete host pipeline

[中文](SOULX_LANGUAGE.md) · [Reference/acoustic stages](SOULX_REFERENCE.en.md) · [Numbered delivery](releases/v0.3.0-dev.20-soulx-language.md) · [Complete release scope](MULTIMODAL_RELEASE_PLAN.md)

This work adds native CPU Qwen3 text-to-semantic-code execution, the actual publisher tokenizer, up to four reference speakers and bounded history. Fresh text passes through trained S3/CAMPPlus, Qwen3 and Flow/HiFT and produces 24 kHz WAV in the complete **Windows development host** check. This is not the Android inference solution. ARM64 compilation is separate; user bundles, App jobs/API, quality/resource acceptance and physical Android remain pending. Research executors are unregistered and excluded from APK. Public release remains v0.2.0; development APK remains dev.20.

## Tokenizer compatibility

The [official pinned model](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B/tree/c2af285fc7ec68a4d3402deae7d2e215ab67fb32) and [verified earlier community quantization](https://huggingface.co/mradermacher/SoulX-Podcast-1.7B-GGUF/tree/400348052b80b513722ead19c4f09839ef0455a2) have different speech vocabularies:

| Layout | Vocabulary | First semantic code | Audio start | Speech EOS |
| --- | ---: | ---: | ---: | ---: |
| Current pinned official conversion | 160156 | 153595 | 153477 | 153478 |
| Earlier community Q4_K_M | 159488 | 152927 | 151674 | 151675 |

Generic Qwen EOS 151645 cannot stop speech. Some older configuration numbers in the official assets also disagree with their actual tokenizer/weights. The controller derives markers from the selected GGUF and checks all 6561 contiguous codes, four speakers and distinct structural markers. An architecture name alone is insufficient.

The official conversion uses all three safetensor shards, 311 tensors and 28 layers, with no reduced or randomly initialized network. [Source/asset pins](../third_party/soulx-language-source-lock.json) fix revisions, lengths and SHA256. Approximately 4.13 GB of official inputs are fully converted to F16 and then Q4_K_M by the same llama.cpp revision as the existing Android text runtime. Failed conversions preserve diagnostics and original assets. Windows model reads use UTF-8; the pinned quantizer writes ASCII filenames relative to a Unicode-safe working directory, without modifying upstream source.

## Execution contracts

| ID | Capability | Implementation and limits |
| --- | --- | --- |
| SL-01 | Text | Strict UTF-8,≤64KiB per segment; original three non-overlapping CJK/English whitespace passes and punctuation; structural control tokens rejected, expressive text retained |
| SL-02 | References | 1–4 explicit reference transcripts/code sequences,1–375 codes each, 0–6560; targets select an existing speaker; task prefix only on first reference |
| SL-03 | History | Up to 64 turns; original references retained; recent complete turns and older text-only turns rebuilt within bounded context; no hidden cross-request cache |
| SL-04 | Resources | Context 256–8192, threads 1–32, batch 1–512, output reservation 1–3000 per turn,total semantic codes≤24000; required references/history/target/reservation must fit or fail locally |
| SL-05 | RAS | Unique generated-token repetition penalty ignores prompt; min-new-tokens/temperature/top-k/top-p precede candidate sampling; recent-window repetition may restore raw logits before an independent final draw |
| SL-06 | Greedy extension | temperature 0 requires explicit `use_ras=false`, for deterministic regression rather than the upstream stochastic default |
| SL-07 | Completion | Only semantic codes and final actual speech EOS accepted; capped output stays explicitly truncated, with a history-only delimiter that is not counted as generated EOS |
| SL-08 | Lifetime/cancellation | One model/context, CPU; successful receipt only after destruction; cancellation before loading, inside actual neural decoding and after token generation |

Defaults: temperature .6, repetition 1.25, top-k 100, top-p .9, min 8, max 3000, RAS window 25/tau .2. A smaller context requires an explicitly smaller output reservation. Upstream RAS can undo **all** processors, including min-new-tokens and filtering; it is not a strict minimum-duration guarantee. Non-semantic output fails locally instead of being silently masked or interpreted as audio.

See [language.cpp](../research/soulx_language/language.cpp) / [policy.hpp](../research/soulx_language/policy.hpp). Android loads only the fixed baseline CPU library adjacent to the actual packaged libllama, never backends from model directories, CWD or environment search paths. No network inference or process fallback exists. Python/PyTorch are developer export/oracle dependencies; future App users must not need these commands.

## Evidence

| ID | Check | Actual result |
| --- | --- | --- |
| V-01 | [Language](../verification/development/soulx-language.json) | 546 assertions /20 actual native host children; full trained Q4 generation/repeat, tokenizer, cancellation and independent upstream comparisons |
| V-02 | Protocol | 115 normalization/tokenizer texts; 12 probability/token/RAS cases;12-turn histories with 1/2/4 references against actual publisher function blocks |
| V-03 | Full original forward | All 160156 logits for one 43-token context from original HF BF16 vs native Q4: cosine0.999914,RMSE0.187364,top20 overlap0.85; predefined gates.99/.5/.4 |
| V-04 | [ARM64](../verification/development/soulx-language-arm64.json) | 327,576 bytes,NDKr30/API28/16KiB,fixed existing llama/ggml dependencies,no network/process imports; no Android execution |
| V-05 | [Complete fresh-text trained host pipeline](../verification/development/soulx-pipeline.json) | 60 assertions /5 sequential native children /4 reference and36 acoustic graph runs /5 trained components; two new texts→WAV |

Normalization, RAS and history oracles execute pinned publisher function blocks and actual HF processors. The neural oracle loads all original publisher weights independently of the quantized model. Numerical agreement is not speech/quantization quality acceptance.

Two fresh synthetic PCM references and English/Chinese texts produce 1.44 / 1.76 seconds of 24 kHz mono 16-bit WAV. These references have no real-person speech or valid transcript; outputs verify execution, lengths, ranges and container structure, without intelligibility, speaker similarity, prosody or listening conclusions. They are not product speech demonstrations. WAVs and original/converted weights remain in ignored build directories, outside Git/APK/Release. Earlier253 acoustic checks retain their original S3-code reconstruction scope rather than being relabeled as earlier TTS evidence.

## Reproduction

First explicitly prepare the four trained reference/acoustic components and current evidence using the [reference guide](SOULX_REFERENCE.en.md). Use native Windows and project-local build caches only; no Docker/WSL/VM/emulator. Code acquisition is separate from model acquisition:

```powershell
git clone --no-checkout https://github.com/ggml-org/llama.cpp.git build/native-src/llama-soulx
git -C build/native-src/llama-soulx checkout b29c606e28a01b1bc8c1351026a0fa6e616bf6c4
python -m pip install --target build/soulx-language-python --cache-dir build/pip-cache --no-deps sentencepiece==0.2.1
python tools/fetch_soulx_language.py
# Only explicit flags request official weights or the community comparison asset.
python tools/fetch_soulx_language.py --download
python tools/fetch_soulx_language.py --community-gguf
python tools/build_soulx_language.py
python tools/export_soulx_language.py --output-dir build/soulx-language-official
python tools/test_soulx_language.py
python tools/build_soulx_language.py --android
python tools/test_soulx_pipeline.py
python tools/export_development.py
python tools/check_repository.py --development
```

Reuse existing clones only after checking the fixed revision and preserving local changes. Existing output directories are never overwritten. Explicit `--origin https://hf-mirror.com` changes file transport only and retains publisher SHA256 verification. Run host/Android builds sequentially; each script removes only its own SUBST alias.

Actual developer versions: torch2.14.0+cpu,transformers5.17.0,tokenizers0.23.2,numpy2.4.2,safetensors0.8.0,sentencepiece0.2.1. Conversion receipts report them rather than claiming an identical upstream requirements environment. HF reference execution is local-files-only with remote code and Hub access disabled. The [NOTICE](../research/soulx_language/NOTICE) retains SoulX Apache-2.0 and llama.cpp MIT attribution; model-card licensing is checked per source, not generalized to other HF models.

## User assets and remaining release work

App updates supply the foundation only. Models/tokenizers/codecs/voices/languages remain explicit user-selected downloads/imports, with pause/resume, update/delete and per-model settings. Installation, upgrade, browsing or missing assets do not start transfers. Flat peers and independent text/image/video/audio/foundation tags remain; recommendations m08→m06→m01 and the separate Uncensored tag are preserved.

Still required: complete explicit user bundles, same-phone WAV input and native execution, App jobs/API/artifacts, resource admission/lifecycle; fresh-input offline speech quality/resources/cancellation/cleanup; physical Android three load/unload cycles,15-minute screen-off,one-hour alternating API and upgrade retention. No phone is available. Host execution and ELF compilation do not satisfy those gates.

Existing text,F-01–F-12,01–14/16/17 and every frozen subtarget,nine MOSS variants,SD1.5/SDXL LoRA,exact old LTX-Video2B0.9.8distilled,A1–A11/R-01–R-05 all remain in one complete v0.3.0. No scope reduction, split release or early Release. This work has no UI change; existing screenshots/recording/GIF remain UI FIXTURE.
