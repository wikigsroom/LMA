"""Register pinned metadata for explicit user selection; never fetch model data."""
import copy
import json
from pathlib import Path

from fetch_openmoss_trained import assets

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ID = 'moss_tts_v15_q8_bf16_cpu_catalogue_v1'
PIPELINE = 'moss_tts_v15_openmoss_cpu_v1'


def manifest():
    lock = assets()
    templates = json.loads((ROOT/'app/src/main/assets/recipe-templates.json').read_text(encoding='utf-8'))['templates']
    definition = copy.deepcopy(next(t for t in templates if t['id'] == PIPELINE)['definition'])
    definition.update(schema='lma.model-bundle/1', id=BUNDLE_ID,
        modelId='moss_tts_v15_q8_bf16_cpu', recipeId=PIPELINE,
        name='MOSS-TTS 1.5 · Q8 / BF16 · CPU',
        description='完整 MOSS-TTS 1.5 语音模型与同版音频编解码器；24 kHz 单声道。约 13.43 GB 文件，需高内存设备；参考音频案例曾到达输出上限而未正常结束，仍需验证；尚未通过 Android 真机验收。由用户选择下载，不随 App 安装。',
        catalogue=True, license=dict(name=lock['license'], url=lock['model_card']),
        evidence=dict(status='pinned_assets_not_device_tested', physicalDeviceTests=0,
            sourceUrl=lock['model_card'], contentClassification='no_uncensored_claim',
            componentCoverage='Complete matched Q8_0/BF16 backbone and BF16/FP32 extras. CPU text, delayed audio generation and codec on the same phone. No weights, tokenizer or voice data in APK.'),
        resources=dict(estimatedPeakRamBytes=0, estimateKnown=False))
    definition['components'] = []
    for c in lock['components']:
        item = copy.deepcopy(c); item['role'] = 'backbone' if c['role'] == 'model' else c['role']; item['format'] = 'gguf'
        definition['components'].append(item)
    return definition


def main():
    bundle = manifest()
    public = ROOT/'research/openmoss_trained/catalogue-bundle.json'
    public.write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    path = ROOT/'catalogue/model-bundles.json'; catalogue = json.loads(path.read_text(encoding='utf-8'))
    existing = next((i for i,b in enumerate(catalogue['bundles']) if b['id']==BUNDLE_ID),None)
    if existing is None: catalogue['bundles'].append(bundle)
    else: catalogue['bundles'][existing] = bundle
    path.write_text(json.dumps(catalogue,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    path = ROOT/'catalogue/bundle-evidence.json'; evidence = json.loads(path.read_text(encoding='utf-8'))
    proof = dict(bundleId=BUNDLE_ID, checked_on='2026-10-30', metadata_transport='HTTPS public HF mirror API; immutable LFS identities also published in the upstream conversion model card',
                 components=[dict(c,kind='hf_lfs',source='https://huggingface.co/api/models/'+c['repository']+'/'+c['revision']+'?blobs=true') for c in bundle['components']])
    existing = next((i for i,b in enumerate(evidence['bundles']) if b['bundleId']==BUNDLE_ID),None)
    if existing is None: evidence['bundles'].append(proof)
    else: evidence['bundles'][existing] = proof
    # Preserve all earlier proof dates and all inference/device claims verbatim.
    path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(bundle=BUNDLE_ID,components=2,bytes=sum(c['bytes'] for c in bundle['components']),model_downloaded=False,model_executed=False)))


if __name__ == '__main__':
    main()
