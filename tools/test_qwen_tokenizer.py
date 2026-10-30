"""Independent HF reference vs actual production Qwen tokenizer and external-data loader.

No network/model inference. Full base vocabulary IDs and multilingual encodings are
compared with the separately downloaded pinned tokenizer.json and Rust tokenizers.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from build_sd_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_flux2_trained import assets, asset_path, sha, verify_reference

ROOT=Path(__file__).resolve().parents[1]
TEXTS=['', 'hello', 'a red robot', 'A small red toy robot standing beside a blue ceramic teapot on a wooden table, studio photograph, soft daylight, clean background',
       'A yellow sailboat on a calm blue lake below snow covered mountains, bright daylight, detailed landscape photograph',
       '一个红色的小机器人，旁边放着蓝色茶壶。', '山间的湖泊与黄色帆船', '台灣繁體中文，光影細節。',
       'こんにちは、世界。', '한국어 문장입니다.', 'Привет, мир!', 'مرحبا بالعالم', 'café déjà vu',
       '🙂 🐈 🧑🏽‍🚀', 'line one\nline two', 'line one\r\nline two', '  multiple   spaces  ', '\tindent\t',
       '1234567890', '3.14159 -42 1e-6', 'photo-realistic, high contrast', '<|endoftext|>', '<|im_start|>user\nA red robot<|im_end|>\n<|im_start|>assistant\n',
       '<think>\n</think>\n', '<tool_call>{"name":"paint"}</tool_call>', '中文English123混合。',
       'a/b\\c: []{}()!?', 'The quick brown fox jumps over the lazy dog.', 'a cat\u00a0a dog', 'e\u0301 and é',
       'red\n\nblue', '“quoted” — test…', 'https://example.invalid/local-model']


def inputs():
    return {**build_inputs(),**fingerprint('tools/test_qwen_tokenizer.py','research/flux2_trained/assets.json','tools/fetch_flux2_trained.py')}


def main():
    from tokenizers import Tokenizer
    if os.name!='nt':raise RuntimeError('Native Windows host only')
    before=inputs();lock=assets();reference=verify_reference();_,compilation=build()
    merges=next(c for c in lock['components'] if c['role']=='qwen_merges');raw=asset_path(merges).read_bytes()
    if len(raw)!=merges['bytes'] or hashlib.sha256(raw).hexdigest()!=merges['sha256']:raise ValueError('Changed selected Qwen merge data')
    if not raw.startswith(b'#version: 0.2\n'):raise ValueError('Expected original HF file header')
    canonical=raw.split(b'\n',1)[1]
    source=(ROOT/'build/native-src/sd-cpp/src/tokenizers/vocab/qwen_merges.hpp').read_text(encoding='utf-8')
    embedded=bytes(int(v,16) for v in re.findall(r'0x([a-fA-F0-9]{2})',source))
    if canonical!=embedded:raise ValueError('Matched HF merge rules differ from pinned upstream tokenizer')
    official=json.loads(reference.read_bytes());expected=Tokenizer.from_file(str(reference));expected_ids=[expected.encode(t,add_special_tokens=False).ids for t in TEXTS]
    folder=ROOT/'build/qwen-tokenizer-tests'/('run-'+str(time.time_ns()));folder.mkdir(parents=True)
    drive=next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst',drive,str(ROOT)],capture_output=True,check=True);checks=[];runs=[]
    def check(value,why):checks.append(dict(passed=bool(value),description=why))
    try:
        def alias(p):return drive+'/'+p.relative_to(ROOT).as_posix()
        variants=[('hf-header',raw),('canonical',canonical),('bom-crlf',b'\xef\xbb\xbf'+raw.replace(b'\n',b'\r\n'))]
        for name,data in variants:
            selected=folder/(name+'.txt');selected.write_bytes(data)
            request=folder/(name+'.json');request.write_text(json.dumps(dict(texts=TEXTS,include_vocab=name=='hf-header'),ensure_ascii=False)+'\n',encoding='utf-8')
            output=folder/(name+'-canonical.txt');environment=dict(os.environ,LMA_VOCAB_QWEN_MERGES=alias(selected))
            process=subprocess.run([alias(ROOT/compilation['tokenizer_executable']),alias(request),alias(output)],env=environment,capture_output=True,timeout=90)
            (folder/(name+'.stdout')).write_bytes(process.stdout);(folder/(name+'.stderr')).write_bytes(process.stderr)
            check(process.returncode==0,name+': actual production tokenizer exits cleanly')
            if process.returncode:continue
            report=json.loads(process.stdout);check(output.read_bytes()==canonical,name+': canonical in-memory rules exactly match pinned upstream bytes')
            check(selected.read_bytes()==data,name+': selected user file stays unchanged')
            for n,(actual,wanted) in enumerate(zip(report['tokens'],expected_ids)):
                check(actual==wanted,name+': independent HF token IDs, text '+str(n))
            check(len(report['tokens'])==len(TEXTS),name+': every multilingual test is encoded')
            if name=='hf-header':
                original=official['model']['vocab'];mismatches=[token for token,value in original.items() if report['vocab'].get(token)!=value]
                check(not mismatches,'Every one of '+str(len(original))+' official base vocabulary token IDs matches the actual C++ encoder')
                added=[t for t in official['added_tokens'] if report['vocab'].get(t['content'])!=t['id']]
                check(not added,'Every official added/special token ID matches the actual C++ encoder')
            runs.append(dict(name=name,returncode=process.returncode,tokens_sha256=hashlib.sha256(json.dumps(report['tokens']).encode()).hexdigest(),canonical_sha256=sha(output)))
        for name,data in [('unknown-header',b'#version: 0.3\n'+canonical),('duplicate-header',b'#version: 0.2\n'+raw),('bare-cr',b'a b\rc d'),('only-header',b'#version: 0.2\n')]:
            selected=folder/(name+'.txt');selected.write_bytes(data);environment=dict(os.environ,LMA_VOCAB_QWEN_MERGES=alias(selected))
            process=subprocess.run([alias(ROOT/compilation['tokenizer_executable']),alias(folder/'hf-header.json'),alias(folder/(name+'-canonical.txt'))],env=environment,capture_output=True,timeout=30)
            (folder/(name+'.stdout')).write_bytes(process.stdout);(folder/(name+'.stderr')).write_bytes(process.stderr)
            check(process.returncode!=0 and not process.stdout,name+': malformed data fails before tokenization')
    finally:subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
    current(before)
    files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.iterdir()) if p.is_file()}
    report=dict(schema='lma.qwen-tokenizer-reference/1',passed=all(c['passed'] for c in checks),checks=checks,check_count=len(checks),
                official_base_vocabulary_ids=len(official['model']['vocab']),official_added_token_ids=len(official['added_tokens']),texts=len(TEXTS),
                variants=len(variants),reference=lock['reference_tokenizer'],selected_merges=merges,canonical_bytes=len(canonical),
                canonical_sha256=hashlib.sha256(canonical).hexdigest(),compilation=compilation,runs=runs,files=files,
                capture_directory=folder.relative_to(ROOT).as_posix(),actual_production_tokenizer=True,independent_reference='Hugging Face tokenizer.json + Rust tokenizers',
                bundled_tokenizer_data=False,hf_header_removed_in_memory=True,nfc_before_bpe=True,installed_asset_unchanged=True,
                network_calls=0,model_inference=False,physical_android=False,complete_release_accepted=False,input_fingerprint=before)
    for p in [folder/'results.json',folder.parent/'results.json']:p.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['passed','check_count','official_base_vocabulary_ids','official_added_token_ids','texts','variants']}),flush=True)
    if not report['passed']:raise RuntimeError('Independent tokenizer comparison failed; original assertions retained')


if __name__=='__main__':main()
