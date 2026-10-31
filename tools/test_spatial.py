"""Bounded spatial production tests: random exports, native inputs and workers.

No learned model weights, virtual machines, external inference or phone tests.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from evidence import fingerprint, current
from spatial_reference import ROOT, verify, definitions, shape

OUT = ROOT/'build/spatial-tests'
ALIAS = None
CHECKS = []


def check(case, value, **details):
    assert value, (case, details)
    CHECKS.append(dict(case=case, **details))


def native_path(p):
    return ALIAS+'/'+p.resolve().relative_to(ROOT).as_posix()


def contract(request, success=True):
    f = OUT/'contract.json'
    f.write_text(json.dumps(request), 'utf-8')
    r = subprocess.run([native_path(ROOT/'build/spatial-worker-host/bin/lma_spatial_contract.exe'), native_path(f)],
                       capture_output=True, text=True, encoding='utf-8', timeout=45)
    assert (r.returncode == 0) == success, (request['type'], r.stdout[-500:], r.stderr[-500:])
    return json.loads(r.stdout) if success else {}


def preprocessing():
    import cv2
    import numpy as np
    import torch
    from PIL import Image
    torch.set_num_threads(2)
    rng = np.random.default_rng(82)
    for iw, ih, ow, oh in [(19, 23, 11, 9), (19, 23, 31, 35), (5, 7, 22, 20), (32, 32, 28, 28)]:
        a = rng.integers(0, 256, (ih, iw, 3), dtype=np.uint8)
        for method, kind in [('area', cv2.INTER_AREA), ('cubic', cv2.INTER_CUBIC), ('nearest', cv2.INTER_NEAREST)]:
            got = np.array(contract(dict(type='resize', values=a.flatten().tolist(), iw=iw, ih=ih, ow=ow, oh=oh, channels=3, method=method))['values']).reshape(oh, ow, 3)
            expected = cv2.resize(a, (ow, oh), interpolation=kind)
            error = float(np.max(np.abs(expected.astype(float)-got)))
            check('native_cv_'+method+'_'+str((iw, ih, ow, oh)), error <= 1, maximum8bitError=error)
        got = np.array(contract(dict(type='resize', values=a.flatten().tolist(), iw=iw, ih=ih, ow=ow, oh=oh, channels=3, method='bilinear_aa', quantize=False))['values']).reshape(oh, ow, 3)
        expected = torch.nn.functional.interpolate(torch.tensor(a).permute(2, 0, 1)[None].float(), (oh, ow), mode='bilinear', align_corners=False, antialias=True)[0].permute(1, 2, 0).numpy()
        error = float(np.max(np.abs(expected-got)))
        check('native_torch_antialias_'+str((iw, ih, ow, oh)), error <= .001, maximumFloatError=error)
    for target in ('D06', 'D07'):
        prefix = 'ultrashape' if target == 'D06' else 'hy3dshape/hy3dshape'
        processor = definitions(target, prefix+'/preprocessors.py').ImageProcessorV2
        for case in ('rgb', 'rgba', 'alpha_gradient', 'upsample', 'downsample'):
            h, w = (89, 73) if case == 'downsample' else (37, 43)
            a = rng.integers(0, 256, (h, w, 4), dtype=np.uint8)
            a[:, :, 3] = 0
            a[7:-5, 9:-8, 3] = 255
            if case == 'alpha_gradient':
                a[7:-5, 9:-8, 3] = rng.integers(1, 256, a[7:-5, 9:-8, 3].shape, dtype=np.uint8)
            if case == 'rgb':
                a = a[:, :, :3]
            image = Image.fromarray(a)
            path = OUT/'reference.png'
            image.save(path)
            ps, im = (56, 28) if case == 'downsample' else (28, 42) if case == 'upsample' else (32, 28)
            p = processor(size=ps, border_ratio=.15)(image)
            rgb = (p['image']+1)/2
            expected = torch.nn.functional.interpolate(rgb, (im, im), mode='bilinear', align_corners=False, antialias=True)
            expected = ((expected-torch.tensor([.485, .456, .406])[None, :, None, None])/torch.tensor([.229, .224, .225])[None, :, None, None]).flatten().numpy()
            got = contract(dict(type='image', path=native_path(path), processorSize=ps, imageSize=im, masked=target=='D06'))
            error = float(np.max(np.abs(expected-np.array(got['pixels']))))
            check(target+'_preprocessing_'+case, error <= 2/255/.224+.0001, maxNormalizedError=error, limit='two_8bit_levels')
            if target == 'D06':
                mask = torch.nn.functional.interpolate(p['mask'], (im, im), mode='nearest')
                pool = torch.nn.functional.max_pool2d(mask, 14, 14).flatten()
                selected = [0]+(torch.nonzero(pool != -1).flatten()+1).tolist()
            else:
                selected = list(range((im//14)**2+1))
            check(target+'_mask_'+case, selected == got['selected'])
        transparent = OUT/'empty.png'
        Image.new('RGBA', (32, 32), (0, 0, 0, 0)).save(transparent)
        contract(dict(type='image', path=native_path(transparent), processorSize=32, imageSize=28, masked=target=='D06'), False)
        check(target+'_empty_image_rejected', True)
        _, _, source = shape(target)
        for steps in (1, 2, 7):
            for shift in (1., 2.5):
                s = source.FlowMatchEulerDiscreteScheduler(shift=shift)
                s.set_timesteps(steps, sigmas=np.linspace(0, 1, steps))
                state = torch.tensor([.2, -.1, 1.])
                for time in s.timesteps:
                    state = s.step(torch.tensor([.1, -.7, .4]), time, state, return_dict=False)[0]
                got = contract(dict(type='schedule', state=[.2, -.1, 1.], velocity=[.1, -.7, .4], steps=steps, shift=shift))
                check(target+'_native_schedule_'+str(steps)+'_'+str(shift), np.allclose(state.numpy(), got['state'], atol=1e-6) and np.allclose((s.timesteps/1000).numpy(), got['times'], atol=1e-6))


def write_mesh(path, modify=None, vertices=None, faces=None):
    import numpy as np
    vertices = np.array(vertices if vertices is not None else [[-1, -1, 0], [1, -1, 0], [0, 1, 0]], dtype='<f4')
    faces = np.array(faces if faces is not None else [[0, 1, 2]], dtype='<u4')
    vb, ib = vertices.tobytes(), faces.tobytes()
    data = vb+ib
    root = dict(asset=dict(version='2.0'), buffers=[dict(byteLength=len(data))], bufferViews=[dict(buffer=0, byteOffset=0, byteLength=len(vb)), dict(buffer=0, byteOffset=len(vb), byteLength=len(ib))],
        accessors=[dict(bufferView=0, componentType=5126, count=len(vertices), type='VEC3'), dict(bufferView=1, componentType=5125, count=faces.size, type='SCALAR')],
        meshes=[dict(primitives=[dict(attributes={'POSITION': 0}, indices=1)])], nodes=[dict(mesh=0)], scenes=[dict(nodes=[0])], scene=0)
    if modify:
        modify(root)
    j = json.dumps(root).encode()
    j += b' '*((-len(j))%4)
    path.write_bytes(struct.pack('<IIIII', 0x46546c67, 2, 28+len(j)+len(data), len(j), 0x4e4f534a)+j+struct.pack('<II', len(data), 0x004e4942)+data)
    return root


def write_tetra(path):
    write_mesh(path, vertices=[[-1, -1, -1], [1, -1, 1], [-1, 1, 1], [1, 1, -1]], faces=[[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]])


def sharp_inputs():
    import numpy as np
    import trimesh
    source = definitions('D06', 'ultrashape/surface_loaders.py')
    for name, mesh in [('cube', trimesh.creation.box()), ('tetra', trimesh.Trimesh(
            vertices=[[-1, -1, -1], [1, -1, 1], [-1, 1, 1], [1, 1, -1]],
            faces=[[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]], process=False))]:
        path = OUT/('sharp-'+name+'.glb')
        write_mesh(path, vertices=mesh.vertices, faces=mesh.faces)
        got = contract(dict(type='sharp', path=native_path(path), samples=8192))
        mesh = source.normalize_mesh(mesh.copy(), scale=.99)
        vn, fn, faces = mesh.vertex_normals, mesh.face_normals, mesh.faces
        check('sharp_'+name+'_angle_weighted_normals', np.allclose(vn, got['normals'], atol=1e-6))
        score = np.ones(len(mesh.vertices))
        for j in range(3):
            score[faces[:, j]] = np.minimum(score[faces[:, j]], (vn[faces[:, j]]*fn).sum(-1))
        a, b = np.concatenate((faces[:, 0], faces[:, 1], faces[:, 2])), np.concatenate((faces[:, 1], faces[:, 2], faces[:, 0]))
        keep = (score[a] < .985) & (score[b] < .985)
        edges = np.stack((a[keep], b[keep]), -1)
        check('sharp_'+name+'_publisher_edge_order_and_multiplicity', np.array_equal(edges, got['edges']))
        cumulative = np.linalg.norm(mesh.vertices[edges[:, 0]]-mesh.vertices[edges[:, 1]], axis=1).cumsum()
        check('sharp_'+name+'_publisher_length_distribution', np.allclose(cumulative, got['cumulative'], atol=1e-6))
        np.random.seed(121)
        expected, _ = source.sharp_sample_pointcloud(mesh, num=4096)
        actual = np.array(got['samples'])[4096:]
        def distance(points):
            first, second = mesh.vertices[edges[:, 0]], mesh.vertices[edges[:, 1]]
            delta = second-first
            t = np.clip(((points[:, None]-first)*delta).sum(-1)/(delta*delta).sum(-1), 0, 1)
            return np.linalg.norm(points[:, None]-(first+t[:, :, None]*delta), axis=-1).min(-1)
        check('sharp_'+name+'_native_and_publisher_points_on_edges', distance(expected).max() < 1e-6 and distance(actual).max() < .00085)
        check('sharp_'+name+'_sample_balance_and_float16', len(got['samples']) == 8192 and np.array_equal(np.array(got['samples']), np.array(got['samples'], dtype=np.float16).astype(float)))
        check('sharp_'+name+'_unbiased_edge_centroid', np.allclose(actual.mean(0), expected.mean(0), atol=.045))
    values = np.concatenate((np.random.default_rng(8).uniform(-1, 1, 4000).astype('f4'),
        np.array([0, -0., 2**-25, 3*2**-25, 2**-24, .5+2**-12, .5+3*2**-12], dtype='f4')))
    got = contract(dict(type='half', values=values.tolist()))
    check('surface_float16_round_to_even_matches_numpy', np.array_equal(np.array(got['values'], dtype='f4'), values.astype('f2').astype('f4')))
    path = OUT/'no-sharp.glb'
    write_mesh(path)
    contract(dict(type='sharp', path=native_path(path)), False)
    check('sharp_missing_edges_fails_without_uniform_substitution', True)


def mesh_inputs():
    import numpy as np
    path = OUT/'input.glb'
    write_mesh(path)
    got = contract(dict(type='mesh', path=native_path(path), samples=4096, tokens=512))
    v, points, voxels = [np.array(got[k]) for k in ('vertices', 'samples', 'voxels')]
    voxels = voxels.reshape(-1, 3)
    check('mesh_normalization_extent', np.allclose(v.min(0), [-.99, -.99, 0]) and np.allclose(v.max(0), [.99, .99, 0]))
    check('area_samples_inside_triangle', np.all(points[:, 1] >= -.990001) and np.all(points[:, 1] <= .990001) and np.all(np.abs(points[:, 0]) <= (.99-points[:, 1])/2+1e-6))
    check('area_samples_centroid', np.allclose(points.mean(0), [0, -.33, 0], atol=.025))
    occupied = set(map(tuple, np.clip(np.floor((points+1)*.5*128), 0, 127).astype(int)))
    check('voxel_conditions_occupied', voxels.shape == (512, 3) and set(map(tuple, voxels)) <= occupied and np.all(voxels == np.floor(voxels)))
    write_mesh(path, lambda r: r['nodes'][0].update(scale=[-2, 2, 2], translation=[3, 4, 5]))
    mirrored = contract(dict(type='mesh', path=native_path(path)))
    check('glb_reflection_reverses_winding', mirrored['indices'] == [0, 2, 1])
    mutations = {
        'external_buffer': lambda r: r['buffers'][0].update(uri='https://example.invalid/input'),
        'cycle': lambda r: r['nodes'][0].update(children=[0]),
        'required_extension': lambda r: r.update(extensionsRequired=['KHR_draco_mesh_compression']),
        'animation': lambda r: r.update(animations=[]),
        'skin': lambda r: r.update(skins=[]),
        'sparse': lambda r: r['accessors'][0].update(sparse={}),
        'declared_buffer_length': lambda r: r['buffers'][0].update(byteLength=46),
        'nontriangles': lambda r: r['meshes'][0]['primitives'][0].update(mode=1),
        'index_bounds': lambda r: r['accessors'][1].update(count=9999),
        'bad_scene': lambda r: r.update(scene=2),
        'projective': lambda r: r['nodes'][0].update(matrix=[1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]),
        'quaternion': lambda r: r['nodes'][0].update(rotation=[0, 0, 0, 0]),
    }
    for case, mutation in mutations.items():
        write_mesh(path, mutation)
        contract(dict(type='mesh', path=native_path(path)), False)
        check('native_glb_reject_'+case, True)


def fixture(directory, pipeline, empty=False):
    import onnx
    from onnx import helper as H, TensorProto as T
    directory.mkdir(parents=True, exist_ok=True)
    f = lambda n, s: H.make_tensor_value_info(n, T.FLOAT, s)
    const = lambda n, d, s: H.make_tensor(n, T.FLOAT, s, d)
    def save(name, nodes, inputs, output, constants):
        model = H.make_model(H.make_graph(nodes, name, inputs, [output], constants), opset_imports=[H.make_opsetid('', 17)], ir_version=10)
        onnx.save(model, str(directory/(name+'.onnx')))
    save('image_encoder', [H.make_node('ReduceMean', ['pixel_values'], ['mean'], keepdims=0), H.make_node('Add', ['mean', 'base'], ['image_embeddings'])],
         [f('pixel_values', [1, 3, 28, 28])], f('image_embeddings', [1, 5, 8]), [const('base', [0.]*40, [1, 5, 8])])
    inputs = [f('latents', [1, 'tokens', 4]), f('timestep', [1]), f('image_embeddings', [1, 'image_tokens', 8])]
    nodes = [H.make_node('ReduceMean', ['timestep'], ['time'], keepdims=0), H.make_node('ReduceMean', ['image_embeddings'], ['image'], keepdims=0),
             H.make_node('Add', ['time', 'image'], ['cond'])]
    if pipeline == 'ultrashape_1_refine':
        inputs += [f('voxel_indices', [1, 'tokens', 3])]
        nodes += [H.make_node('ReduceMean', ['voxel_indices'], ['voxel'], keepdims=0), H.make_node('Add', ['cond', 'voxel'], ['combined'])]
    else:
        nodes += [H.make_node('Identity', ['cond'], ['combined'])]
    nodes += [H.make_node('Mul', ['combined', 'zero'], ['bias']), H.make_node('Mul', ['latents', 'scale'], ['state']), H.make_node('Add', ['state', 'bias'], ['velocity'])]
    save('flow', nodes, inputs, f('velocity', [1, 'tokens', 4]), [const('scale', [.1], []), const('zero', [0.], [])])
    save('cache', [H.make_node('Concat', ['latents']*4, ['cache'], axis=2)], [f('latents', [1, 'tokens', 4])], f('cache', [1, 'tokens', 16]), [])
    save('query', [H.make_node('Mul', ['points', 'points'], ['square']), H.make_node('ReduceSum', ['square', 'axes'], ['radius'], keepdims=1),
         H.make_node('ReduceMean', ['cache'], ['mean'], keepdims=0), H.make_node('Mul', ['mean', 'zero'], ['bias']), H.make_node('Sub', ['level', 'radius'], ['sphere']), H.make_node('Add', ['sphere', 'bias'], ['sdf'])],
         [f('cache', [1, 'tokens', 16]), f('points', [1, 'queries', 3])], f('sdf', [1, 'queries', 1]),
         [const('level', [-5. if empty else .5], []), const('zero', [0.], []), H.make_tensor('axes', T.INT64, [1], [2])])
    target = 'D06' if pipeline == 'ultrashape_1_refine' else 'D07'
    entry = next(e for e in verify()['sources'] if e['id'] == target)
    cfg = dict(schema='lma.spatial-shape-export/1', pipeline=pipeline, dtype='float32', opset=17, source={k: entry[k] for k in ('repository', 'revision')},
        latentChannels=4, decoderWidth=16, imageSize=28, processorSize=32, encoderTokens=5, encoderWidth=8, maxTokens=32768, voxelResolution=128,
        scheduleShift=1, borderRatio=.15, boxExtent=1.01)
    (directory/'spatial-config.json').write_text(json.dumps(cfg), 'utf-8')
    return cfg


def custom_fixture(directory):
    import onnx
    from onnx import helper as H, TensorProto as T
    f=lambda n,s:H.make_tensor_value_info(n,T.FLOAT,s)
    constants=[H.make_tensor('axis0',T.INT64,[1],[0]),H.make_tensor('axis1',T.INT64,[1],[1]),H.make_tensor('token_axis',T.INT64,[1],[1])]
    nodes=[H.make_node('Concat',['latents']*4,['full'],axis=2),H.make_node('Squeeze',['full','axis0'],['rows']),H.make_node('Unsqueeze',['rows','axis1'],['heads']),
           H.make_node('Shape',['latents'],['dims']),H.make_node('Gather',['dims','token_axis'],['lengths'],axis=0),
           H.make_node('PackedAttention',['heads','heads','heads','lengths','lengths'],['packed'],domain='lma.spatial'),H.make_node('Transpose',['packed'],['cache'],perm=[1,0,2])]
    model=H.make_model(H.make_graph(nodes,'custom_cache',[f('latents',[1,'tokens',4])],[f('cache',[1,'tokens',16])],constants),opset_imports=[H.make_opsetid('',17),H.make_opsetid('lma.spatial',1)],ir_version=10)
    onnx.checker.check_model(model)
    onnx.save(model,str(directory/'cache.onnx'))


def workers():
    from PIL import Image
    path = OUT/'photo.png'
    Image.new('RGB', (40, 32), (230, 220, 210)).save(path)
    coarse = OUT/'coarse.glb'
    write_tetra(coarse)
    worker = ROOT/'build/spatial-worker-host/bin/lma_spatial.exe'
    check('native_info_no_model_downloads', json.loads(subprocess.check_output([str(worker), '--info']))['modelDownloads'] is False)
    for pipeline in ('hunyuan3d_21_shape', 'ultrashape_1_refine'):
        folder = OUT/pipeline
        cfg = fixture(folder, pipeline)
        names = {'config': 'spatial-config.json', **{k: k+'.onnx' for k in ('image_encoder', 'flow', 'cache', 'query')}}
        original = dict(schema='lma.engine-request/1', type='mesh.generate', pipeline=pipeline, workspace=native_path(folder), referenceImage=native_path(path),
            output=native_path(OUT/'result.glb'), coarseMesh=native_path(coarse), components={k: native_path(folder/v) for k, v in names.items()},
            parameters=dict(steps=2, tokens=512, grid=32, queryChunk=512, maxTriangles=300000))
        cases = ['success', 'custom_domain', 'source_revision', 'wrong_pipeline', 'missing_role', 'external_path', 'bad_dimensions', 'misaligned_grid', 'token_limit', 'missing_image', 'empty_surface', 'triangle_budget', 'unknown_parameter']
        if pipeline.startswith('ultra'):
            cases += ['missing_coarse', 'cyclic_coarse']
        for case in cases:
            request, selected = copy.deepcopy(original), copy.deepcopy(cfg)
            output = Path(request['output'])
            output.unlink(missing_ok=True)
            if case == 'custom_domain': custom_fixture(folder)
            if case == 'source_revision': selected['source']['revision'] = '0'*40
            if case == 'wrong_pipeline': request['pipeline'] = 'unknown'
            if case == 'missing_role': request['components'].pop('cache')
            if case == 'external_path': request['components']['flow'] = native_path(path)
            if case == 'bad_dimensions': selected['latentChannels'] = 0
            if case == 'misaligned_grid': request['parameters']['grid'] = 33
            if case == 'token_limit': selected['maxTokens'], request['parameters']['tokens'] = 512, 1024
            if case == 'missing_image': request['referenceImage'] = native_path(OUT/'absent.png')
            if case == 'empty_surface': fixture(folder, pipeline, True)
            if case == 'triangle_budget': request['parameters']['maxTriangles'] = 1000
            if case == 'unknown_parameter': request['parameters']['remote_url'] = 'https://example.invalid'
            if case == 'missing_coarse': request.pop('coarseMesh')
            if case == 'cyclic_coarse': write_mesh(coarse, lambda r: r['nodes'][0].update(children=[0]))
            if case != 'empty_surface': (folder/'spatial-config.json').write_text(json.dumps(selected), 'utf-8')
            f = OUT/'worker.json'
            f.write_text(json.dumps(request), 'utf-8')
            r = subprocess.run([native_path(worker), native_path(f)], capture_output=True, text=True, encoding='utf-8', timeout=45)
            events = [json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
            done = any(e['event'] == 'complete' for e in events)
            check(pipeline+'_'+case, done == (case in ('success','custom_domain')) and (r.returncode == 0) == done, exitCode=r.returncode)
            check(pipeline+'_'+case+'_measurement', any(e['event'] == 'execution' and 'runtimeMeasurements' in e['details'] for e in events))
            if done:
                data = output.read_bytes()
                g = json.loads(data[20:20+struct.unpack_from('<I', data, 12)[0]])
                check(pipeline+'_actual_glb', len(g['meshes']) == 1 and all('uri' not in b for b in g['buffers']) and g['accessors'][0]['count'] > 100)
            else:
                check(pipeline+'_'+case+'_no_result', not output.exists())
            if case in ('empty_surface','custom_domain'): fixture(folder, pipeline)
            if case == 'cyclic_coarse': write_tetra(coarse)


def cli_exports():
    import torch
    from safetensors.torch import save_file
    from transformers import Dinov2Config, Dinov2Model
    from spatial_shape_graphs import modules
    for target, pipeline in [('D06', 'ultrashape_1_refine'), ('D07', 'hunyuan3d_21_shape')]:
        fc = dict(input_size=512, in_channels=4, hidden_size=16, context_dim=8, depth=3, num_heads=2, qk_norm=True, qkv_bias=False,
                  num_moe_layers=1, num_experts=3, moe_top_k=2)
        if target == 'D07': fc.update(use_attention_pooling=False, use_pos_emb=False)
        vc = dict(num_latents=512, embed_dim=4, width=16, heads=2, num_decoder_layers=2, qkv_bias=False, qk_norm=True, num_freqs=2, scale_factor=1.0039506158752403)
        flow, cache, query, _ = modules(target, fc, vc)
        ic = Dinov2Config(image_size=28, patch_size=14, hidden_size=8, num_hidden_layers=2, num_attention_heads=2, intermediate_size=32).to_dict()
        image = Dinov2Model(Dinov2Config.from_dict(ic))
        prefix = 'ultrashape' if target == 'D06' else 'hy3dshape'
        raw = dict(model=dict(target=prefix+'.models.denoisers.'+('dit_mask.RefineDiT' if target == 'D06' else 'hunyuandit.HunYuanDiTPlain'), params=fc),
            vae=dict(target=prefix+'.models.autoencoders.ShapeVAE', params=vc),
            conditioner=dict(target=prefix+'.models.'+('conditioner_mask' if target == 'D06' else 'conditioner')+'.SingleImageEncoder', params=dict(drop_ratio=0., main_image_encoder=dict(type='DinoImageEncoder', kwargs=dict(config=ic, image_size=28, use_cls_token=True)))),
            scheduler=dict(target=prefix+'.schedulers.FlowMatchEulerDiscreteScheduler', params=dict(num_train_timesteps=1000)),
            image_processor=dict(target=prefix+'.preprocessors.ImageProcessorV2', params=dict(size=32)))
        if target == 'D06':
            raw = dict(model=dict(target='ultrashape.pipelines.UltraShapePipeline', params=dict(dit_cfg=raw['model'], vae_config=raw['vae'], conditioner_config=raw['conditioner'], scheduler_cfg=raw['scheduler'], image_processor_cfg=raw['image_processor'])))
        ckpt = {('dit.' if target == 'D06' else 'model.')+k: v.contiguous() for k, v in flow.state_dict().items()}
        ckpt.update({'vae.'+k: v.contiguous() for k, v in cache.state_dict().items()})
        ckpt.update({'vae.'+k: v.contiguous() for k, v in query.state_dict().items()})
        ckpt.update({'conditioner.main_image_encoder.model.'+k: v.contiguous() for k, v in image.state_dict().items()})
        folder = OUT/(target+'-snapshot')
        folder.mkdir(exist_ok=True)
        c, w = folder/'config.json', folder/'random.safetensors'
        c.write_text(json.dumps(raw), 'utf-8')
        save_file(ckpt, str(w))
        exported = OUT/(target+'-export')
        if exported.exists(): assert exported.resolve().parent == OUT.resolve(); shutil.rmtree(exported)
        command = [sys.executable, str(ROOT/'tools/export_spatial.py'), '--pipeline', pipeline, '--config', str(c), '--checkpoint', str(w), '--output', str(exported)]
        r = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=100,
            env={**os.environ, 'PYTHONPATH': os.pathsep.join([str(ROOT/'build/shape-reference-python'), str(ROOT/'build/spatial-reference-python')])})
        (folder/'export.log').write_text(r.stdout+r.stderr, 'utf-8')
        assert r.returncode == 0, (pipeline, r.stdout[-300:], r.stderr[-1800:])
        manifest = json.loads((exported/'lma-bundle.json').read_text('utf-8'))
        check(pipeline+'_cli_bundle', manifest['engine'] == 'spatial_ort' and manifest['pipeline'] == pipeline and manifest['evidence']['acquisition'] == 'import_only')
        for component in manifest['components']:
            file = exported/component['path']
            check(pipeline+'_cli_'+component['role'], component['url'] == '' and file.stat().st_size == component['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest() == component['sha256'])
        r = subprocess.run(command, capture_output=True, timeout=30, env={**os.environ, 'PYTHONPATH': str(ROOT/'build/shape-reference-python')})
        check(pipeline+'_no_overwrite', r.returncode != 0)


def main():
    global ALIAS
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1')
    sys.path[:0] = [str(ROOT/'build/spatial-reference-python'), str(ROOT/'build/shape-reference-python')]
    verify()
    OUT.mkdir(exist_ok=True)
    inputs = fingerprint('native/spatial', 'native/rf_shape', 'tests/expansion-native/spatial.cpp', 'tools/test_spatial.py', 'tools/export_spatial.py',
        'tools/spatial_shape_graphs.py', 'tools/spatial_reference.py', 'tools/spatial_catalogue.py', 'third_party/spatial-shape-source-lock.json')
    ALIAS = next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()), None)
    assert ALIAS
    subprocess.run(['subst', ALIAS, str(ROOT)], check=True, capture_output=True)
    try:
        preprocessing()
        mesh_inputs()
        sharp_inputs()
        workers()
        cli_exports()
        current(inputs)
    finally:
        subprocess.run(['subst', ALIAS, '/D'], check=True, capture_output=True)
    report = dict(passed=len(CHECKS), checks=CHECKS, input_fingerprint=inputs, completeModelsDownloaded=0, completeModelsRun=0, physicalDeviceTests=0, virtualizationUsed=False)
    (OUT/'results.json').write_text(json.dumps(report, indent=2)+'\n', 'utf-8')
    print(json.dumps(dict(passed=report['passed'], completeModelsRun=0, physicalDeviceTests=0)))


if __name__ == '__main__':
    main()
