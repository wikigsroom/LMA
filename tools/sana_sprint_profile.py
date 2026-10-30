"""Matched Sana-Sprint data recipe and cached source checks. Never fetch weights."""
import copy
import json
from pathlib import Path
from fetch_moss_nano import validate_sources

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = 'sana_sprint_06b_mnn_v1'
FILES = [('diffusion', 'dit.mnn', 'mnn'), ('diffusion_data', 'dit.mnn.weight', 'mnn_data')]
for i in range(4):
    FILES += [('gemma'+str(i), 'gemma_chunk'+str(i)+'.mnn', 'mnn'), ('gemma'+str(i)+'_data', 'gemma_chunk'+str(i)+'.mnn.weight', 'mnn_data')]
FILES += [('embeddings', 'token_emb.bin', 'bin'), ('encoder_config', 'gemma_meta.json', 'json'), ('tokenizer', 'tokenizer.model', 'sentencepiece'), ('vae', 'vae_decoder.mnn', 'mnn')]


def sources():
    lock = json.loads((ROOT/'third_party/moss-nano-source-lock.json').read_text(encoding='utf-8'))
    piece = next(x for x in lock['sources'] if x['name'] == 'sentencepiece')
    validate_sources(dict(sources=[piece]))
    return copy.deepcopy(piece)


def recipe_template():
    fields = {}
    for key, label, default, low, high, presets, kind in [
        ('width', '宽度（配方固定）', 1024, 1024, 1024, [1024], 'integer'),
        ('height', '高度（配方固定）', 1024, 1024, 1024, [1024], 'integer'),
        ('steps', 'SCM 采样步数', 2, 1, 4, [1, 2, 3, 4], 'integer'),
        ('guidance', '内嵌引导强度', 4.5, 1, 30, [1, 3, 4.5, 7], 'number'),
        ('threads', 'CPU 线程', 4, 1, 32, [1, 2, 4, 8], 'integer'),
        ('seed', '随机种子（-1 随机）', -1, -1, 2147483647, [-1, 42], 'integer')]:
        fields[key] = dict(type=kind, label=label, default=default, minimum=low, maximum=high, presets=presets,
            limitSource='matched_export' if key in ('width', 'height') else 'application_guard')
    requirements = []
    for role, filename, format in FILES:
        hint = dict(matchFiles=[filename])
        if role.endswith('_data'): hint = dict(matchSibling=dict(role=role[:-5], suffix='.weight'))
        requirements.append(dict(role=role, label=filename, formats=[format], required=True, **hint))
    return dict(id='sana_sprint_06b_mnn_cpu_v1', name='Sana-Sprint 0.6B · 文生图', primaryRole='diffusion',
        definition=dict(engine='mnn_diffusion', backend='cpu', architecture='sana_sprint_06b', pipeline=PIPELINE, tasks=['image'],
            capabilities=['text_to_image', 'distilled_sampling'], parameters=dict(version=1, fields=fields)),
        requirements=requirements, fixedComponents=[],
        help='仅适用于匹配的 Sana-Sprint 0.6B MNN 转换：四段 Gemma2-2B、FP16 embedding、SentencePiece 与 DC-AE，14 个组件由用户选择。固定 1024×1024、1–4 步 SCM、内嵌引导，不支持负面提示词 / LoRA / 图片输入。提示词经小写和首尾空白处理，加固定文本编码前缀；超过 506 token 时截断，扩散选择首 token 加末 299 个位置。不是 Sana Edit、普通 600M 或 1.6B 的通用配方；Gemma 有独立条款。总资产约 6.29 GiB，编码器分段释放；高内存需求与 CPU 耗时没有 LMA 手机实测，不代表 Z20 可运行。App 更新与浏览不会下载权重。')
