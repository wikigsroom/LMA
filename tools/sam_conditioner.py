"""Fixed publisher SAM image/mask/pointmap embedders and learned fuser."""
import types
import logging
import torch
from torch import nn
from local_definitions import LocalDefinitions,unavailable


def timm_block():
    loader=LocalDefinitions('TIMM','timm',injections=dict(use_fused_attn=lambda:True,to_2tuple=lambda x:tuple(x) if isinstance(x,(tuple,list)) else (x,x),
        register_notrace_function=lambda f:f,LayerNorm=nn.LayerNorm,DropPath=unavailable),definitions={
        'timm.layers.attention':{'Attention','maybe_add_mask'},'timm.layers.mlp':{'Mlp'},
        'timm.layers.layer_scale':{'LayerScale'},'timm.models.vision_transformer':{'Block'}})
    loader.injections['Attention']=loader.module('timm.layers.attention').Attention
    loader.injections['Mlp']=loader.module('timm.layers.mlp').Mlp
    loader.injections['LayerScale']=loader.module('timm.layers.layer_scale').LayerScale
    return loader,loader.module('timm.models.vision_transformer').Block


def conditioner(target,settings,tiny_backbone=None):
    auxiliary,block=timm_block()
    dino_source=LocalDefinitions('MOGE','moge')
    vit=dino_source.module('moge.model.modules.dinov2.models.vision_transformer')
    names={'dinov2_vits14':'vit_small','dinov2_vitb14':'vit_base','dinov2_vitl14':'vit_large','dinov2_vitg14':'vit_giant2'}
    def hub(repo_or_dir,model,source,verbose=False,**kwargs):
        assert repo_or_dir=='facebookresearch/dinov2' and source in ('github','local')
        registers=model.endswith('_reg');name=model[:-4] if registers else model;assert name in names and not kwargs
        args=dict(img_size=518,patch_size=14,init_values=1.,block_chunks=0,num_register_tokens=4 if registers else 0,
            interpolate_antialias=registers,interpolate_offset=0. if registers else .1,ffn_layer='swiglufused' if name=='dinov2_vitg14' else 'mlp')
        return vit.DinoVisionTransformer(**dict(args,**tiny_backbone)) if tiny_backbone else getattr(vit,names[name])(**args)
    proxy=types.SimpleNamespace(**vars(torch));proxy.hub=types.SimpleNamespace(load=hub)
    loader=LocalDefinitions(target,'sam3d_objects',injections=dict(Block=block,torch=proxy,logger=logging.getLogger('lma.sam'),
        OmegaConf=types.SimpleNamespace(to_container=lambda x:x)))
    prefix='sam3d_objects.model.backbone.dit.embedder.'
    modules=[]
    for entry in settings['embedders']:
        if entry['type']=='dino':model=loader.module(prefix+'dino').Dino(**entry['args'])
        else:
            assert entry['type']=='pointmap'
            model=loader.module(prefix+'pointmap').PointPatchEmbed(**entry['args'])
            assert not model.force_dropout_always
            model._lma_literal_windows=model.embed_pointmap_windows
            # Source boolean in-place scatter lowers to incompatible Where
            # broadcasts in the legacy exporter. Use the same per-pixel mask
            # with an explicit feature axis; projections/remapping stay source.
            def windows(xyz,valid_mask=None,model=model):
                xyz=model.resize_input(xyz)
                valid=xyz.isfinite().all(dim=-1) if valid_mask is None else valid_mask
                safe=torch.where(valid[...,None],xyz,torch.zeros_like(xyz))
                x=model.point_proj(model.point_remapper(safe))
                x=torch.where(valid[...,None],x,model.invalid_xyz_token)
                return x,xyz.shape[0],xyz.shape[1],xyz.shape[2]
            model.embed_pointmap_windows=windows
        modules.append((model,[tuple(p) for p in entry['inputs']]))
    cls=loader.module(prefix+'embedder_fuser').EmbedderFuser
    fuser=cls(modules,**settings['fuser']).float().eval()
    assert fuser.compression_projection_multiplier==0,'Native branch spans require concatenated tokens'
    return loader,dino_source,auxiliary,fuser


class Conditioner(nn.Module):
    def __init__(self,model,keys,point_spans=()):
        super().__init__();self.model=model;self.keys=tuple(keys);self.point_spans=tuple(point_spans)
        # Positional interpolation depends only on selected fixed resolution
        # and the already loaded parameters. Evaluate the exact publisher AA
        # interpolation once; bake its result as a non-persistent graph constant.
        # This must happen after strict checkpoint loading in the export CLI.
        for module in model.module_list:
            if not hasattr(module,'backbone') or not hasattr(module.backbone,'interpolate_pos_encoding'):continue
            backbone=module.backbone;size=module.input_size;tokens=(size//backbone.patch_size)**2
            original=backbone.interpolate_pos_encoding
            with torch.no_grad():position=original(torch.zeros(1,tokens+1,backbone.embed_dim),size,size).detach().clone()
            backbone.register_buffer('_lma_export_position',position,persistent=False)
            def frozen(x,h,w,backbone=backbone,size=size,tokens=tokens):
                assert h==w==size and x.shape[1]==tokens+1
                return backbone._lma_export_position.to(x.dtype)
            backbone.interpolate_pos_encoding=frozen
    def forward(self,*inputs):
        args={};offset=0
        for key in self.keys:
            value=inputs[offset];offset+=1
            if key in ('pointmap','rgb_pointmap'):
                valid=inputs[offset];offset+=1
                value=torch.where(valid>0,value,torch.full_like(value,float('nan')))
            args[key]=value
        condition=self.model(**args)
        unconditional=self.model(**{k:torch.zeros_like(v) for k,v in args.items()})
        # Forced pointmap drops occur after each trained projection and index
        # embedding in the publisher fuser. Multiplying those exact spans is
        # equivalent, and preserves ordering and the two real RGB branches.
        parts=[];start=0
        for lo,hi in self.point_spans:
            parts.extend((condition[:,start:lo],condition[:,lo:hi]*0));start=hi
        parts.append(condition[:,start:]);without_pointmap=torch.cat(parts,1)
        return condition,unconditional,without_pointmap
