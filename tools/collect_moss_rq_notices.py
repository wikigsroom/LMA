"""Register only an actually built moss_rq worker and exact source notices."""
import hashlib
import json
from pathlib import Path
from evidence import current
from fetch_moss_rq import validate_sources
from native_payload import engine_files

ROOT = Path(__file__).resolve().parents[1]


def main():
    lock=json.loads((ROOT/'third_party/moss-rq-source-lock.json').read_text(encoding='utf-8')); source=validate_sources(lock)
    receipt=json.loads((ROOT/'build/moss_rq-build-info.json').read_text(encoding='utf-8'));current(receipt['source_inputs'])
    output=ROOT/'third_party/notices'; records=[]
    for item in lock['notices']:
        data=(source/item['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256'] or Path(item['output']).name!=item['output']:raise RuntimeError('moss_rq source notice changed')
        (output/item['output']).write_bytes(data)
        records.append(dict(file=item['output'],sha256=item['sha256'],source=item['source']))
    notices={r['file']:r['sha256'] for r in records}
    for name in ('sd-nlohmann-json-LICENSE.txt','sd-NDK-LLVM-NOTICE.txt'):notices[name]=hashlib.sha256((output/name).read_bytes()).hexdigest()
    engine={k:receipt[k] for k in ('engine','file','source_revision','ggml_revision','abi','backend','ndk','sha256','bytes','android_api_notes')};engine['notices']=notices
    path=ROOT/'third_party/engine-lock.json';engines=json.loads(path.read_text(encoding='utf-8'));engines['engines']=[e for e in engines['engines'] if e['engine']!=engine['engine']]+[engine];engine_files(engines['engines'])
    newline='\r\n' if b'\r\n' in path.read_bytes() else '\n';path.write_bytes((json.dumps(engines,indent=2)+'\n').replace('\n',newline).encode('utf-8'))
    (output/'moss_rq-sources.json').write_text(json.dumps(dict(revision=lock['revision'],files=records,model_assets=False,license_note=lock['license_note'],local_modification='LMA inserts input/context guards and measured stage callbacks into generated Local and Realtime pipeline copies; the pinned source checkout remains pristine.',pipeline_guard_sha256=receipt['pipeline_guard_sha256']),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(notices=len(records),engine=engine['engine'],bundled_model_data=False)))


if __name__ == '__main__':main()
