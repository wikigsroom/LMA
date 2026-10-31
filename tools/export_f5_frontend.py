"""Prepare an explicit, local F5 linguistic asset; never downloads neural weights.

The app executes DAG/HMM segmentation in C++. Finite pypinyin dictionary entries
are converted with the pinned library at preparation time, including its exact
ToneSandhiMixin behavior. The resulting data belongs to the user's model bundle,
not the APK. No user Python/module/target name is dynamically imported.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

VERSIONS = dict(rjiebaVersion='0.2.2', jiebaRsVersion='0.11.0', pypinyinVersion='0.55.0')


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def dictionary(path):
    assert path.is_file() and path.stat().st_size <= 32*1024*1024
    words = {}
    for row in path.read_text('utf-8').splitlines():
        if not row.strip():
            continue
        fields = row.split()
        assert len(fields) >= 2 and len(fields[0]) <= 128
        word, frequency = fields[:2]
        assert frequency.isdecimal() and 0 <= int(frequency) <= 10**12
        words[word] = int(frequency)
    assert 0 < len(words) <= 1000000 and 0 < sum(words.values()) <= 10**15
    return words


def hmm(path):
    import math
    assert path.is_file() and path.stat().st_size <= 16*1024*1024
    rows = [r.strip() for r in path.read_text('utf-8').splitlines() if r.strip() and not r.lstrip().startswith('#')]
    assert len(rows) == 9
    params = [[float(x) for x in row.split()] for row in rows[:5]]
    assert all(len(row) == 4 for row in params)
    emission = {}
    for state, row in enumerate(rows[5:]):
        for pair in row.split(','):
            char, probability = pair.rsplit(':', 1)
            assert len(char) == 1
            emission.setdefault(char, [-3.14e100]*4)[state] = float(probability)
    assert len(emission) <= 65536
    assert all(math.isfinite(x) and -1e101 <= x <= 0 for row in params+list(emission.values()) for x in row)
    return dict(initial=params[0], transition=params[1:], emission=emission)


def pronunciations():
    import pypinyin
    from pypinyin.constants import PHRASES_DICT, PINYIN_DICT
    assert importlib.metadata.version('pypinyin') == VERSIONS['pypinyinVersion']
    # Do not simplify the publisher's rules (including unusual third-tone
    # sequences). Every entry is evaluated by the actual pinned converter.
    output = {}
    for text in sorted(set(PHRASES_DICT) | {chr(cp) for cp in PINYIN_DICT}):
        value = pypinyin.lazy_pinyin(text, style=pypinyin.Style.TONE3, tone_sandhi=True)
        assert len(text) == len(value) and 0 < len(text) <= 128
        output[text] = value
    return output


def export(dict_path, hmm_path, output):
    assert not output.exists(), 'Choose a new asset path; never replace installed user resources'
    value = dict(schema='lma.f5-frontend/1', **VERSIONS, words=dictionary(dict_path), hmm=hmm(hmm_path), pinyin=pronunciations(),
                 source=dict(dictionarySha256=sha(dict_path), hmmSha256=sha(hmm_path)),
                 modelWeightsIncluded=False, network=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n', 'utf-8')
    assert output.stat().st_size <= 96*1024*1024
    receipt = dict(schema='lma.f5-frontend-receipt/1', file=output.name, bytes=output.stat().st_size, sha256=sha(output), **VERSIONS,
                   words=len(value['words']), pinyinEntries=len(value['pinyin']), hmmEmissionCharacters=len(value['hmm']['emission']),
                   network=False, neuralWeightsLoaded=False, modelInferenceTested=False, physicalDeviceTests=0)
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', 'utf-8')
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jieba-dict', type=Path, required=True)
    p.add_argument('--hmm-model', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(export(a.jieba_dict, a.hmm_model, a.output)))
