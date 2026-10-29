"""Counterfactual zero-scale LCM weights, with every sampler/base/prompt parameter fixed.

This native-only diagnostic bypasses the App's deliberate zero-LCM rejection.
It is not an offered App recipe, user setting, or quality/phone acceptance.
"""
import json
import os
from pathlib import Path
import subprocess
import time

from build_sd_host import build
from evidence import current, fingerprint
from fetch_sd15_trained import asset_path as sd15_path, sha, verify as verify_sd15
from fetch_sd_variants_trained import asset_path, verify
from sd_variants_capture import execute
from test_sd_variants_trained import inputs as direct_inputs, image_stats, PROMPT_A

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**direct_inputs(), **fingerprint('tools/test_sd_lcm_effect.py')}


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows only')
    before = inputs(); old = verify_sd15(); lock = verify(); binary, compilation = build()
    direct_path = ROOT/'build/sd-variants-trained-tests/results.json'; direct = json.loads(direct_path.read_text(encoding='utf-8'))
    current(direct['input_fingerprint'])
    if not direct['host_execution_checks_passed'] or direct['compilation'] != compilation: raise ValueError('Require complete original native cases first')
    directory = ROOT/'build/sd-variants-lcm-effect-tests'/('run-'+str(time.time_ns())); directory.mkdir(parents=True,exist_ok=False)
    assets = {item['id']:item for item in lock['assets']}; jobs = []; failures = []
    drive = next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        def alias(path): return drive+'/'+path.relative_to(ROOT).as_posix()
        merges = next(item for item in old['components'] if item['role']=='clip_merges')
        environment = os.environ.copy(); environment['LMA_VOCAB_CLIP_MERGES'] = alias(sd15_path(merges))
        for family in ['sd15','sdxl']:
            name = family+'-lcm-zero-diagnostic'; output = directory/(name+'.png')
            base = next(j for j in direct['jobs'] if j['name']==family+'-lcm-a')
            original = json.loads((ROOT/direct['capture_directory']/(base['name']+'.json')).read_text(encoding='utf-8'))
            model = next(sd15_path(item) for item in old['components'] if item['role']=='model') if family=='sd15' else asset_path(assets['sdxl_base_q4_0'])
            value = dict(schema='lma.engine-request/1',pipeline=family,architecture=family,samplingProfile='lcm',type='image.generate',
                input=dict(prompt=PROMPT_A,negativePrompt=''),parameters=dict(base['parameters']),output=alias(output),
                components=dict(model=alias(model),clip_merges=alias(sd15_path(merges))),
                loras=[dict(path=alias(asset_path(assets[family+'_lcm_lora'])),scale=0.)])
            assert value['input']==original['input'] and value['parameters']==original['parameters']
            assert original['loras'][0]['scale']==1. and len(original['loras'])==len(value['loras'])==1
            request = directory/(name+'.json'); request.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
            print('Real LCM weight-effect diagnostic:',family,flush=True)
            result,logs = execute([alias(binary),alias(request)],environment,sampler_steps=4)
            for suffix,data in zip(['stdout','stderr'],logs): (directory/(name+'.'+suffix)).write_bytes(data)
            result.update(name=name,family=family,request_sha256=sha(request),parameters=value['parameters'],
                baseline_name=base['name'],enabled_scale=1.,diagnostic_scale=0.,diagnostic_only=True,app_recipe=False,
                adapters=value['loras'],case=dict(family=family,prompt=PROMPT_A,width=512,height=512,profile='lcm',
                    adapters=[[family+'_lcm_lora',0.]],cancel_step=None,diagnostic_only=True))
            complete = [e for e in result['events'] if e.get('event')=='complete']
            result['passed'] = result['returncode']==0 and not result['timed_out'] and not result['forced_host_termination'] and not result['protocol_errors'] and not any(result['logs_truncated'])
            result['passed'] = result['passed'] and complete==[dict(event='complete',output=alias(output),format='png',width=512,height=512)] and output.is_file()
            if output.is_file():
                result['image']=image_stats(output)
                result['enabled_image_sha256']=base['image']['sha256']
                result['only_scale_changed']=True
                result['enabled_weights_change_output']=result['image']['sha256']!=base['image']['sha256']
                result['passed']=result['passed'] and result['enabled_weights_change_output'] and all(v>1 for v in result['image']['channel_stddev'])
            result['sampling_steps_observed']=[e['step'] for e in result['events'] if e.get('event')=='progress' and e.get('stage')=='generating' and e.get('steps')==4]
            result['passed']=result['passed'] and result['sampling_steps_observed']==list(range(5))
            (directory/(name+'-capture.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');jobs.append(result)
            print(json.dumps({k:result.get(k) for k in ['name','seconds','passed','enabled_weights_change_output']}),flush=True)
            if not result['passed']: failures.append(name)
    finally: subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    current(before)
    report=dict(schema='lma.sd-lcm-weight-effect-host/1',jobs=jobs,failures=failures,host_weight_effect_checks_passed=not failures,
        compilation=compilation,direct_trained_report_sha256=sha(direct_path),capture_directory=directory.relative_to(ROOT).as_posix(),
        files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(directory.iterdir()) if p.is_file()},
        diagnostic_only=True,app_recipe=False,asset_download_attempted=False,physical_android=False,
        semantic_quality_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    for p in [directory/'results.json',directory.parent/'results.json']: p.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if failures: raise SystemExit(1)


if __name__=='__main__': main()
