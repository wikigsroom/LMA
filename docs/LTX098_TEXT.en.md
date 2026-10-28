# Old LTX 0.9.8: native T5 text encoder

[中文](LTX098_TEXT.md) · [DiT and sampling](LTX098_SAMPLING.en.md) · [Single complete release scope](MULTIMODAL_RELEASE_PLAN.md)

This supplies a local text-encoding component for frozen target 17. It is an unregistered research executable, with no complete-video, quality, App or physical-Android acceptance. LMA continues to update its foundation; users choose, download, import and manage external models and dependencies.

## Contract and execution

The old pipeline applies only Python `str.strip()` to prompts and uses at most 256 tokens. Native code validates UTF-8, trims Python's Unicode whitespace set, preserves case/content, and tokenizes with the external GGUF's learned vocabulary/normalization table plus the original external tokenizer config. The pinned Transformers 5.17 postprocessor always appends EOS, including after a literal EOS; truncation preserves the final EOS. Historical 4.x tokenizer behavior is not asserted.

Outputs are raw per-token final-RMSNorm embeddings, `[1,valid_tokens,4096]`, without pooling or L2 normalization, accompanied by an all-ones valid-token mask. Independent comparisons check compact inputs against the valid rows of original 256-token padding/masked inputs. An explicit PAD token supplied as content remains a valid position.

The production profile requires `t5encoder`, 24 layers, width 4096, 64 heads, key/value width 64, FFN 10240, vocabulary 32128, 32 relative-position buckets and RMS epsilon `1e-6`. Small untrained files require explicit `--fixture` and are rejected by production mode.

An independent GGML CPU graph executes bidirectional attention, relative bias, gated-GELU FFN, residuals and final normalization over read-only mapped weights. Explicit F32 tanh GELU avoids the shared runtime's F16 lookup loss; existing App libraries remain untouched. Quantized matrices are temporarily cast to F32 before each matmul, avoiding the extra Q8 activation rounding of direct quantized CPU matmuls. The allocator reuses dead matrix buffers instead of keeping the full F32 checkpoint resident. Mapped file/tensor bytes and peak graph-buffer bytes are reported separately from sampled process memory. Every input gets a fresh bounded compute graph, while the same instance reuses mapped weights. Destruction releases graph resources, mappings and vocabulary.

The CLI takes local files only, with no networking or child-process execution. It rejects unknown/duplicate keys, invalid integer/token/thread limits and oversized inputs; preserves existing outputs; and publishes no final artifact after failure/cancellation. A CPU abort callback covers actual neural evaluation. Progress distinguishes loading, encoding and compute entry.

## External assets and attribution

| Asset | Pinned source | Identity and limits |
| --- | --- | --- |
| T5 Q5_K_M encoder | `city96/t5-v1_1-xxl-encoder-gguf` @ `005a6ea51a7d0b84d677b3e633bb52a8c85a83d9` | 3,386,856,640 bytes; SHA256 `b51cbb10b1a7aac6dd1c3b62f0ed908bfd06e0b42d2f3577d43e061361f51dae`; community conversion, not an official Lightricks quantization |
| Reference config/tokenizer | `google/t5-v1_1-xxl` @ `3db67ab1af984cf10548a73467f0e5bca2aaaeb2` | Config, SentencePiece model, tokenizer config and special-token map; developer reference assets |
| Native dependency | llama.cpp @ `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` | MIT; pinned existing Android CPU-runtime identities, no research executable added to APK |

Apache-2.0 asset declarations, source/runtime/Python file hashes and individual asset identities are in the [source lock](../third_party/ltx098-text-source-lock.json) and [NOTICE](../research/ltx098_text/NOTICE). T5 licensing does not replace the separate old-LTX DiT/VAE terms.

The community GGUF marks its 100 sentinel positions as unused padding. Therefore its tokenizer metadata alone is insufficient: `TOKENIZER_CONFIG.json` is a required separately selected original file. Native code loads its sentinel names and applies the published reversed-ID convention. Independent checks compare all 32000 learned pieces/scores and the entire 237539-byte normalization table to original SentencePiece.

All weights, vocabulary, SentencePiece, normalization data and oracle artifacts stay in ignored project `build/` directories. Installation, upgrades, browsing, builds, tests and missing-asset errors never download models. Developer preparation does not establish a complete public App video-model candidate.

## Reproduction

Run from the repository root in native Windows PowerShell, following [build prerequisites](BUILD.en.md). No Docker, WSL, VM or emulator is used.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
python tools/fetch_ltx098_text.py --download --download-oracle-assets
python tools/build_ltx098_text.py
python tools/ltx098_text_oracle.py --trained
python tools/test_ltx098_text.py --trained
python tools/build_ltx098_text.py --android
```

Fetching verifies only unless an explicit download flag is supplied. An allowed mirror changes transport origin, never revision, size or SHA. Run native builds sequentially; their temporary SUBST is removed in finally. Prepare missing Python dependencies explicitly according to the lock; scripts do not install them. The reference uses hash-locked Transformers 5.17.0 sources, Torch 2.14.0+cpu, NumPy 2.4.2, SentencePiece 0.2.1 and pinned gguf-py.

CLI: `lma_ltx098_text_cli MODEL.gguf TOKENIZER_CONFIG.json REQUEST.json OUTPUT THREADS [--fixture]`. Example:

```json
{"operation":"encode","max_tokens":256,"inputs":[{"prompt":"A red balloon floats above a quiet lake."}]}
```

`tokenize` writes contiguous little-endian int32; `encode` writes contiguous little-endian F32. stdout JSON records tokens, mask, shape, byte offsets and lifetimes; stderr carries progress. Requests allow 1–4 inputs, at most 65536 UTF-8 bytes per prompt and 1–32 threads. Creating the optional `cancel_file` cancels execution.

## Evidence limits

The independent reference runs unmodified installed `T5EncoderModel` forwards. Untrained cases cover 2/24 layers, full external vocabulary, short/256-token inputs, literal PAD and vocabulary boundaries. Tokenizer cases cover whitespace, Chinese, accents, specials, unknown characters and truncation. The trained reference dequantizes the pinned GGUF to F32 and loads one original module at a time, evaluating all 219 tensors.

This checks execution semantics for that quantized file. It does **not** compare original unquantized Google weights or establish prompt/video quality. Numerical gates are locked before execution; failures require investigation. Android ARM64/API28/16KiB compilation and dependency checks remain separate from host trained inference, App registration and phone execution.

See the [numbered handoff](releases/v0.3.0-dev.21-ltx-text.md) for results and pending work. Production noise/sampling/VAE/frames/MP4, complete user assets/App management, real quality/resources/cancellation and physical Android background acceptance remain in the same full v0.3.0 alongside 01–14/16/17, every frozen subtarget and F-01–F-12.
