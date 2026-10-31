"""Build optional pinned speech / 3D bundles from reviewed metadata, never weights."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'research/expansion/sources.json'


def field(kind, label, default, low=None, high=None, **extra):
    value = dict(type=kind, label=label, default=default, **extra)
    if low is not None: value.update(minimum=low, maximum=high, limitSource='application_guard')
    return value


def parameters(pipeline, texture=False, high=False):
    f = dict(threads=field('integer','CPU 线程',2,1,16,presets=[1,2,4,8]))
    if pipeline in ('trellis2','pixal3d'):
        f.update(resolution=field('integer','3D 生成分辨率',1024 if high else 512,512,1024,multipleOf=512,presets=[512,1024]),
            steps=field('integer','每阶段采样步数',12,1,50,presets=[4,8,12,20]),
            seed=field('integer','随机种子',1234,0,2147483647),
            faces=field('integer','输出网格面数目标',30000,1000,150000,presets=[10000,30000,60000]),
            atlas=field('integer','贴图图集尺寸',1024,256,2048,multipleOf=256,presets=[512,1024,2048]),
            guidance=field('number','引导强度',7.5,0,15), fov=field('number','相机水平视角（Pixal3D）',49.13,10,120),
            texture=field('boolean','生成贴图',texture))
    elif pipeline == 'melo_zh':
        f.update(speaker=field('integer','音色 ID',0,0,0),speed=field('number','语速',1,.25,3,presets=[.75,1,1.25]),
            silenceScale=field('number','句间停顿比例',1,0,3),maxAudioSeconds=field('integer','输出时长保护上限（秒）',180,1,600),
            noiseScale=field('number','音色变化',.667,0,2),noiseScaleW=field('number','时长变化',.8,0,2))
    else:
        f.update(steps=field('integer','采样步数',32,1,64,presets=[8,16,32]), speed=field('number','语速',1,.5,2),
            cfg=field('number','引导强度',2,0,10),seed=field('integer','随机种子',1234,0,2147483647),
            maxAudioSeconds=field('integer','输出时长保护上限（秒）',30,1,120))
        if pipeline=='f5_v1':
            f.update(frameBudget=field('integer','单块 mel 帧预算',2048,512,4096,presets=[512,1024,2048]),sway=field('number','Sway 系数',-1,-5,5))
        else:
            f.update(durationSeconds=field('number','目标时长（秒）',4,1,30,maximumFrom={'field':'maxAudioSeconds'}),
                language=field('string','语言（auto 自动）','auto',maxLength=80),
                voiceMode=field('enum','音色模式','auto',values=['auto','clone','design']),
                voiceInstruction=field('string','音色描述','',maxLength=1000))
    return dict(version=1,fields=f)


def build():
    source=json.loads(SOURCE.read_text(encoding='utf-8')); repositories=source['repositories']; bundles=[]; proofs=[]
    def component(repo,path,role,format):
        record=repositories[repo]; item=next(f for f in record['files'] if f['path']==path)
        return dict(item,role=role,format=format,repository=repo,revision=record['revision'],
            url='https://huggingface.co/'+repo+'/resolve/'+record['revision']+'/'+path)
    def add(id,name,engine,architecture,pipeline,components,description,license,**options):
        task='3d' if engine=='trellis_native' else 'audio'
        b=dict(schema='lma.model-bundle/2',id=id,modelId=id,recipeId=pipeline+'_cpu_v1',name=name,description=description,
            catalogue=True,engine=engine,architecture=architecture,pipeline=pipeline,backend='cpu',tasks=[task],
            capabilities=['image_to_3d'] if task=='3d' else ['text_to_speech'],
            parameters=parameters(pipeline,**options),components=components,
            resources=dict(source='unmeasured',estimatedPeakRamBytes=0),
            content=dict(classification='unclassified',basis='none',summary='未获得明确内容声明；不推定为 NSFW 或无审查。'),
            license=dict(name=license,url='https://huggingface.co/'+('vegax87/Pixal3D' if pipeline=='pixal3d' else components[0]['repository']),status='component_terms_apply'),
            evidence=dict(status='compiled_program_only_not_model_or_device_tested',physicalDeviceTests=0,modelInferenceTested=False,
                sourceUrl='https://github.com/pwilkin/trellis.cpp' if task=='3d' else 'https://github.com/k2-fsa/sherpa-onnx' if engine=='sherpa_tts' else 'https://github.com/0xShug0/audio.cpp'))
        bundles.append(b)
        proofs.append(dict(bundleId=id,components=[dict(c,kind='hf_lfs' if c.get('sha256') and c['url'].startswith('https://huggingface.co/') else 'hf_git_blob' if c.get('gitBlobSha1') else 'pinned_pronunciation_dictionary') for c in components]))
    melo='csukuangfj/vits-melo-tts-zh_en'
    for quant,file in [('int8','model.int8.onnx'),('fp32','model.onnx')]:
        components=[component(melo,p,r,f) for p,r,f in [(file,'model','onnx'),('tokens.txt','tokens','text'),('lexicon.txt','lexicon','text'),
            ('date.fst','rule_fst','fst'),('number.fst','rule_fst_2','fst'),('phone.fst','rule_fst_3','fst'),('new_heteronym.fst','rule_fst_4','fst')]]
        add('melo_zh_'+quant+'_a0d5c6a','MeloTTS Chinese · '+quant.upper(),'sherpa_tts','melo_vits','melo_zh',components,
            '匹配中文 / 英文 ONNX 导出、带声调词典与文字规范化规则；单音色。当前运行库以最长词匹配读取词典，无需旧版 Jieba 目录。未验证手机音质或性能。','MIT; dictionary/rule terms apply')
    f5='SWivid/F5-TTS'; components=[component(f5,'F5TTS_v1_Base/model_1250000.safetensors','model','safetensors'),
        component('charactr/vocos-mel-24khz','pytorch_model.bin','vocoder','bin'),component(f5,'F5TTS_v1_Base/vocab.txt','vocab','text')]
    for index,item in enumerate(source['pronunciationDictionaries']):
        components.append(dict(item,role='pinyin_chars' if index==0 else 'pinyin_phrases',format='text'))
    add('f5_tts_v1_base_84e5a41','F5-TTS v1 Base · 中英文参考音色','audio_cpp','f5_tts_v1','f5_v1',components,
        '原版 v1 safetensors + Vocos；选择 24 kHz 单声道 1–12 秒参考 WAV 及准确转写。原生拼音最长词匹配不等于 Python 前端逐字节复现，音质待验证。','F5 code MIT; weights CC-BY-NC-4.0; Vocos MIT; pronunciation MIT')
    omni='k2-fsa/OmniVoice'
    add('omnivoice_q8_874fcb4','OmniVoice · Q8 GGUF','audio_cpp','omnivoice','omnivoice',
        [component('audio-cpp/audio.cpp-gguf','OmniVoice-GGUF/omnivoice-q8_0.gguf','model','gguf')],
        '同机 CPU 多语言语音；GGUF 集成模型、codec 与分词资源。支持文本、参考音色、音色描述模式；输出完整 WAV，不宣称逐块流式。上游 600+ 语言未逐项验证。','CC-BY-NC-4.0; source code Apache-2.0; codec terms apply')
    add('omnivoice_original_c5fdb5c','OmniVoice · 原版 safetensors','audio_cpp','omnivoice','omnivoice',
        [component(omni,p,r,f) for p,r,f in [('model.safetensors','model','safetensors'),('config.json','config','json'),('tokenizer.json','text_tokenizer','json'),
         ('tokenizer_config.json','tokenizer_config','json'),('audio_tokenizer/config.json','codec_config','json'),
         ('audio_tokenizer/preprocessor_config.json','codec_preprocessor','json'),('audio_tokenizer/model.safetensors','audio_codec','safetensors')]],
        '原版模型与配套 codec / 分词文件均由用户选择下载。CPU 原生执行，权重较大，内存与音质未测；不安装 Python。','CC-BY-NC-4.0; source code Apache-2.0; codec terms apply')
    tre='ilintar/trellis2-gguf'; pix='vegax87/Pixal3D'
    shared=[component(tre,'q4/'+p+'.gguf',r,'gguf') for p,r in [('dinov3','image_encoder'),('ss_dec','ss_decoder'),('shape_dec','shape_decoder')]]
    for pipeline,repo,prefix in [('trellis2',tre,''),('pixal3d',pix,'pixal3d_')]:
        for mode,texture,high in [('geometry512',False,False),('pbr1024',True,True)]+([('pbr512',True,False)] if pipeline=='trellis2' else []):
            def part(name,role): return component(repo,('q4/' if pipeline=='trellis2' else '')+prefix+name+'.gguf',role,'gguf')
            components=copy.deepcopy(shared)+[part('ss_flow','ss_flow'),part('shape_flow_512','shape_flow')]
            if pipeline=='pixal3d': components.append(part('naf','naf'))
            if high: components.append(part('shape_flow_1024','shape_flow_hr'))
            if texture:
                components += [part('tex_flow_1024' if high else 'tex_flow_512','texture_flow_hr' if high else 'texture_flow'),component(tre,'q4/tex_dec.gguf','texture_decoder','gguf')]
            add(pipeline+'_'+mode+'_cpu_v1',('TRELLIS.2' if pipeline=='trellis2' else 'Pixal3D')+' · '+mode,
                'trellis_native',pipeline,pipeline,components,
                '实验性单图 → GLB；同机 CPU 完成编码、采样、网格与可选 PBR。无多视图、MoGe 自动相机、重拓扑插件。512 / 1024 为生成阶段分辨率；图集上限 2048。权重体积不代表运行内存，未证明 Z20 可完成。',
                'Upstream model licenses and GGUF conversion terms apply; see source repositories',texture=texture,high=high)
    # A new optional quantization complements the immutable existing Kokoro bundle.
    kokoro=copy.deepcopy(next(b for b in json.loads((ROOT/'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles'] if b['pipeline']=='kokoro'))
    k='csukuangfj/kokoro-int8-multi-lang-v1_0'; kokoro.update(schema='lma.model-bundle/2',id='kokoro82_int8_57adb37',modelId='kokoro82_v1_int8',name='Kokoro 82M · INT8 English',
        description='Kokoro PyTorch 架构的匹配 ONNX INT8 导出；不直接执行原版 .pth。沿用英语词典路线，不宣称支持所有原版语言。',
        components=[component(k,'model.int8.onnx','model','onnx')]+copy.deepcopy(kokoro['components'][1:]))
    bundles.append(kokoro)
    oldproof=next(b for b in json.loads((ROOT/'catalogue/bundle-evidence.json').read_text(encoding='utf-8'))['bundles'] if b['bundleId'].startswith('kokoro'))
    proofs.append(dict(bundleId=kokoro['id'],components=[dict(kokoro['components'][0],kind='hf_lfs')]+copy.deepcopy(oldproof['components'][1:])))
    return bundles,proofs


def recipes():
    bundles,_=build(); result=[]
    for pipeline,model_format in [('melo_zh','onnx'),('f5_v1','safetensors'),('omnivoice','gguf'),('omnivoice','safetensors'),('trellis2','gguf'),('pixal3d','gguf')]:
        b=copy.deepcopy(next(b for b in bundles if b['pipeline']==pipeline and b['components'][0]['format']==model_format))
        if pipeline in ('trellis2','pixal3d'): b=copy.deepcopy(next(b for b in bundles if b['pipeline']==pipeline and 'pbr1024' in b['id']))
        definition={k:b[k] for k in ('engine','architecture','pipeline','backend','tasks','capabilities','parameters')}
        req=[dict(role=c['role'],label=c['role']+' · '+Path(c['path']).name,formats=[c['format']],required=True,matchFiles=[Path(c['path']).name]) for c in b['components']]
        if pipeline in ('trellis2','pixal3d'):
            for item in req:
                if item['role'] in ('shape_flow_hr','texture_flow_hr','texture_decoder'): item['required']=False
            definition['parameters']=parameters(pipeline,texture=False)
        result.append(dict(id=pipeline+'_'+model_format+'_cpu_expansion_v1',name=b['name'].split(' · ')[0]+' · 自选配套组件',primaryRole='image_encoder' if pipeline in ('trellis2','pixal3d') else 'model',
            definition=definition,requirements=req,fixedComponents=[],help=b['description']))
        if pipeline=='f5_v1':
            official=copy.deepcopy(result[-1])
            official.update(id='f5_v1_official_frontend_cpu_v1',name='F5-TTS v1 · 官方兼容中文前端',
                help='明确选择原版 F5 v1、Vocos、vocab.txt 与独立 f5-frontend.json。词典由 export_f5_frontend.py 按固定版本生成；手机端执行 DAG/HMM、多音字与变调，不调用 Python 或网络。旧版字典配方继续保留。')
            official['requirements']=[r for r in official['requirements'] if r['role'] not in ('pinyin_chars','pinyin_phrases')]
            official['requirements'].append(dict(role='frontend',label='官方兼容分词 / 拼音词典',formats=['json'],required=True,matchFiles=['f5-frontend.json']))
            result.append(official)
    return result


def main():
    bundles,proofs=build()
    for name,value in [('expansion-bundles.json',dict(schema='lma.bundle-catalogue/1',bundles=bundles)),
        ('expansion-bundle-evidence.json',dict(schema='lma.bundle-metadata-evidence/2',model_inference_tested=False,model_weights_downloaded=False,physical_device_tests=0,bundles=proofs))]:
        (ROOT/'catalogue'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(bundles=len(bundles),recipes=len(recipes()),model_weights_downloaded=False)))

if __name__=='__main__': main()
