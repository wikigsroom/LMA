"""Retain source, SDK/runtime third-party notices; register actual compiled bytes."""
import hashlib,json,zipfile
from pathlib import Path
from evidence import current
from fetch_stable_audio import validate_sources,runtime
from native_payload import engine_files
ROOT=Path(__file__).resolve().parents[1]

def main():
    lock=json.loads((ROOT/'third_party/stable-audio-source-lock.json').read_text(encoding='utf-8'));receipt=json.loads((ROOT/'build/stable-audio-build-info.json').read_text(encoding='utf-8'));current(receipt['source_inputs'])
    if validate_sources(lock)!=receipt['sources']:raise RuntimeError('Compiled sources differ')
    cache=runtime(lock);out=ROOT/'third_party/notices';notices={}
    def save(item,data):
        if hashlib.sha256(data).hexdigest()!=item['sha256'] or Path(item['output']).name!=item['output']:raise RuntimeError('Source notice changed')
        (out/item['output']).write_bytes(data);notices[item['output']]=item['sha256']
    for s in lock['sources']:
        for item in s['notices']:save(item,(ROOT/'build/native-src'/s['name']/item['path']).read_bytes())
    with zipfile.ZipFile(cache/'litert-2.2.0.aar') as z:
        for item in lock['runtime']['notices']:save(item,z.read(item['path']))
    for name in ['sd-nlohmann-json-LICENSE.txt','sd-NDK-LLVM-NOTICE.txt']:notices[name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    engine={k:receipt[k] for k in ('engine','file','source_revision','abi','backend','ndk','sha256','bytes','android_api_notes','dependencies')};engine['notices']=notices
    p=ROOT/'third_party/engine-lock.json';value=json.loads(p.read_text(encoding='utf-8'));value['engines']=[e for e in value['engines'] if e['engine']!=engine['engine']]+[engine];engine_files(value['engines']);newline='\r\n' if b'\r\n' in p.read_bytes() else '\n';p.write_bytes((json.dumps(value,indent=2)+'\n').replace('\n',newline).encode('utf-8'))
    (out/'stable-audio-sources.json').write_text(json.dumps(dict(sources=receipt['sources'],runtime=lock['runtime'],files=notices,model_assets=False,local_modification='LMA C API adapter uses sequential CPU graph lifetimes, strict shapes, 64-token effective prompt budget, guarded requests, private events and PCM16 output. Arm sampler seed schedule retained; LiteRT default XNNPACK flags.'),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(engine=engine['engine'],notices=len(notices),bundled_model_data=False)))

if __name__=='__main__':main()
