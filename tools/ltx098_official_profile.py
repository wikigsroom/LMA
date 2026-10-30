"""Pinned publisher files and a weight-free ONNX architecture for old LTX multiscale."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = 'ltx098_pixart_multiscale_v1'
PROFILE = 'ltx098_pixart_7_plus_3_v1'
META = ROOT / 'third_party/ltx098-official'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph(header, *, filename='ltx098-upscaler.onnx.data', header_bytes=21928):
    """Architecture only. Learned initializers reference exact ranges of the user file."""
    sys.path.insert(0, str(ROOT / 'build/soulx-python'))
    import numpy as np
    import onnx
    from onnx import helper as h, numpy_helper as nh, TensorProto as T
    nodes, initializers = [], []
    sequence = 0

    def name():
        nonlocal sequence
        sequence += 1
        return 'v' + str(sequence)

    def constant(data, dtype=np.int64):
        item = name()
        initializers.append(nh.from_array(np.asarray(data, dtype=dtype), item))
        return item

    def node(op, *args, **attrs):
        out = name()
        nodes.append(h.make_node(op, list(args), [out], **attrs))
        return out

    consumed = set()

    def weight(key, reshape=None):
        value = header[key]
        assert value['dtype'] == 'F32' and key not in consumed
        consumed.add(key)
        begin, end = value['data_offsets']
        tensor = T(name=key, data_type=T.FLOAT, dims=reshape or value['shape'], data_location=T.EXTERNAL)
        for k, v in [('location', filename), ('offset', str(8 + header_bytes + begin)), ('length', str(end - begin))]:
            tensor.external_data.add(key=k, value=v)
        assert end - begin == 4 * int(np.prod(tensor.dims))
        initializers.append(tensor)
        return key

    def conv(x, key, spatial=False):
        w = header[key + '.weight']['shape']
        return node('Conv', x, weight(key + '.weight', [w[0], w[1], 1, 3, 3] if spatial else None), weight(key + '.bias'),
                    pads=[0, 1, 1, 0, 1, 1] if spatial else [1] * 6, strides=[1] * 3)

    def norm(x, key):
        channels = header[key + '.weight']['shape'][0]
        grouped = node('Reshape', x, constant([1, 32, -1]))
        normalized = node('InstanceNormalization', grouped, constant(np.ones(32), np.float32), constant(np.zeros(32), np.float32), epsilon=1e-5)
        normalized = node('Reshape', normalized, node('Shape', x))
        gamma = weight(key + '.weight', [1, channels, 1, 1, 1])
        beta = weight(key + '.bias', [1, channels, 1, 1, 1])
        return node('Add', node('Mul', normalized, gamma), beta)

    def silu(x):
        return node('Mul', x, node('Sigmoid', x))

    def block(x, key):
        residual = x
        x = silu(norm(conv(x, key + '.conv1'), key + '.norm1'))
        x = norm(conv(x, key + '.conv2'), key + '.norm2')
        return silu(node('Add', x, residual))

    x = silu(norm(conv('latents', 'initial_conv'), 'initial_norm'))
    for i in range(4):
        x = block(x, f'res_blocks.{i}')
    mid = header['initial_conv.bias']['shape'][0]
    x = conv(x, 'upsampler.0', spatial=True)
    spatial = node('Gather', node('Shape', x), constant([2, 3, 4]), axis=0)
    shuffle_shape = node('Concat', constant([1, mid, 2, 2]), spatial, axis=0)
    x = node('Transpose', node('Reshape', x, shuffle_shape), perm=[0, 1, 4, 5, 2, 6, 3])
    expanded = node('Mul', spatial, constant([1, 2, 2]))
    x = node('Reshape', x, node('Concat', constant([1, mid]), expanded, axis=0))
    for i in range(4):
        x = block(x, f'post_upsample_res_blocks.{i}')
    x = conv(x, 'final_conv')
    nodes.append(h.make_node('Identity', [x], ['upsampled']))
    assert consumed == set(header) - {'__metadata__'} and len(consumed) == 72
    channels = header['initial_conv.weight']['shape'][1]
    result = h.make_model(h.make_graph(nodes, 'LMA old LTX spatial upsampler',
        [h.make_tensor_value_info('latents', T.FLOAT, [1, channels, 'F', 'H', 'W'])],
        [h.make_tensor_value_info('upsampled', T.FLOAT, [1, channels, 'F', 'OH', 'OW'])], initializers),
        producer_name='LMA architecture only; no learned weights', opset_imports=[h.make_opsetid('', 17)])
    result.ir_version = 8
    return result


def lock():
    value = json.loads((META / 'identity.json').read_text(encoding='utf-8'))
    for source in value['sources']:
        for item in source['files']:
            p = META / item['metadata_file']
            if p.exists() and digest(p) != item.get('header_sha256', item['sha256']):
                raise ValueError('Changed official metadata: ' + p.name)
    return value


def schema():
    from ltx098_recipe import schema as original
    result = original()
    for key in ['width', 'height']:
        result['fields'][key].update(minimum=128, maximum=256, default=256, presets=[128, 192, 256])
    result['fields']['steps'].update(default=10, minimum=10, maximum=10, presets=[10],
        help='官方多尺度调度：7 步初次生成、空间放大和 AdaIN、3 步细化。')
    return result


def recipe():
    from ltx098_recipe import recipe as original
    result = original()
    result.update(id=PIPELINE, name='旧 LTX 2B 0.9.8 · PixArt 多尺度', primaryRole='diffusion_model')
    result['definition'].update(pipeline=PIPELINE, capabilities=['text_to_video', 'multiscale', 'pixart_t5'], parameters=schema())
    requirements = [r for r in result['requirements'] if r['role'] not in ['text_encoder', 'tokenizer_config']]
    for role, label, format in [
        ('text_config', 'PixArt T5 · config.json', 'json'), ('text_index', 'PixArt T5 · 分片索引', 'json'),
        ('text_shard_1', 'PixArt T5 · 官方 F32 分片 1', 'safetensors'), ('text_shard_2', 'PixArt T5 · 官方 F32 分片 2', 'safetensors'),
        ('tokenizer_config', 'PixArt T5 · tokenizer_config.json', 'json'), ('tokenizer', 'PixArt T5 · spiece.model', 'sentencepiece'),
        ('upscaler', 'LTX 0.9.8 · 官方空间放大器', 'safetensors')]:
        requirements.append(dict(role=role, label=label, formats=[format], required=True))
    result['requirements'] = requirements
    result['help'] = ('用户自行选择、下载或导入旧 0.9.8 DiT / 九段 VAE，以及官方 PixArt T5 F32 两分片、分词文件和空间放大器。'
        '全部在本手机顺序运行：T5 CPU → Vulkan 初次采样 7 步 → CPU 空间放大与 AdaIN → 重新加噪 → Vulkan 细化 3 步 → VAE CPU → 双线性缩放 → AVC 视频。'
        '输出 128–256（32 倍数）、9–33 帧（8n+1），CFG=1、STG=0，提示词直接编码，不自动下载可选的提示词增强模型。'
        '官方 T5 原文件约 17.74 GiB，总运行资产约 24 GiB；映射读取不代表手机可用内存足够。不代表 Z20 可运行，画质与真机未验收。App 仅提供程序，不内置模型。')
    return copy.deepcopy(result)


def generate():
    value = lock()
    header_file = next(f for s in value['sources'] if s['repository'] == 'Lightricks/LTX-Video' for f in s['files'])
    header = json.loads((META / header_file['metadata_file']).read_text(encoding='utf-8'))
    model = graph(header, header_bytes=header_file['header_bytes'])
    target = ROOT / 'app/src/main/assets/architectures/ltx098-upscaler.onnx'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(model.SerializeToString())
    print(json.dumps(dict(file=str(target.relative_to(ROOT)), bytes=target.stat().st_size, sha256=digest(target),
                         external_learned_tensors=72, model_data_embedded=False)))


if __name__ == '__main__':
    generate()
