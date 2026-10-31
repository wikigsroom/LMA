"""Optional, equal-peer shape recipes. No guessed download URLs or weights."""
from expansion_catalogue import field

def parameters(pipeline):
    parts=pipeline!='triposg'
    return dict(version=1,fields=dict(threads=field('integer','CPU 线程',2,1,16,presets=[1,2,4,8]),
        steps=field('integer','形状采样步数',30,1,100,presets=[10,20,30,50]),seed=field('integer','随机种子',1234,0,2147483647),
        tokens=field('integer','每部件潜变量 token',2048 if pipeline in ['triposg','partcrafter_scene'] else 1024,512,4096,multipleOf=512,presets=[512,1024,2048,4096]),
        parts=field('integer','部件数量',3 if parts else 1,1,16 if parts else 1,presets=[1,2,3,4,8] if parts else [1]),
        grid=field('integer','SDF 网格单轴格数',64,32,256,multipleOf=16,presets=[32,64,96,128]),
        queryChunk=field('integer','SDF 分块查询点数',512,128,4096,presets=[256,512,1024,2048]),
        guidance=field('number','图像引导强度',7,0,15),maxTriangles=field('integer','全部部件三角面保护上限',300000,1000,1000000,presets=[100000,300000,600000])))

def definition(pipeline):
    return dict(engine='rf_shape_ort',architecture='triposg' if pipeline=='triposg' else 'partcrafter',pipeline=pipeline,backend='cpu',tasks=['3d'],
        capabilities=['image_to_3d','sdf_geometry']+(['part_level_geometry'] if pipeline!='triposg' else []),parameters=parameters(pipeline))

def recipes():
    result=[]
    for pipeline,label in [('triposg','TripoSG'),('partcrafter','PartCrafter · 物体部件'),('partcrafter_scene','PartCrafter · 场景部件')]:
        requirements=[dict(role='config',label='配套 shape-config.json',formats=['json'],required=True,matchFiles=['shape-config.json'])]
        for role in ['image_encoder','flow','cache','query']:
            requirements.append(dict(role=role,label=role+'.onnx',formats=['onnx'],required=True,matchFiles=[role+'.onnx']))
            requirements.append(dict(role=role+'_data',label=role+'.onnx.data（如导出包含）',formats=['onnx_data'],required=False,matchFiles=[role+'.onnx.data']))
        result.append(dict(id=pipeline+'_onnx_cpu_v1',name=label+' · 配套 FP32 ONNX',primaryRole='flow',definition=definition(pipeline),requirements=requirements,fixedComponents=[],
            help='需要 LMA 离线转换工具生成的同一组 FP32 ONNX 图、外置 data 与 shape-config.json；原版 safetensors 不能直接运行。当前没有已核实的公开配套下载包，支持导入转换结果或从 HF 明确选择同格式文件。选择已去背景 / 白底 PNG；无自动抠图、贴图、外部 VLM 或云服务。全部手机 CPU，内存、速度与质量未测。'))
    return result
