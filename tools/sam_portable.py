"""Fixed SAM 3D / MV-SAM learned classes with signed batch-one CPU bindings.

Only sparse execution and storage are replaced. Publisher module names, learned
projections, MoT modality protection, residuals and checkpoint keys are retained.
The closed export profile uses source APE and full / shifted-window attention.
"""
from collections import namedtuple
from enum import Enum
from fractions import Fraction
import math
import types
import torch
from torch import nn
from spatial_portable import Source
from spatial_sparse_graphs import operation


def tree_reduce_unique(function,tree):
    values=[function(value) for value in torch.utils._pytree.tree_leaves(tree)]
    assert values and all(value==values[0] for value in values)
    return values[0]


class SerializeMode(Enum):
    Z_ORDER=0
    Z_ORDER_TRANSPOSED=1
    HILBERT=2
    HILBERT_TRANSPOSED=3


def concatenate_modalities(self,values,names):
    # Tracing represents shape entries as scalar tensors. Source += aliases
    # previously stored offsets in that mode; addition keeps identical integer
    # positions while preserving the earlier start of each modality slice.
    tensors=[];offsets={};total=0
    for name in names:
        value=values[name];length=value.shape[1];tensors.append(value)
        offsets[name]=[total,length];total=total+length
    return torch.cat(tensors,dim=1),offsets


def sine_cosine(self,indices):
    # Torch promotes int coordinates with FP32 frequencies; make that cast
    # explicit because the legacy ONNX outer/Einsum export omits promotion.
    phase=torch.outer(indices.float(),self.freqs.to(indices.device))
    return torch.cat((phase.sin(),phase.cos()),dim=-1)


class SamSource(Source):
    def __init__(self,target='D08'):
        assert target in ('D08','D09')
        super().__init__(target)
        self.injections=dict(_pytree=torch.utils._pytree,namedtuple=namedtuple,
            tree_reduce_unique=tree_reduce_unique,
            OmegaConf=types.SimpleNamespace(to_container=lambda value:dict(value) if isinstance(value,dict) else list(value)))

    def sparse_api(self):
        if self.sparse is not None:return self.sparse
        # The container is plain tensor bookkeeping, without learned weights,
        # and supports dynamic row counts without a CUDA SparseConvTensor.
        base=Source('D05').sparse_api()
        api=self.sparse=types.SimpleNamespace(**vars(base))
        api.DEBUG=False;api.ATTN='lma_cpu';api.BACKEND='lma_cpu'
        api.SerializeMode=SerializeMode;api.SerializeModes=list(SerializeMode)
        S=api.SparseTensor
        def elementwise(x,other,op):
            # Closed B=1: [1,C] global values and [N,C] per-row values both
            # broadcast directly. Avoid attempting a failing [N,C] -> [1,C]
            # broadcast inside try/except, which corrupts the legacy tracer.
            if isinstance(other,api.VarLenTensor):other=other.feats
            return x.replace(op(x.feats,other))
        S.__elemwise__=elementwise
        class Conv(nn.Module):
            def __init__(self,*args,**kwargs):
                super().__init__();self.conv=base.SparseConv3d(*args,**kwargs)
            def forward(self,x):return self.conv(x)
        class Down(nn.Module):
            def __init__(self,factor):
                super().__init__();self.factor=(factor,)*3 if isinstance(factor,int) else tuple(factor)
                assert len(self.factor)==3 and all(type(n) is int and 1<=n<=4 for n in self.factor)
            def forward(self,x):
                f,c,idx=operation('pool')(x.feats,x.coords.long(),torch.tensor([*self.factor,1]))
                out=S(f,c);out._scale=tuple(s*n for s,n in zip(x._scale,self.factor));out._spatial_cache=x._spatial_cache
                out.register_spatial_cache('sam_upsample_'+str(self.factor),(x.coords,idx));return out
        class Up(nn.Module):
            def __init__(self,factor):
                super().__init__();self.factor=(factor,)*3 if isinstance(factor,int) else tuple(factor)
            def forward(self,x):
                cached=x.get_spatial_cache('sam_upsample_'+str(self.factor))
                assert cached is not None,'SAM upsample requires its paired encoder topology'
                coords,index=cached;out=S(x.feats[index],coords)
                out._scale=tuple(s/n for s,n in zip(x._scale,self.factor));out._spatial_cache=x._spatial_cache;return out
        class Subdivide(nn.Module):
            def forward(self,x):
                mask=torch.ones(x.feats.shape[0],8,dtype=torch.int64,device=x.device)
                f,c,_,_=operation('subdivide')(x.feats,x.coords.long(),mask,torch.tensor([0]))
                out=S(f,c);out._scale=tuple(s/2 for s in x._scale);out._spatial_cache=x._spatial_cache;return out
        def window(qkv,window_size,shift_window=(0,0,0)):
            widths=(window_size,)*3 if isinstance(window_size,int) else tuple(window_size)
            shifts=(shift_window,)*3 if isinstance(shift_window,int) else tuple(shift_window or (0,0,0))
            q,k,v=qkv.feats.unbind(1)
            return qkv.replace(operation('window_attention')(q,k,v,qkv.coords.long(),torch.tensor([*widths,*shifts])))
        def serialized(*args,**kwargs):
            raise ValueError('Select the source full or swin APE profile; serialized / Hilbert profiles require a different recipe')
        api.SparseConv3d=Conv;api.SparseDownsample=Down;api.SparseUpsample=Up;api.SparseSubdivide=Subdivide
        api.sparse_windowed_scaled_dot_product_self_attention=window
        api.sparse_serialized_scaled_dot_product_self_attention=serialized
        for file in ('linear.py','nonlinearity.py','norm.py'):
            module=self.namespace(self.prefix+'/modules/sparse/'+file)
            for name,value in vars(module).items():
                if name.startswith('Sparse'):setattr(api,name,value)
        module=self.namespace(self.prefix+'/modules/sparse/attention/modules.py')
        api.SparseMultiHeadAttention=module.SparseMultiHeadAttention
        api.SparseMultiHeadRMSNorm=module.SparseMultiHeadRMSNorm
        return api

    def namespace(self,relative,injections=None):
        module=super().namespace(relative,injections)
        if relative==self.prefix+'/modules/utils.py':module.FP16_TYPE=torch.float16
        if relative==self.prefix+'/modules/attention/modules.py':
            module.MOTMultiHeadSelfAttention.concatenate_tensor=concatenate_modalities
        if relative==self.prefix+'/modules/transformer/blocks.py':
            module.AbsolutePositionEmbedder._sin_cos_embedding=sine_cosine
        return module


def checked_model(source,relative,name,args):
    assert args.get('pe_mode','ape')=='ape','The signed SAM recipe uses source absolute positional embeddings'
    assert args.get('attn_mode','full') in ('full','swin')
    args=dict(args);args['use_fp16']=False
    if 'use_checkpoint' in args:args['use_checkpoint']=False
    return getattr(source.namespace(source.prefix+'/'+relative),name)(**args)
