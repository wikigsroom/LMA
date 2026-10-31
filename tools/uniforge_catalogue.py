"""Closed UniForge four-view CPU recipe; models remain user-selected."""
from expansion_catalogue import field

GRAPHS=('dino512','dino1024','structure_flow','structure_decoder','conditioner',
        'shape512_adapter','shape1024_adapter','texture_adapter',
        'shape512_flow','shape1024_flow','texture_flow','shape512_decoder','shape1024_decoder','texture_decoder')


def roles():return dict(config='uniforge-config.json',**{n:n+'.onnx' for n in GRAPHS})


def recipe():
    fields=dict(threads=field('integer','CPU 线程',2,1,16),seed=field('integer','随机种子',42,0,2147483647),
        structureSteps=field('integer','结构采样步数',12,1,100),shapeSteps=field('integer','每阶段形状采样步数',20,1,100),
        textureSteps=field('integer','材质采样步数',20,1,100),maxRows=field('integer','潜变量坐标保护上限',16384,64,20000),
        maxTriangles=field('integer','三角面保护上限',300000,1000,300000),atlas=field('integer','UV 图集目标尺寸',1024,256,4096,multipleOf=256))
    requirements=[]
    for role,name in roles().items():
        fmt='json' if role=='config' else 'onnx'
        requirements.append(dict(role=role,label=name,formats=[fmt],required=True,matchFiles=[name]))
        if fmt=='onnx':requirements.append(dict(role=role+'_data',label=name+'.data',formats=['onnx_data'],required=False,matchFiles=[name+'.data']))
    return dict(id='uniforge3d_onnx_cpu_v1',name='UniForge3D · 四视图形状与 PBR',primaryRole='structure_flow',
        definition=dict(engine='spatial_ort',architecture='uniforge3d',pipeline='uniforge3d',backend='cpu',tasks=['3d'],
            capabilities=['multiview_conditioning','sparse_structure','shape_cascade','pbr_material','uv_baking'],parameters=dict(version=1,fields=fields)),
        requirements=requirements,fixedComponents=[],
        help='选择同批固定源码转换的 14 份网络和配置，输入正 / 右 / 后 / 左四张已去背景 RGBA PNG。手机依次完成结构、512 / 1024 形状、材质和 PBR GLB；无外部推理。保留原始 FDG 网格与 SAT 形状交接，未复制 CUDA 重网格、补洞和减面；超限报错。完整权重非常大，不代表努比亚 Z20 能容纳。未做完整模型或真机验收，无已核实公开整包。')
