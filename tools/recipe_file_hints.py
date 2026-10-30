"""Signed data-only filename suggestions, never architecture or model pairing evidence."""
import copy
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def add_hints(templates):
    bundles = json.loads((ROOT/'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles']
    speech = {'kokoro_en_cpu_v1':'kokoro', 'piper_vits_en_cpu_v1':'piper_vits',
              'matcha_en_cpu_v1':'matcha', 'moss_nano_cpu_v1':'moss_nano',
              'qwen3_tts_06b_base_cpu_v1':'qwen3_tts_06b_base'}
    sana = dict(diffusion='transformer.mnn', connector='connector.mnn', projector='projector.mnn',
                vae='vae_decoder.mnn', llm='llm.mnn', llm_config='llm_config.json',
                tokenizer='tokenizer.txt', meta_queries='meta_queries.mnn')
    split = dict(clip_l=['clip_l.safetensors','clip_l.gguf'],clip_g=['clip_g.safetensors','clip_g.gguf'],
                 t5=['umt5-xxl-encoder-*.gguf','umt5_xxl*.safetensors'],
                 umt5_tokenizer=['tokenizer.json'],qwen_merges=['merges.txt'])
    for template in templates:
        hints = {}
        if template['id'] in speech:
            model = next(b for b in bundles if b['pipeline']==speech[template['id']])
            hints.update({c['role']:dict(matchFiles=[Path(c['path']).name]) for c in model['components']})
        if template['id']=='sana_mnn_cpu_v1':
            hints.update({role:dict(matchFiles=[name]) for role,name in sana.items()})
            hints.update({role+'_data':dict(matchSibling=dict(role=role,suffix='.weight')) for role in ['diffusion','connector','projector','vae','llm']})
        if template['definition']['engine']=='openmoss_native':
            hints['extras']=dict(matchFiles=['*.extras.gguf'])
        if template['definition']['engine']=='sd_cpp':
            hints.update({role:dict(matchFiles=names) for role,names in split.items()})
        for requirement in template['requirements']:
            requirement.update(copy.deepcopy(hints.get(requirement['role'],{})))
    return templates
