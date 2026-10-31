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
    from fetch_shape_sources import verify
    shape_lock=verify()
    for source in shape_lock['sources']:
        files['expansion-shape-'+source['id']+'-LICENSE.txt']=(ROOT/source['directory']/'LICENSE').read_bytes()
        for relative in source['files']:
            if not relative.endswith('.py'):continue
            text=(ROOT/source['directory']/relative).read_text(encoding='utf-8');lines=text.splitlines();header=[]
            for line in lines:
                if line.strip() and not line.lstrip().startswith('#'):break
                header.append(line)
            if any('copyright' in line.lower() or 'license' in line.lower() for line in header):
                files['expansion-shape-'+source['id']+'-'+relative.replace('/','-')+'-NOTICE.txt']=('\n'.join(header)+'\n').encode('utf-8')
    from spatial_reference import verify as verify_spatial
    for source in verify_spatial()['sources']:
        files['expansion-spatial-'+source['id']+'-LICENSE.txt']=(ROOT/source['directory']/'LICENSE').read_bytes()
        if source['id']=='D04':files['expansion-spatial-UltraTex-SLA-LICENSE.txt']=(ROOT/source['directory']/'ultratex/sparse_attention/LICENSE.txt').read_bytes()
        for item in source['files']:
            relative=item['path']
            if not relative.endswith('.py'):continue
            header=[]
            for line in (ROOT/source['directory']/relative).read_text(encoding='utf-8').splitlines():
                if line.strip() and not line.lstrip().startswith('#'):break
                header.append(line)
            if any('copyright' in line.lower() or 'license' in line.lower() for line in header):
                files['expansion-spatial-'+source['id']+'-'+relative.replace('/','-')+'-NOTICE.txt']=('\n'.join(header)+'\n').encode('utf-8')
    files['expansion-spatial-ORT-LICENSE.txt']=(ROOT/'third_party/notices/tts-onnxruntime-LICENSE.txt').read_bytes()
    files['expansion-spatial-stb-NOTICE.txt']=files['expansion-multiview-stb_image.h-NOTICE.txt']
    files['expansion-spatial-stb-write-NOTICE.txt']=files['expansion-multiview-stb_image_write.h-NOTICE.txt']
    files['expansion-spatial-xatlas-NOTICE.txt']=files['expansion-mesh-xatlas-NOTICE.txt']
    # Spatial text encoding uses user-selected vocabularies with pinned CPU
    # SentencePiece, Oniguruma and utf8proc code; no embedded normalizer data.
    for relative in ['LICENSE','third_party/protobuf-lite/LICENSE','third_party/darts_clone/LICENSE','third_party/esaxx/LICENSE','third_party/absl/LICENSE']:
        files['expansion-spatial-sentencepiece-'+relative.replace('/','-')+'.txt']=(ROOT/'build/native-src/sentencepiece'/relative).read_bytes()
    for name,relative in [('oniguruma','oniguruma/COPYING'),('utf8proc','utf8proc/LICENSE.md')]:
        files['expansion-spatial-'+name+'-LICENSE.txt']=(ROOT/'build/native-src/sd-cpp/thirdparty'/relative).read_bytes()
    from fetch_fdg_sources import verify as verify_fdg
    fdg=verify_fdg()
    for label,name in [('fdg_license','TRELLIS2-FDG'),('volume_license','FlexGEMM')]:
        files['expansion-spatial-'+name+'-LICENSE.txt']=(ROOT/fdg['sources'][label]['path']).read_bytes()
    for name in ['COPYING.README','COPYING.MPL2','COPYING.BSD','COPYING.APACHE','COPYING.MINPACK']:
        files['expansion-spatial-Eigen-'+name+'.txt']=(ROOT/'build/native-src/eigen-fdg'/name).read_bytes()
    from fetch_depth_notices import verify as verify_depth_notices
    for item in verify_depth_notices()['sources']:
        path=ROOT/item['file'];files[path.name]=path.read_bytes()
    from fetch_surface_sources import verify as verify_surface
    for source in verify_surface()['sources']:
        if source['id'] not in ('DISO','LEWINER','LEWINER_CPP'):continue
        license_path='LICENSE.txt' if source['id']=='LEWINER' else 'LICENSE'
        files['expansion-shape-'+source['id']+'-LICENSE.txt']=(ROOT/source['directory']/license_path).read_bytes()
    files['expansion-shape-surface-ATTRIBUTION.txt']=(
        'DISO CPU forward-kernel port: SarahWeiii/diso@9792ad928ccb09bdec938779651ee03e395758a6.\n'
        'Original CUDA launch/indexing is replaced by bounded CPU loops; no gradients are included.\n'
        'DISO is licensed CC BY-NC 4.0. This component has a noncommercial restriction.\n'
        'Lewiner source: scikit-image@51b3367761a52ab9111bdbd9537272d7dd2eccde and\n'
        'neurolabusc/LewinerMarchingCubes@23642e6716c77ac15a2c2349b5125d605ac76234.\n'
        'CPU extraction omits file exporters; original tables and attribution are retained.\n'
        'See the adjacent complete license notices; LMA MIT licensing does not relicense these components.\n').encode('utf-8')
    from fetch_vision_sources import verify as verify_vision
    vision=verify_vision();files['expansion-vision-DIS-LICENSE.txt']=(ROOT/vision['directory']/'LICENSE.md').read_bytes()
    llama=ROOT/'build/native-src/llama-soulx'
    for path in ['LICENSE','vendor/hash/xxhash/LICENSE','vendor/hash/sha256/LICENSE','vendor/hash/rotate-bits/LICENSE.md']:
        files['expansion-vision-llama-'+path.replace('/','-')+'.txt']=(llama/path).read_bytes()
    miniaudio=(llama/'vendor/miniaudio/miniaudio.h').read_text(encoding='utf-8')
    start=miniaudio.rindex('This software is available as a choice of the following licenses. Choose')
    files['expansion-vision-miniaudio-NOTICE.txt']=miniaudio[start:].encode('utf-8')
    files['expansion-vision-stb-NOTICE.txt']=files['expansion-spatial-stb-NOTICE.txt']
    files['expansion-vision-stb-write-NOTICE.txt']=files['expansion-spatial-stb-write-NOTICE.txt']
    files['expansion-vision-ORT-LICENSE.txt']=files['expansion-spatial-ORT-LICENSE.txt']
    from fetch_f5_sources import verify as verify_f5
    verify_f5()
    for name,path in [('f5','f5-LICENSE.txt'),('rjieba','LICENSE'),('jieba-rs','jieba-rs-LICENSE.txt'),('pypinyin','pypinyin-source/LICENSE.txt')]:
        files['expansion-speech-'+name+'-LICENSE.txt']=(ROOT/'build/frontend-reference'/path).read_bytes()
    from paint_reference import verify as verify_paint
    paint=verify_paint()
    files['expansion-spatial-BasicSR-LICENSE.txt']=(ROOT/paint['directory']/'LICENSE.txt').read_bytes()
    files['expansion-shape-ORT-LICENSE.txt']=(ROOT/'third_party/notices/tts-onnxruntime-LICENSE.txt').read_bytes()
    files['expansion-shape-stb-NOTICE.txt']=files['expansion-multiview-stb_image.h-NOTICE.txt']
    for name,data in files.items(): (ROOT/'third_party/notices'/name).write_bytes(data)
    notice_data={name:data.decode('utf-8') for name,data in files.items()}
    (ROOT/'app/src/main/assets/expansion-notices.json').write_text(json.dumps(notice_data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lock_path=ROOT/'third_party/engine-lock.json'; lock=json.loads(lock_path.read_text(encoding='utf-8'))
    for engine,receipt_name in [('audio_cpp','speech_extra'),('trellis_native','mesh'),('pixal_multiview','multiview'),('sherpa_tts','tts'),('rf_shape_ort','shape'),('spatial_ort','spatial'),('vision_cpu','vision')]:
        receipt=json.loads((ROOT/('build/'+receipt_name+'-build-info.json')).read_text(encoding='utf-8'));current(receipt['source_inputs'])
        previous=next((e for e in lock['engines'] if e['engine']==engine),{})
        entry={k:receipt[k] for k in ('engine','file','source_revision','abi','backend','ndk','sha256','bytes','android_api_notes','dependencies')}
        prefix={'audio_cpp':'speech','trellis_native':'mesh','pixal_multiview':'multiview','rf_shape_ort':'shape','spatial_ort':'spatial','vision_cpu':'vision'}.get(engine)
        if engine=='rf_shape_ort':entry['partcrafter_revision']=receipt['partcrafter_revision']
        if engine=='spatial_ort':entry['source_revisions']=receipt['source_revisions']
        if engine=='vision_cpu':entry['llama_revision']=receipt['llama_revision']
        entry['notices']=previous['notices'] if engine=='sherpa_tts' else {name:hashlib.sha256(data).hexdigest() for name,data in files.items() if not name.startswith('expansion-') or name.startswith('expansion-'+prefix+'-')}
        if previous: lock['engines'][lock['engines'].index(previous)]=entry
        else: lock['engines'].append(entry)
    lock_path.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(notices=len(files),model_data_in_apk=False)))

if __name__=='__main__': main()
