"""Optional, equal-peer local material recipe; no fabricated weight URLs."""
from expansion_catalogue import field
PIPELINE='hunyuan3d_21_paint'
ROLES={'config':'material-config.json','sampler':'sampler.json',**{name:name+'.onnx' for name in ('image_encoder','vae_encoder','flow','vae_decoder','upscale')}}


def definition():
    return dict(engine='spatial_ort',architecture='hunyuan3d_21_paint',pipeline=PIPELINE,backend='cpu',tasks=['3d'],
        capabilities=['mesh_texturing','image_conditioning','multi_view_material','pbr_material','uv_baking'],
        parameters=dict(version=1,fields=dict(threads=field('integer','CPU 线程',2,1,16,presets=[1,2,4,8]),
            steps=field('integer','贴图采样步数',15,1,100,presets=[8,15,30]),seed=field('integer','随机种子',0,0,2147483647),
            guidance=field('number','参考图引导强度',3,1,15),atlas=field('integer','UV 图集目标尺寸',1024,256,4096,multipleOf=256,presets=[512,1024,2048]),
            upscale=field('boolean','使用配套本地 RealESRGAN 4× 图',True))))


def recipes():
    req=[dict(role=k,label=k+' · '+v,formats=['json' if k in ('config','sampler') else 'onnx'],required=True,matchFiles=[v]) for k,v in ROLES.items()]
    req += [dict(role=k+'_data',label=v+'.data',formats=['onnx_data'],required=False,matchFiles=[v+'.data']) for k,v in ROLES.items() if v.endswith('.onnx')]
    return [dict(id=PIPELINE+'_onnx_cpu_v1',name='Hunyuan3D 2.1 Paint · 本地 PBR 贴图',primaryRole='flow',definition=definition(),requirements=req,fixedComponents=[],
        help='选择同批离线转换的配置、UniPC 程序及五个 ONNX 图；选择参考 PNG 和待贴图 GLB。全部编码、采样、RealESRGAN、UV 和烘焙在手机 CPU。固定六视图、双材质；CPU 光栅和接缝填充存在数值差异。无已核实公开配套整包；不含模型或远程服务，真机与完整模型未测。')]
