"""Closed local material recipes. No unverified remote export URLs."""
from expansion_catalogue import field


def roles(pipeline):
    assert pipeline in ('ultratex_flux1','ultratex_flux2')
    result=dict(config='ultratex-config.json',tokenizer='t5.model' if pipeline.endswith('1') else 'qwen-tokenizer.json')
    if pipeline.endswith('1'):result.update(clip_tokenizer='clip-tokenizer.json',clip='clip.onnx')
    result.update({name:name+'.onnx' for name in ('text','vae_encoder','albedo_flow','mr_flow','albedo_decoder','mr_decoder')})
    return result


def recipe(pipeline):
    one=pipeline.endswith('1')
    fields=dict(threads=field('integer','CPU 线程',2,1,16,presets=[1,2,4,8]),
        steps=field('integer','每种材质采样步数',25,1,100,presets=[8,15,25,40]),
        seed=field('integer','随机种子',0,0,2147483647),guidance=field('number','材质引导强度',4 if one else 3.5,0,15),
        atlas=field('integer','UV 图集目标尺寸',1024,256,4096,multipleOf=256,presets=[512,1024,2048]))
    if not one:fields['dropBackground']=field('boolean','省略背景 token',False)
    definition=dict(engine='spatial_ort',architecture=pipeline,pipeline=pipeline,backend='cpu',tasks=['3d'],
        capabilities=['mesh_texturing','text_conditioning','image_conditioning','pbr_material','uv_baking'],parameters=dict(version=1,fields=fields))
    files=roles(pipeline);req=[]
    for role,name in files.items():
        fmt='sentencepiece' if name.endswith('.model') else 'json' if name.endswith('.json') else 'onnx'
        req.append(dict(role=role,label=role+' · '+name,formats=[fmt],required=True,matchFiles=[name]))
        if fmt=='onnx':req.append(dict(role=role+'_data',label=name+'.data',formats=['onnx_data'],required=False,matchFiles=[name+'.data']))
    return dict(id=pipeline+'_onnx_cpu_v1',name='UltraTex · '+('FLUX.1 dev' if one else 'FLUX.2 / Klein')+' · 本地 PBR',
        primaryRole='albedo_flow',definition=definition,requirements=req,fixedComponents=[],
        help='选择同批固定源码转换的文本、VAE、albedo / MR 网络和分词资产，再选择参考 PNG 与 GLB；输入材质描述。全部在手机 CPU，逐图释放。便携六视图相机、FP32 采样 / 随机流、UV 和填缝与训练环境有差异；未做完整模型或真机验收，无已核实公开整包。')


def recipes():return [recipe(p) for p in ('ultratex_flux1','ultratex_flux2')]
