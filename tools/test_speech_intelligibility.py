"""Local English ASR diagnostic on actual WAVs, without transcript hints.

Default cases intentionally retain a known MOSS reference text-following failure.
This is an independent diagnostic, not full speech-quality or phone acceptance.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import time
import wave

from evidence import current, fingerprint
from fetch_sd15_trained import sha
from fetch_speech_asr_reference import CACHE, verify

ROOT = Path(__file__).resolve().parents[1]


def words(value):
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", value.lower())


def distance(reference, hypothesis):
    previous = list(range(len(hypothesis) + 1))
    for i, left in enumerate(reference, 1):
        row = [i]
        for j, right in enumerate(hypothesis, 1):
            row.append(min(previous[j] + 1, row[-1] + 1, previous[j - 1] + (left != right)))
        previous = row
    return previous[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'research/speech_asr_reference/openmoss-original-cases.json')
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    manifest.relative_to(ROOT)
    cases = json.loads(manifest.read_text(encoding='utf-8'))['cases']
    before = fingerprint('tools/test_speech_intelligibility.py', 'tools/fetch_speech_asr_reference.py',
                         'research/speech_asr_reference', manifest.relative_to(ROOT).as_posix())
    assets = verify()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import numpy as np
    import torch
    import transformers
    from scipy.signal import resample_poly
    from transformers import WhisperForConditionalGeneration, WhisperProcessor
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    folder = ROOT / 'build/speech-intelligibility-tests' / ('run-' + str(time.time_ns()))
    folder.mkdir(parents=True)
    processor = WhisperProcessor.from_pretrained(str(CACHE), local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(str(CACHE), local_files_only=True,
        dtype=torch.float32, attn_implementation='sdpa').eval()
    results = []
    for case in cases:
        path = (ROOT / case['path']).resolve()
        path.relative_to(ROOT)
        if sha(path) != case['sha256']:
            raise ValueError('Original WAV identity changed: ' + case['name'])
        expected = words(case['expected_text'])
        if not expected:
            raise ValueError('Use a nonempty independently fixed English reference')
        with wave.open(str(path), 'rb') as stream:
            if stream.getsampwidth() != 2 or stream.getnchannels() not in {1, 2} or stream.getnframes() <= 0:
                raise ValueError('Expected actual mono/stereo PCM16 WAV')
            rate = stream.getframerate()
            audio = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2')
            audio = audio.reshape(-1, stream.getnchannels()).astype(np.float32).mean(axis=1) / 32768
        if rate != 16000:
            common = math.gcd(rate, 16000)
            audio = resample_poly(audio, 16000 // common, rate // common)
        if len(audio) > 30 * 16000:
            raise ValueError('This probe requires a full WAV of at most 30 seconds; no silent cropping')
        features = processor(audio, sampling_rate=16000, return_tensors='pt', return_attention_mask=True)
        start = time.monotonic()
        with torch.inference_mode():
            output = model.generate(input_features=features.input_features, attention_mask=features.attention_mask,
                max_new_tokens=128, do_sample=False, num_beams=1, return_dict_in_generate=True)
        transcript = processor.batch_decode(output.sequences, skip_special_tokens=True)[0]
        errors = distance(expected, words(transcript))
        result = dict(**case, transcript=transcript, normalized_reference=expected,
            normalized_hypothesis=words(transcript), word_errors=errors,
            word_error_rate=errors / len(expected), exact_words=errors == 0,
            asr_tokens=int(output.sequences.shape[-1]), asr_seconds=time.monotonic() - start,
            seconds_audio=len(audio) / 16000, prompt_hint_supplied=False)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    current(before)
    report = dict(schema='lma.speech-intelligibility-diagnostic/1', cases=results,
        passed=sum(x['exact_words'] for x in results), expected_cases=len(results),
        all_exact_words=all(x['exact_words'] for x in results), asr_assets=assets,
        torch_version=torch.__version__, transformers_version=transformers.__version__,
        execution=dict(device='cpu', threads=2, do_sample=False, num_beams=1, max_new_tokens=128),
        model_inference=True, remote_inference=False, apk_model_data=False, physical_android=False,
        speech_quality_accepted=False, voice_similarity_accepted=False, release_accepted=False,
        capture_directory=folder.relative_to(ROOT).as_posix(), input_fingerprint=before)
    for target in [folder / 'results.json', folder.parent / 'results.json']:
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if not report['all_exact_words']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
