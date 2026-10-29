"""Bounded, read-only tensor-header inspection; no learned tensor data is exported."""
from collections import Counter
import hashlib
import json
import math
import struct


def safetensors(path):
    with path.open('rb') as stream:
        raw = stream.read(8)
        if len(raw) != 8: raise ValueError('Truncated safetensors length')
        length = struct.unpack('<Q', raw)[0]
        if not 1 <= length <= 32 * 1024 * 1024: raise ValueError('Invalid safetensors header bound')
        header = stream.read(length)
    value = json.loads(header); tensors = []; widths = dict(F16=2, BF16=2, F32=4, F64=8, I64=8, I32=4)
    for name, spec in value.items():
        if name == '__metadata__': continue
        shape = spec['shape']; begin, end = spec['data_offsets']; dtype = spec['dtype']
        if not isinstance(name, str) or not all(isinstance(n, int) and n > 0 for n in shape): raise ValueError('Invalid tensor identity')
        if dtype not in widths or end - begin != math.prod(shape) * widths[dtype]: raise ValueError('Tensor span/dtype mismatch')
        if not 0 <= begin < end <= path.stat().st_size - 8 - length: raise ValueError('Tensor outside full file')
        tensors.append(dict(name=name, shape=shape, dtype=dtype, data_offsets=[begin, end]))
    spans = sorted(t['data_offsets'] for t in tensors)
    if not spans or spans[0][0] != 0 or spans[-1][1] != path.stat().st_size - 8 - length:
        raise ValueError('Incomplete tensor body')
    if any(left[1] != right[0] for left, right in zip(spans, spans[1:])): raise ValueError('Overlapping or missing tensor bytes')
    return dict(format='safetensors', tensor_count=len(tensors), header_bytes=length,
                header_sha256=hashlib.sha256(header).hexdigest(), tensors=tensors,
                dtype_counts=dict(Counter(t['dtype'] for t in tensors)), learned_data_exported=False)


def gguf(path):
    widths = {0:(1,4), 1:(1,2), 2:(32,18), 3:(32,20), 6:(32,22), 7:(32,24), 8:(32,34),
              9:(32,40), 10:(256,84), 11:(256,110), 12:(256,144), 13:(256,176), 14:(256,210), 15:(256,292), 30:(1,2)}
    scalars = {0:'B', 1:'b', 2:'H', 3:'h', 4:'I', 5:'i', 6:'f', 7:'?', 10:'Q', 11:'q', 12:'d'}
    with path.open('rb') as stream:
        def unpack(fmt):
            size = struct.calcsize('<' + fmt); raw = stream.read(size)
            if len(raw) != size: raise ValueError('Truncated GGUF field')
            return struct.unpack('<' + fmt, raw)[0]
        def string():
            length = unpack('Q')
            if length > 32 * 1024 * 1024: raise ValueError('GGUF string bound')
            raw = stream.read(length)
            if len(raw) != length: raise ValueError('Truncated GGUF string')
            return raw.decode('utf-8')
        def value(kind):
            if kind == 8: return string()
            if kind == 9:
                item = unpack('I'); count = unpack('Q')
                if item not in scalars or count > 10**7: raise ValueError('Unsupported GGUF metadata array')
                stream.seek(struct.calcsize('<' + scalars[item]) * count, 1); return dict(element_type=item, count=count)
            if kind not in scalars: raise ValueError('Unknown GGUF metadata kind')
            return unpack(scalars[kind])
        if stream.read(4) != b'GGUF' or unpack('I') != 3: raise ValueError('Expected complete GGUF v3')
        count = unpack('Q'); fields = unpack('Q')
        if not 1 <= count <= 200000 or fields > 10000: raise ValueError('GGUF count bound')
        metadata = {}
        for _ in range(fields):
            key = string(); metadata[key] = value(unpack('I'))
        tensors = []
        for _ in range(count):
            name = string(); dimensions = unpack('I')
            if not 1 <= dimensions <= 4: raise ValueError('GGUF tensor rank')
            shape = [unpack('Q') for _ in range(dimensions)]; dtype = unpack('I'); offset = unpack('Q')
            if dtype not in widths or not all(n > 0 for n in shape): raise ValueError('GGUF shape/type')
            block, size = widths[dtype]
            if shape[0] % block: raise ValueError('Unaligned quantized row')
            tensors.append(dict(name=name, shape=shape, ggml_type=dtype, offset=offset, bytes=math.prod(shape) // block * size))
        end = stream.tell(); alignment = metadata.get('general.alignment', 32)
        if alignment not in [16, 32, 64, 128]: raise ValueError('GGUF alignment')
        data_offset = (end + alignment - 1) // alignment * alignment
        spans = sorted((t['offset'], t['offset'] + t['bytes']) for t in tensors)
        if any(right[0] < left[1] for left, right in zip(spans, spans[1:])): raise ValueError('GGUF tensor overlap')
        if spans[-1][1] + data_offset > path.stat().st_size: raise ValueError('GGUF tensor outside complete file')
        stream.seek(0); header_sha = hashlib.sha256(stream.read(end)).hexdigest()
    return dict(format='gguf', version=3, tensor_count=count, header_bytes=end, header_sha256=header_sha,
                data_offset=data_offset, metadata={k:v for k,v in metadata.items() if k in ['general.architecture', 'general.file_type', 'general.alignment']},
                tensors=tensors, dtype_counts=dict(Counter(str(t['ggml_type']) for t in tensors)), learned_data_exported=False)
