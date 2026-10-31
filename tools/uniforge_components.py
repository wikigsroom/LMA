"""Closed offline CPU network boundaries for the pinned UniForge cascade.

Constructors use local configurations and strict tensors. None invokes Hub,
checkpoint pickle, source-package imports, CUDA, or an upstream installer.
Android executes the closed cascade in native/spatial/uniforge.hpp.
"""
from fnmatch import fnmatchcase
import torch
from torch import nn
from spatial_portable import Source

PREFIX='uniforge3d/models/'


def frozen(module):
    return module.float().eval().requires_grad_(False)


def dino(source,config):
    from transformers import DINOv3ViTConfig,DINOv3ViTModel
    cls=source.namespace(PREFIX+'dino.py').DinoV3Encoder
    # Bypass only from_pretrained: the publisher's actual forward, final
    # parameter-free norm, special tokens and 5D restoration stay intact.
    value=cls.__new__(cls);nn.Module.__init__(value)
    value.model=DINOv3ViTModel(DINOv3ViTConfig(**config))
    value.register_buffer('_mean',torch.tensor([.485,.456,.406]).reshape(1,3,1,1),persistent=False)
    value.register_buffer('_std',torch.tensor([.229,.224,.225]).reshape(1,3,1,1),persistent=False)
    return frozen(value)


def joint(source,args,lora=None):
    model=source.namespace(PREFIX+'joint_dit_vggt_stage1.py').JointDiTVGGTStage1Model(**args)
    if lora:
        module=source.namespace(PREFIX+'lora.py',dict(fnmatchcase=fnmatchcase))
        assert set(lora)=={'dit','vggt'}
        module.attach_stage1_lora(model.dit,**lora['dit'])
        module.attach_stage1_lora(model.vggt,**lora['vggt'])
    return frozen(model)


class JointPositive(nn.Module):
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,noisy,time,images,dino):return self.model(noisy,time,images,dino)


class JointNegative(nn.Module):
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,noisy,time):return self.model.forward_unconditional(noisy,time)


class JointPredictions(nn.Module):
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,noisy,time,images,dino):
        return self.model(noisy,time,images,dino),self.model.forward_unconditional(noisy,time)


class FrozenConditioner(nn.Module):
    """Actual shape-conditioned aggregator/DPT, with no checkpoint constructor.

    Parameter paths match the publisher's composite VGGT checkpoint exactly.
    The source's backbone condition method and point head body are reused.
    """
    def __init__(self,source):
        super().__init__()
        base=source.namespace(PREFIX+'vggt_adapter.py')
        routed=source.namespace(PREFIX+'vggt_routed_features.py')
        self.feature_layers=(4,11,17,23);self.conditioning_layers=(4,7,11,14,17,20,23)
        self.aggregator=base.Aggregator(cached_layer_indices=self.feature_layers)
        self.shape_encoder=base.ShapeCoordEncoder(grid_resolution=64)
        self.backbone_shape_adapters=nn.ModuleDict({str(i):base.PackedCrossAttention(1024,1024,1024,16) for i in self.conditioning_layers})
        self.point_head=routed.DPTHead(dim_in=2048,output_dim=4,activation='inv_log',conf_activation='expp1')
        self.dpt_shape_adapter_32=routed.DPTShapeAdapter32()
        self._aggregate=base.FrozenVGGTFeatureExtractor._conditioned_aggregate
        self._points=routed.FrozenRoutedVGGTFeatureExtractor._point_forward

    def forward(self,images,coords):
        shape=self.shape_encoder(coords[:,1:])
        offsets=torch.cat((torch.zeros(1,dtype=torch.int64),torch._shape_as_tensor(coords)[0:1]))
        cached,start=self._aggregate(self,images,shape,offsets)
        points,confidence=self._points(self,cached,images,start,shape,offsets)
        return *(cached[i] for i in self.feature_layers),points,confidence


class StageAdapter(nn.Module):
    def __init__(self,adapter):super().__init__();self.adapter=adapter
    def forward(self,layer4,layer11,layer17,layer23):
        cached=[None]*24
        for i,value in zip((4,11,17,23),(layer4,layer11,layer17,layer23)):cached[i]=value
        return self.adapter(cached,5)


def flow(source,args):
    return frozen(source.namespace(PREFIX+'structured_latent_flow.py').VGGTConditionedSLatFlowModel(**args))


class RoutedFlow(nn.Module):
    def __init__(self,source,model,texture=False):
        super().__init__();self.model=model;self.api=source.sparse_api();self.texture=texture
    def forward(self,features,coords,time,full,selected,shape=None):
        condition=dict(full_bank=full,selected_rows=selected,all_view_tokens=full.reshape(1,-1,full.shape[-1]))
        value=self.api.SparseTensor(features,coords)
        concat=self.api.SparseTensor(shape,coords) if self.texture else None
        # Time is already 1000*t for these SLAT methods; the joint positive
        # graph accepts t and applies its own source scaling once.
        return self.model(value,time,condition,concat_cond=concat).feats


def structure_decoder(source,args):
    return frozen(source.namespace(PREFIX+'vaes/sparse_structure.py').SparseStructureDecoder(**args))


def sparse_decoder(source,args):
    return frozen(source.namespace(PREFIX+'vaes/sparse_unet.py').SparseUnetVaeDecoder(**args))


class ShapeDecode(nn.Module):
    def __init__(self,source,decoder):super().__init__();self.decoder=decoder;self.api=source.sparse_api()
    def forward(self,features,coords):
        output,subdivisions=self.decoder(self.api.SparseTensor(features,coords),return_subs=True)
        return (output.feats,output.coords,*(v for s in subdivisions for v in (s.feats,s.coords)))


class MaterialDecode(nn.Module):
    def __init__(self,source,decoder):super().__init__();self.decoder=decoder;self.api=source.sparse_api()
    def forward(self,features,coords,*guides):
        assert len(guides)==2*(len(self.decoder.blocks)-1)
        subs=[self.api.SparseTensor(guides[i],guides[i+1]) for i in range(0,len(guides),2)]
        output=self.decoder(self.api.SparseTensor(features,coords),guide_subs=subs)
        return output.feats,output.coords
