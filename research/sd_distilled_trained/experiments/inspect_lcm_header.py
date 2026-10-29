"""Private bounded header probe; skips embedded vocabulary values without exporting them."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[2]
directory=ROOT/'build/sd-distilled-asset-probe'
plan=json.loads((directory/'asset-plan.json').read_text(encoding='utf-8'))
item=next(a for a in plan['assets'] if a['id']=='lcm_dreamshaper_v7_f16')
path=directory/'originals'/item['sha256']/item['path']
size=path.stat().st_size
assert size==item['bytes']
scalars={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
with path.open('rb') as f:
    def unpack(fmt):
        raw=f.read(struct.calcsize('<'+fmt))
        if len(raw)!=struct.calcsize('<'+fmt):raise ValueError('Truncated scalar')
        return struct.unpack('<'+fmt,raw)[0]
    def string(keep=True):
        length=unpack('Q')
        if length>32*1024*1024 or f.tell()+length>size:raise ValueError('Invalid string length')
        if keep:return f.read(length).decode('utf-8')
        f.seek(length,1)
    def value(kind,depth=0):
        if kind==8:return string(False)
        if kind in scalars:return unpack(scalars[kind])
        if kind!=9 or depth>0:raise ValueError('Unsupported metadata kind')
        subkind,count=unpack('I'),unpack('Q')
        if count>10**7 or subkind not in list(scalars)+[8]:raise ValueError('Invalid array bound/type')
        if subkind in scalars:
            length=struct.calcsize('<'+scalars[subkind])*count
            if f.tell()+length>size:raise ValueError('Truncated metadata array')
            f.seek(length,1)
        else:
            for _ in range(count):string(False)
        return dict(element_type=subkind,count=count,values_exported=False)
    assert f.read(4)==b'GGUF' and unpack('I')==3
    count,fields=unpack('Q'),unpack('Q')
    assert 0<count<=200000 and fields<=10000
    metadata={}
    for _ in range(fields):
        key=string();kind=unpack('I');data=value(kind)
        assert key not in metadata
        metadata[key]=dict(type=kind,summary=data)
    tensors=[]
    for _ in range(count):
        name=string();rank=unpack('I');assert 1<=rank<=4
        shape=[unpack('Q') for _ in range(rank)];dtype,offset=unpack('I'),unpack('Q')
        assert dtype in [0,1] and all(0<n<=10**9 for n in shape)
        elements=1
        for n in shape:elements*=n
        tensors.append(dict(name=name,shape=shape,ggml_type=dtype,offset=offset,bytes=elements*(4 if dtype==0 else 2)))
    end=f.tell();alignment=metadata.get('general.alignment',{}).get('summary',32)
    assert alignment in [16,32,64,128]
    offset=(end+alignment-1)//alignment*alignment
    spans=sorted((t['offset'],t['offset']+t['bytes']) for t in tensors)
    assert len({t['name'] for t in tensors})==count and spans[-1][1]+offset<=size
    assert all(a[1]<=b[0] for a,b in zip(spans,spans[1:]))
    f.seek(0);header_sha=hashlib.sha256(f.read(end)).hexdigest()
report=dict(schema='lma.private-distilled-header/1',asset_id=item['id'],tensor_count=count,tensors=tensors,
            metadata=metadata,header_bytes=end,header_sha256=header_sha,data_offset=offset,
            dtype_counts=dict(Counter(t['ggml_type'] for t in tensors)),learned_values_exported=False,
            embedded_vocabulary_values_exported=False,model_executed=False,physical_android=False)
(directory/'lcm-checkpoint-header.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('Bounded private header:',count,'tensors; learned/vocabulary values not exported.')
for t in tensors:
    if any(s in t['name'] for s in ['cond_proj','time_cond','time_embed','label_emb']):print(t['name'],t['shape'])
