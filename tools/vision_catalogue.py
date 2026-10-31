"""Model choices for local image preparation; no weights in foundation updates."""
from expansion_catalogue import field


def definition(pipeline):
    fields=dict(threads=field('integer','CPU 线程',2,1,16))
    if pipeline=='vlm_parts':
        fields.update(context=field('integer','视觉模型上下文',4096,512,16384),maxTokens=field('integer','部件识别输出上限',512,32,2048),imageTokens=field('integer','图像 token 上限',1024,64,4096))
        for key in ('maxTokens','imageTokens'):fields[key]['maximumFrom']=dict(field='context',offset=-1)
    return dict(engine='vision_cpu',architecture='isnet_dis' if pipeline=='isnet_dis' else 'mtmd_vlm',pipeline=pipeline,backend='cpu',tasks=['image' if pipeline=='isnet_dis' else 'text'],
                capabilities=['image_segmentation','foreground_preparation'] if pipeline=='isnet_dis' else ['image_understanding','part_identification'],parameters=dict(version=1,fields=fields))


def recipes():
    return [dict(id='isnet_dis_onnx_cpu_v1',name='DIS · 本地自动前景',primaryRole='foreground',definition=definition('isnet_dis'),
                 requirements=[dict(role='config',label='vision-config.json',formats=['json'],required=True,matchFiles=['vision-config.json']),dict(role='foreground',label='配套 foreground.onnx',formats=['onnx'],required=True,matchFiles=['foreground.onnx']),dict(role='foreground_data',label='foreground.onnx.data（如有）',formats=['onnx_data'],required=False,matchFiles=['foreground.onnx.data'])],fixedComponents=[],
                 help='用户选择原版 DIS 对应的本地导出资产，手机 CPU 预测 alpha 并导出 RGBA PNG；支持作为 3D 图片准备步骤。没有预装权重，没有网络推理。'),
            dict(id='vlm_parts_gguf_cpu_v1',name='视觉模型 · 本地部件识别',primaryRole='model',definition=definition('vlm_parts'),
                 requirements=[dict(role='model',label='支持 mtmd 的视觉语言 GGUF 主模型',formats=['gguf'],required=True),dict(role='mmproj',label='同一模型配套视觉投影 GGUF',formats=['gguf'],required=True)],fixedComponents=[],
                 help='用户明确选择支持 llama.cpp mtmd 的 GGUF 视觉语言模型及匹配 mmproj，例如匹配的 Qwen2/3-VL 导出。手机本地分词、图片编码和 JSON 约束生成，输出 1–16 个部件名称；可用于 PartCrafter 部件数。原版 safetensors 不能直接执行，不提供远端方案。')]
