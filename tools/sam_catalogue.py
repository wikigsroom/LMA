"""Closed local SAM and four-view MV-SAM3D / DA3 recipes; no bundled assets."""
from expansion_catalogue import field


def graphs(multi):
    return ('ss_conditioner','slat_conditioner','structure_flow','structure_decoder','slat_flow','mesh_decoder')+(('depth_anyview','depth_metric') if multi else ('depth_moge',))


def roles(multi):return dict(config='sam-config.json',**{n:n+'.onnx' for n in graphs(multi)})


def recipe(multi):
    pipeline='mv_sam3d_da3' if multi else 'sam3d_objects';requirements=[]
    for role,name in roles(multi).items():
        fmt='json' if role=='config' else 'onnx'
        requirements.append(dict(role=role,label=name,formats=[fmt],required=True,matchFiles=[name]))
        if fmt=='onnx':requirements.append(dict(role=role+'_data',label=name+'.data',formats=['onnx_data'],required=False,matchFiles=[name+'.data']))
    fields=dict(threads=field('integer','CPU 线程',2,1,16),seed=field('integer','随机种子',42,0,2147483647),
        structureSteps=field('integer','结构采样步数',25,1,100),slatSteps=field('integer','细节采样步数',25,1,100),
        maxRows=field('integer','潜变量坐标保护上限',4096,64,4096),maxTriangles=field('integer','三角面保护上限',300000,1000,1000000))
    capabilities=['reference_image','local_depth','sparse_structure','source_flexicubes','vertex_color','pose_metadata']
    if multi:capabilities+=['multiview_conditioning','joint_da3_metric_depth','entropy_weighted_velocity_fusion']
    return dict(id=pipeline+'_onnx_cpu_v1',name='MV-SAM3D + DA3 · 四视图本地重建' if multi else 'SAM 3D Objects · 单图本地重建',primaryRole='structure_flow',
        definition=dict(engine='spatial_ort',architecture=pipeline,pipeline=pipeline,backend='cpu',tasks=['3d'],capabilities=capabilities,parameters=dict(version=1,fields=fields)),
        requirements=requirements,fixedComponents=[],help='用户导入同批固定源码转换的完整网络与配置。'+('输入正 / 右 / 后 / 左四张 RGBA 图；联合 DA3 与度量分支、结构随机状态重放、细节暖身和逐潜变量熵加权融合均在手机。' if multi else '输入单张 RGBA 图；MoGe、条件编码、MoT / SLAT 采样与原始 FlexiCubes 均在手机。')+'固定方形输入、APE / full 或 swin、FP32 与本地随机流；输出原始网格及学习到的顶点属性、姿态元数据。不包含训练高斯烘焙或上游 CUDA 减面。完整模型与真机资源未验收，内存超限本地报错，无已核实的公开匹配整包。')
