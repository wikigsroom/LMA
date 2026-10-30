# MOSS reference input: independent diagnostics

[中文](MOSS_REFERENCE_DIAGNOSTICS.md) · [Model usage](MOSS_TTS15.en.md) · [Full pending scope](releases/v0.3.0-dev.42.md)

Dev.42 investigates existing actual failures without changing production native engines, weights or sampler settings. Reference natural completion and text following still block acceptance.

## Official formatting comparison

Nine developer files pin official `OpenMOSS-Team/MOSS-TTS-v1.5@cdd3b911b1585e3f2dbc7775ef10f9926f58850a`: config, processor, template and tokenizer, verified against the [source lock](../research/openmoss_reference/official-sources.json). The diagnostic compiles the actual generated production pipeline translation unit, using real GGUF vocabulary and unchanged official formatting method bodies. Seven grids cover English, Chinese, several reference lengths and mixed script.

**0/7 match exactly**: native formatting adds one assistant `audio_start` row; every other grid cell matches. This vocabulary/formatting probe executes neither backbone nor codec and does not establish the generation failure's cause. The [original report](../verification/research/openmoss-prompt-issue/first-run.json), driver and raw output are retained.

An actual CPU candidate removed only that row while keeping the original reference text, seed, sampler settings, 375-step limit and full weights. Its 1800-second deadline expired at step 332/375, without a WAV or complete execution result. It **is not adopted**. This timeout is neither output-limit termination nor a natural-completion fix. The [original candidate report](../verification/research/openmoss-prompt-candidate/results.json), request, logs, driver and source remain unchanged.

## Independent ASR on original audio

The developer explicitly acquired pinned [OpenAI Whisper tiny.en](https://huggingface.co/openai/whisper-tiny.en/tree/87c7102498dcde7456f24cfd30239ca606ed9063), then transcribed complete original WAVs offline on local CPU. No target text or initial prompt is supplied. ASR weights/tokenizer data enter neither APK nor Git; the App gains no downloads. See the [developer asset lock](../research/speech_asr_reference/assets.json).

| Original case | Independently fixed target | Recognition |
|---|---|---|
| Kokoro control | Hello world. The sun is shining. | Exact normalized words; 0 errors |
| MOSS unconditioned English | Hello world. | Exact normalized words; 0 errors |
| Original MOSS reference mode | Hello world. | Repeated reference content and extra words; 35 errors / 2 target words |

The reference WAV lasts 27.44 seconds, SHA `6a6080b55f241563f95ff023c0c4c609127453d6a388f0ac5d94b28dd8e06808`. It shows a text-following failure signal besides failed natural termination. WER can exceed 100%; 35/2 is 17.5. Recognition can err; this does not establish subjective quality, voice similarity, every language or Android acceptance.

[Current reproducible report](../verification/development/speech-intelligibility.json) · [First independent capture](../verification/research/openmoss-reference-asr/original-transcriptions.json). The tool exits nonzero on mismatch, retaining two passes and one failure without relaxing its threshold.

## Developer reproduction

```powershell
# Defaults verify existing assets offline; only explicit --download fetches references.
python tools/fetch_openmoss_reference.py
python tools/fetch_speech_asr_reference.py
python tools/test_openmoss_prompt.py
python tools/test_speech_intelligibility.py
```

The prompt tool's final cache-layout adjustment has not been rerun; its failed original driver/source snapshots remain historical evidence. ASR uses torch 2.14.0+cpu, transformers 5.17.0 and SciPy, two CPU threads, greedy / beam=1 / max_new_tokens=128. WAVs over 30 seconds are rejected rather than cropped. These developer checks do not change the same-Android requirement or add external execution.
