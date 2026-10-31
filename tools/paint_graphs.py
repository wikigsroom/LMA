"""Fixed-source Hunyuan Paint PBR graphs; CPU/ONNX, no upstream pipeline loader."""
import torch
from torch import nn
from spatial_reference import definitions


def reference():
    attention = definitions('D07','hy3dpaint/hunyuanpaintpbr/unet/attn_processor.py',cpu_devices=True)
    return definitions('D07','hy3dpaint/hunyuanpaintpbr/unet/modules.py',
        {name:getattr(attention,name) for name in ('SelfAttnProcessor2_0','RefAttnProcessor2_0','PoseRoPEAttnProcessor2_0')},static_shape_keys=True)


def construct(config):
    from diffusers import UNet2DConditionModel
    module = reference()
    assert config.get('in_channels',4)==4 and config.get('out_channels',4)==4
    assert config.get('cross_attention_dim',1024)==1024
    base = UNet2DConditionModel.from_config(config)
    model = module.UNet2p5DConditionModel(base)
    conv = model.unet.conv_in
    model.unet.conv_in = nn.Conv2d(12,conv.out_channels,conv.kernel_size,stride=conv.stride,padding=conv.padding,
                                   dilation=conv.dilation,groups=conv.groups,bias=conv.bias is not None)
    return model.float().eval(), module


def static_positions(module, views, latent):
    # Source dictionaries use tensor.shape as keys. ONNX tracing produces
    # symbolic scalar keys, which never compare equal to later shape objects.
    # The export is intentionally fixed to one view count/image size. Quantized
    # voxel values remain dynamic; only these resolution metadata keys are fixed.
    def calculate(position_maps, grid_resolutions=None, voxel_resolutions=None):
        result={}
        for grid,voxel in zip((latent,latent//2,latent//4,latent//8),(latent*8,latent*4,latent*2,latent)):
            # Equal source FP16 accumulation/masking with ONNX Where, avoiding
            # PyTorch's unsupported aten::eq(Tensor, bool) assignment lowering.
            position=position_maps.half()
            mask=(position!=1).all(dim=2,keepdim=True).expand_as(position)
            position=torch.where(mask,position,torch.zeros_like(position))
            side=latent*8
            position=position.reshape(3,views,3,grid,side//grid,grid,side//grid).permute(0,1,3,5,2,4,6)
            mask=mask.reshape(3,views,3,grid,side//grid,grid,side//grid).permute(0,1,3,5,2,4,6)
            count=mask.sum(dim=(-2,-1))
            average=position.sum(dim=(-2,-1))/count.clamp(min=1)
            average=torch.where(count<(side//grid)**2//16,torch.zeros_like(average),average)
            values=torch.round(average.permute(0,1,4,2,3).clamp(0,1)*(voxel-1)).long()
            values=values.permute(0,1,3,4,2).reshape(3,views*grid*grid,3)
            result[views*grid*grid]=dict(voxel_indices=values,voxel_resolution=voxel)
        return result
    module.calc_multires_voxel_idxs=calculate


class PaintFlow(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model=model

    def forward(self,latents,timestep,normal_latents,position_latents,reference_latents,dino_features,position_maps,guidance):
        model=self.model
        text=torch.stack([getattr(model.unet,'learned_text_clip_'+name) for name in model.pbr_setting],dim=0)[None].repeat(3,1,1,1)
        predicted=model(latents.repeat(3,1,1,1,1,1),timestep[0],text,
            embeds_normal=normal_latents.repeat(3,1,1,1,1),embeds_position=position_latents.repeat(3,1,1,1,1),
            ref_latents=reference_latents.repeat(3,1,1,1,1),
            dino_hidden_states=torch.cat((torch.zeros_like(dino_features),torch.zeros_like(dino_features),dino_features),dim=0),
            position_maps=position_maps.repeat(3,1,1,1,1),ref_scale=latents.new_tensor([0.,1.,1.]))[0]
        u,r,f=predicted.chunk(3)
        return u+guidance*(r-u)+guidance*(f-r)


class VaeStatistics(nn.Module):
    def __init__(self,vae):super().__init__();self.vae=vae
    def forward(self,image):
        posterior=self.vae.encode(image,return_dict=False)[0]
        return torch.cat((posterior.mean,posterior.logvar),dim=1)


class VaeDecode(nn.Module):
    def __init__(self,vae):super().__init__();self.vae=vae
    def forward(self,latents):return self.vae.decode(latents,return_dict=False)[0]


def arguments(size=64,views=6,dino_tokens=5):
    latent=size//8
    return (torch.randn(1,2,views,4,latent,latent),torch.tensor([500.]),
        torch.randn(1,views,4,latent,latent),torch.randn(1,views,4,latent,latent),
        torch.randn(1,1,4,latent,latent),torch.randn(1,dino_tokens,1536),
        torch.rand(1,views,3,size,size),torch.tensor([3.]))


NAMES=['latents','timestep','normal_latents','position_latents','reference_latents','dino_features','position_maps','guidance']
