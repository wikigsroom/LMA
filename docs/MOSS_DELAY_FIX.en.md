# MOSS prompt, delayed state and reference scratch

[中文](MOSS_DELAY_FIX.md) · [User workflow](MOSS_TTS15.en.md) · [Original diagnostics](MOSS_REFERENCE_DIAGNOSTICS.en.md) · [Delivery and full pending scope](releases/v0.3.0-dev.43.md)

Dev.43 integrates the corrections into the actual CPU engine. ARM64 and native Windows build the same generated sources. App updates deliver only the foundation; users independently select, download, import and manage models. No model, voice, tokenizer or recognizer data enter the APK.

| ID | Correction | Checked scope |
|---|---|---|
| M01 | Ordinary Delay-architecture assistant generation no longer forces an audio_start prefix; continuation and other architectures retain their paths | Real GGUF vocabulary and unchanged official formatting methods: 7/7 exact grids, including English, Chinese, mixed text and reference lengths |
| M02 | Increment the flush counter in its first step; remove n_vq−1 trailing rows; exclude user reference audio when the assistant never opens audio | Actual native DelayState against official generation/de-delay methods: 5/5 exact step rows and codes, using fixed greedy logits without model inference |
| M03 | Release CPU batch-encoder scratch after every output code has been copied to host | 21 checks, seven real GGML computations and three releases; independent exact matrix results, persistent parameters, a concurrent live streaming graph and repeated output |

M01 follows engine architecture. M02/M03 share the native implementation without model-name branches in pages or queues, or external execution. Other frozen MOSS targets still require individual validation. Fixed-logit parity identifies algorithm differences; it does not establish trained output, text following, voice similarity, resource suitability or Android acceptance.

Execution statistics report release count, cumulative allocated buffer bytes and largest released buffer. These are **not resident-memory measurements** or a promise that a phone can run the model. Weight mappings and the independent streaming allocator remain separately owned. Actual process resources are sampled independently.

Original reports, WAVs and failures remain unchanged. Prior byte-for-byte PCM comparisons remain visible as diagnostics. Correcting autoregressive prompt/delay inputs can change output, so old PCM identity no longer establishes correctness. Actual checks still require the original text, seed, sampler and 375-step budget, natural completion, explicit truncation, cancellation and recovery.

The fresh original-text/seed/375-step reference case produces 27.44 seconds of WAV and still fails natural completion. Its failure remains required work. The recorded encoder scratch release is 7,368,704 allocated bytes; resources and quality are checked separately. [Current trained report](../verification/development/openmoss-trained.json) and [original failure](../verification/research/openmoss-reference-issue/first-run.json) remain distinct.

With existing pinned sources and explicitly acquired complete assets:

```powershell
python tools/test_openmoss_prompt.py
python tools/test_openmoss_delay.py
python tools/test_openmoss_codec_memory.py
python tools/test_openmoss.py
python tools/build_openmoss.py
python tools/test_openmoss_trained.py
python tools/test_openmoss_app_host.py --reuse-existing-local-files
```

The trained driver writes actual live events to each case's `*-events.jsonl`, retaining requests, raw logs, WAVs, resource samples and input fingerprints. Existing-file adoption uses the production full-SHA path; this does not establish large-file stream copying or Android document-provider acceptance. Desktop evidence remains explicitly host evidence. Same-phone execution, no ROOT and every complete v0.3.0 release gate remain required.

This checkpoint explicitly uses Java `--skip-reference-case`: complete asset adoption, independent settings, English output, budget error, cancellation and recovery. Current reference sampling is covered by the complete direct-native test, without claiming a fresh Java reference-generation pass. Exact dev.41 full Java reference evidence remains historical. The command above still runs the full Java suite by default; complete acceptance gates are retained. A changed native binary cannot reuse old trained-run reports.

Independent offline English ASR on the new WAVs gives zero word errors for the Kokoro control and current unconditioned MOSS English. Current reference mode still has 36 errors / 2 target words. The original dev.41/42 35/2 failure remains separately preserved; algorithm parity cannot establish text following. [Current recognition](../verification/development/openmoss-intelligibility.json). Run `python tools/render_openmoss_trained.py --audio-only`, then `python tools/test_speech_intelligibility.py --manifest research/openmoss_trained/dev43-asr-cases.json` to check verified original WAVs without rerunning the complete model. Recognition remains entirely local.

The actual Java run completes **71 checks / four children / two WAVs**. English, budget errors, sampling cancellation and recovery pass; English/recovery output matches the current direct-native WAV byte for byte, with zero network calls. This scope does not rerun Java reference generation. The complete default suite and all phone gates remain required.

![Current actual host speech and retained reference failure](media/development/openmoss-0.3.0-dev.43/openmoss-trained-contact-sheet.png)

[Waveform GIF](media/development/openmoss-0.3.0-dev.43/openmoss-trained-waveforms.gif) · [Actual-audio MP4](media/development/openmoss-0.3.0-dev.43/openmoss-trained-speech.mp4) · [Chinese WAV](media/development/openmoss-0.3.0-dev.43/openmoss-trained-zh.wav) · [English WAV](media/development/openmoss-0.3.0-dev.43/openmoss-trained-en.wav) · [Reference WAV, retained failure](media/development/openmoss-0.3.0-dev.43/openmoss-trained-reference.wav) · [Media identities](media/development/openmoss-0.3.0-dev.43/openmoss-trained-media.json). These are original host audio and waveform slides, not phone footage. The MP4 audio is explicitly AAC-transcoded; original WAV bytes remain unchanged.
