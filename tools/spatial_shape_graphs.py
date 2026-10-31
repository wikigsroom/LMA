"""Matched Hunyuan3D 2.1 / UltraShape CPU graphs, using fixed publisher classes.

All routed experts retain their actual weights; dense evaluation replaces only
the data-dependent GPU dispatch. Export never substitutes a different model.
"""
import types
import torch
from torch import nn
from spatial_reference import shape


def moe_forward(self, hidden):
    # Same top-k, unnormalised routing probabilities and shared expert as the
    # publisher's eval path. Evaluating all experts is slower, but exportable.
    indices, weights, _ = self.gate(hidden)
    result = torch.zeros_like(hidden)
    for i, expert in enumerate(self.experts):
        gate = ((indices == i).to(weights.dtype) * weights).sum(-1)
        result = result + expert(hidden) * gate.reshape(*hidden.shape[:-1], 1)
    return result + self.shared_experts(hidden)


def masked_cross(self, x, y):
    # Keep the unusual publisher KV interleaving within each head.
    b, n, _ = x.shape
    m = y.shape[1]
    h = self.num_heads
    d = self.head_dim
    q = self.to_q(x).reshape(b, n, h, d)
    kv = torch.cat((self.to_k(y), self.to_v(y)), -1).reshape(b, m, h, 2 * d)
    k, v = kv.split(d, -1)
    q, k = self.q_norm(q), self.k_norm(k)
    valid = (y != -1).any(-1)[:, None, None, :]
    value = nn.functional.scaled_dot_product_attention(q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2), attn_mask=valid)
    return self.out_proj(value.transpose(1, 2).reshape(b, n, h * d))


def rms_forward(self, x):
    eps = self.eps if self.eps is not None else torch.finfo(x.dtype).eps
    return x * torch.rsqrt(x.square().mean(-1, keepdim=True) + eps) * self.weight


def portable(model, target):
    for module in model.modules():
        if module.__class__.__name__ == 'MoEBlock':
            module.forward = types.MethodType(moe_forward, module)
        if target == 'D06' and module.__class__.__name__ == 'CrossAttention':
            module.forward = types.MethodType(masked_cross, module)
        if isinstance(module, nn.RMSNorm):
            module.forward = types.MethodType(rms_forward, module)


class ShapeCache(nn.Module):
    def __init__(self, attention, cfg):
        super().__init__()
        self.scale = float(cfg.get('scale_factor', 1))
        w, c = cfg['width'], cfg['embed_dim']
        self.post_kl = nn.Linear(c, w)
        self.transformer = attention.Transformer(n_ctx=cfg['num_latents'], width=w,
            layers=cfg['num_decoder_layers'], heads=cfg['heads'], qkv_bias=cfg.get('qkv_bias', True),
            qk_norm=cfg.get('qk_norm', False), drop_path_rate=cfg.get('drop_path_rate', 0.))

    def forward(self, latents):
        return self.transformer(self.post_kl(latents / self.scale))


class ShapeQuery(nn.Module):
    def __init__(self, attention, cfg):
        super().__init__()
        down = cfg.get('geo_decoder_downsample_ratio', 1)
        self.geo_decoder = attention.CrossAttentionDecoder(
            fourier_embedder=attention.FourierEmbedder(num_freqs=cfg.get('num_freqs', 8), include_pi=cfg.get('include_pi', True)),
            out_channels=1, num_latents=cfg['num_latents'], mlp_expand_ratio=cfg.get('geo_decoder_mlp_expand_ratio', 4),
            downsample_ratio=down, enable_ln_post=cfg.get('geo_decoder_ln_post', True), width=cfg['width'] // down,
            heads=cfg['heads'] // down, qkv_bias=cfg.get('qkv_bias', True), qk_norm=cfg.get('qk_norm', False),
            label_type=cfg.get('label_type', 'binary'))

    def forward(self, cache, points):
        return self.geo_decoder(queries=points, latents=cache)


class HunyuanFlow(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, latents, timestep, image_embeddings):
        return self.model(latents, timestep, {'main': image_embeddings})


class UltraFlow(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, latents, timestep, image_embeddings, voxel_indices):
        return self.model(latents, timestep, {'main': image_embeddings}, voxel_cond=voxel_indices)


def modules(target, flow_config, vae_config):
    attention, source, scheduler = shape(target)
    # Reject other architectures and constructor-side checkpoint loading.
    assert flow_config.get('guidance_cond_proj_dim') is None
    assert not flow_config.get('with_decoupled_ca', False)
    assert not flow_config.get('use_pos_emb', False)
    assert not flow_config.get('use_attention_pooling', False)
    assert not flow_config.get('ckpt_path') and not vae_config.get('ckpt_path')
    flow_config = dict(flow_config)
    if target == 'D07':
        flow_config.update(use_attention_pooling=False, use_pos_emb=False)
    model = (source.RefineDiT if target == 'D06' else source.HunYuanDiTPlain)(**flow_config).float().eval()
    cache, query = ShapeCache(attention, vae_config).float().eval(), ShapeQuery(attention, vae_config).float().eval()
    return model, cache, query, scheduler
