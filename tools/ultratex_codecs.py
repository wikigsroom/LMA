"""Pinned publisher VAE and local Transformers text encoders for UltraTex.

Only class/function definitions execute from the reviewed source. Inputs and
checkpoints are explicit local files; this module has no Hub/download path.
"""
import torch
import json
from torch import nn
from einops import rearrange
from ultratex_flows import definitions


def autoencoder(family, parameters):
    assert family in ('flux1', 'flux2')
    relative = ('ultratex/backbones/flux1/modules/autoencoder.py' if family == 'flux1'
                else 'ultratex/backbones/flux2/autoencoder.py')
    module = definitions(relative)
    return module.AutoEncoder(module.AutoEncoderParams(**parameters)).float().eval().requires_grad_(False)


class Encode(nn.Module):
    def __init__(self, model, family):
        super().__init__(); self.model = model; self.family = family

    def forward(self, image, noise):
        if self.family == 'flux2':
            # Keep an explicit zero-valued noise dependency: both families use
            # one closed native signature, while FLUX2 uses the mean, not RNG.
            mean = self.model.encoder(image).chunk(2, dim=1)[0]
            packed = rearrange(mean, 'b c (h ph) (w pw) -> b (c ph pw) h w', ph=2, pw=2)
            # Frozen eval BatchNorm, written as its exact affine equation so
            # legacy ONNX export does not require einops' symbolic channel size.
            mean = self.model.bn.running_mean.view(1, -1, 1, 1)
            scale = torch.sqrt(self.model.bn.running_var.view(1, -1, 1, 1) + self.model.bn_eps)
            return (packed - mean) / scale + noise * 0
        mean, logvar = self.model.encoder(image).chunk(2, dim=1)
        latent = self.model.scale_factor * (mean + torch.exp(.5 * logvar) * noise - self.model.shift_factor)
        return rearrange(latent, 'b c (h ph) (w pw) -> b (c ph pw) h w', ph=2, pw=2)


class Decode(nn.Module):
    def __init__(self, model, family):
        super().__init__(); self.model = model; self.family = family

    def forward(self, latents):
        if self.family == 'flux1':
            latents = rearrange(latents, 'b (c ph pw) h w -> b c (h ph) (w pw)', ph=2, pw=2)
        return self.model.decode(latents)


class Clip(nn.Module):
    def __init__(self, model): super().__init__(); self.model = model
    def forward(self, input_ids):
        return self.model(input_ids=input_ids, attention_mask=None, return_dict=False)[1]


class T5(nn.Module):
    def __init__(self, model): super().__init__(); self.model = model
    def forward(self, input_ids):
        return self.model(input_ids=input_ids, attention_mask=None, return_dict=False)[0]


class Qwen(nn.Module):
    def __init__(self, model): super().__init__(); self.model = model
    def forward(self, input_ids, attention_mask):
        # Same eager causal + right-padding mask as Transformers, with no vmap
        # during legacy ONNX tracing. User masks remain graph inputs.
        positions = torch.arange(input_ids.shape[1], device=input_ids.device)
        allowed = (positions[None, :] <= positions[:, None])[None, None] & attention_mask[:, None, None, :].bool()
        mask = torch.where(allowed, torch.tensor(0., dtype=torch.float32), torch.tensor(torch.finfo(torch.float32).min))
        hidden = self.model(input_ids=input_ids, attention_mask={'full_attention': mask},
                            output_hidden_states=True, use_cache=False, return_dict=True).hidden_states
        # Publisher Qwen3Embedder: states 9,18,27, not just the final state.
        return torch.cat([hidden[i] for i in (9, 18, 27)], dim=-1)


def padding_id(directory, model_config):
    """Tokenizer padding is not necessarily the text model's config default."""
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_file(str(directory/'tokenizer.json'))
    config=directory/'tokenizer_config.json'
    if config.is_file():
        assert not config.is_symlink() and config.stat().st_size<=1024*1024
        declaration=json.loads(config.read_text('utf-8')).get('pad_token')
        if isinstance(declaration,dict):declaration=declaration.get('content')
        if declaration is not None:
            assert isinstance(declaration,str)
            value=tokenizer.token_to_id(declaration)
            assert value is not None,'Padding token is missing from the selected tokenizer'
            return value
    # Both publisher CLIP and Qwen3 use this padding token. Qwen3's model
    # config can omit pad_token_id; CLIP's model default can differ from it.
    value=tokenizer.token_to_id('<|endoftext|>')
    if value is not None:return value
    value=model_config.pad_token_id
    assert isinstance(value,int) and 0<=value<model_config.vocab_size,'Select an explicit matched tokenizer padding declaration'
    return value


def export_codec(model, family, size, directory):
    from shape_graphs import export_graph
    assert size % 16 == 0 and 32 <= size <= 512
    channels = model.encoder.conv_out.out_channels // 2
    reduction = 2 ** (model.encoder.num_resolutions - 1)
    assert reduction == 8, 'Select the publisher four-stage VAE'
    noise_shape = (1, channels, size // 8, size // 8) if family == 'flux1' else (1, channels * 4, size // 16, size // 16)
    export_graph(Encode(model, family), (torch.zeros(1, 3, size, size), torch.zeros(noise_shape)),
                 directory/'vae_encoder.onnx', ['image', 'noise'], 'latents', {})
    export_graph(Decode(model, family), (torch.zeros(1, channels * 4, size // 16, size // 16),),
                 directory/'albedo_decoder.onnx', ['latents'], 'image', {})


def export_text(family, paths, directory):
    import importlib.metadata
    assert importlib.metadata.version('transformers') == '4.57.6'
    from transformers import CLIPTextModel, T5EncoderModel, Qwen3Model
    from shape_graphs import export_graph
    import gc
    if family == 'flux1':
        model = CLIPTextModel.from_pretrained(paths['clip'], local_files_only=True,
            use_safetensors=True, attn_implementation='eager').float().eval().requires_grad_(False)
        clip_width, clip_vocab, clip_pad = model.config.hidden_size, model.config.vocab_size, padding_id(paths['clip'],model.config)
        export_graph(Clip(model), (torch.zeros(1,77,dtype=torch.int64),), directory/'clip.onnx', ['input_ids'], 'pooled_text', {})
        del model; gc.collect()
        model = T5EncoderModel.from_pretrained(paths['t5'], local_files_only=True,
            use_safetensors=True, attn_implementation='eager').float().eval().requires_grad_(False)
        width, vocab = model.config.d_model, model.config.vocab_size
        export_graph(T5(model), (torch.zeros(1,512,dtype=torch.int64),), directory/'text.onnx', ['input_ids'], 'text', {})
        del model; gc.collect()
        return dict(textWidth=width, textVocab=vocab, textPad=0, clipWidth=clip_width,
                    clipVocab=clip_vocab, clipPad=clip_pad, textLength=512, clipLength=77)
    model = Qwen3Model.from_pretrained(paths['qwen'], local_files_only=True,
        use_safetensors=True, attn_implementation='eager').float().eval().requires_grad_(False)
    assert model.config.num_hidden_layers >= 27 and model.config.num_hidden_layers <= 64
    assert all(x=='full_attention' for x in model.config.layer_types),'This fixed Qwen3 export requires the publisher full-attention encoder'
    width, vocab, pad = model.config.hidden_size * 3, model.config.vocab_size, padding_id(paths['qwen'],model.config)
    export_graph(Qwen(model), (torch.zeros(1,512,dtype=torch.int64), torch.ones(1,512,dtype=torch.int64)),
                 directory/'text.onnx', ['input_ids','attention_mask'], 'text', {})
    del model; gc.collect()
    return dict(textWidth=width, textVocab=vocab, textPad=pad, textLength=512)
