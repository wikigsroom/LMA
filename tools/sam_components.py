"""Actual fixed SAM learned components; local tensor-only export boundaries."""
import types
import torch
from torch import nn
from sam_portable import SamSource,checked_model


def structure(source,args,heads):
    args=dict(args);assert args.get('pe_mode','ape')=='ape' and args['qk_rms_norm'] is True
    module=source.namespace(source.prefix+'/models/mm_latent.py');mapping={}
    for item in heads:
        assert set(item)=={'name','channels','position'} and item['name'] not in mapping
        position=item['position'];kind=position['type'];params=dict(position['args'])
        assert kind in ('ShapePositionEmbedder','RandomPositionEmbedder','LearntPositionEmbedder')
        assert params['model_channels']==args['model_channels']
        mapping[item['name']]=module.Latent(item['channels'],args['model_channels'],getattr(module,kind)(**params))
    assert 'shape' in mapping and len(mapping)>=2
    args['use_fp16']=False;args['use_checkpoint']=False
    cls=source.namespace(source.prefix+'/models/mot_sparse_structure_flow.py').SparseStructureFlowTdfyWrapper
    return cls(latent_mapping=mapping,**args)


class Structure(nn.Module):
    def __init__(self,model,capture_layer=None):
        super().__init__();self.model=model;self.heads=[];self.capture=None
        for name,item in model.latent_mapping.items():self.heads.append((name,int(item.pos_emb.shape[0]),item.input_layer.in_features))
        if capture_layer is not None:self.capture=AttentionCapture(model.blocks[capture_layer].cross_attn['shape'])
    def forward(self,features,time,condition,shortcut):
        latents={};offset=0
        for name,length,width in self.heads:
            latents[name]=features[:,offset:offset+length*width].reshape(1,length,width);offset+=length*width
        value=self.model(latents,time,condition,d=shortcut if self.model.is_shortcut_model else None)
        result=torch.cat([value[name].reshape(1,-1) for name,_,_ in self.heads],1)
        return (result,*self.capture.values) if self.capture else result


class AttentionCapture:
    """Expose source projected / normalized Q and K without changing forward.

    The native weighted coordinator computes the publisher's head-averaged
    patch entropy from these tensors only during the prescribed warmup pass.
    """
    def __init__(self,module):
        self.values=None;self.module=module
        original=module.forward
        # Legacy Torch tracing cannot marshal a custom SparseTensor through
        # its hook bridge. An ordinary local wrapper preserves the same call
        # and parameters while exposing tensor-only diagnostic outputs.
        def forward(*args,**kwargs):
            self.capture(module,args);return original(*args,**kwargs)
        module.forward=forward
    def capture(self,module,args):
        x,context=args[:2];sparse=hasattr(x,'feats');x=x.feats if sparse else x
        context=context.feats if hasattr(context,'feats') else context
        if not sparse:x=x[0]
        if context.ndim==3:context=context[0]
        heads=module.num_heads;q=module.to_q(x).reshape(x.shape[0],heads,-1)
        kv=module.to_kv(context).reshape(context.shape[0],2,heads,-1);k=kv[:,0]
        if module.qk_rms_norm:
            # Dense RMS takes ordinary tensors. Sparse RMS also accepts them.
            q=module.q_rms_norm(q);k=module.k_rms_norm(k)
        self.values=(q,k)
        if sparse:self.values+=(args[0].coords,)


class Slat(nn.Module):
    def __init__(self,source,model,capture_layer=None):
        super().__init__();self.model=model;self.sparse=source.sparse_api();self.capture=None
        if capture_layer is not None:self.capture=AttentionCapture(model.blocks[capture_layer].cross_attn)
    def forward(self,features,coords,time,condition,shortcut):
        x=self.sparse.SparseTensor(features,coords)
        value=self.model(x,time,condition,d=shortcut if self.model.is_shortcut_model else None)
        return (value.feats,*self.capture.values) if self.capture else value.feats


def mesh_decoder(source,args):
    class Layout:
        def __init__(self,res,use_color=False,device='cpu'):
            self.feats_channels=53+(48 if use_color else 0)
    module=source.namespace(source.prefix+'/models/structured_latent_vae/decoder_mesh.py',
        dict(SparseFeatures2Mesh=Layout,MeshExtractResult=object))
    args=dict(args);assert args.get('pe_mode','ape')=='ape' and args.get('attn_mode','swin') in ('full','swin')
    args['use_fp16']=False;args['use_checkpoint']=False;args['device']='cpu'
    model=module.SLatMeshDecoder(**args)
    # The real learned path calls this only after its transformer, two learned
    # sparse subdivision blocks and final trained 53/101-channel projection.
    # Actual source FlexiCubes and vertex-color conversion execute in C++.
    model.to_representation=lambda value:value
    return model


class MeshFields(nn.Module):
    def __init__(self,source,model):super().__init__();self.model=model;self.sparse=source.sparse_api()
    def forward(self,features,coords):
        result=self.model(self.sparse.SparseTensor(features,coords));return result.feats,result.coords


class Occupancy(nn.Module):
    def __init__(self,model,resolution=16):super().__init__();self.model=model;self.resolution=resolution
    def forward(self,features):
        return self.model(features.transpose(1,2).reshape(1,8,self.resolution,self.resolution,self.resolution))
