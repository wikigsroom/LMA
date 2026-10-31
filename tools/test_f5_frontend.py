"""Compare actual native F5 frontend against the pinned publisher function.

Only text/linguistic program dependencies are used; no neural model, voice,
speech generation, remote inference, VM, emulator or physical phone is used.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/f5-frontend-tests'
REFERENCE = ROOT/'build/frontend-reference'


def build():
    alias = next((x+':' for x in 'TUVWXYZR' if not Path(x+':/').exists()), None)
    assert alias
    subprocess.run(['subst', alias, str(ROOT)], check=True, capture_output=True)
    try:
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        command = ['cl', '/nologo', '/std:c++17', '/utf-8', '/EHsc', '/O2', '/I', alias+'/build/native-src/sd-cpp/thirdparty',
                   '/Fe:'+alias+'/build/f5-frontend-tests/frontend.exe', '/Fo:'+alias+'/build/f5-frontend-tests/frontend.obj',
                   alias+'/tests/expansion-native/f5_official.cpp']
        script = OUT/'build.cmd'
        script.write_text('@echo off\ncall "'+setup+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n', 'utf-8')
        result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=90)
        (OUT/'build.log').write_bytes(result.stdout+result.stderr)
        assert result.returncode == 0, 'Inspect build/f5-frontend-tests/build.log'
    finally:
        subprocess.run(['subst', alias, '/D'], check=True, capture_output=True)
    return OUT/'frontend.exe'


def reference():
    import rjieba
    from pypinyin import Style, lazy_pinyin
    source = REFERENCE/'f5_utils.py'
    lock = json.loads((ROOT/'third_party/f5-frontend-source-lock.json').read_text('utf-8'))
    for item in lock['files']:
        path = ROOT/item['cachePath']
        with path.open('rb') as f:
            assert hashlib.file_digest(f, 'sha256').hexdigest() == item['sha256'], item['cachePath']
    tree = ast.parse(source.read_text('utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'convert_char_to_pinyin']
    assert len(nodes) == 1
    namespace = dict(rjieba=rjieba, Style=Style, lazy_pinyin=lazy_pinyin)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace['convert_char_to_pinyin'], rjieba


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT/'build/frontend-python'))
    from export_f5_frontend import export
    before = fingerprint('native/speech_extra/f5_official.hpp', 'native/speech_extra/f5_frontend.hpp',
        'tools/export_f5_frontend.py', 'tools/test_f5_frontend.py', 'tests/expansion-native/f5_official.cpp',
        'third_party/f5-frontend-source-lock.json', 'native/worker_common.hpp', 'native/runtime_metrics.hpp')
    oracle, rjieba = reference()
    asset = OUT/'f5-frontend.json'
    if asset.exists():
        assert asset.resolve().parent == OUT.resolve()
        asset.unlink()
    receipt = export(REFERENCE/'jieba-data/dict.txt', REFERENCE/'jieba-macros/src/hmm.model', asset)
    executable = build()
    examples = ['', '你好，中国。', '重庆银行行长说重重叠叠。', '一不做二不休，不是，一定，一起，你好。',
        '我爱北京天安门', '南京市长江大桥', '乒乓球拍卖完了', '这是一个用于检查的中文句子。', '你好世界hello world!',
        '“Hello”;‘world’；中文。', 'LMA-1.2.3 foo_bar test.example 25% 1-2 1_2', 'a+b#c&d% -_ .',
        '\r\n\t\r\n', '你好\n世界', 'nv3 lǜ ü é café', '𦡦𦡦䶯䶰讥𠀀𠀀', '한글日本語かな🙂🚀', '龘靐齉齾爩鱻麤龗灪',
        '女儿绿水长流，音乐与快乐。', '中华人民共和国成立于1949年10月1日。', 'Python3.13与Android 9+', 'a\r\nb']
    rng = random.Random(48371)
    alphabet = list('你好我是中国重庆银行长乐音乐不是一定起来比较管理保守世界南京市桥银行要还行吗。！？，；：“”‘’你好你好你好')+list('abC XYZ-_.+#&%12309\n\t\r')+['ü', 'é', '𦡦', '龘', '🙂', '한', '字', '〇']
    examples += [''.join(rng.choices(alphabet, k=rng.randrange(1, 35))) for _ in range(1600)]
    # More source-dictionary polyphones and HMM unknown-word combinations.
    from pypinyin.constants import PHRASES_DICT
    keys = sorted(PHRASES_DICT)
    examples += rng.sample(keys, min(600, len(keys)))
    queries = []
    expected = []
    vocabulary = {' ':0, ',':1, '.':2, 'ni2':3, 'hao3':4, 'a':5}
    for text in examples:
        item = dict(text=text, vocab=vocabulary)
        try:
            tokens = oracle([text])[0]
            value = dict(segments=list(rjieba.cut(text)), tokens=tokens, ids=[vocabulary.get(x, 0) for x in tokens])
        except (IndexError, ValueError):
            value = dict(rejected=True)
        queries.append(item); expected.append(value)
    result = subprocess.run([str(executable), str(asset)], input=''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in queries),
        capture_output=True, encoding='utf-8', timeout=90)
    assert result.returncode == 0, (result.returncode, result.stderr)
    lines = result.stdout.splitlines()
    assert len(lines) == len(expected), (len(lines), len(expected))
    mismatches = [dict(text=query['text'], expected=want, actual=json.loads(row)) for query,want,row in zip(queries,expected,lines) if json.loads(row) != want]
    (OUT/'mismatches.json').write_text(json.dumps(mismatches[:30], ensure_ascii=False, indent=2)+'\n', 'utf-8')
    assert not mismatches, ('Native/reference mismatches', len(mismatches), 'Inspect build/f5-frontend-tests/mismatches.json')
    negative = [dict(text='a'*12001), dict(text='a'*65537)]
    result = subprocess.run([str(executable), str(asset)], input=''.join(json.dumps(x)+'\n' for x in negative), capture_output=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0 and all(json.loads(x).get('rejected') for x in result.stdout.splitlines()) and len(result.stdout.splitlines())==2
    malformed = json.loads(asset.read_text('utf-8'))
    for label, change in [('version', lambda j:j.update(pypinyinVersion='unknown')),
                          ('probability',lambda j:j['hmm']['initial'].__setitem__(0,1)),
                          ('alignment',lambda j:j['pinyin'].update({'你好':['ni2']}))]:
        value = json.loads(json.dumps(malformed));change(value)
        path = OUT/('invalid-'+label+'.json');path.write_text(json.dumps(value, ensure_ascii=False), 'utf-8')
        run = subprocess.run([str(executable), str(path)], input='', capture_output=True, encoding='utf-8', timeout=30)
        assert run.returncode == 2, label
    current(before)
    report = dict(passed=len(examples)*3+2+3, textCases=len(examples), publisherFunctionCompared=True, nativeProductionFrontend=True,
        exactSegmentation=True, exactPinyinTokens=True, exactVocabularyIds=True, malformedAssetsRejected=True,
        linguisticAsset=receipt, completeModelDownloads=0, completeModelRuns=0, neuralWeightsLoaded=False, physicalDeviceTests=0,
        virtualizationUsed=False, input_fingerprint=before)
    (OUT/'results.json').write_text(json.dumps(report, indent=2)+'\n', 'utf-8')
    print(json.dumps({k:report[k] for k in ['passed','textCases','exactSegmentation','exactPinyinTokens','completeModelRuns']}))


if __name__ == '__main__':
    main()
