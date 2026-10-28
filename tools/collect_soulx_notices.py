"""Preserve complete notices for code compiled by the SoulX App worker. No asset fetches."""
import hashlib,json
from pathlib import Path
from evidence import current
from native_payload import engine_files
ROOT=Path(__file__).resolve().parents[1]
FILES={
    'soulx-NOTICE.txt':'native/soulx/NOTICE',
    'soulx-Apache-LICENSE.txt':'research/soulx/LICENSE-APACHE-2.0',
    'soulx-kissfft-BSD-3-Clause.txt':'research/soulx/LICENSE-KISSFFT-BSD-3-CLAUSE',
    'soulx-snake-MIT.txt':'research/soulx_acoustic/LICENSE-SNAKE-MIT',
    'soulx-llama-MIT.txt':'research/soulx_language/LICENSE-LLAMA-MIT',
    'moss-onnxruntime-LICENSE.txt':'third_party/notices/moss-onnxruntime-LICENSE.txt',
    'moss-onnxruntime-ThirdPartyNotices.txt.txt':'third_party/notices/moss-onnxruntime-ThirdPartyNotices.txt.txt',
    'sd-nlohmann-json-LICENSE.txt':'third_party/notices/sd-nlohmann-json-LICENSE.txt',
    'sd-NDK-LLVM-NOTICE.txt':'third_party/notices/sd-NDK-LLVM-NOTICE.txt',
}

def collect():
    notices={}
    for name,source in FILES.items():
        data=(ROOT/source).read_bytes();destination=ROOT/'third_party/notices'/name
        if destination!=ROOT/source:destination.write_bytes(data)
        notices[name]=hashlib.sha256(data).hexdigest()
    return notices

def main():
    receipt=json.loads((ROOT/'build/soulx-build-info.json').read_text(encoding='utf-8'));current(receipt['source_inputs']);notices=collect()
    engine={k:receipt[k] for k in ['engine','file','source_revision','abi','backend','ndk','sha256','bytes','android_api_notes','dependencies']};engine['notices']=notices
    p=ROOT/'third_party/engine-lock.json';value=json.loads(p.read_text(encoding='utf-8'));value['engines']=[e for e in value['engines'] if e['engine']!=engine['engine']]+[engine];engine_files(value['engines'])
    newline='\r\n' if b'\r\n' in p.read_bytes() else '\n';p.write_bytes((json.dumps(value,indent=2)+'\n').replace('\n',newline).encode('utf-8'))
    print(json.dumps(dict(engine=engine['engine'],notices=len(notices),bundled_model_data=False)))

if __name__=='__main__':main()
