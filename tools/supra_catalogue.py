"""User-selected local SUPRA-Tex mesh/camera/RGBA material recipe."""
from expansion_catalogue import field
from export_supra import GRAPHS


def roles():return dict(config='supra-config.json',tokenizer='qwen-tokenizer.json',**{name:name+'.onnx' for name in GRAPHS})


def recipe():
    requirements=[]
    for role,name in roles().items():
        fmt='json' if name.endswith('.json') else 'onnx'
        requirements.append(dict(role=role,label=name,formats=[fmt],required=True,matchFiles=[name]))
        if fmt=='onnx':requirements.append(dict(role=role+'_data',label=name+'.data',formats=['onnx_data'],required=False,matchFiles=[name+'.data']))
    fields=dict(threads=field('integer','CPU 线程',2,1,16),seed=field('integer','补全随机种子',42,0,2147483647),steps=field('integer','材质补全步数',25,1,100),
        atlas=field('integer','UV 图集目标尺寸',1024,256,4096,multipleOf=256),maxRows=field('integer','潜变量坐标保护上限',20000,64,20000))
    return dict(id='supratex_onnx_cpu_v1',name='SUPRA-Tex · 本地 Qwen 与材质补全',primaryRole='completion',
        definition=dict(engine='spatial_ort',architecture='supratex',pipeline='supratex',backend='cpu',tasks=['3d'],
            capabilities=['reference_image','existing_mesh','camera_conditioning','qwen_pbr','material_completion','pbr_material','uv_baking'],parameters=dict(version=1,fields=fields)),
        requirements=requirements,fixedComponents=[],help='选择同批固定源码转换的九份网络、Qwen tokenizer 和配置。输入归一化 GLB、匹配相机 JSON 文本和 1024×1024 RGBA PNG。Qwen 视觉编码、双材质预测、SCVAE、交错补全及烘焙全部在手机；保留原始网格，不调用远端或 Pixal 几何推理。FP32 / 随机流与 CUDA 不同。完整权重很大，未做完整模型或手机资源验收，无已核实的公开匹配整包。')
