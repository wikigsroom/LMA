"""Closed CPU exports of the pinned SUPRA-Tex learned components.

Source class definitions retain the actual trained projections, blocks and
state names. The explicit batch-one Qwen layout eliminates Python .tolist()
and complex tensors from ONNX, with the source block-causal attention policy.
No pretrained loader, pickle, installer or network operation is called.
"""
import ast
import math
import types
import typing
import torch
from torch import nn
from spatial_sparse_graphs import operation

QWEN='deployment/runtime/qwen/diffsynth/'


def definitions(source,relative,injections=None):
    path,text=source.read(relative)
    env={k:v for k,v in vars(typing).items() if not k.startswith('_')}
    env.update(torch=torch,nn=nn,F=nn.functional,math=math,FLEX_ATTN_AVAILABLE=False,
        gradient_checkpoint_forward=lambda block,*args,**kw:block(**kw),CACHE_T=2)
    env.update(injections or {})
    tree=ast.parse(text,str(path));nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
    code=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+nodes,type_ignores=[])
    exec(compile(ast.fix_missing_locations(code),str(path),'exec'),env)
    return types.SimpleNamespace(**env)


def cpu_attention(q,k,v,attn_mask=None,use_flex=False):
    assert q.shape[0]==1 and k.shape[0]==1 and v.shape[0]==1
    if attn_mask is None:
        return operation('attention')(q[0],k[0],v[0],torch._shape_as_tensor(q)[1:2],torch._shape_as_tensor(k)[1:2]).unsqueeze(0)
    return nn.functional.scaled_dot_product_attention(q.transpose(1,2),k.transpose(1,2),v.transpose(1,2),attn_mask=attn_mask).transpose(1,2)


def real_rotary(x,freqs_cis,use_real=True,use_real_unbind_dim=-1):
    # Source uses adjacent complex pairs, not split-half text RoPE.
    cos,sin=freqs_cis
    pairs=x.float().reshape(*x.shape[:-1],int(x.shape[-1])//2,2)
    cos=cos[None,:,None,:];sin=sin[None,:,None,:]
    return torch.stack((pairs[...,0]*cos-pairs[...,1]*sin,pairs[...,0]*sin+pairs[...,1]*cos),-1).flatten(-2).to(x.dtype)


def qwen_dit(source,args=None):
    module=definitions(source,QWEN+'models/qwen_image_21_dit.py')
    # Replace only the execution boundary; the reference source module can be
    # separately constructed by tests with its original complex implementation.
    module.QwenImage21AttnProcessor.__call__.__globals__['_attention']=cpu_attention
    module.QwenImage21AttnProcessor.__call__.__globals__['apply_rotary_emb_qwen']=real_rotary
    return module.QwenImage21DiT(**(args or {}))


def patchify(x):return x.flatten(2).transpose(1,2)
def unpatchify(x,h,w):return x.transpose(1,2).reshape(x.shape[0],x.shape[-1],h,w)


def qwen_pbr(source,dit):
    return definitions(source,QWEN+'pipelines/qwen_image_21_pbr.py',dict(patchify=patchify,unpatchify=unpatchify)).QwenImage21PBRModel(dit)


class FixedPBR(nn.Module):
    """Actual PBR endpoint for a fixed, validated local-tokenizer layout.

    layout is the post-system-drop VL image-placeholder mask. Every placeholder
    expands to four VAE tokens. All tokens are real; no pad rows are admitted.
    Both targets remain in one bidirectional group, with separate spatial RoPE.
    """
    def __init__(self,pbr,layout,height,width):
        super().__init__();self.pbr=pbr;self.height=height;self.width=width
        layout=torch.as_tensor(layout,dtype=torch.bool)
        assert layout.ndim==1 and height%2==0 and width%2==0
        assert int(layout.sum())==height*width//4
        compact=torch.cat((layout,torch.ones(2*height*width//4,dtype=torch.bool)))
        repeats=torch.where(compact,4,1)
        expanded=torch.repeat_interleave(compact,repeats)
        shapes=[(1,height,width)]*3;dit=pbr.dit
        ids,target=dit.build_token_metadata(expanded,shapes,2)
        # Source coordinate indexing is evaluated on the actual fixed integer
        # layout, never captured from tensor values supplied at inference.
        rope=dit.pos_embed(shapes,expanded,device=torch.device('cpu'))
        self.register_buffer('rope_cos',rope.real.float())
        self.register_buffer('rope_sin',rope.imag.float())
        self.register_buffer('repeats',repeats)
        self.register_buffer('image_rows',expanded.nonzero().flatten())
        self.register_buffer('target',target)
        self.prefix=int((~target).sum());self.compact_targets=height*width//2
        self.segments=dit.forward.__globals__['_qwenimage21_prefix_segments'](ids,self.prefix)

    def forward(self,noise,prompt,rgb):
        dit=self.pbr.dit;h,w=self.height,self.width
        image=torch.cat((patchify(rgb),*[patchify(noise[:,i])+self.pbr.modality_embeddings[i] for i in range(2)]),1)
        image=dit.img_in(image);text=dit.txt_in(prompt)
        joint=torch.cat((text,text.new_zeros(1,self.compact_targets,dit.inner_dim)),1)
        joint=torch.repeat_interleave(joint,self.repeats,dim=1)
        joint=joint.index_copy(1,self.image_rows,image)
        # Publisher endpoint always predicts at t=1000, divided by 1000 before
        # the DiT; its clean prefix is modulated at exactly zero.
        time=joint.new_tensor([1.,0.]) if dit.causal_condition else joint.new_tensor([1.])
        temb=dit.time_text_embed(time,image);modulation=dit.modulation(temb)
        target=self.target if dit.causal_condition else None
        for block in dit.transformer_blocks:
            joint=block(joint,modulation=modulation,rotary_emb=(self.rope_cos,self.rope_sin),
                attention_mask=None,target_token_mask=target,kv_cache=None,
                cache_write_slice=None,segments=self.segments,key_valid=None)
        value=dit.proj_out(dit.norm_out(joint,temb,target))[:,-2*h*w:]
        return torch.stack((unpatchify(value[:,:h*w],h,w),unpatchify(value[:,h*w:],h,w)),1)


def qwen_vae(source,args=None):
    module=definitions(source,QWEN+'models/qwen_image_21_vae.py')
    def integer_upsample(self,x):
        assert self.size is None and self.scale_factor==(2.,2.) and self.mode=='nearest-exact'
        # The source only uses integral 2x nearest-exact. Repeating each sample
        # is identical and avoids an unsupported Torch exporter operator.
        return nn.functional.interpolate(x.float(),scale_factor=(2.,2.),mode='nearest').type_as(x)
    module.QwenImage21Upsample.forward=integer_upsample
    return module.QwenImage21VAE(**(args or {}))


class VaeEncode(nn.Module):
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,rgba):return self.model.encode(rgba,tiled=False)


class VaeDecode(nn.Module):
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,latents):return self.model.decode(latents,tiled=False).add(1).mul(.5)


class VLFeatures(nn.Module):
    """The real Qwen3-VL vision/deepstack/language stack, pre-final norm.

    Position IDs and image-slot indices are immutable outputs of the exact local
    tokenizer/profile. Image grid/size is fixed; pixel values and IDs are inputs.
    """
    def __init__(self,model,ids,image_grid,drop):
        super().__init__();self.model=model;self.drop=drop
        core=model.model if hasattr(model,'model') else model
        # Qwen3VLForConditionalGeneration.model is the multimodal backbone.
        self.core=core
        grid=torch.as_tensor(image_grid,dtype=torch.int64).reshape(1,3)
        values=torch.as_tensor(ids,dtype=torch.int64).reshape(1,-1)
        positions,_=core.get_rope_index(values,grid,attention_mask=torch.ones_like(values))
        self.register_buffer('grid',grid)
        self.register_buffer('positions',positions)
        image_rows=(values[0]==core.config.image_token_id).nonzero().flatten()
        self.register_buffer('image_rows',image_rows)

    def forward(self,ids,pixels):
        core=self.core;visual,deep=core.visual(pixels,grid_thw=self.grid)
        embeddings=core.language_model.embed_tokens(ids).index_copy(1,self.image_rows,visual.unsqueeze(0))
        hidden=embeddings;language=core.language_model
        seq=ids.shape[1];rows=torch.arange(seq,device=ids.device)
        mask=torch.where(rows[:,None]>=rows[None,:],0.,torch.finfo(hidden.dtype).min)[None,None]
        rotary=language.rotary_emb(hidden,self.positions)
        for i,layer in enumerate(language.layers):
            hidden=layer(hidden,attention_mask=mask,position_ids=self.positions[0],
                past_key_values=None,cache_position=rows,position_embeddings=rotary,use_cache=False)
            if i<len(deep):hidden=hidden.index_add(1,self.image_rows,deep[i].unsqueeze(0))
        return hidden[:,self.drop:]


class Completion(nn.Module):
    def __init__(self,source,model):super().__init__();self.model=model;self.sparse=source.sparse_api()
    def forward(self,features,coords,time,shape,observed,observed_coords):
        sp=self.sparse
        return self.model(sp.SparseTensor(features,coords),time,concat_cond=sp.SparseTensor(shape,coords),
            partial_z_obs=sp.SparseTensor(observed,observed_coords),observation_cache=None).feats


class ShapeEncode(nn.Module):
    def __init__(self,source,model):super().__init__();self.model=model;self.sparse=source.sparse_api()
    def forward(self,vertices,intersected,coords):
        sp=self.sparse
        result=self.model(sp.SparseTensor(vertices,coords),sp.SparseTensor(intersected,coords))
        return result.feats,result.coords


class MaterialEncode(nn.Module):
    def __init__(self,source,model):super().__init__();self.model=model;self.sparse=source.sparse_api()
    def forward(self,features,coords):
        result=self.model(self.sparse.SparseTensor(features,coords));return result.feats,result.coords


class CachedDecode(nn.Module):
    """Preserve the source SCVAE encoder's exact topology across processes.

    Reconstruct only its integer S2C caches from the original surface, using the
    same signed coordinate operator. Learned geometry is not recomputed from a
    guessed subdivision mask, and no source row is dropped or interpolated.
    """
    def __init__(self,source,model,levels=4):
        super().__init__();self.model=model;self.sparse=source.sparse_api()
        self.down=nn.ModuleList([self.sparse.SparseSpatial2Channel(2) for _ in range(levels)])
        self.levels=levels
    def forward(self,features,coords,surface_coords):
        sp=self.sparse
        topology=sp.SparseTensor(features.new_zeros(surface_coords.shape[0],1),surface_coords)
        for down in self.down:
            topology=down(topology.replace(features.new_zeros(topology.feats.shape[0],1)))
        latent=sp.SparseTensor(features,coords);latent._scale=topology._scale
        latent._spatial_cache=topology._spatial_cache
        result=self.model(latent)
        return result.feats,result.coords


def scvae(source,kind,args):
    base='supratex/models/sc_vaes/'
    file='fdg_vae.py' if kind=='shape_encoder' else 'sparse_unet_vae.py'
    name='FlexiDualGridVaeEncoder' if kind=='shape_encoder' else 'SparseUnetVaeEncoder' if kind=='material_encoder' else 'SparseUnetVaeDecoder'
    if kind=='shape_encoder':
        module=source.namespace(base+'sparse_unet_vae.py')
        injected={k:v for k,v in vars(module).items() if k.startswith('Sparse')}
        injected['sp']=source.sparse_api()
        return definitions(source,base+file,injected).FlexiDualGridVaeEncoder(**args)
    return getattr(source.namespace(base+file),name)(**args)
