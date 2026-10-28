"""Bounded local safetensors reading and streaming GGUF writing for old LTX.

No network, App startup actions, model execution or automatic asset selection.
"""
import hashlib,json,math,struct
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PREFIX='model.diffusion_model.'
DTYPES={'BF16':2,'F16':2,'F32':4}

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(4*1024*1024):digest.update(block)
    return digest.hexdigest()

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate safetensors JSON key')
        result[key]=value
    return result

class Checkpoint:
    def __init__(self,path):
        self.path=Path(path);self.length=self.path.stat().st_size
        with self.path.open('rb') as stream:
            size=stream.read(8)
            if len(size)!=8:raise ValueError('Truncated safetensors prefix')
            count=struct.unpack('<Q',size)[0]
            if not 2<=count<=16*1024*1024 or count>self.length-8:raise ValueError('Invalid safetensors header length')
            raw=stream.read(count)
        self.header_sha256=hashlib.sha256(raw).hexdigest();self.start=8+count
        header=json.loads(raw,object_pairs_hook=unique)
        if not isinstance(header,dict):raise ValueError('Invalid safetensors dictionary')
        self.metadata=header.pop('__metadata__',{})
        if not isinstance(self.metadata,dict) or not isinstance(self.metadata.get('config'),str):raise ValueError('Missing publisher model config')
        self.config=json.loads(self.metadata['config'],object_pairs_hook=unique)
        self.tensors={};ranges=[]
        for name,item in header.items():
            if not isinstance(name,str) or not name or len(name)>256 or not isinstance(item,dict):raise ValueError('Invalid tensor entry')
            dtype=item.get('dtype');shape=item.get('shape');offsets=item.get('data_offsets')
            if dtype not in DTYPES or not isinstance(shape,list) or not 0<=len(shape)<=5 or any(type(x)!=int or not 1<=x<=1000000 for x in shape):raise ValueError('Invalid tensor dtype/shape')
            if not isinstance(offsets,list) or len(offsets)!=2 or any(type(x)!=int for x in offsets):raise ValueError('Invalid tensor range')
            first,last=offsets
            if first<0 or last<first or last>self.length-self.start or last-first!=math.prod(shape)*DTYPES[dtype]:raise ValueError('Truncated/mismatched tensor payload')
            ranges.append((first,last));self.tensors[name]=item
        if not 1<=len(ranges)<=10000:raise ValueError('Tensor count outside budget')
        previous=0
        for first,last in sorted(ranges):
            if first!=previous:raise ValueError('Tensor ranges overlap or leave unreviewed bytes')
            previous=last
        if previous!=self.length-self.start:raise ValueError('Unexpected checkpoint trailing data')
    def array(self,name):
        item=self.tensors[name];first,last=item['data_offsets'];dtype=item['dtype']
        # Copy only this tensor; never map/copy the complete multi-GB checkpoint.
        with self.path.open('rb') as stream:
            stream.seek(self.start+first);blob=stream.read(last-first)
        if len(blob)!=last-first:raise ValueError('Checkpoint changed while reading')
        if dtype=='BF16':array=(np.frombuffer(blob,dtype='<u2').astype('<u4')<<16).view('<f4')
        else:array=np.frombuffer(blob,dtype='<f2' if dtype=='F16' else '<f4').astype('<f4')
        array=array.reshape(item['shape'])
        if not np.isfinite(array).all():raise ValueError('Non-finite trained parameter')
        return array
    def transformer(self):
        return {name[len(PREFIX):]:item for name,item in self.tensors.items() if name.startswith(PREFIX)}

def gguf_header(config,items,source_sha256):
    """Return a standard v3 header and bounded per-tensor destination plan."""
    def string(value):
        blob=value.encode('utf-8');return struct.pack('<Q',len(blob))+blob
    entries={'general.architecture':'lma-ltx-video-098','ltx098.config':json.dumps(config,separators=(',',':')),'ltx098.source_sha256':source_sha256}
    header=b'GGUF'+struct.pack('<IQQ',3,len(items),len(entries));plan=[];offset=0
    for key,value in entries.items():header+=string(key)+struct.pack('<I',8)+string(value)
    for name,item in items.items():
        shape=item['shape'];half=len(shape)==2 and name.endswith('.weight');size=math.prod(shape)*(2 if half else 4)
        header+=string(name)+struct.pack('<I',len(shape))+b''.join(struct.pack('<Q',x) for x in reversed(shape))+struct.pack('<IQ',1 if half else 0,offset)
        plan.append((name,half,size));offset+=(size+31)//32*32
    return header+b'\0'*((-len(header))%32),plan,offset

def layout_sha(items):
    return hashlib.sha256(json.dumps({k:v['shape'] for k,v in items.items()},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate_transformer(checkpoint,fixture=False):
    lock=json.loads((ROOT/'third_party/ltx098-source-lock.json').read_text(encoding='utf-8'))
    config=checkpoint.config.get('transformer');expected=lock['checkpoint_transformer_config']
    if not isinstance(config,dict):raise ValueError('Missing old transformer config')
    flexible={'num_attention_heads','attention_head_dim','cross_attention_dim','caption_channels','in_channels','out_channels','num_layers'} if fixture else set()
    for key,value in expected.items():
        if not key.startswith('_') and key not in flexible and (type(config.get(key))!=type(value) or config.get(key)!=value):raise ValueError('Unsupported exact-old transformer constant: '+key)
    for key in flexible:
        if type(config.get(key))!=int or config[key]<=0:raise ValueError('Invalid fixture dimensions')
    items=checkpoint.transformer()
    if fixture:
        width=config['num_attention_heads']*config['attention_head_dim']
        if not (config['num_attention_heads']==2 and width in [24,32] and config['cross_attention_dim']==width and config['caption_channels']==32 and config['in_channels']==config['out_channels']==8 and config['num_layers'] in [2,3,28]):raise ValueError('Unreviewed fixture architecture')
        if len(items)!=15+25*config['num_layers']:raise ValueError('Incomplete fixture transformer')
    elif len(items)!=715 or layout_sha(items)!=lock['checkpoint_transformer_layout_sha256']:raise ValueError('Transformer layout differs from exact old checkpoint')
    if not fixture and checkpoint.config.get('allowed_inference_steps')!=[1.,.9937,.9875,.9812,.975,.9094,.725,.4219]:raise ValueError('Checkpoint is not the reviewed distilled schedule')
    return config,items
