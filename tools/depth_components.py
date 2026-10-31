"""Actual MoGe v1 and DA3 neural stages for fixed local export profiles."""
import types
import torch
from torch import nn
from local_definitions import LocalDefinitions,unavailable


def export_symbolics():
    """Exact two-axis Cartesian product, represented by standard ONNX ops."""
    from torch.onnx import symbolic_helper
    def product(g,values):
        a,b=symbolic_helper._unpack_list(values)
        zero=g.op('Constant',value_t=torch.tensor([0],dtype=torch.int64))
        one=g.op('Constant',value_t=torch.tensor([1],dtype=torch.int64))
        shape=g.op('Concat',g.op('Shape',a),g.op('Shape',b),axis_i=0)
        av=g.op('Expand',g.op('Unsqueeze',a,one),shape)
        bv=g.op('Expand',g.op('Unsqueeze',b,zero),shape)
        stacked=g.op('Concat',g.op('Unsqueeze',av,g.op('Constant',value_t=torch.tensor([2]))),g.op('Unsqueeze',bv,g.op('Constant',value_t=torch.tensor([2]))),axis_i=2)
        return g.op('Reshape',stacked,g.op('Constant',value_t=torch.tensor([-1,2],dtype=torch.int64)))
    torch.onnx.register_custom_op_symbolic('aten::cartesian_prod',product,17)


def moge(args,tiny_backbone=None):
    source=LocalDefinitions('MOGE','moge')
    vit=source.module('moge.model.modules.dinov2.models.vision_transformer')
    names={'dinov2_vits14':'vit_small','dinov2_vitb14':'vit_base','dinov2_vitl14':'vit_large','dinov2_vitg14':'vit_giant2'}
    def factory(name,pretrained=False):
        assert not pretrained and name in names
        settings=dict(img_size=518,patch_size=14,init_values=1.,ffn_layer='swiglufused' if name=='dinov2_vitg14' else 'mlp',
            block_chunks=0,num_register_tokens=0,interpolate_antialias=False,interpolate_offset=.1)
        if tiny_backbone is not None:
            return vit.DinoVisionTransformer(**dict(settings,**tiny_backbone))
        return getattr(vit,names[name])(**settings)
    backbones=types.SimpleNamespace(**{name:(lambda pretrained=False,name=name:factory(name,pretrained)) for name in names})
    def local_import(name,package=None):
        assert name=='.modules.dinov2.hub.backbones';return backbones
    source.injections['importlib']=types.SimpleNamespace(import_module=local_import)
    cls=source.module('moge.model.v1').MoGeModel
    return source,cls(**args)


class MoGe(nn.Module):
    """The selected square multiple-of-14 profile has identity source resizes.

    RGB pixels arrive in [0,1] at the explicitly declared imageSize. Native
    preprocessing owns the original-to-profile resize. num_tokens equals the
    input patch count so both antialias resizes inside source forward are
    exact identities, rather than silently changing their interpolation.
    """
    def __init__(self,model,image_size):super().__init__();self.model=model;self.image_size=image_size
    def forward(self,image):
        assert image.shape[-2:]==(self.image_size,self.image_size) and self.image_size%14==0
        normalized=(image-self.model.image_mean)/self.model.image_std
        features=self.model.backbone.get_intermediate_layers(normalized,self.model.intermediate_layers,return_class_token=True)
        points,mask=self.model.head(features,normalized)
        # The head already restores the exact input shape.
        return self.model._remap_points(points.permute(0,2,3,1)),mask.squeeze(1)


def da3(args,tiny_backbone=None):
    export_symbolics()
    source=LocalDefinitions('DA3','depth_anything_3','src/depth_anything_3',dict(logger=__import__('logging').getLogger('lma.depth')))
    model=args['backbone'];heads=args['head'];camera=args['camera']
    backbone_module=source.module('depth_anything_3.model.dinov2.dinov2')
    if tiny_backbone is None:backbone=backbone_module.DinoV2(**model)
    else:
        # Same class and ABI, tiny learned dimensions solely for program checks.
        backbone=backbone_module.DinoV2.__new__(backbone_module.DinoV2);nn.Module.__init__(backbone)
        for key,value in model.items():setattr(backbone,key,value)
        cls=source.module('depth_anything_3.model.dinov2.vision_transformer').DinoVisionTransformer
        backbone.pretrained=cls(**tiny_backbone)
    head_class=source.module('depth_anything_3.model.'+args.get('headType','dualdpt')).__dict__[args.get('headClass','DualDPT')]
    head=head_class(**heads)
    cam=source.module('depth_anything_3.model.cam_dec').CameraDec(**camera) if camera else None
    cls=source.module('depth_anything_3.model.da3').DepthAnything3Net
    return source,cls(backbone,head,cam_dec=cam,cam_enc=nn.Identity() if cam else None)


class DA3(nn.Module):
    """Actual joint-view backbone/head/camera; tensor-only postprocess boundary."""
    def __init__(self,model,ref_view_strategy='first'):
        super().__init__();self.model=model;self.ref_view_strategy=ref_view_strategy
    def forward(self,images):
        feats,_=self.model.backbone(images,cam_token=None,export_feat_layers=[],ref_view_strategy=self.ref_view_strategy)
        h,w=images.shape[-2:];out=self.model._process_depth_head(feats,h,w)
        # Camera raw representation is decoded by the same signed CPU stage
        # as nested metric alignment; export avoids ONNX matrix-inverse gaps.
        camera=self.model.cam_dec(feats[-1][1]) if self.model.cam_dec else images.new_zeros(images.shape[:2]+(9,))
        sky=out['sky'] if 'sky' in out else torch.zeros_like(out.depth)
        return out.depth,out.depth_conf,sky,camera


class Metric(nn.Module):
    """Actual DA3 nested metric branch, including its own sky prediction."""
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,images):
        feats,_=self.model.backbone(images,cam_token=None,export_feat_layers=[],ref_view_strategy='first')
        h,w=images.shape[-2:];out=self.model._process_depth_head(feats,h,w)
        assert 'sky' in out,'Nested metric alignment requires the trained sky head'
        return out.depth,out.sky
