# SPDX-License-Identifier: Apache-2.0
# Soul-AILab/Alibaba acoustic network layout; LMA export adaptations 2026.
"""Pinned SoulX acoustic export layouts, using the complete upstream networks.

Developer-side conversion only. No inference provider or checkpoint downloader.
The Android runtime consumes exported data; it never imports Python/PyTorch.
"""
import gc
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

FORMAT = 'lma.soulx-acoustic-onnx/1'
MAX_TOKENS = 3375  # <=375 reference + <=3000 generated semantic codes
UPSTREAM = '5ac9c0e1cfe596396200c7d38e3fd53b7b3fbf4b'
CONTRACTS = {
    'flow_encoder': dict(file='flow-encoder.onnx', inputs={'tokens':('int64',[1,'N']), 'speaker':('float32',[1,192])},
                         outputs={'mu':('float32',[1,80,'2N']), 'spks':('float32',[1,80])}),
    'flow_estimator': dict(file='flow-estimator.onnx', inputs={'x':('float32',[2,80,'F']), 'mask':('float32',[2,1,'F']),
                           'mu':('float32',[2,80,'F']), 'time':('float32',[2]), 'spks':('float32',[2,80]), 'cond':('float32',[2,80,'F'])},
                           outputs={'velocity':('float32',[2,80,'F'])}),
    'hift_f0': dict(file='hift-f0.onnx', inputs={'mel':('float32',[1,80,'T'])}, outputs={'f0':('float32',[1,'T'])}),
    'hift_spectrum': dict(file='hift-spectrum.onnx', inputs={'mel':('float32',[1,80,'T']), 'source_stft':('float32',[1,18,'120T+1'])},
                          outputs={'magnitude':('float32',[1,9,'120T+1']), 'phase':('float32',[1,9,'120T+1'])}),
}


class FlowEncoder(nn.Module):
    def __init__(self, flow):
        super().__init__()
        self.input_embedding = flow.input_embedding
        self.spk_embed_affine_layer = flow.spk_embed_affine_layer
        self.encoder = flow.encoder
        self.encoder_proj = flow.encoder_proj
        # The upstream cache-extension branch is traced at export time. Warm
        # both deterministic positional tables for the complete accepted range.
        # Native bounds reject a longer token sequence before graph execution.
        self.encoder.embed.pos_enc.extend_pe(torch.zeros(1,MAX_TOKENS))
        self.encoder.up_embed.pos_enc.extend_pe(torch.zeros(1,MAX_TOKENS*2))

    def forward(self, tokens, speaker):
        # Batch one, no padded tokens: all original length masks are true.
        lengths = torch.ones(tokens.shape[0],dtype=torch.int64,device=tokens.device)*tokens.shape[1]
        hidden, _ = self.encoder(self.input_embedding(tokens),lengths,streaming=False)
        mu = self.encoder_proj(hidden).transpose(1,2).contiguous()
        spks = self.spk_embed_affine_layer(F.normalize(speaker,dim=1))
        return mu, spks


class FlowEstimator(nn.Module):
    def __init__(self, estimator):
        super().__init__(); self.estimator = estimator

    def forward(self, x, mask, mu, time, spks, cond):
        return self.estimator(x,mask,mu,time,spks,cond,streaming=False)


class HiFTSpectrum(nn.Module):
    """The upstream decode network, with complex STFT/ISTFT outside ONNX.

    Preserve the final leaky_relu DEFAULT slope (.01), not lrelu_slope (.1).
    This seam makes the original convolution network portable to ORT CPU.
    """
    def __init__(self, hift):
        super().__init__(); self.hift = hift

    def forward(self, mel, source_stft):
        h = self.hift; x = h.conv_pre(mel)
        for i in range(h.num_upsamples):
            x = h.ups[i](F.leaky_relu(x,h.lrelu_slope))
            if i==h.num_upsamples-1: x = h.reflection_pad(x)
            x = x + h.source_resblocks[i](h.source_downs[i](source_stft))
            residual = h.resblocks[i*h.num_kernels](x)
            for j in range(1,h.num_kernels): residual = residual+h.resblocks[i*h.num_kernels+j](x)
            x = residual/h.num_kernels
        x = h.conv_post(F.leaky_relu(x))
        return torch.exp(x[:,:9,:]), torch.sin(x[:,9:,:])


def freeze_weight_norm(module):
    # Load ORIGINAL strict state keys first; then fold parametrized weight norm
    # into constant weights. Never replace trained tensors with random weights.
    for child in module.modules():
        if hasattr(child,'parametrizations') and 'weight' in child.parametrizations:
            torch.nn.utils.parametrize.remove_parametrizations(child,'weight',leave_parametrized=True)
    module.eval().requires_grad_(False)


def example(role, frames=12):
    if role=='flow_encoder': return (torch.arange(frames,dtype=torch.int64)[None,:]%6561,torch.ones(1,192)*.03)
    if role=='flow_estimator': return (torch.zeros(2,80,frames),torch.ones(2,1,frames),torch.zeros(2,80,frames),torch.zeros(2),torch.zeros(2,80),torch.zeros(2,80,frames))
    if role=='hift_f0': return (torch.zeros(1,80,frames),)
    if role=='hift_spectrum': return (torch.zeros(1,80,frames),torch.zeros(1,18,frames*120+1))
    raise ValueError('Unknown SoulX acoustic role')


def export_graph(role, module, directory):
    import onnx
    contract=CONTRACTS[role]; path=directory/contract['file']; raw=path.with_suffix('.raw.onnx')
    axes={}
    for name, (_,shape) in {**contract['inputs'],**contract['outputs']}.items():
        axes[name]={i:dim for i,dim in enumerate(shape) if isinstance(dim,str)}
    module.eval().requires_grad_(False)
    torch.onnx.export(module,example(role),str(raw),input_names=list(contract['inputs']),output_names=list(contract['outputs']),
        dynamic_axes=axes,opset_version=17,dynamo=False,do_constant_folding=True,keep_initializers_as_inputs=False)
    graph=onnx.load(str(raw),load_external_data=True)
    # Externalize even small tensors; the native loader never resolves an
    # undeclared sidecar or arbitrary relative/absolute location.
    data_file=path.name+'.data'
    if (directory/data_file).exists(): raise RuntimeError('Refuse to append to an existing tensor sidecar')
    onnx.save_model(graph,str(path),save_as_external_data=True,all_tensors_to_one_file=True,
                    location=data_file,size_threshold=0,convert_attribute=False)
    del graph; gc.collect(); raw.unlink()
    onnx.checker.check_model(str(path))
    return path


def source_weights(hift, directory):
    linear=hift.m_source.l_linear
    weights=linear.weight.detach().cpu().float().numpy().reshape(-1)
    bias=linear.bias.detach().cpu().float().numpy().reshape(-1)
    if weights.shape!=(9,) or bias.shape!=(1,) or not np.isfinite(np.r_[weights,bias]).all():
        raise RuntimeError('Unsupported learned HiFT source merge')
    path=directory/'hift-source.f32';path.write_bytes(struct.pack('<10f',*weights,*bias));return path


def strict_checkpoint(module, path, generator_prefix=False):
    if not path.is_file() or path.stat().st_size>2*1024**3: raise RuntimeError('Missing or oversized acoustic checkpoint')
    try: state=torch.load(path,map_location='cpu',weights_only=True,mmap=True)
    except RuntimeError as error:
        if 'mmap can only be used' not in str(error): raise
        state=torch.load(path,map_location='cpu',weights_only=True)
    if not isinstance(state,dict) or not state or any(not isinstance(k,str) or not isinstance(v,torch.Tensor) for k,v in state.items()):
        raise RuntimeError('Expected a tensor-only SoulX state dictionary')
    if generator_prefix:
        mapped={(k[len('generator.'):] if k.startswith('generator.') else k):v for k,v in state.items()}
        if len(mapped)!=len(state): raise RuntimeError('Colliding HiFT generator state keys')
        state=mapped
    if any(not torch.isfinite(t).all().item() for t in state.values()): raise RuntimeError('Non-finite checkpoint tensor')
    module.load_state_dict(state,strict=True); del state; module.cpu().float().eval().requires_grad_(False)


def asset(path, role):
    return dict(role=role,file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def write_manifest(directory, sources, synthetic=None):
    assets=[]
    for role,contract in CONTRACTS.items():
        assets.append(asset(directory/contract['file'],role))
        sidecar=directory/(contract['file']+'.data')
        if sidecar.exists(): assets.append(asset(sidecar,role+'_data'))
    assets.append(asset(directory/'hift-source.f32','hift_source'))
    record=dict(format=FORMAT,architecture='soulx_podcast_1_7b_acoustic',upstream_code_revision=UPSTREAM,
        sample_rate=24000,channels=1,semantic_codes=6561,reference_tokens_max=375,generated_tokens_max=3000,
        flow_cfg=.7,flow_steps_default=15,onnx_opset=17,precision='float32',backend='ort_cpu',
        contracts=CONTRACTS,assets=assets,checkpoint_sources=sources,synthetic_parameters=synthetic,
        complete_soulx_model=False,includes_language_backbone=False,includes_reference_models=False,
        provenance_verified=False,model_assets_packaged_in_apk=False)
    (directory/'soulx-acoustic.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');return record
