"""Data-only descriptor for the explicit old-LTX Google/community T5 variant."""
def schema():
    fields={}
    for key,label,value,low,high,presets in [
        ('width','宽度',256,64,256,[128,192,256]),('height','高度',256,64,256,[128,192,256]),
        ('frames','视频帧数',33,9,33,[9,17,25,33]),('fps','帧率',24,1,60,[8,16,24]),
        ('seed','种子（-1 自动）',-1,-1,2147483647,[-1,42]),('threads','CPU 线程',4,1,8,[2,4,8]),('steps','固定蒸馏步数',8,8,8,[8])]:
        fields[key]=dict(type='integer',label=label,default=value,minimum=low,maximum=high,presets=presets,limitSource='explicit_old_ltx_profile')
    for key in ['width','height']:fields[key]['multipleOf']=32
    fields['frames'].update(multipleOf=8,alignmentOrigin=1)
    fields['steps']['help']='此蒸馏配方固定八步；单尺度、CFG=1、STG=0，数值与画质尚未验收。'
    return dict(version=1,fields=fields)

def recipe():
    requirements=[]
    for role,label,fmt in [('diffusion_model','已在本机准备的旧 0.9.8 DiT','gguf'),('text_encoder','Google/community T5 XXL Q5_K_M','gguf'),('tokenizer_config','与 Google T5 配套的 tokenizer_config.json','json')]:
        requirements.append(dict(role=role,label=label,formats=[fmt],required=True))
    for i in range(9):
        for suffix,label,fmt in [('graph','图','onnx'),('data','权重','onnx_data')]:
            requirements.append(dict(role='vae_'+suffix+'_'+str(i),label='旧 LTX VAE 第 '+str(i+1)+' 段'+label,formats=[fmt],required=True))
    requirements.append(dict(role='vae_manifest',label='准备得到的 ltx098-vae.json',formats=['json'],required=True))
    return dict(id='ltx098_single_scale_google_q5_v1',name='旧 LTX 2B 0.9.8 · 单尺度 Google T5 Q5',primaryRole='diffusion_model',
        definition=dict(engine='ltx098_native',backend='vulkan',architecture='ltx098',pipeline='ltx098_single_scale_google_q5',tasks=['video'],
            capabilities=['text_to_video','single_scale','community_google_t5_q5','experimental_numerical_gates_open'],parameters=schema()),
        requirements=requirements,fixedComponents=[],help='推荐选择目录中的旧 LTX 源模型，显式下载 / 导入后准备 DiT 与九段 VAE，再关联运行模型并自行取得 T5 与分词配置。此表单也可逐项选择已有匹配组件。T5 CPU、DiT Vulkan、VAE CPU、手机 AVC 编码顺序执行；支持 64–256（32 倍数）、9–33 帧（8n+1）、固定八步。Google/community T5 量化单尺度变体不等于官方 PixArt / 多尺度默认；原数值门槛仍有失败，画质和 Android 尚未验收。模型与专用数据不随 App 提供；不自动下载，不接受图像 LoRA 或远端执行。')
