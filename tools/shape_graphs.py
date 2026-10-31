"""Exportable reference adapters: preserve per-head QKV packing and part fusion.

No model construction/download occurs on import. All graph inputs/outputs are
FP32. CFG is evaluated sequentially with the same part IDs, so parts never
attend across a conditional/unconditional batch. VAE cache is evaluated once.
"""
import torch
from torch import nn

class Attention:
    def __init__(self,global_parts=False):self.global_parts=global_parts
    def __call__(self,attn,hidden_states,encoder_hidden_states=None,attention_mask=None,temb=None,image_rotary_emb=None,**kwargs):
        if attention_mask is not None or image_rotary_emb is not None or attn.spatial_norm is not None or attn.group_norm is not None:
            raise ValueError('This export contract accepts unmasked shape attention only')
        residual=hidden_states;b,t,_=hidden_states.shape
        q=attn.to_q(hidden_states)
        context=hidden_states if encoder_hidden_states is None else encoder_hidden_states
        if encoder_hidden_states is not None and attn.norm_cross:context=attn.norm_encoder_hidden_states(context)
        k,v=attn.to_k(context),attn.to_v(context);h=attn.heads;d=q.shape[-1]//h
        # Publisher checkpoints concatenate then split within each head. A
        # conventional independent Q/K/V head split silently corrupts results.
        if not attn.is_cross_attention:
            q,k,v=torch.cat((q,k,v),dim=-1).reshape(b,-1,h,d*3).split(d,dim=-1)
        else:k,v=torch.cat((k,v),dim=-1).reshape(b,-1,h,d*2).split(d,dim=-1)
        q=q.reshape(b,-1,h,d).transpose(1,2);k=k.reshape(b,-1,h,d).transpose(1,2);v=v.reshape(b,-1,h,d).transpose(1,2)
        if attn.norm_q is not None:q=attn.norm_q(q)
        if attn.norm_k is not None:k=attn.norm_k(k)
        if self.global_parts:
            q=q.permute(1,0,2,3).reshape(1,h,-1,d)
            if encoder_hidden_states is None:
                k=k.permute(1,0,2,3).reshape(1,h,-1,d);v=v.permute(1,0,2,3).reshape(1,h,-1,d)
            else:k,v=k[:1],v[:1]
        out=torch.nn.functional.scaled_dot_product_attention(q,k,v,dropout_p=0.,is_causal=False)
        if self.global_parts:out=out.reshape(h,b,t,d).permute(1,2,0,3).reshape(b,t,h*d)
        else:out=out.transpose(1,2).reshape(b,t,h*d)
        out=attn.to_out[1](attn.to_out[0](out))
        if attn.residual_connection:out=out+residual
        return out/attn.rescale_output_factor

def portable_attention(model,global_ids=()):
    from diffusers.models.attention_processor import Attention as DiffusersAttention
    for name,module in model.named_modules():
        if isinstance(module,DiffusersAttention):
            bits=name.split('.');global_part=bool(len(bits)>=3 and bits[0]=='blocks' and int(bits[1]) in global_ids)
            module.set_processor(Attention(global_part))

class ImageEncoder(nn.Module):
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,pixel_values):return self.model(pixel_values,return_dict=False)[0]

class Flow(nn.Module):
    def __init__(self,model,parts=False):super().__init__();self.model=model;self.parts=parts
    def forward(self,latents,timestep,image_embeddings):
        m=self.model
        if not self.parts:return m(latents,timestep,encoder_hidden_states=image_embeddings,return_dict=False)[0]
        t=latents.shape[1];h=torch.cat((m.time_proj(m.time_embed(timestep).to(latents.dtype)).unsqueeze(1),m.proj_in(latents)),dim=1)
        if m.enable_part_embedding:h=h+m.part_embedding(torch.arange(latents.shape[0],device=latents.device)).unsqueeze(1)
        skips=[]
        for i,block in enumerate(m.blocks):
            skip=None if i<=m.config.num_layers//2 else skips.pop()
            global_block=i in m.global_attn_block_ids
            inject=m.enable_global_cross_attn if global_block else m.enable_local_cross_attn
            context=image_embeddings if inject else torch.zeros_like(image_embeddings)
            h=block(h,encoder_hidden_states=context,skip=skip)
            if i<m.config.num_layers//2:skips.append(h)
        return m.proj_out(m.norm_out(h)[:,-t:])

class Cache(nn.Module):
    def __init__(self,vae):super().__init__();self.projection=vae.post_quant;self.blocks=vae.decoder.blocks[:-1]
    def forward(self,latents):
        h=self.projection(latents)
        for block in self.blocks:h=block(h)
        return h

class Query(nn.Module):
    def __init__(self,vae):
        super().__init__();self.embedder=vae.embedder;self.query=vae.decoder.proj_query;self.block=vae.decoder.blocks[-1];self.norm=vae.decoder.norm_out;self.out=vae.decoder.proj_out
    def forward(self,cache,points):return -self.out(self.norm(self.block(self.query(self.embedder(points)),encoder_hidden_states=cache)))

def export_graph(module,args,path,inputs,output,dynamic):
    import onnx
    path.parent.mkdir(parents=True,exist_ok=True)
    (path.parent/(path.name+'.data')).unlink(missing_ok=True)
    with torch.inference_mode():
        torch.onnx.export(module.eval(),args,str(path),input_names=inputs,output_names=[output],dynamic_axes=dynamic,
                          opset_version=17,dynamo=False,external_data=True,do_constant_folding=True)
    # A single disclosed sidecar per graph keeps Android resolution bounded.
    model=onnx.load(str(path),load_external_data=True)
    onnx.save_model(model,str(path),save_as_external_data=True,all_tensors_to_one_file=True,
                    location=path.name+'.data',size_threshold=0,convert_attribute=False)
    onnx.checker.check_model(str(path))

def export_all(image,flow,vae,out,channels,width,encoder_tokens,encoder_width,image_size,parts=False):
    portable_attention(flow,flow.global_attn_block_ids if parts else ())
    portable_attention(vae)
    p=2 if parts else 1;t=8;q=11
    models=[(ImageEncoder(image),(torch.zeros(1,3,image_size,image_size),),'image_encoder',['pixel_values'],'image_embeddings',{}),
      (Flow(flow,parts),(torch.randn(p,t,channels),torch.ones(p),torch.zeros(p,encoder_tokens,encoder_width)),'flow',['latents','timestep','image_embeddings'],'velocity',
       {'latents':{0:'parts',1:'tokens'},'timestep':{0:'parts'},'image_embeddings':{0:'parts'},'velocity':{0:'parts',1:'tokens'}}),
      (Cache(vae),(torch.randn(1,t,channels),),'cache',['latents'],'cache',{'latents':{1:'tokens'},'cache':{1:'tokens'}}),
      (Query(vae),(torch.randn(1,t,width),torch.randn(1,q,3)),'query',['cache','points'],'sdf',{'cache':{1:'tokens'},'points':{1:'queries'},'sdf':{1:'queries'}})]
    for wrapper,args,name,inputs,output,dynamic in models:export_graph(wrapper,args,out/(name+'.onnx'),inputs,output,dynamic)
