"""Equal-peer, user-selected point-cloud reconstruction assets."""
from expansion_catalogue import field
from surface_catalogue import fields as surface_fields


def parameters():
    return dict(version=1,fields=dict(**surface_fields(),threads=field('integer','CPU 线程',2,1,16),
        seed=field('integer','随机种子',1234,0,2147483647),tokens=field('integer','VAE 查询 token',2048,512,4096,multipleOf=512),
        posterior=dict(type='enum',label='VAE 重建方式',default='mean',values=['mean','sample']),
        grid=field('integer','SDF 网格格数',64,32,256,multipleOf=16),queryChunk=field('integer','SDF 分块点数',512,128,4096),
        maxTriangles=field('integer','三角面保护上限',300000,1000,1000000)))


def definition(pipeline):
    return dict(engine='rf_shape_ort',backend='cpu',architecture='triposg' if pipeline=='triposg_points' else 'partcrafter',
                pipeline=pipeline,tasks=['3d'],capabilities=['pointcloud_to_3d','vae_reconstruction','sdf_geometry'],parameters=parameters())


def recipes():
    result=[]
    for base in ['triposg','partcrafter']:
        roles=[dict(role='config',label='配套点云配置',formats=['json'],required=True,matchFiles=['shape-config.json'])]
        for role in ['encoder','cache','query']:
            roles.append(dict(role=role,label=role+'.onnx',formats=['onnx'],required=True,matchFiles=[role+'.onnx']))
            roles.append(dict(role=role+'_data',label=role+'.onnx.data（如有）',formats=['onnx_data'],required=False,matchFiles=[role+'.onnx.data']))
        result.append(dict(id=base+'_points_onnx_cpu_v1',name=base+' · 点云 VAE 重建',primaryRole='encoder',definition=definition(base+'_points'),
            requirements=roles,fixedComponents=[],help='选择本地配套 VAE 导出，输入 xyz＋法线 JSON 文本。坐标须已按发布者约定归一化；支持后验均值或采样，不是图片扩散。CPU FPS；初始四倍采样随机流与 NumPy 不同。无网络执行，不下载任何模型。'))
    return result
