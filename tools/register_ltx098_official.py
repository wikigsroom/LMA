"""Register optional publisher-pinned assets. Never download or execute models."""
import copy
import json
from pathlib import Path
from ltx098_official_profile import ROOT, lock, recipe, PIPELINE


def main():
    sources = lock()['sources']
    path = ROOT / 'catalogue/model-bundles.json'
    catalogue = json.loads(path.read_text(encoding='utf-8'))
    old = next(b for b in catalogue['bundles'] if b['id'] == 'ltx098_runtime_google_q5_v2')
    model = copy.deepcopy(old)
    model.update(id='ltx098_runtime_pixart_multiscale_v1', modelId='ltx_video_2b_098_distilled_pixart', recipeId=PIPELINE,
        name='旧 LTX 0.9.8 · PixArt 多尺度', description=recipe()['help'], pipeline=PIPELINE,
        capabilities=['text_to_video', 'runtime_assets', 'derived_assets', 'pixart_t5', 'multiscale'], parameters=recipe()['definition']['parameters'],
        license=dict(name='LTX-Video Open Weights 0.x; PixArt OpenRAIL++',
            url='https://huggingface.co/PixArt-alpha/PixArt-XL-2-1024-MS/blob/b89adadeccd9ead2adcb9fa2825d3fabec48d404/README.md'))
    model['evidence'].update(status='program_adapter_not_model_or_device_tested', modelInferenceTested=False)
    model['components'] = [c for c in model['components'] if c['role'] not in ['text_encoder', 'tokenizer_config']]
    roles = [('text_config', 'text_encoder/config.json', 'json'), ('text_index', 'text_encoder/model.safetensors.index.json', 'json'),
        ('text_shard_1', 'text_encoder/model-00001-of-00002.safetensors', 'safetensors'),
        ('text_shard_2', 'text_encoder/model-00002-of-00002.safetensors', 'safetensors'),
        ('tokenizer_config', 'tokenizer/tokenizer_config.json', 'json'), ('tokenizer', 'tokenizer/spiece.model', 'sentencepiece'),
        ('upscaler', 'ltxv-spatial-upscaler-0.9.8.safetensors', 'safetensors')]
    for role, file, format in roles:
        source = next(s for s in sources if any(f['file'] == file for f in s['files']))
        record = next(f for f in source['files'] if f['file'] == file)
        model['components'].append(dict(role=role, path=file, format=format, bytes=record['bytes'], sha256=record['sha256'],
            repository=source['repository'], revision=source['revision'],
            url='https://huggingface.co/' + source['repository'] + '/resolve/' + source['revision'] + '/' + file))
    catalogue['bundles'] = [b for b in catalogue['bundles'] if b['id'] != model['id']] + [model]
    path.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    path = ROOT / 'catalogue/bundle-evidence.json'
    evidence = json.loads(path.read_text(encoding='utf-8'))
    old_proof = next(b for b in evidence['bundles'] if b['bundleId'] == old['id'])
    proof = copy.deepcopy(old_proof)
    proof['bundleId'] = model['id']
    old_components = {c['role']: c for c in old_proof['components']}
    proof['components'] = []
    for component in model['components']:
        if component['role'] in old_components and component['role'] != 'tokenizer_config':
            proof['components'].append(copy.deepcopy(old_components[component['role']]))
        else:
            item = copy.deepcopy(component)
            item.update(kind='hf_lfs' if component['format'] == 'safetensors' else 'downloaded_small_data',
                        source='third_party/ltx098-official/identity.json', full_model_downloaded_for_this_update=False)
            proof['components'].append(item)
    evidence['bundles'] = [b for b in evidence['bundles'] if b['bundleId'] != model['id']] + [proof]
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    path = ROOT / 'catalogue/model-assemblies.json'
    assemblies = json.loads(path.read_text(encoding='utf-8'))
    plan = copy.deepcopy(next(p for p in assemblies['plans'] if p['id'] == 'ltx098_google_q5_generation_v2'))
    plan.update(id='ltx098_pixart_generation_v1', name='关联运行模型 · 旧 LTX PixArt 多尺度', bundleId=model['id'])
    assemblies['plans'] = [p for p in assemblies['plans'] if p['id'] != plan['id']] + [plan]
    path.write_text(json.dumps(assemblies, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(optional_bundle=model['id'], components=len(model['components']), total_bytes=sum(c['bytes'] for c in model['components']),
                         automatic_downloads=False, model_inference=False)))


if __name__ == '__main__':
    main()
