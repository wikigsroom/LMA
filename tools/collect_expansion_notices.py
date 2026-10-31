"""Collect complete source notices and lock actual worker receipts; no model assets."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from evidence import current

ROOT=Path(__file__).resolve().parents[1]


def main():
    audio=ROOT/'build/native-src/audio-cpp-ssh'; mesh=ROOT/'build/native-src/trellis-cpp'; mv=ROOT/'build/native-src/pixal3d-mv-cpp'
    files={}
    for prefix,folder,names in [('speech',audio,['LICENSE','external/ggml/LICENSE','external/cJSON/LICENSE','external/utf8proc/LICENSE.md',
        'external/sentencepiece/LICENSE','external/sentencepiece/third_party/protobuf-lite/LICENSE',
        'external/sentencepiece/third_party/darts_clone/LICENSE','external/sentencepiece/third_party/esaxx/LICENSE',
        'external/sentencepiece/third_party/absl/LICENSE','external/libyaml/License']),
        ('mesh',mesh,['LICENSE','thirdparty/ggml/LICENSE','thirdparty/meshoptimizer/LICENSE.md','thirdparty/fqms/LICENSE.md']),
        ('multiview',mv,['LICENSE','NOTICE','thirdparty/ggml/LICENSE','thirdparty/meshoptimizer/LICENSE.md','thirdparty/fqms/LICENSE.md'])]:
        for path in names:
            source=folder/path
            data=source.read_bytes() if source.exists() else subprocess.check_output(['git','show','HEAD:'+path],cwd=folder)
            files['expansion-'+prefix+'-'+path.replace('/','-')+'.txt']=data
    for prefix,folder in [('mesh',mesh),('multiview',mv)]:
        xatlas=(folder/'thirdparty/xatlas/xatlas.h').read_text(encoding='utf-8')
        files['expansion-'+prefix+'-xatlas-NOTICE.txt']=xatlas[:xatlas.index('#pragma once')].encode('utf-8')
        for header in ['stb_image.h','stb_image_write.h','stb_image_resize.h','stb_image_resize2.h']:
            path=folder/'thirdparty/stb'/header
            if not path.exists(): continue
            text=path.read_text(encoding='utf-8'); start=text.rfind('ALTERNATIVE A - MIT License')
            if start>0: notice=text[start:]
            else:
                start=text.index('This software is in the public domain.');end=text.index('*/',start)
                notice=header+'\n\n'+text[start:end].strip()+'\n'
            files['expansion-'+prefix+'-'+header+'-NOTICE.txt']=notice.encode('utf-8')
    for name in ['sd-nlohmann-json-LICENSE.txt','sd-NDK-LLVM-NOTICE.txt']:
        files[name]=(ROOT/'third_party/notices'/name).read_bytes()
    for name,data in files.items(): (ROOT/'third_party/notices'/name).write_bytes(data)
    notice_data={name:data.decode('utf-8') for name,data in files.items()}
    (ROOT/'app/src/main/assets/expansion-notices.json').write_text(json.dumps(notice_data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lock_path=ROOT/'third_party/engine-lock.json'; lock=json.loads(lock_path.read_text(encoding='utf-8'))
    for engine,receipt_name in [('audio_cpp','speech_extra'),('trellis_native','mesh'),('pixal_multiview','multiview'),('sherpa_tts','tts')]:
        receipt=json.loads((ROOT/('build/'+receipt_name+'-build-info.json')).read_text(encoding='utf-8'));current(receipt['source_inputs'])
        previous=next((e for e in lock['engines'] if e['engine']==engine),{})
        entry={k:receipt[k] for k in ('engine','file','source_revision','abi','backend','ndk','sha256','bytes','android_api_notes','dependencies')}
        prefix={'audio_cpp':'speech','trellis_native':'mesh','pixal_multiview':'multiview'}.get(engine)
        entry['notices']=previous['notices'] if engine=='sherpa_tts' else {name:hashlib.sha256(data).hexdigest() for name,data in files.items() if not name.startswith('expansion-') or name.startswith('expansion-'+prefix+'-')}
        if previous: lock['engines'][lock['engines'].index(previous)]=entry
        else: lock['engines'].append(entry)
    lock_path.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(notices=len(files),model_data_in_apk=False)))

if __name__=='__main__': main()
