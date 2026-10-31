"""Closed UltraTex/SLA export bridge; not a complete UltraTex recipe.

CPU online-softmax forward uses the pinned source's block-selection and
probability-casting rules. No Triton, CUDA runtime or downloadable plugin.
"""
import torch
from torch import nn


def selected(q,k,qb,kb,ratio):
    # Preserve the publisher's valid-element denominator on the partial blocks.
    smooth=k-k.mean(dim=-2,keepdim=True)
    def pool(x,n):
        return torch.stack([a.mean(dim=-2) for a in x.split(n,dim=-2)],dim=-2)
    score=pool(q,qb)@pool(smooth,kb).transpose(-1,-2)
    count=min(score.shape[-1],int(ratio*score.shape[-1]))
    if count<1:raise ValueError('Block attention has no selected keys for this support')
    # Portable CPU tie handling is explicit, since Torch sorted=False topk
    # does not specify order or tie handling across devices.
    return score.argsort(dim=-1,descending=True,stable=True)[...,:count]


class BlockSparseAttention(torch.autograd.Function):
    @staticmethod
    def forward(ctx,q,k,v,policy):
        qb,kb,ratio,precision=map(int,policy.tolist())
        assert q.ndim==4 and q.shape==k.shape==v.shape and 1<=qb<=1024 and 1<=kb<=1024 and 0<ratio<=1000000 and precision in (0,1)
        blocks=selected(q,k,qb,kb,ratio/1000000)
        dtype=torch.bfloat16 if precision else torch.float32
        q,k,v=(a.to(dtype).float() for a in (q,k,v))
        out=torch.empty_like(q);scale=q.shape[-1]**-.5
        for b in range(q.shape[0]):
            for h in range(q.shape[1]):
                for i in range(blocks.shape[-2]):
                    query=q[b,h,i*qb:(i+1)*qb]
                    maximum=torch.full((len(query),1),-torch.inf)
                    total=torch.zeros_like(maximum);acc=torch.zeros_like(query)
                    for j in blocks[b,h,i].tolist():
                        keys=k[b,h,j*kb:(j+1)*kb];values=v[b,h,j*kb:(j+1)*kb]
                        score=query@keys.T*scale
                        new=torch.maximum(maximum,score.amax(-1,keepdim=True));alpha=torch.exp(maximum-new)
                        p=torch.exp(score-new);total=total*alpha+p.sum(-1,keepdim=True)
                        acc=acc*alpha+p.to(dtype).float()@values;maximum=new
                    out[b,h,i*qb:(i+1)*qb]=(acc/total).to(dtype).float()
        return out

    @staticmethod
    def symbolic(g,q,k,v,policy):
        out=g.op('lma.spatial::BlockSparseAttention',q,k,v,policy)
        out.setType(q.type());return out


_library=torch.library.Library('lma_ultratex_export','DEF')
_library.define('block_attention(Tensor q, Tensor k, Tensor v, Tensor policy) -> Tensor')
_library.impl('block_attention',lambda *args:BlockSparseAttention.forward(None,*args),'CPU')
torch.onnx.register_custom_op_symbolic('lma_ultratex_export::block_attention',BlockSparseAttention.symbolic,17)


class Attention(nn.Module):
    def __init__(self,query_block=128,key_block=64,ratio=.2,bfloat16=True):
        super().__init__();assert float(ratio*1000000).is_integer()
        self.register_buffer('policy',torch.tensor([query_block,key_block,int(ratio*1000000),int(bfloat16)],dtype=torch.int64))

    def forward(self,q,k,v):
        return torch.ops.lma_ultratex_export.block_attention(q.float(),k.float(),v.float(),self.policy).to(q.dtype)
