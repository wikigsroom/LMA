"""Data-only complete SoulX recipe; no models, URLs or automatic transfers."""

FILES = {
    'language': 'language.gguf', 's3': 'reference-s3.onnx', 's3_data': 'reference-s3.onnx.data',
    'speaker': 'reference-speaker.onnx', 'speaker_data': 'reference-speaker.onnx.data',
    'flow_encoder': 'flow-encoder.onnx', 'flow_encoder_data': 'flow-encoder.onnx.data',
    'flow_estimator': 'flow-estimator.onnx', 'flow_estimator_data': 'flow-estimator.onnx.data',
    'hift_f0': 'hift-f0.onnx', 'hift_f0_data': 'hift-f0.onnx.data',
    'hift_spectrum': 'hift-spectrum.onnx', 'hift_spectrum_data': 'hift-spectrum.onnx.data',
    'hift_source': 'hift-source.f32',
}


def schema():
    def f(t, value, low, high, label, source='application_guard', presets=None, bound=None):
        result = dict(type=t, default=value, minimum=low, maximum=high, label=label, limitSource=source)
        if presets is not None: result['presets'] = presets
        if bound: result['maximumFrom'] = dict(field=bound[0], offset=bound[1])
        return result
    integer = lambda v, a, b, label, **kw: f('integer', v, a, b, label, **kw)
    number = lambda v, a, b, label, **kw: f('number', v, a, b, label, **kw)
    fields = dict(
        context=integer(4096,256,8192,'语言上下文（token；应用上限）',presets=[2048,4096,8192]),
        threads=integer(4,1,32,'CPU 线程',presets=[2,4,8]),
        maxNewTokens=integer(512,1,3000,'每段语义输出上限（每 token 40 ms；预留上下文）',source='model_and_application_guard',presets=[160,512,1500,3000],bound=('context',-64)),
        minNewTokens=integer(8,0,2999,'每段最少采样次数（RAS 可恢复原始 EOS 分数）',bound=('maxNewTokens',-1)),
        temperature=number(.6,0,3,'语言温度（0 自动关闭 RAS）',presets=[0,.6,1]),
        repetitionPenalty=number(1.25,.01,10,'语言重复惩罚',presets=[1,1.25,1.5]),
        topK=integer(100,0,262144,'Top K（0 不裁剪）',presets=[0,50,100]),
        topP=number(.9,.0001,1,'Top P',presets=[.8,.9,1]),
        useRas=dict(type='boolean',default=True,label='重复感知采样 RAS（温度 0 时关闭）',limitSource='upstream_sampling_contract'),
        rasWindow=integer(25,1,256,'RAS 窗口',presets=[15,25,50]),
        rasTau=number(.2,.0001,1,'RAS 重复比例阈值',presets=[.1,.2,.4]),
        maxHistoryTurns=integer(10,5,64,'历史重建段数阈值（预留四个参考段）',presets=[5,10,20]),
        historyTurns=integer(2,1,8,'保留的完整音频历史段数',bound=('maxHistoryTurns',-4)),
        textHistoryTurns=integer(2,0,16,'额外文字历史段数',presets=[0,2,4]),
        historyThreshold=integer(4096,128,8192,'历史重建 token 阈值',presets=[2048,4096,6192],bound=('context',0)),
        steps=integer(15,1,100,'Flow Euler 步数',source='model_and_application_guard',presets=[8,15,30]),
        cfg=number(.7,0,10,'Flow CFG',source='model_and_application_guard',presets=[0,.7,1]),
        seed=integer(-1,-1,2147483647,'随机种子（-1 本次随机）',presets=[-1,42,9183]),
        pauseMs=integer(200,0,2000,'段间静音（毫秒）',presets=[0,200,500]),
        maxOutputSeconds=integer(120,1,960,'整个任务最长音频（秒；含静音）',presets=[30,120,300]),
    )
    return dict(version=1,fields=fields)


def recipe():
    labels = dict(language='完整 SoulX-Podcast Qwen3 GGUF（内含匹配词表）',s3='S3v2 语义编码图',speaker='CAMPPlus 说话人编码图',flow_encoder='Flow 编码图',flow_estimator='Flow 估计图',hift_f0='HiFT 基频图',hift_spectrum='HiFT 频谱图',hift_source='HiFT 已训练声源合并参数（40 字节 .f32）')
    requirements = []
    for role, name in FILES.items():
        fmt = 'gguf' if role=='language' else 'bin' if role=='hift_source' else 'onnx_data' if role.endswith('_data') else 'onnx'
        label = labels.get(role, '配套外部权重：'+name)
        requirements.append(dict(role=role,label=label,formats=[fmt],required=True))
    return dict(id='soulx_podcast_cpu_v1',name='SoulX-Podcast 1.7B · 多说话人语音 / CPU',primaryRole='language',
        definition=dict(engine='soulx_native',backend='cpu',architecture='soulx_podcast_17b',pipeline='soulx_podcast_cpu_v1',tasks=['audio'],capabilities=['text_to_speech','multi_speaker','reference_transcript'],parameters=schema()),
        requirements=requirements,fixedComponents=[],
        help='完整配方共 14 份资产，由用户逐一选择 / 下载或导入；App 不含权重、词表或那份 40 字节声源参数。仅匹配 LMA SoulX ONNX 导出及完整 SoulX GGUF，不支持直接运行 flow.pt / hift.pt 或任意 Qwen GGUF。现有转换工具用于开发验证，尚无已核对的全组件公开下载条目；此配方不代表原始发布者权重可直接下载即用。S1 必选，S2–S4 从 S1 开始连续选择，每段参考 WAV 为 24 kHz 单声道 PCM16 / float32、1–15 秒，并填写实际原文。单段文字默认 S1；多段每行 [S1] 原文 至 [S4] 原文。手机 CPU 依次执行参考编码、完整语言生成、Flow / HiFT、24 kHz PCM16 保存；最多 64 段，总计最多 24000 语义 token，时长含段间静音。上下文不足明确报错，不丢弃参考原文。每段 EOS / 输出上限会分别记录；RAS 可恢复原始分数，不保证最少时长。参数按模型保存，任务固定快照；无图像 LoRA、负面提示词、外部推理或自动下载。已有真实训练模型主机链路证据，语音质量、Android 资源与后台门槛仍待验收，不能据此认定 Z20 可运行。')
