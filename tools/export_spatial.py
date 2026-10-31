"""Offline conversion of user-selected Hunyuan3D/UltraShape assets, no fetching.

This is asset preparation, never a runtime inference provider. Model YAML target
strings are checked against fixed classes, never imported dynamically. PT files
use weights_only=True; plain pickle and constructor/download fallbacks are absent.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
from spatial_reference import ROOT, verify

PIPELINES = {'hunyuan3d_21_shape': 'D07', 'ultrashape_1_refine': 'D06'}


class Weights:
    def __init__(self, path):
        import torch
        self.path, self.mapping = path, None
        if path.suffix == '.safetensors':
            from safetensors import safe_open
            self.file = safe_open(str(path), framework='pt', device='cpu')
            self.keys = set(self.file.keys())
        elif path.suffix in ('.pt', '.ckpt'):
            data = torch.load(path, map_location='cpu', weights_only=True)
            assert isinstance(data, dict), 'Expected a tensor state dictionary'
            flat = {}
            for k, v in data.items():
                assert isinstance(k, str)
                if isinstance(v, dict):
                    for name, tensor in v.items():
                        assert isinstance(name, str) and torch.is_tensor(tensor), 'Non-tensor checkpoint value'
                        flat[k + '.' + name] = tensor
                else:
                    assert torch.is_tensor(v), 'Non-tensor checkpoint value'
                    flat[k] = v
            self.mapping, self.keys = flat, set(flat)
        else:
            raise ValueError('Choose .safetensors or a weights-only .pt/.ckpt')

    def load(self, module, prefix, exact=False):
        wanted = set(module.state_dict())
        available = {key[len(prefix):] for key in self.keys if key.startswith(prefix)}
        assert wanted <= available, 'Missing matched tensors for ' + prefix + ': ' + str(sorted(wanted - available)[:12])
        if exact:
            assert available == wanted, 'Unexpected architecture tensors for ' + prefix
        selected = {k: self.mapping[prefix+k] if self.mapping is not None else self.file.get_tensor(prefix+k) for k in wanted}
        module.load_state_dict(selected, strict=True)
        del selected


def configs(target, c, image_config=None):
    prefix = 'ultrashape' if target == 'D06' else 'hy3dshape'
    if target == 'D06':
        assert c['model']['target'] == 'ultrashape.pipelines.UltraShapePipeline'
        c = c['model']['params']
        fc, vc, ic, sc, pc = [c[n] for n in ('dit_cfg', 'vae_config', 'conditioner_config', 'scheduler_cfg', 'image_processor_cfg')]
    else:
        fc, vc, ic, sc, pc = [c[n] for n in ('model', 'vae', 'conditioner', 'scheduler', 'image_processor')]
    assert fc['target'] == prefix + '.models.denoisers.' + ('dit_mask.RefineDiT' if target == 'D06' else 'hunyuandit.HunYuanDiTPlain')
    assert vc['target'] == prefix + '.models.autoencoders.ShapeVAE'
    assert ic['target'] == prefix + '.models.' + ('conditioner_mask' if target == 'D06' else 'conditioner') + '.SingleImageEncoder'
    assert sc['target'] == prefix + '.schedulers.FlowMatchEulerDiscreteScheduler'
    assert pc['target'] == prefix + '.preprocessors.ImageProcessorV2'
    ic = ic['params']
    assert set(ic) <= {'main_image_encoder', 'drop_ratio'}
    encoder = ic['main_image_encoder']
    assert encoder['type'] == 'DinoImageEncoder'
    kw = encoder['kwargs']
    assert kw.get('use_cls_token', True) is True
    dinoconfig = kw.get('config') or image_config
    assert dinoconfig and dinoconfig.get('model_type', 'dinov2') == 'dinov2', 'Supply --image-config for version-only local DINO architecture'
    assert dinoconfig.get('patch_size', 14) == 14
    schedule = sc.get('params', {})
    assert set(schedule) <= {'num_train_timesteps', 'shift'}
    image = pc.get('params', {})
    assert set(image) <= {'size', 'border_ratio'}
    return fc['params'], vc['params'], dinoconfig, int(kw.get('image_size', 224)), schedule, image


def manifest(out, pipeline, cfg, identity):
    from spatial_catalogue import definition
    (out/'spatial-config.json').write_text(json.dumps(cfg, indent=2)+'\n', 'utf-8')
    roles = {'config': 'spatial-config.json', **{k: k+'.onnx' for k in ('image_encoder', 'flow', 'cache', 'query')}}
    for role, name in list(roles.items()):
        if (out/(name+'.data')).is_file():
            roles[role+'_data'] = name+'.data'
    components = []
    for role, name in roles.items():
        file = out/name
        with file.open('rb') as f:
            sha = hashlib.file_digest(f, 'sha256').hexdigest()
        components.append(dict(role=role, path=name, format='json' if role == 'config' else 'onnx_data' if role.endswith('_data') else 'onnx',
                               bytes=file.stat().st_size, sha256=sha, url='', repository='local/export', revision=identity))
    d = definition(pipeline)
    maximum = min(cfg['maxTokens'], (32000000//cfg['decoderWidth']//512)*512)
    d['parameters']['fields']['tokens'].update(maximum=maximum, default=min(maximum, d['parameters']['fields']['tokens']['default']))
    d['parameters']['fields']['tokens']['presets'] = [n for n in (512, 1024, 4096, 8192, 16384) if n <= maximum]
    b = dict(schema='lma.model-bundle/2', id=pipeline+'_'+identity[:12], modelId=pipeline+'_'+identity[:12], name=pipeline+' · local FP32 export',
             recipeId=pipeline+'_onnx_cpu_v1', catalogue=False, components=components, **d,
             description='用户明确选择的离线转换资产；模型质量、手机运行和资源未测。',
             resources=dict(source='unmeasured', estimatedPeakRamBytes=0), content=dict(classification='unclassified', basis='none'),
             evidence=dict(status='user_export_not_device_tested', acquisition='import_only', modelInferenceTested=False, physicalDeviceTests=0),
             license=dict(name='Original model and per-file terms apply', url='https://github.com/'+cfg['source']['repository'], status='component_terms_apply'))
    (out/'lma-bundle.json').write_text(json.dumps(b, ensure_ascii=False, indent=2)+'\n', 'utf-8')
    (out/'export-receipt.json').write_text(json.dumps(dict(schema='lma.spatial-export-receipt/1', source=cfg['source'], snapshotIdentity=identity,
        network=False, exportTracingExecutesDummyForwards=True, completeModelInferenceTested=False, physicalDeviceTests=0, components=components), indent=2)+'\n', 'utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pipeline', choices=PIPELINES, required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--image-config', type=Path)
    p.add_argument('--image-snapshot', type=Path, help='Optional existing local DINO safetensors directory when checkpoint omits conditioner')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1', USE_SAGEATTN='0')
    verify()
    import torch
    import yaml
    from transformers import Dinov2Config, Dinov2Model
    from spatial_shape_graphs import modules, portable, HunyuanFlow, UltraFlow
    from shape_graphs import export_graph, ImageEncoder
    target = PIPELINES[a.pipeline]
    assert a.config.is_file() and a.config.stat().st_size <= 65536 and a.checkpoint.is_file()
    out = a.output.resolve()
    assert not out.exists(), 'Export destination must be new; existing assets are never replaced'
    text = a.config.read_text('utf-8')
    raw = json.loads(text) if text.lstrip().startswith('{') else yaml.safe_load(text)
    extra = json.loads(a.image_config.read_text('utf-8')) if a.image_config else None
    fc, vc, ic, im, schedule, pre = configs(target, raw, extra)
    assert 28 <= im <= 1022 and im % 14 == 0
    assert 1 <= int(fc['in_channels']) <= 512 and 8 <= int(vc['width']) <= 4096
    assert int(fc['context_dim']) == int(ic['hidden_size']) and int(fc['in_channels']) == int(vc['embed_dim'])
    assert 512 <= int(vc['num_latents']) <= 32768
    flow, cache, query, _ = modules(target, fc, vc)
    weights = Weights(a.checkpoint.resolve())
    weights.load(flow, 'dit.' if target == 'D06' else 'model.', exact=True)
    weights.load(cache, 'vae.')
    weights.load(query, 'vae.')
    portable(flow, target)
    image = Dinov2Model(Dinov2Config.from_dict(ic)).float().eval()
    if any(k.startswith('conditioner.main_image_encoder.model.') for k in weights.keys):
        weights.load(image, 'conditioner.main_image_encoder.model.', exact=True)
    else:
        assert a.image_snapshot and a.image_snapshot.is_dir(), 'Missing conditioner; explicitly select an existing local DINO snapshot'
        image = Dinov2Model.from_pretrained(a.image_snapshot, local_files_only=True, use_safetensors=True, attn_implementation='eager').float().eval()
        assert image.config.to_dict() == Dinov2Config.from_dict(ic).to_dict(), 'DINO snapshot architecture differs from the chosen config'
    image.set_attn_implementation('eager')
    entry = next(e for e in verify()['sources'] if e['id'] == target)
    cfg = dict(schema='lma.spatial-shape-export/1', pipeline=a.pipeline, dtype='float32', opset=17,
        source={k: entry[k] for k in ('repository', 'revision')}, latentChannels=int(fc['in_channels']), decoderWidth=int(vc['width']),
        imageSize=im, processorSize=int(pre.get('size', 512)), encoderTokens=(im//14)**2+1, encoderWidth=int(ic['hidden_size']),
        maxTokens=int(vc['num_latents']), voxelResolution=int(fc.get('voxel_query_res', 128)), scheduleShift=float(schedule.get('shift', 1)),
        borderRatio=.15 if pre.get('border_ratio') is None else float(pre['border_ratio']), boxExtent=1.0 if target == 'D06' else 1.01)
    assert 28 <= cfg['processorSize'] <= 1024 and 0 <= cfg['borderRatio'] < .5 and 0 < cfg['scheduleShift'] <= 16
    identity = hashlib.sha256(json.dumps(dict(config=raw, image=ic, pipeline=a.pipeline), sort_keys=True).encode())
    files = [a.checkpoint, a.config] + ([a.image_config] if a.image_config else [])
    if a.image_snapshot:
        files += sorted(a.image_snapshot.glob('*.safetensors'))
    for file in files:
        with file.open('rb') as f:
            identity.update(hashlib.file_digest(f, 'sha256').digest())
    del weights
    gc.collect()
    torch.set_num_threads(4)
    out.mkdir(parents=True)
    export_graph(ImageEncoder(image), (torch.zeros(1, 3, im, im),), out/'image_encoder.onnx', ['pixel_values'], 'image_embeddings', {})
    del image
    gc.collect()
    x, t, e = torch.randn(1, 8, cfg['latentChannels']), torch.ones(1), torch.zeros(1, 5, cfg['encoderWidth'])
    args = (x, t, e, torch.zeros(1, 8, 3)) if target == 'D06' else (x, t, e)
    names = ['latents', 'timestep', 'image_embeddings'] + (['voxel_indices'] if target == 'D06' else [])
    dynamic = {'latents': {1: 'tokens'}, 'velocity': {1: 'tokens'}, 'image_embeddings': {1: 'image_tokens'}}
    if target == 'D06':
        dynamic['voxel_indices'] = {1: 'tokens'}
    export_graph(UltraFlow(flow) if target == 'D06' else HunyuanFlow(flow), args, out/'flow.onnx', names, 'velocity', dynamic)
    del flow
    gc.collect()
    export_graph(cache, (x,), out/'cache.onnx', ['latents'], 'cache', {'latents': {1: 'tokens'}, 'cache': {1: 'tokens'}})
    export_graph(query, (torch.randn(1, 8, cfg['decoderWidth']), torch.randn(1, 11, 3)), out/'query.onnx', ['cache', 'points'], 'sdf',
                 {'cache': {1: 'tokens'}, 'points': {1: 'queries'}, 'sdf': {1: 'queries'}})
    manifest(out, a.pipeline, cfg, identity.hexdigest())
    print('Local export complete. Import lma-bundle.json and its chosen components. No phone or quality acceptance is implied.')


if __name__ == '__main__':
    main()
