"""Stage only reviewed compiled old-LTX code/dependencies. Never stage model data."""
import json,shutil
from pathlib import Path
from build_ltx098_app import sha
from evidence import current,fingerprint

ROOT=Path(__file__).resolve().parents[1]

def package():
    receipt=json.loads((ROOT/'build/ltx098-app-arm64/receipt.json').read_text(encoding='utf-8'));current(receipt['input_fingerprint'])
    assert receipt['android_arm64_compiled'] and len(receipt['stages'])==4
    destination=ROOT/'app/src/main/jniLibs/arm64-v8a';compiled=[]
    for stage in receipt['stages']:
        source=ROOT/stage['path'];assert source.stat().st_size==stage['bytes'] and sha(source)==stage['sha256']
        target=destination/stage['file'];shutil.copyfile(source,target)
        assert sha(target)==stage['sha256']
        compiled.append(dict(file=stage['file'],bytes=stage['bytes'],sha256=stage['sha256'],android_api_notes=[28]))
    engine_lock=ROOT/'third_party/engine-lock.json';lock=json.loads(engine_lock.read_text(encoding='utf-8'))
    shared=next(e for e in lock['engines'] if e['engine']=='soulx_native')['dependencies']
    for item in shared:
        path=destination/item['file'];assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256']
    names=['ltx098-Lightricks-Apache-2.0.txt','ltx098-App-NOTICE.txt','ltx098-ggml-MIT.txt','ltx098-Vulkan-Headers.txt',
        'ltx098-Vulkan-MIT.txt','ltx098-Vulkan-Apache-2.0.txt','ltx098-SPIRV-Headers-MIT.txt','soulx-llama-MIT.txt',
        'moss-onnxruntime-LICENSE.txt','moss-onnxruntime-ThirdPartyNotices.txt.txt','sd-nlohmann-json-LICENSE.txt','sd-NDK-LLVM-NOTICE.txt',
        'moss-sentencepiece-LICENSE.txt','moss-sentencepiece-third_party-protobuf-lite-LICENSE.txt','moss-sentencepiece-third_party-darts_clone-LICENSE.txt','moss-sentencepiece-third_party-absl-LICENSE.txt']
    notices={name:sha(ROOT/'third_party/notices'/name) for name in names}
    primary=next(c for c in compiled if 'tensors' in c['file']);dependencies=[c for c in compiled if c is not primary]+shared
    result=dict(primary,schema='lma.native-build/1',engine='ltx098_native',version='0.9.8-lma-multiscale-v1',abi='arm64-v8a',min_sdk=28,backend='vulkan',
        source_revision=receipt['source_revision'],ggml_revision=receipt['ggml_revision'],llama_revision=receipt['llama_revision'],ndk=receipt['ndk'],
        dependencies=dependencies,notices=notices,elf_load_alignment=receipt['stages'][0]['elf']['load_segment_alignment'],
        vocabularies='external_user_selected_components',pipeline='ltx098_single_scale_google_q5',stage_loading='sequential_processes',
        text_backend='cpu',vae_backend='cpu',media_backend='android_mediacodec_avc',model_inference_tested=False,deviceValidated=False,
        numerical_accepted=False,quality_accepted=False,model_data_embedded=False)
    result['pipelines']=['ltx098_single_scale_google_q5','ltx098_pixart_multiscale_v1']
    result['sentencepiece_revision']=receipt['sentencepiece_revision']
    result['source_inputs']=receipt['input_fingerprint']|fingerprint('tools/package_ltx098_app.py',*['third_party/notices/'+n for n in names])
    (ROOT/'build/ltx098-app-build-info.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    expected={k:v for k,v in result.items() if k!='source_inputs'}
    index=next((i for i,e in enumerate(lock['engines']) if e['engine']=='ltx098_native'),None)
    if index is None:lock['engines'].append(expected)
    else:lock['engines'][index]=expected
    engine_lock.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(engine=result['engine'],stages=len(compiled),compiled_bytes=sum(c['bytes'] for c in compiled),model_data_embedded=False)))

if __name__=='__main__':package()
