"""Bounded inspection of the single-tensor local LCM preparation output."""
import hashlib
import struct


def inspect(data):
    if not isinstance(data, bytes) or not 5120 <= len(data) <= 64 * 1024:
        raise ValueError('Overlay outside byte budget')
    position = 0

    def take(count):
        nonlocal position
        if count < 0 or position + count > len(data):
            raise ValueError('Truncated overlay')
        value = data[position:position + count]
        position += count
        return value

    def u32(): return struct.unpack('<I', take(4))[0]
    def u64(): return struct.unpack('<Q', take(8))[0]

    def string():
        count = u64()
        if not 0 < count <= 512:
            raise ValueError('Overlay string outside budget')
        result = take(count).decode('utf-8')
        if '\0' in result:
            raise ValueError('Overlay NUL string')
        return result

    if take(4) != b'GGUF' or u32() != 3 or u64() != 1:
        raise ValueError('Expected GGUFv3 single-tensor overlay')
    count = u64()
    if count not in (0, 6):
        raise ValueError('Unexpected overlay metadata')
    metadata = {}
    for _ in range(count):
        name = string()
        if name in metadata or u32() != 8:
            raise ValueError('Duplicate / non-string overlay metadata')
        metadata[name] = string()
    name = string()
    if name != 'model.diffusion_model.time_embed.0.bias' or u32() != 1 or u64() != 1280 or u32() != 0 or u64() != 0:
        raise ValueError('Unexpected override tensor layout')
    start = (position + 31) // 32 * 32
    if any(take(start - position)) or len(data) != start + 5120:
        raise ValueError('Overlay padding / payload span mismatch')
    payload = take(5120)
    floats = struct.unpack('<1280f', payload)
    if any(not -float('inf') < f < float('inf') for f in floats):
        raise ValueError('Non-finite override tensor')
    return dict(metadata=metadata, name=name, shape=[1280], type='F32', payload_offset=start, payload=payload,
                bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), payload_sha256=hashlib.sha256(payload).hexdigest())
