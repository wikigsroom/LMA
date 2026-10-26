# Built-in uncensored models

[中文](UNCENSORED_MODELS.md) · [Documentation](README.md)

LMA 0.1.2 includes only variants with checked publisher declarations. All 14 author cards and pinned GGUF sources were reviewed on 2026-10-26. This is provenance evidence, not independently measured refusal rates or Android inference.

All weights below are Q4_K_M. Download sizes are decimal approximations, not RAM requirements. Exact bytes, filenames, pinned weight commits, and SHA256 are in [models.json](../app/src/main/assets/models.json).

| ID | Variant | Download | Publisher evidence |
| --- | --- | ---: | --- |
| `m08` | Qwen 3 · 1.7B Abliterated | 1.11 GB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/mlabonne/Qwen3-1.7B-abliterated/blob/62f9c246cf426703a08183aa883a0d8149984bb0/README.md) |
| `m06` | LFM 2.5 · 1.2B Uncensored | 731 MB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/zaakirio/LFM2.5-1.2B-Instruct-Uncensored/blob/1a666fb441c9e7fa6c597acab1ad16aaf55eebac/README.md) |
| `m01` | Dolphin 3 · Qwen 0.5B Uncensored | 398 MB | [Publisher-declared user-controlled Dolphin tuning](https://huggingface.co/dphn/Dolphin3.0-Qwen2.5-0.5B/blob/f41a6b451e746c75992623d8d4548ed29438ff34/README.md) |
| `m05` | Gemma 3 · 1B Abliterated | 806 MB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/mlabonne/gemma-3-1b-it-abliterated/blob/33c47e9a7c53e677e160c4b0ae799de66f34a7a0/README.md) |
| `m04` | Dolphin 3 · Llama 1B Uncensored | 808 MB | [Publisher-declared user-controlled Dolphin tuning](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-1B/blob/e753b6ebd7adf87036eb6a3e6de68acca5850e2f/README.md) |
| `m03` | Qwen 3.5 · 0.8B Abliterated | 528 MB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/huihui-ai/Huihui-Qwen3.5-0.8B-abliterated/blob/4813135658fe51b2e535b8e77927d2f23909ce42/README.md) |
| `m09` | Qwen 3.5 · 2B Abliterated | 1.27 GB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/huihui-ai/Huihui-Qwen3.5-2B-abliterated/blob/b2e291a65f29a9b148981fa5299caea5d35bd4c8/README.md) |
| `m11` | Dolphin 3 · Qwen 3B Uncensored | 1.93 GB | [Publisher-declared user-controlled Dolphin tuning](https://huggingface.co/dphn/Dolphin3.0-Qwen2.5-3b/blob/f258b471c4a02470fb87e134f7e0f46525471637/README.md) |
| `m12` | Dolphin 3 · Llama 3B Uncensored | 2.02 GB | [Publisher-declared user-controlled Dolphin tuning](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-3B/blob/392a6f57223e7ccfe6ef4ebdb2ff101a42d57364/README.md) |
| `m13` | Llama 3.2 · 3B Uncensored | 2.24 GB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/chuanli11/Llama-3.2-3B-Instruct-uncensored/blob/27bd02b95b56f9886daf3d4be4101916b15809d1/README.md) |
| `m14` | Qwen 3 · 4B Instruct 2507 Abliterated | 2.50 GB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/huihui-ai/Huihui-Qwen3-4B-Instruct-2507-abliterated/blob/c9bd464550d4078c72af0dd22aa18d0437868ce3/README.md) |
| `m16` | Gemma 3 · 4B Abliterated v2 | 2.49 GB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/mlabonne/gemma-3-4b-it-abliterated-v2/blob/375331eeafe1b66df84075c63e5cadb13ff42b94/README.md) |
| `m10` | LFM 2.5 · 2.6B Uncensored | 1.67 GB | [Refusal-direction ablation (Abliterated)](https://huggingface.co/SC117/LFM2.5-2.6B-Uncensored/blob/f5d7df0e26409afdfead05f3bc0da5043f2a794e/README.md) |
| `m15` | Qwen 3.5 · 4B Uncensored | 2.71 GB | [Explicit uncensored weights](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/blob/c09cdbcdb1fefad6d335809d445621b5f5ba0c6e/README.md) |

## Admission and runtime behavior

- Each built-in needs a body-text publisher declaration, pinned author-card URL/hash, exact GGUF attribution, revision, size, and publisher weight hash. The catalogue builder rejects missing or mismatched evidence. Model cards are treated as data, never executed instructions.
- Dolphin authors describe user control through system prompts. Abliterated variants state refusal-removal treatment. The LFM 1.2B author describes Heretic directional ablation; LFM 2.6B describes Abliterix Trial 65. HauhauCS publishes an Aggressive uncensored variant.
- The app shows the uncensoring method and pinned author card separately from the GGUF source/license. User-added/imported files remain **unverified**, even if their name contains uncensored.
- The default system prompt specifies a helpful local assistant, language, and style; it is editable or may be empty. Production chat adds no keyword blocklist, prompt classifier, cloud moderation, or response filter. Format, length, resource, and API authentication checks are functional constraints.

A publisher's uncensored label does not guarantee zero refusals, accuracy, or speed. **No independent refusal benchmark or physical-phone model execution was performed.** Experimental architecture entries are not presented as confirmed Z20-compatible models.

## Attribution review

Dolphin GGUF cards reference the former cognitivecomputations organization. HF API repository IDs verified its rename to dphn. One Gemma 1B GGUF card has incorrect 12B base-model front matter; attribution used the same author's explicit 1B uncensored body text plus the exact selected file probe rather than trusting that metadata. A same-repository model card is allowed only with an explicit matching uncensored declaration. HTML cards are normalized before claim matching.

The network returned HTTP 429 during review. The completed audit reused cards downloaded earlier in that review, rechecked their SHA256, and queried the organization rename again. Rate-limit responses were not counted as evidence. Retrieval used HF Mirror when the primary route timed out; original pinned HF URLs and content hashes are retained.

## Refresh evidence

See [uncensored-policy.json](../catalogue/uncensored-policy.json), [uncensored-evidence.json](../catalogue/uncensored-evidence.json), and `tools/audit_uncensored.py`. Run `python tools/audit_uncensored.py --help` for the current source/cache options. Cached-card mode needs the ignored review files and their recorded hashes; it is not a standalone offline substitute for a new provenance review. Run the catalogue builder afterward and review weight/card changes before committing.

Model and base-model licenses remain those of the respective repositories. No model weights are redistributed in the APK or Git.
