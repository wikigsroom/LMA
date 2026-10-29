"""Read-only structural mapping; no learned-value or model-execution claim."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];directory=Path(__file__).resolve().parent
original=json.loads((directory/'original-unet-acquisition-receipt.json').read_text())['header']['tensors']
candidate=json.loads((directory/'lcm-checkpoint-header.json').read_text())['tensors']
byname={t['name']:t for t in candidate if t['name'].startswith('model.diffusion_model.')}
direct={hf:sd for sd,hf in [
    ('time_embed.0.weight','time_embedding.linear_1.weight'),('time_embed.0.bias','time_embedding.linear_1.bias'),
    ('time_embed.2.weight','time_embedding.linear_2.weight'),('time_embed.2.bias','time_embedding.linear_2.bias'),
    ('input_blocks.0.0.weight','conv_in.weight'),('input_blocks.0.0.bias','conv_in.bias'),
    ('out.0.weight','conv_norm_out.weight'),('out.0.bias','conv_norm_out.bias'),('out.2.weight','conv_out.weight'),('out.2.bias','conv_out.bias')]}
resnets=[('norm1','in_layers.0'),('conv1','in_layers.2'),('norm2','out_layers.0'),('conv2','out_layers.3'),('time_emb_proj','emb_layers.1'),('conv_shortcut','skip_connection')]
layers=[]
for i in range(4):
    for j in range(2):
        layers.append((f'down_blocks.{i}.resnets.{j}.',f'input_blocks.{3*i+j+1}.0.'))
        if i<3:layers.append((f'down_blocks.{i}.attentions.{j}.',f'input_blocks.{3*i+j+1}.1.'))
    for j in range(3):
        layers.append((f'up_blocks.{i}.resnets.{j}.',f'output_blocks.{3*i+j}.0.'))
        layers.append((f'up_blocks.{i}.attentions.{j}.',f'output_blocks.{3*i+j}.1.'))
    if i<3:
        layers.append((f'down_blocks.{i}.downsamplers.0.conv.',f'input_blocks.{3*(i+1)}.0.op.'))
        layers.append((f'up_blocks.{i}.upsamplers.0.',f'output_blocks.{3*i+2}.{1 if i==0 else 2}.'))
layers.append(('mid_block.attentions.0.','middle_block.1.'))
for j in range(2):layers.append((f'mid_block.resnets.{j}.',f'middle_block.{2*j}.'))
mapping=[];missing=[];used=set()
for t in original:
    name=t['name']
    if name in direct:name=direct[name]
    else:
        if 'resnets' in name:
            for hf,sd in resnets:name=name.replace(hf,sd,1)
        for hf,sd in layers:name=name.replace(hf,sd,1)
    name='model.diffusion_model.'+name
    if name not in byname:missing.append(dict(original=t['name'],mapped=name));continue
    assert name not in used;used.add(name)
    c=byname[name];assert list(reversed(c['shape']))==t['shape'],(name,c['shape'],t['shape'])
    mapping.append(dict(original=t['name'],candidate=name,shape=t['shape'],original_dtype=t['dtype'],ggml_type=c['ggml_type']))
source=root/'build/native-src/sd-cpp/src/name_conversion.cpp'
result=dict(schema='lma.private-lcm-structural-mapping/1',native_mapping_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            original_tensors=len(original),candidate_unet_tensors=len(byname),mapped_tensors=len(mapping),mapping=mapping,
            missing=missing,unexpected_candidate=sorted(set(byname)-used),learned_values_compared=False,model_forward_executed=False,physical_android=False)
(directory/'lcm-tensor-mapping.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='mapping'}))
