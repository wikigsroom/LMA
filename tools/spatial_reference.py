"""Load reviewed CPU reference definitions without installing upstream runtimes.

Only named source files from the fixed source-tree receipt are accepted. Model
constructors are called by the offline exporter with checkpoint paths disabled.
Training, CUDA installation and upstream download helpers are never invoked.
"""
import ast
import hashlib
import json
import logging
import os
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'build/spatial-source-review'


def verify():
    lock = json.loads((ROOT / 'third_party/spatial-shape-source-lock.json').read_text('utf-8'))
    for entry in lock['sources']:
        for item in entry['files']:
            data = (ROOT / entry['directory'] / item['path']).read_bytes()
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], 'Changed pinned spatial source: ' + item['path']
    return lock


def read(target, relative):
    lock = json.loads((ROOT / 'third_party/spatial-shape-source-lock.json').read_text('utf-8'))
    entry = next(x for x in lock['sources'] if x['id'] == target)
    item = next(x for x in entry['files'] if x['path'] == relative)
    path = SOURCES / 'repos' / target / relative
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == item['sha256'], 'Changed reference: ' + relative
    return path, data.decode('utf-8-sig')


def definitions(target, relative, injections=None, omit_imports=(), cpu_devices=False, static_shape_keys=False):
    path, source = read(target, relative)
    tree = ast.parse(source, str(path))
    if cpu_devices or static_shape_keys:
        class CpuExport(ast.NodeTransformer):
            def visit_Constant(self,node):
                if cpu_devices and isinstance(node.value,str) and node.value in ('cuda:0','cuda:1'):
                    return ast.copy_location(ast.Constant('cpu'),node)
                return node
            def visit_Subscript(self,node):
                self.generic_visit(node)
                if static_shape_keys and ast.unparse(node)=='multivew_hidden_states.shape[1]':
                    return ast.copy_location(ast.Call(ast.Name('int',ast.Load()),[node],[]),node)
                return node
        tree=ast.fix_missing_locations(CpuExport().visit(tree))
    omitted = []
    body = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.level or node.module in omit_imports):
            omitted.append(ast.unparse(node))
            continue
        if isinstance(node, ast.Import) and any(a.name in omit_imports for a in node.names):
            omitted.append(ast.unparse(node))
            continue
        body.append(node)
    module = types.ModuleType('lma_reference_' + target + '_' + path.stem)
    module.__file__ = str(path)
    module.__dict__.update(injections or {})
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), module.__dict__)
    module.omitted_imports = omitted
    return module


def reject_unused(*args, **kwargs):
    raise RuntimeError('This training/checkpoint helper is not part of the offline CPU export')


def shape(target):
    assert target in ('D06', 'D07')
    os.environ['USE_SAGEATTN'] = '0'
    prefix = 'ultrashape' if target == 'D06' else 'hy3dshape/hy3dshape'
    processor = definitions(target, prefix + '/models/autoencoders/attention_processors.py')
    injected = dict(CrossAttentionProcessor=processor.CrossAttentionProcessor,
                    logger=logging.getLogger('lma.spatial.reference'), smart_load_model=reject_unused,
                    synchronize_timer=lambda *a, **kw: lambda f: f)
    if target == 'D06':
        injected['voxelize_from_point'] = definitions(target, prefix + '/utils/voxelize.py').voxelize_from_point
    attention = definitions(target, prefix + '/models/autoencoders/attention_blocks.py', injected,
                            omit_imports=('ultrashape.utils',))
    moe = definitions(target, prefix + '/models/denoisers/moe_layers.py', omit_imports=('timm.models.vision_transformer',))
    injected.update(MoEBlock=moe.MoEBlock, flash_attn_varlen_func=reject_unused)
    flow = definitions(target, prefix + '/models/denoisers/' + ('dit_mask.py' if target == 'D06' else 'hunyuandit.py'),
                       injected, omit_imports=('flash_attn',))
    scheduler = definitions(target, prefix + '/schedulers.py')
    return attention, flow, scheduler
