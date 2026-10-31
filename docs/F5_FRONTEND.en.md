# F5-TTS v1 Chinese frontend

[中文](F5_FRONTEND.md) · [Material foundation](LOCAL_MATERIALS.en.md) · [Remaining scope](REMAINING_ADAPTATION.en.md)

Development adds a separate **F5-TTS v1 · official-compatible Chinese frontend** component recipe. The published v0.3.5 APK still uses its previous dictionary implementation. This document covers unreleased code pending the next complete APK delivery.

## 1. Selection and use

1. Obtain the selected F5 v1 Base, matching Vocos and `vocab.txt` under their respective licenses. Existing models and settings remain available.
2. Explicitly prepare `f5-frontend.json` as described below. It contains word frequencies, HMM probabilities and pronunciation data, with no speech neural weights. The APK contains no such tables and never acquires them during installation, browsing or upgrade.
3. Choose the new component recipe and select the model, vocoder, vocabulary and frontend JSON. Save them as a model bundle and manage its files and settings through Local.
4. Select a mono 24 kHz WAV lasting 1–12 seconds, enter its accurate transcript and the target text. Steps, speed, CFG, seed, duration and frame budget belong to this model; limits are enforced by the foundation.
5. Preflight and enqueue. C++ on the phone performs segmentation, pronunciation and model execution. Python, Termux and other devices are unnecessary at runtime. This adapter produces a complete WAV; chunked audio streaming is not claimed.

The original `f5_v1_safetensors_cpu_expansion_v1` recipe retains legacy pronunciation dictionaries. Only bundles explicitly selecting the new frontend asset use it. Existing user pronunciations are not silently replaced.

## 2. Exact program boundary

| Area | Contract |
| --- | --- |
| Reference | F5 `convert_char_to_pinyin`, revision `45868abaabd74aabf03cd673d6dd00cc9d9c01ae` |
| Segmentation | rjieba 0.2.2 / jieba-rs 0.11.0 default frequency DAG, HMM, unknown-word and non-Han rules |
| Pronunciation | pypinyin 0.55.0, `Style.TONE3`, `tone_sandhi=True`; finite entries are prepared by the pinned library, with longest-entry matching on the phone |
| Formatting | Publisher mixed-language spacing, punctuation translation and per-character branches; unknown vocabulary IDs map to 0 |
| Bounds | Strict UTF-8; 65,536 bytes / 12,000 characters / 24,000 tokens per input; linguistic asset at most 96 MiB |
| Failures | Wrong versions, nonfinite probabilities, alignment errors, malformed JSON and invalid UTF-8 fail explicitly |

Equivalence covers the default dictionaries and this function. Custom rjieba dictionaries, modified pypinyin global tables, other versions and the complete F5 Python audio pipeline are outside that comparison.

## 3. Explicit offline preparation

Use native Python without virtualization. Preparation needs pypinyin 0.55.0; reference tests also need rjieba 0.2.2. `third_party/f5-frontend-source-lock.json` pins source archives, linguistic data and license identities.

```powershell
# Fixed source, text data and licenses only; no speech weights/installers
python tools/fetch_f5_sources.py
python tools/export_f5_frontend.py `
  --jieba-dict build/frontend-reference/jieba-data/dict.txt `
  --hmm-model build/frontend-reference/jieba-macros/src/hmm.model `
  --output my-assets/f5-frontend.json
```

Choose a new output path. The accompanying `.receipt.json` records actual bytes, SHA256, entry counts and dependency versions. Copy only the explicitly selected assets to the phone; the preparation computer never participates in phone inference.

## 4. Program validation

`python tools/test_f5_frontend.py` compiles the production C++ frontend and compares 2,222 fixed/random mixed texts against the pinned F5 function, rjieba and pypinyin. It checks segmentation, tokens and IDs, polyphones, sandhi, punctuation, English, rare characters, emoji, bounds and malformed resources. **6,671 assertions** pass; complete trained-model downloads/runs and physical-device checks are zero.

Source and license references accompany the tools. Linguistic tables remain independently prepared user assets. Current source fingerprints determine evidence validity; frontend equivalence does not establish voice quality or phone performance.
