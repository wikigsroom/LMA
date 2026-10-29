"""Execute the frozen Qwen Base/codec using unchanged production C++ on Windows."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

from build_qwen_tts_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_qwen_tts_trained import verify, path_for, inputs as asset_inputs
from fetch_sd15_trained import sha
from qwen_host_capture import execute
from test_moss_nano_trained import audio_stats

ROOT = Path(__file__).resolve().parents[1]
PROMPT_A = '今天的天空很蓝，我们一起去公园散步。'
PROMPT_B = '这是一段新的本地语音，模型正在朗读不同的文字。'
LANGUAGES = [('en', 'Hello world. The sun is shining.'),
    ('ja', '今日はいい天気です。一緒に公園を散歩しましょう。'),
    ('ko', '오늘은 날씨가 좋아요. 함께 공원에서 산책해요.'),
    ('de', 'Heute scheint die Sonne. Wir gehen im Park spazieren.'),
    ('fr', 'Il fait beau. Allons nous promener dans le parc.'),
    ('ru', 'Сегодня хорошая погода. Давай погуляем в парке.'),
    ('pt', 'Hoje o dia está bonito. Vamos passear no parque.'),
    ('es', 'Hoy hace buen tiempo. Vamos a pasear por el parque.'),
    ('it', 'Oggi è una bella giornata. Andiamo al parco.')]
REFERENCE = 'docs/media/development/tts-trained-kokoro.wav'


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint('tools/test_qwen_tts_trained.py',
        'tools/qwen_host_capture.py', 'tools/test_moss_nano_trained.py', REFERENCE)}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--smoke', action='store_true'); args = parser.parse_args()
    before = inputs(); bundle = verify(); binary, compilation = build()
    acquisition_path = ROOT / 'build/qwen-tts-trained/receipt.json'
    acquisition = json.loads(acquisition_path.read_text(encoding='utf-8')); current(acquisition['input_fingerprint'])
    folder = ROOT / 'build/qwen-tts-trained-tests' / ('run-'+str(time.time_ns())+'-'+uuid.uuid4().hex[:8]); folder.mkdir(parents=True)
    def workspace(name, missing_codec=False, swapped=False):
        models = folder/name/'models'; models.mkdir(parents=True)
        for c in bundle['components']:
            if missing_codec and c['role']=='audio_codec': continue
            filename = 'qwen-talker-0.6b-base.gguf' if c['role']=='talker' else 'qwen-tokenizer-12hz.gguf'
            source = bundle['components'][1] if swapped and c['role']=='talker' else c
            os.link(path_for(source), models/filename)
        return models.parent
    root = workspace('workspace'); missing = workspace('missing-codec', missing_codec=True); swapped = workspace('swapped-talker', swapped=True)
    drive = next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()), None)
    if not drive: raise RuntimeError('No unused owned test alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    jobs = []; controls = []; failures = []; info = None
    try:
        def alias(path): return drive+'/'+path.relative_to(ROOT).as_posix()
        info, logs = execute([alias(binary), '--info'])
        for suffix, data in zip(['stdout','stderr'], logs): (folder/('info.'+suffix)).write_bytes(data)
        expected = dict(schema='lma.engine/1', engine='qwen_tts_native', revision=compilation['source_revision'],
            backend='cpu', bundled_model_data=False, generation_tested=False)
        if info['returncode'] or info['events'] != [expected] or info['protocol_errors']: raise RuntimeError('Different actual Qwen worker identity')
        def request(name, prompt=PROMPT_A, changes=None, reference=False):
            parameters = dict(threads=4,maxInputTokens=512,maxAudioTokens=375,temperature=.9,topP=1,topK=50,
                repetitionPenalty=1.05,seed=1234,language='zh')
            parameters.update(changes or {})
            value = dict(schema='lma.engine-request/1',type='speech.synthesize',pipeline='qwen3_tts_06b_base',
                input=dict(prompt=prompt),parameters=parameters,workspace=alias(root),output=alias(folder/(name+'.wav')))
            if reference: value['referenceAudio'] = alias(ROOT/REFERENCE)
            return value
        def invoke(name, value, cancel=False, error=None):
            path=folder/(name+'.json'); path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print('Execute trained Qwen production source:', name, flush=True)
            result, logs=execute([alias(binary),alias(path)],cancel=cancel)
            for suffix,data in zip(['stdout','stderr'],logs): (folder/(name+'.'+suffix)).write_bytes(data)
            result.update(name=name,parameters=value['parameters'],prompt=value['input']['prompt'],request_sha256=sha(path))
            output=folder/(name+'.wav'); result['output_exists']=output.is_file(); execution={}
            for e in result['events']:
                if e.get('event')=='execution': execution.update(e['details'])
            result['execution']=execution
            complete=[e for e in result['events'] if e.get('event')=='complete']; errors=[e for e in result['events'] if e.get('event')=='error']
            common=not result['protocol_errors'] and not any(result['logs_truncated']) and not result['timed_out']
            if cancel:
                result['passed']=common and result['forced_host_termination'] and result['returncode']!=0 and not complete and not result['output_exists']
                controls.append(result)
            elif error:
                result['expected_error']=error
                result['passed']=common and result['returncode']==1 and not complete and not result['output_exists'] and len(errors)==1 and errors[0]['message']==error
                controls.append(result)
            else:
                result['passed']=common and result['returncode']==0 and not errors and len(complete)==1 and complete[0]['output']==value['output'] and output.is_file()
                if output.is_file():
                    audio=audio_stats(output); result['audio']=audio
                    result['passed']=result['passed'] and audio['sample_rate']==24000 and audio['channels']==1 and audio['sample_width']==2 and audio['rms']>1e-5 and audio['nonzero_samples']>10
                    result['passed']=result['passed'] and execution.get('audioSamples')==audio['samples'] and execution.get('effectiveParameters')==value['parameters'] and execution.get('referenceMode')==('speaker_embedding' if 'referenceAudio' in value else 'none')
                    result['passed']=result['passed'] and 0<audio['samples']<=value['parameters']['maxAudioTokens']*1920+48000
                jobs.append(result)
            (folder/(name+'-capture.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({k:result.get(k) for k in ['name','passed','returncode','seconds','audio','execution']},ensure_ascii=False),flush=True)
            if not result['passed']: failures.append(name); raise RuntimeError('Retain failed actual trained Qwen case: '+name)
            return result
        invoke('prompt-a',request('prompt-a'))
        if not args.smoke:
            for name,mutate,error in [
                ('bad-schema',lambda r:r.update(schema='unknown'),'Unsupported speech pipeline'),
                ('empty-prompt',lambda r:r['input'].update(prompt=''),'Invalid speech input or paths'),
                ('bad-threads',lambda r:r['parameters'].update(threads=33),'CPU thread count exceeds the application guard'),
                ('bad-language',lambda r:r['parameters'].update(language='unknown'),'Unsupported Qwen speech language'),
                ('bad-seed',lambda r:r['parameters'].update(seed=-1),'Record an actual seed before execution'),
                ('bad-frame-budget',lambda r:r['parameters'].update(maxAudioTokens=1501),'Audio frame budget exceeds the application guard'),
                ('negative-prompt',lambda r:r['input'].update(negativePrompt='noise'),'Speech synthesis does not accept negative prompts'),
                ('token-budget',lambda r:r['parameters'].update(maxInputTokens=1),"Formatted speech text exceeds this model's selected input token budget"),
                ('missing-codec',lambda r:r.update(workspace=alias(missing)),'Cannot read audio codec GGUF'),
                ('swapped-talker',lambda r:r.update(workspace=alias(swapped)),'Select the exact Qwen3-TTS 0.6B Base conversion'),
                ('bad-reference',lambda r:r.update(referenceAudio=alias(folder/'bad-reference.wav')),'Reference WAV size must be 44 bytes to 4 MiB')]:
                value=request(name); mutate(value); invoke(name,value,error=error)
            invoke('prompt-b',request('prompt-b',PROMPT_B))
            for language,prompt in LANGUAGES: invoke('language-'+language,request('language-'+language,prompt,dict(language=language)))
            invoke('auto-language',request('auto-language',changes=dict(language='auto')))
            invoke('seed-change',request('seed-change',changes=dict(seed=5678)))
            invoke('greedy',request('greedy',changes=dict(temperature=0,topK=1)))
            invoke('frame-budget',request('frame-budget',changes=dict(maxAudioTokens=16)))
            invoke('reference-a',request('reference-a',reference=True))
            invoke('reference-b',request('reference-b',PROMPT_B,reference=True))
            invoke('cancel',request('cancel',PROMPT_B),cancel=True)
            invoke('recovery-a',request('recovery-a'))
    except Exception as error:
        failures.append(type(error).__name__+': '+str(error))
    finally: subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
    current(before); by_name={j['name']:j for j in jobs}
    comparisons={}
    for name in ['prompt-b','seed-change','greedy','frame-budget','reference-a','recovery-a']:
        if name in by_name and 'audio' in by_name[name] and 'audio' in by_name['prompt-a']:
            comparisons[name]=by_name[name]['audio']['sha256']==by_name['prompt-a']['audio']['sha256']
    files={p.relative_to(folder).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.rglob('*')) if p.is_file()}
    report=dict(schema='lma.qwen-tts-trained-host/1',compilation=compilation,acquisition=acquisition,acquisition_receipt_sha256=sha(acquisition_path),
        info=info,jobs=jobs,controls=controls,comparison_to_a_bitwise_identical=comparisons,files=files,capture_directory=folder.relative_to(ROOT).as_posix(),
        failures=failures,smoke_only=args.smoke,host_execution_checks_passed=not failures and not args.smoke,
        trained_production_worker_executed=bool(jobs),production_worker_source_unmodified=True,backend='cpu',fixture=False,asset_download_attempted=False,
        reference=dict(path=REFERENCE,sha256=sha(ROOT/REFERENCE),synthetic_trained_kokoro_output=True,human_identity_claimed=False),
        physical_android=False,app_executed=False,speech_quality_accepted=False,voice_similarity_accepted=False,device_resource_fit_accepted=False,
        android_background_accepted=False,complete_target11_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    filename='smoke-results.json' if args.smoke else 'results.json'
    for path in [folder/filename,folder.parent/filename]: path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(jobs=len(jobs),controls=len(controls),comparisons=comparisons,failures=failures),ensure_ascii=False),flush=True)
    if failures: raise SystemExit(1)


if __name__=='__main__': main()
