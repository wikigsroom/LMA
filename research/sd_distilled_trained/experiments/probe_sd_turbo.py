"""Private trained checkpoint execution; not App, Android or complete target03 acceptance."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time
root=Path(__file__).resolve().parents[2];directory=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tools'))
from build_sd_host import build
from evidence import current,fingerprint
from fetch_sd15_trained import asset_path as existing_path,bundle,sha
from sd_variants_capture import execute
from test_sd_variants_trained import image_stats
before=fingerprint('build/sd-distilled-asset-probe/probe_sd_turbo.py')
asset=next(a for a in json.loads((directory/'asset-plan.json').read_text())['assets'] if a['id']=='sd_turbo_q8_0')
model=directory/'originals'/asset['sha256']/asset['path']
assert model.stat().st_size==asset['bytes'] and sha(model)==asset['sha256']
merges=next(c for c in bundle()['components'] if c['role']=='clip_merges');vocab=existing_path(merges)
assert vocab.stat().st_size==merges['bytes'] and sha(vocab)==merges['sha256']
binary,compilation=build()
output=directory/('sd-turbo-private-'+str(time.time_ns()));output.mkdir()
print('Private actual SD-Turbo capture: '+output.relative_to(root).as_posix(),flush=True)
drive=next(c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists());subprocess.run(['subst',drive,str(root)],capture_output=True,check=True)
cases=[];failed=False
try:
    def alias(path):return drive+'/'+path.relative_to(root).as_posix()
    environment=os.environ.copy();environment['LMA_VOCAB_CLIP_MERGES']=alias(vocab)
    for name,steps,cancel,cfg in [('one-step',1,None,1.),('four-step',4,None,1.),('invalid-cfg',4,None,7.),('cancel-step1',4,1,1.),('recovery',4,None,1.)]:
        image=output/(name+'.png');request=dict(schema='lma.engine-request/1',pipeline='sd21_turbo',architecture='sd21',samplingProfile='sd_turbo',type='image.generate',
            input=dict(prompt='A small red fox sitting beside a blue ceramic teapot on a wooden table, clean composition',negativePrompt=''),
            parameters=dict(width=512,height=512,steps=steps,cfg=cfg,sampler='euler_a',scheduler='discrete',seed=42,threads=6,vaeTiling=True,flowShift=0),
            components=dict(model=alias(model),clip_merges=alias(vocab)),loras=[],output=alias(image))
        request_path=output/(name+'.json');request_path.write_text(json.dumps(request,indent=2)+'\n',encoding='utf-8')
        result,logs=execute([alias(binary),alias(request_path)],environment,steps,cancel)
        for suffix,raw in zip(['stdout','stderr'],logs):(output/(name+'.'+suffix)).write_bytes(raw)
        valid=not result['timed_out'] and not result['protocol_errors'] and not any(result['logs_truncated'])
        if cancel is not None:
            valid=valid and result['forced_host_termination'] and result['cancel_trigger'] is not None and result['returncode']!=0 and not image.exists()
        elif cfg!=1.:
            valid=valid and result['returncode']==1 and not image.exists() and [e['message'] for e in result['events'] if e.get('event')=='error']==['Distilled sampling parameters do not match the frozen plan']
        else:
            valid=valid and result['returncode']==0 and image.exists() and any(e.get('event')=='complete' for e in result['events'])
            if valid:result['image']=image_stats(image)
        result.update(name=name,parameters=request['parameters'],passed=valid)
        (output/(name+'-capture.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');cases.append(result)
        print(json.dumps(dict(name=name,passed=valid,returncode=result['returncode'],seconds=result['seconds'],errors=[e for e in result['events'] if e.get('event')=='error'])),flush=True)
        if not valid:failed=True;break
finally:subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
current(before)
recovery=False
if len(cases)==5 and not failed:
    recovery=cases[1]['image']['sha256']==cases[4]['image']['sha256']
report=dict(schema='lma.private-sd-turbo-trained-host-probe/1',asset=asset,compilation=compilation,full_asset_sha_verified=True,
            jobs=cases,recovery_matches=recovery,host_checks_passed=not failed and recovery,production_app_executed=False,physical_android=False,
            image_quality_accepted=False,complete_target03_accepted=False,complete_release_accepted=False,input_fingerprint=before,capture_directory=output.relative_to(root).as_posix())
(output/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(directory/'sd-turbo-probe-results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
if failed or not recovery:raise RuntimeError('Inspect retained private trained captures; no acceptance')
