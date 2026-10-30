"""Run the complete pinned MOSS-TTS 1.5 pair through production native code.

Native Windows evidence only. No downloads, services, virtual machines or mock
speech. Preserve failed cases and original output bytes; never a quality verdict.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import copy
import shutil

from build_openmoss_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_openmoss_trained import verify, assets, asset_path, inputs as asset_inputs
from fetch_sd15_trained import sha
from openmoss_host_capture import execute
from test_moss_nano_trained import audio_stats
from test_openmoss_mapping import run as mapping_contract, inputs as mapping_inputs

ROOT = Path(__file__).resolve().parents[1]
REFERENCE='docs/media/development/tts-trained-kokoro.wav'


def inputs():
    return {**build_inputs(), **asset_inputs(), **mapping_inputs(), **fingerprint('tools/test_openmoss_trained.py',
        'tools/openmoss_host_capture.py','tools/test_moss_nano_trained.py',
        'research/openmoss_trained/catalogue-bundle.json','verification/research/openmoss-memory','verification/research/openmoss-reference-issue',REFERENCE)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--resume-report',type=Path,help='Reuse original captures only when native build, assets and exact request still match')
    args=parser.parse_args();before=inputs();mapping=mapping_contract()
    if args.resume_report:
        args.resume_report=args.resume_report.resolve()
        bundle=assets()
        for c in bundle['components']:
            p=asset_path(c)
            if not p.is_file() or p.stat().st_size!=c['bytes']:raise ValueError('Original verified component is missing or resized')
    else:bundle=verify()
    binary,compilation=build()
    baseline=json.loads((ROOT/'verification/research/openmoss-memory/baseline.json').read_text(encoding='utf-8'))
    resumed=None;previous={};reused=[]
    if args.resume_report:
        args.resume_report.resolve().relative_to(ROOT.resolve())
        resumed=json.loads(args.resume_report.read_text(encoding='utf-8'))
        current(resumed['compilation']['input_fingerprint']);current(resumed['acquisition']['input_fingerprint'])
        if resumed['compilation']['sha256']!=compilation['sha256'] or resumed['acquisition_receipt_sha256']!=sha(ROOT/'build/openmoss-trained/receipt.json'):
            raise ValueError('Cannot reuse captures from different native code or weights')
        previous={j['name']:j for j in resumed['jobs']+resumed['controls']}
    receipt_path=ROOT/'build/openmoss-trained/receipt.json'
    acquisition=json.loads(receipt_path.read_text(encoding='utf-8'));current(acquisition['input_fingerprint'])
    folder=ROOT/'build/openmoss-trained-tests'/('run-'+str(time.time_ns()));folder.mkdir(parents=True)
    models=folder/'workspace/models';models.mkdir(parents=True)
    for c in bundle['components']:
        os.link(asset_path(c),models/('model.gguf' if c['role']=='model' else 'model.extras.gguf'))
    missing=folder/'missing/models';missing.mkdir(parents=True)
    os.link(asset_path(bundle['components'][0]),missing/'model.gguf')
    drive=next((c+':' for c in 'UVWXYZT' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No unused owned test alias')
    subprocess.run(['subst',drive,str(ROOT)],capture_output=True,check=True)
    jobs=[];controls=[];failures=[];info=None
    try:
        def alias(p):return drive+'/'+p.relative_to(ROOT).as_posix()
        info,logs=execute([alias(binary),'--info'])
        for suffix,data in zip(['stdout','stderr'],logs):(folder/('info.'+suffix)).write_bytes(data)
        expected=dict(schema='lma.engine/1',engine='openmoss_native',revision=compilation['source_revision'],backend='cpu',bundled_model_data=False,generation_tested=False)
        if info['returncode'] or info['events'] != [expected] or info['protocol_errors']:raise RuntimeError('Different actual MOSS worker identity')
        def request(name,prompt='Hello world.',changes=None):
            parameters=dict(threads=4,seed=1234,maxInputTokens=1024,maxNewTokens=375,
                textTemperature=1,audioTemperature=1.7,audioTopP=.8,audioTopK=25,
                audioRepetitionPenalty=1,voiceInstruction='',language='English')
            parameters.update(changes or {})
            return dict(schema='lma.engine-request/1',type='speech.synthesize',pipeline='moss_tts_v15_openmoss_cpu_v1',
                input=dict(prompt=prompt),parameters=parameters,workspace=alias(models.parent),output=alias(folder/(name+'.wav')))
        def invoke(name,value,cancel=False,error=None,truncated=False):
            path=folder/(name+'.json');path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            if name in previous:
                original=ROOT/resumed['capture_directory'];old=json.loads((original/path.name).read_text(encoding='utf-8'))
                def comparable(r):
                    r=copy.deepcopy(r)
                    for key in ['workspace','output']:r.pop(key,None)
                    for key in ['referenceAudio','referenceAudios']:
                        if key in r:
                            values=r[key] if isinstance(r[key],list) else [r[key]]
                            r[key]=[v.replace('\\','/').split(':/',1)[-1] for v in values]
                    return r
                if comparable(old)!=comparable(value):raise ValueError('Changed request cannot reuse original case: '+name)
                for suffix in ['.json','.stdout','.stderr','.wav','-capture.json']:
                    name_in_capture=name+suffix;p=original/name_in_capture
                    if not p.exists():continue
                    proof=resumed['files'][name_in_capture]
                    if p.stat().st_size!=proof['bytes'] or sha(p)!=proof['sha256']:raise ValueError('Original capture changed: '+name)
                    if suffix!='-capture.json':shutil.copy2(p,folder/p.name)
                result=copy.deepcopy(previous[name]);value=old;reused.append(name)
                result['capture_origin']=dict(report=args.resume_report.relative_to(ROOT).as_posix(),report_sha256=sha(args.resume_report),
                    original_capture_directory=resumed['capture_directory'],original_capture_sha256=sha(original/(name+'-capture.json')),
                    reexecuted=False,native_build_and_exact_request_unchanged=True)
                print('Recheck unchanged original trained capture:',name,flush=True)
            else:
                print('Execute complete trained MOSS production source:',name,flush=True)
                with (folder/(name+'-events.jsonl')).open('x',encoding='utf-8') as journal:
                    def record_event(event):
                        journal.write(json.dumps(event,ensure_ascii=False)+'\n');journal.flush()
                    result,logs=execute([alias(binary),alias(path)],cancel=cancel,timeout=1800,on_event=record_event)
                for suffix,data in zip(['stdout','stderr'],logs):(folder/(name+'.'+suffix)).write_bytes(data)
                result['capture_origin']=dict(reexecuted=True,native_build_and_exact_request_unchanged=True)
            result.update(name=name,request_sha256=sha(path),parameters=value['parameters'],prompt=value['input']['prompt'])
            output=folder/(name+'.wav');result['output_exists']=output.is_file()
            details={}
            for e in result['events']:
                if e.get('event')=='execution':details.update(e['details'])
            result['execution']=details
            complete=[e for e in result['events'] if e.get('event')=='complete']
            errors=[e for e in result['events'] if e.get('event')=='error']
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
                progress=[e['step'] for e in result['events'] if e.get('event')=='progress' and e.get('stage')=='generating_speech']
                result['sampled_progress']=progress
                if output.is_file():
                    a=audio_stats(output);result['audio']=a
                    result['passed']=result['passed'] and a['sample_rate']==24000 and a['channels']==1 and a['sample_width']==2 and a['rms']>1e-5 and a['nonzero_samples']>10
                    result['passed']=result['passed'] and 0<a['seconds']<=120 and details.get('sampleRate')==24000 and details.get('channels')==1
                    result['passed']=result['passed'] and details.get('auxWeightStorage')=='private_file_mapping' and details.get('auxWeightMappingsReleased') is True
                    result['passed']=result['passed'] and details.get('auxMappedFiles')==2 and details.get('auxMappedTensors',0)>1000 and details.get('mappedBytesAreResidentMemory') is False
                    if name in baseline['cases']:
                        result['pre_mapping_pcm_bitwise_identical']=a['sha256']==baseline['cases'][name]['audio']['sha256']
                        # Keep the original comparison visible. Correcting official
                        # prompt/state semantics deliberately changes sampled input
                        # rows, so old PCM identity is no longer an acceptance gate.
                        if not compilation.get('official_delay_flush_and_extraction'):
                            result['passed']=result['passed'] and result['pre_mapping_pcm_bitwise_identical']
                        result['prior_pcm_identity_required']=not compilation.get('official_delay_flush_and_extraction',False)
                    steps=details.get('generationSteps',0)
                    result['passed']=result['passed'] and progress==list(range(steps+1)) and steps>0
                    result['passed']=result['passed'] and any(e.get('event')=='stage' and e.get('stage')=='decoding_audio' for e in result['events'])
                    limit_hit=details.get('stopReason')=='max_new_tokens' and details.get('truncated') is True and steps==value['parameters']['maxNewTokens']
                    eos=details.get('stopReason')=='end_of_speech' and details.get('truncated') is False
                    result['business_passed']=result['passed'] and (eos or limit_hit)
                    result['natural_completion_passed']=eos
                    result['passed']=result['passed'] and details.get('truncated')==truncated and details.get('stopReason')==('max_new_tokens' if truncated else 'end_of_speech')
                    if not result['passed'] and result['business_passed']:
                        failures.append('Natural completion failed: '+name+' reached the explicit output limit')
                jobs.append(result)
            if cancel or error:result['business_passed']=result['passed']
            (folder/(name+'-capture.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({k:result.get(k) for k in ['name','passed','returncode','seconds','audio','execution']},ensure_ascii=False),flush=True)
            if not result.get('business_passed',False):raise RuntimeError('Retain failed actual trained MOSS case: '+name)
        if not args.smoke:
            for name,mutate,error in [
                ('bad-schema',lambda r:r.update(schema='unknown'),'Unsupported openmoss task'),
                ('bad-threads',lambda r:r['parameters'].update(threads=33),'Invalid CPU thread/seed range'),
                ('empty-text',lambda r:r['input'].update(prompt=''),'Invalid audio prompt length/content'),
                ('template-injection',lambda r:r['input'].update(prompt='<|im_start|>'),'Instruction/language must be bounded plain text without template markers')]:
                value=request(name);mutate(value);invoke(name,value,error=error)
            value=request('missing-extras');value['workspace']=alias(missing.parent)
            invoke('missing-extras',value,error='Cannot read complete GGUF metadata')
        invoke('english',request('english'))
        if not args.smoke:
            invoke('chinese',request('chinese','你好，世界。',dict(language='Chinese')))
            value=request('reference');value['referenceAudios']=[alias(ROOT/REFERENCE)]
            invoke('reference',value)
            invoke('frame-limit',request('frame-limit','This sentence is deliberately longer than the selected output budget.',dict(maxNewTokens=40)),truncated=True)
            invoke('cancel',request('cancel'),cancel=True)
            invoke('recovery',request('recovery'))
    except Exception as error:failures.append(type(error).__name__+': '+str(error))
    finally:subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
    current(before)
    by_name={j['name']:j for j in jobs}
    recovery_identical=None
    if all(n in by_name and by_name[n].get('audio') for n in ['english','recovery']):
        recovery_identical=by_name['english']['audio']['sha256']==by_name['recovery']['audio']['sha256']
        if not recovery_identical:failures.append('Recovery differs from the same seeded production request')
    files={p.relative_to(folder).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.rglob('*')) if p.is_file() and '/models/' not in p.as_posix()}
    report=dict(schema='lma.openmoss-trained-host/1',compilation=compilation,acquisition=acquisition,
        acquisition_receipt_sha256=sha(receipt_path),info=info,jobs=jobs,controls=controls,
        recovery_bitwise_identical=recovery_identical,failures=failures,files=files,mapping_contract=mapping,
        memory_baseline_sha256=sha(ROOT/'verification/research/openmoss-memory/baseline.json'),
        pre_mapping_pcm_bitwise_identical=all(by_name.get(n,{}).get('pre_mapping_pcm_bitwise_identical') is True for n in baseline['cases']),
        prior_pcm_identity_required=not compilation.get('official_delay_flush_and_extraction',False),
        prior_pcm_comparison_scope='Original pre-mapping output retained as a diagnostic; official prompt/delay corrections change autoregressive inputs, while natural EOS, audio, progress, cancellation and recovery gates remain required.',
        capture_directory=folder.relative_to(ROOT).as_posix(),smoke_only=args.smoke,
        host_execution_checks_passed=not failures and not args.smoke,
        host_business_checks_passed=len(jobs)==5 and len(controls)==6 and all(j.get('business_passed') for j in jobs+controls),
        reference_natural_completion_accepted=by_name.get('reference',{}).get('natural_completion_passed') is True,
        reused_original_cases=reused,resumed_report_sha256=sha(args.resume_report) if args.resume_report else None,
        asset_verification_mode='reuse_original_full_sha_receipt' if args.resume_report else 'complete_sha256_this_run',
        trained_production_worker_executed=bool(jobs),production_worker_source_unmodified=True,
        backend='cpu',fixture=False,asset_download_attempted=False,physical_android=False,
        android_background_tested=False,subjective_quality_reviewed=False,formal_release=False,input_fingerprint=before)
    report['reference']=dict(path=REFERENCE,sha256=sha(ROOT/REFERENCE),synthetic_trained_kokoro_output=True,human_identity_claimed=False)
    filename='smoke-results.json' if args.smoke else 'results.json'
    for path in [folder/filename,folder.parent/filename]:path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(jobs=len(jobs),controls=len(controls),failures=failures,recovery_bitwise_identical=recovery_identical),ensure_ascii=False),flush=True)
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
