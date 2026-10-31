"""CPU batch-one bindings for hash-pinned sparse network definitions.

Offline asset preparation only. Android loads signed native operators and ONNX,
never this Python source. Learned layers/state names remain the publisher's.
CUDA sparse containers, packed attention and coordinate resampling are replaced
with fixed CPU operators; no checkpoint constructor or Hub helper is invoked.
"""
import ast
import copy
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from functools import partial
import hashlib
import importlib.util
import json
import math
import logging
from pathlib import Path
import re
import sys
import types
import typing

import numpy as np
import torch
from torch import nn
from spatial_sparse_graphs import operation

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT/'third_party/portable-sparse-source-lock.json'


def dynamic_len(value):
    return value.shape[0] if isinstance(value, torch.Tensor) else len(value)


def static_layer_norm(value,shape,*args,**kwargs):
    # Only feature widths are architecture constants; row counts stay dynamic.
    return nn.functional.layer_norm(value,tuple(int(v) for v in shape),*args,**kwargs)


class RealRoPE(nn.Module):
    """Same adjacent complex pairs, represented by real cos/sin for ONNX."""
    def __init__(self, head_dim, dim=3, rope_freq=(1., 10000.)):
        super().__init__()
        assert head_dim % 2 == 0
        self.head_dim, self.dim, self.rope_freq = head_dim, dim, rope_freq
        self.freq_dim = head_dim//2//dim
        self.freqs = rope_freq[0]/(rope_freq[1]**(torch.arange(self.freq_dim).float()/self.freq_dim))

    def forward(self, indices):
        phases = (indices.float().unsqueeze(-1)*self.freqs).reshape(*indices.shape[:-1],self.dim*self.freq_dim)
        return nn.functional.pad(phases, (0, self.head_dim//2-self.freq_dim*self.dim))

    @staticmethod
    def apply_rotary_embedding(x, phases):
        width=int(x.shape[-1])
        a = x.float().reshape(*x.shape[:-1], width//2, 2)
        cos, sin = phases.cos().unsqueeze(-2), phases.sin().unsqueeze(-2)
        return torch.stack((a[..., 0]*cos-a[..., 1]*sin, a[..., 0]*sin+a[..., 1]*cos), -1).reshape(*x.shape[:-1],width).to(x.dtype)


class SparseRoPE(RealRoPE):
    def forward(self, q, k=None):
        phases = super().forward(q.coords[:, 1:])
        rotated = q.replace(self.apply_rotary_embedding(q.feats, phases))
        return rotated if k is None else (rotated, k.replace(self.apply_rotary_embedding(k.feats, phases)))


def routed_attention(self,x,context):
    """Publisher projections/RMS with the same selected real-view attention.

    Batch one is a closed exporter/runtime contract. The native op replaces
    only packing, stable grouping, Flash varlen and inverse permutation.
    """
    full=context['full_bank']
    assert full.shape[0]==1 and full.shape[2]==self.full_tokens
    q=self.to_q(x.feats).reshape(-1,self.num_heads,self.head_dim)
    if self.qk_rms_norm:q=self.q_rms_norm(q)
    kv=self.to_kv(full[0]).reshape(full.shape[1],self.full_tokens,2,self.num_heads,self.head_dim)
    k,v=kv.unbind(2)
    if self.qk_rms_norm:k=self.k_rms_norm(k)
    output=operation('routed')(q,k,v,context['selected_rows'].long())
    return x.replace(self.to_out(output.reshape(x.feats.shape[0],self.channels)))


def packed_shape_attention(self,query,shape_tokens,shape_offsets):
    # The phone coordinator validates [0,N] before this closed B=1 graph.
    # Keeping the real attention method prevents Python int(offset) from
    # freezing the traced example's sparse shape-token count into the graph.
    assert query.shape[0]==1
    residual=self.out_proj(self._attention(query[0],shape_tokens))
    return query+residual.unsqueeze(0)


class Source:
    def __init__(self, target):
        lock = json.loads(LOCK.read_text('utf-8'))
        self.record = next(s for s in lock['sources'] if s['id'] == target)
        self.target = target
        self.prefix = {'D05':'uniforge3d','D10':'supratex','D08':'sam3d_objects/model/backbone/tdfy_dit',
                       'D09':'sam3d_objects/model/backbone/tdfy_dit','MOGE':'moge','DA3':'src/depth_anything_3','TIMM':'timm'}[target]
        self.package = self.prefix.replace('/','.')
        self.files = {i['path']: i for i in self.record['files']}
        self.modules = {}
        self.used = set()
        self.config = types.SimpleNamespace(CONV='lma_cpu', DEBUG=False, BATCH_BROADCAST='direct')
        self.sparse = None

    def read(self, relative):
        item = self.files[relative]
        path = ROOT/self.record['directory']/relative
        data = path.read_bytes()
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], relative
        self.used.add(relative)
        return path, data.decode('utf-8-sig')

    def namespace(self, relative, injections=None):
        if relative==self.prefix+'/modules/utils.py' and self.sparse is None:
            # utils references sparse primitives, while sparse norm imports
            # utils.manual_cast. Resolve the primitives before caching utils,
            # avoiding a half-initialized module whose definitions are absent.
            self.sparse_api()
        if relative in self.modules:
            return self.modules[relative]
        path, text = self.read(relative)
        name = 'lma_portable_'+self.target+'_'+relative.replace('/', '_').replace('.', '_')
        module = types.ModuleType(name)
        module.__file__ = str(path)
        self.modules[relative] = module
        sys.modules[name] = module
        env = module.__dict__
        env.update({k:v for k,v in vars(typing).items() if not k.startswith('_')})
        functional=types.SimpleNamespace(**{k:v for k,v in vars(nn.functional).items() if not k.startswith('__')})
        functional.layer_norm=static_layer_norm
        env.update(torch=torch, nn=nn, F=functional, np=np, math=math, re=re, copy=copy,
                   Fraction=Fraction, partial=partial, dataclass=dataclass, contextmanager=contextmanager,
                   config=self.config, len=dynamic_len, Tensor=torch.Tensor, OrderedDict=OrderedDict,
                   Path=Path, logging=logging, logger=logging.getLogger('lma.portable'))
        env.update(getattr(self,'injections',{}))
        env['trunc_normal_']=nn.init.trunc_normal_
        env['flash_attn_varlen_func']=lambda q,k,v,cq,ck,*args,**kw: operation('attention')(q,k,v,(cq[1:]-cq[:-1]).long(),(ck[1:]-ck[:-1]).long())
        # Hub mixin has no role in local constructors; exposing a method that
        # could fetch assets would defeat this offline source boundary.
        env['PyTorchModelHubMixin']=type('LocalOnlyModelMixin', (), {})
        tree = ast.parse(text, str(path))
        # Resolve only explicitly source-locked local definitions. Import bodies,
        # source package __init__, installers and module-level I/O never execute.
        for node in tree.body:
            if not isinstance(node, ast.ImportFrom) or node.module == '__future__':
                continue
            if node.level:
                base = relative[:-3].replace('/', '.')
                qualified = importlib.util.resolve_name('.'*node.level+(node.module or ''), base.rsplit('.', 1)[0])
            else:
                qualified = node.module or ''
            if not qualified.startswith(self.package):
                continue
            for alias in node.names:
                if (alias.asname or alias.name) in (injections or {}):continue
                if qualified == self.package+'.modules' and alias.name == 'sparse':
                    env[alias.asname or alias.name] = self.sparse_api()
                elif qualified.startswith(self.package+'.modules.sparse'):
                    api = self.sparse_api()
                    if alias.name == 'config':env[alias.asname or alias.name] = self.config
                    elif alias.name == '*':env.update(vars(api))
                    elif hasattr(api, alias.name):env[alias.asname or alias.name] = getattr(api, alias.name)
                    else:
                        file = qualified.replace('.', '/')+'.py'
                        if qualified.endswith('.attention') and 'ProjectAttention' in alias.name:
                            file=qualified.replace('.', '/')+'/proj_attention.py'
                        if file not in self.files:file=qualified.replace('.', '/')+'/blocks.py'
                        dependency=self.namespace(file)
                        if not hasattr(dependency,alias.name) and qualified.endswith('.transformer'):
                            dependency=self.namespace(qualified.replace('.', '/')+'/modulated.py')
                        env[alias.asname or alias.name]=getattr(dependency,alias.name)
                elif qualified == self.package+'.modules.attention':
                    dependency = self.namespace(self.prefix+'/modules/attention/modules.py')
                    if alias.name == 'RotaryPositionEmbedder':env[alias.asname or alias.name] = RealRoPE
                    else:
                        if not hasattr(dependency,alias.name) and 'ProjectAttention' in alias.name:
                            dependency=self.namespace(qualified.replace('.', '/')+'/proj_attention.py')
                        elif not hasattr(dependency,alias.name):
                            dependency=self.namespace(self.find_definition(qualified,alias.name))
                        env[alias.asname or alias.name] = getattr(dependency, alias.name)
                elif qualified.endswith('.attention.full_attn'):
                    env[alias.asname or alias.name] = self.attention
                elif qualified.replace('.','/')+'/'+alias.name+'.py' in self.files:
                    env[alias.asname or alias.name]=self.namespace(qualified.replace('.','/')+'/'+alias.name+'.py')
                else:
                    file = qualified.replace('.', '/')+'.py'
                    if file not in self.files and qualified.endswith('.transformer'):
                        file = qualified.replace('.', '/')+'/blocks.py'
                    if file not in self.files:file=self.find_definition(qualified,alias.name)
                    dependency = self.namespace(file)
                    if alias.name == '*':env.update({k:v for k,v in vars(dependency).items() if not k.startswith('_')})
                    else:
                        if not hasattr(dependency,alias.name) and qualified.endswith('.transformer'):
                            dependency=self.namespace(qualified.replace('.', '/')+'/modulated.py')
                        env[alias.asname or alias.name] = getattr(dependency, alias.name)
        env.update(injections or {})
        env.setdefault('RotaryPositionEmbedder', RealRoPE)
        env.setdefault('scaled_dot_product_attention', self.attention)
        if relative.endswith('/modules/utils.py'):
            api = self.sparse_api()
            env['MIX_PRECISION_MODULES'] = (nn.Conv1d, nn.Conv2d, nn.Conv3d, nn.ConvTranspose1d,
                nn.ConvTranspose2d, nn.ConvTranspose3d, nn.Linear, api.SparseConv3d)
        body = []
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):body.append(node)
            elif isinstance(node,(ast.Assign,ast.AnnAssign)):
                # Frozen scalar/list/dict policies only, never model factories,
                # tensor creation, I/O or arbitrary module-level function calls.
                allowed=(ast.Constant,ast.List,ast.Tuple,ast.Dict,ast.Set,ast.Name,ast.Load,ast.Store,
                    ast.Attribute,ast.UnaryOp,ast.USub,ast.UAdd)
                value=node.value
                if value is not None and all(isinstance(n,allowed) for n in ast.walk(value)):body.append(node)
        code = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)]+body, type_ignores=[])
        exec(compile(ast.fix_missing_locations(code), str(path), 'exec'), env)
        if relative.endswith('/attention/routed_full_only_flash.py'):
            # Keep the exact constructor/state names and formal 12x128 guard;
            # remove the CUDA execution requirement at this fixed boundary.
            env['RoutedFullOnlyFlashCrossAttention'].forward=routed_attention
        if relative==self.prefix+'/models/vggt_adapter.py':
            env['PackedCrossAttention'].forward=packed_shape_attention
        if relative==self.prefix+'/modules/attention/rope.py':env['RotaryPositionEmbedder']=RealRoPE
        # Runtime coordinate join is checked by a signed CPU hash operator, not
        # captured as constant row indices from this export's tracing fixture.
        if '_join_exact_rows' in env:env['_join_exact_rows'] = lambda full,observed: operation('join')(full.long(),observed.long())
        if '_layouts_from_batch' in env:env['_layouts_from_batch'] = lambda batch, size: [slice(0, batch.shape[0])]
        return module

    def find_definition(self,qualified,name):
        prefix=qualified.replace('.','/')+'/'
        for file in self.files:
            if file.startswith(prefix) and file.count('/')==prefix.count('/') and file.endswith('.py'):
                _,text=self.read(file)
                if any(isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name for n in ast.parse(text).body):return file
        raise ValueError('Definition is not in the fixed export allowlist: '+qualified+'.'+name)

    def attention(self, *args):
        api = self.sparse_api()
        sparse = isinstance(args[0], api.VarLenTensor)
        tensors = [v.feats if isinstance(v, api.VarLenTensor) else v for v in args]
        if len(tensors) == 1:q, k, v = tensors[0].unbind(-3)
        elif len(tensors) == 2:q = tensors[0]; k, v = tensors[1].unbind(-3)
        else:q, k, v = tensors
        dense_query=not sparse and q.ndim==4
        def packed(t):
            if t.ndim==4:
                assert t.shape[0]==1,'Portable dense attention requires batch one'
                return t[0]
            assert t.ndim==3
            return t
        q,k,v=packed(q),packed(k),packed(v)
        lengths = lambda t: torch._shape_as_tensor(t)[0:1]
        result = operation('attention')(q, k, v, lengths(q), lengths(k))
        return args[0].replace(result) if sparse else result.unsqueeze(0) if dense_query else result

    def sparse_api(self):
        if self.sparse is not None:return self.sparse
        api = self.sparse = types.SimpleNamespace()
        prefix = self.prefix+'/modules/sparse/'
        # Basic containers already have a dependency-free dictionary backend.
        basic = self.namespace(prefix+'basic.py')
        for name in ('VarLenTensor', 'SparseTensor', 'varlen_cat', 'varlen_unbind', 'sparse_cat', 'sparse_unbind'):
            setattr(api, name, getattr(basic, name))
        S, V = api.SparseTensor, api.VarLenTensor
        S.shape = property(lambda t: torch.Size([1, *t.feats.shape[1:]]))
        S.layout = property(lambda t: [slice(0, t.feats.shape[0])])
        for cls in (S, V):
            cls.seqlen = property(lambda t: torch._shape_as_tensor(t.feats)[0:1])
            cls.batch_boardcast_map = property(lambda t: torch.zeros(t.feats.shape[0], dtype=torch.int64))
        api.SparseRotaryPositionEmbedder = SparseRoPE
        api.sparse_scaled_dot_product_attention = self.attention
        def unsupported(*args, **kwargs):raise ValueError('This source policy needs a dedicated portable operator')
        api.sparse_windowed_scaled_dot_product_self_attention = unsupported
        api.sparse_windowed_scaled_dot_product_cross_attention = unsupported
        # Preserve publisher Co,Kx,Ky,Kz,Ci parameters and strict state ABI.
        class Conv(nn.Module):
            def __init__(self, ci, co, kernel_size, stride=1, dilation=1, padding=None, bias=True, indice_key=None):
                super().__init__()
                assert stride == 1 and padding is None
                sizes = tuple(kernel_size) if isinstance(kernel_size, (list, tuple)) else (kernel_size,)*3
                self.weight = nn.Parameter(torch.empty(co, *sizes, ci))
                self.bias = nn.Parameter(torch.zeros(co)) if bias else None
                self.dilation = tuple(dilation) if isinstance(dilation, (list, tuple)) else (dilation,)*3
                nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
            def forward(self, x):
                b = self.bias if self.bias is not None else self.weight.new_zeros(self.weight.shape[0])
                return x.replace(operation('conv')(x.feats, x.coords.long(), self.weight, b, torch.tensor(self.dilation)))
        api.SparseConv3d = Conv
        api.SparseInverseConv3d = type('UnsupportedInverseConv', (nn.Module,), {'forward':unsupported})
        for filename in ('linear.py', 'nonlinearity.py'):
            module = self.namespace(prefix+filename)
            for name, value in vars(module).items():
                if name.startswith('Sparse'):setattr(api, name, value)
        module=self.namespace(prefix+'norm.py')
        for name,value in vars(module).items():
            if name.startswith('Sparse'):setattr(api,name,value)
        class Down(nn.Module):
            def __init__(self, factor, mode='mean'):super().__init__();self.factor=factor;self.mode=mode
            def forward(self, x):
                f,c,idx = operation('pool')(x.feats, x.coords.long(), torch.tensor([self.factor]*3+[2 if self.mode=='max' else 0]))
                out = S(f,c);out._scale=tuple(s*self.factor for s in x._scale);out._spatial_cache=x._spatial_cache
                out.register_spatial_cache('upsample_'+str(self.factor), (x.coords,idx));return out
        class Up(nn.Module):
            def __init__(self, factor=2):super().__init__();assert factor==2;self.factor=factor
            def forward(self, x, subdivision=None):
                cached=x.get_spatial_cache('upsample_2')
                if cached is not None:
                    c,idx=cached;f=x.feats[idx]
                else:
                    assert subdivision is not None,'Select explicit subdivision guides'
                    f,c,_,_=operation('subdivide')(x.feats,x.coords.long(),subdivision.feats.long(),torch.tensor([1]))
                out=S(f,c);out._scale=tuple(s/2 for s in x._scale)
                if cached is not None:out._spatial_cache=x._spatial_cache
                return out
        class S2C(nn.Module):
            def __init__(self, factor=2):super().__init__();assert factor==2
            def forward(self,x):
                f,c,idx,child=operation('spatial_to_channel')(x.feats,x.coords.long(),torch.tensor([2]))
                out=S(f,c);out._scale=tuple(s*2 for s in x._scale);out._spatial_cache=x._spatial_cache
                out.register_spatial_cache('channel2spatial_2',(x.coords,idx,child));return out
        class C2S(nn.Module):
            def __init__(self,factor=2):super().__init__();assert factor==2
            def forward(self,x,subdivision=None):
                cached=x.get_spatial_cache('channel2spatial_2')
                if cached is not None:
                    c,idx,child=cached
                else:
                    assert subdivision is not None,'Select explicit channel subdivision guides'
                    _,c,idx,child=operation('subdivide')(x.feats,x.coords.long(),subdivision.feats.long(),torch.tensor([1]))
                f=x.feats.reshape(x.feats.shape[0]*8,-1)[idx*8+child]
                out=S(f,c);out._scale=tuple(s/2 for s in x._scale)
                if cached is not None:out._spatial_cache=x._spatial_cache
                return out
        api.SparseDownsample,api.SparseUpsample=Down,Up
        api.SparseSpatial2Channel,api.SparseChannel2Spatial=S2C,C2S
        module=self.namespace(prefix+'attention/modules.py')
        api.SparseMultiHeadAttention=module.SparseMultiHeadAttention
        api.SparseMultiHeadRMSNorm=module.SparseMultiHeadRMSNorm
        return api


def strict_weights(model, file):
    """Tensor-only input with exact key/shape validation before any assignment."""
    from safetensors.torch import load_file
    assert file.suffix == '.safetensors' and file.is_file() and not file.is_symlink()
    weights=load_file(str(file),device='cpu')
    expected=model.state_dict()
    assert set(weights)<=set(expected),'Select the complete matched architecture checkpoint'
    # Some publisher heads share the same Parameter at several ABI paths.
    # safetensors may omit duplicate aliases. Reconstruct only aliases proven
    # identical by the actual source model, never absent learned parameters.
    aliases={}
    for key,value in expected.items():
        if value.numel():
            identity=(value.untyped_storage().data_ptr(),value.storage_offset(),tuple(value.stride()),tuple(value.shape),value.dtype)
            aliases.setdefault(identity,[]).append(key)
    for group in aliases.values():
        present=[key for key in group if key in weights]
        if present:
            reference=weights[present[0]]
            assert all(torch.equal(reference,weights[key]) for key in present),'Conflicting shared checkpoint tensors: '+str(group)
            for key in group:weights.setdefault(key,reference)
    assert set(weights)==set(expected),'Select the complete matched architecture checkpoint'
    for key,value in weights.items():
        assert value.shape==expected[key].shape and torch.isfinite(value).all(),key
        if key.endswith('rope_phases'):
            # Source checkpoints may store complex unit phases; the portable
            # graph represents the same deterministic positions as real angles.
            reference=expected[key]
            if value.is_complex():
                assert torch.allclose(value,torch.polar(torch.ones_like(reference),reference),atol=2e-5,rtol=2e-5),key
                weights[key]=reference
            else:assert torch.equal(value.float(),reference.float()),key
        if key.rsplit('.',1)[-1] in ('partial_mean','partial_std','pbr_mean','pbr_std'):
            assert torch.equal(value.float(),expected[key].float()),'Checkpoint normalization does not match configured statistics: '+key
    model.load_state_dict(weights,strict=True)
    return model.float().eval().requires_grad_(False)
