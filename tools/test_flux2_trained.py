"""Execute complete user-supplied FLUX.2-klein 4B assets in the production worker.

Native Windows CPU evidence only. No downloads, phone inference or quality claims.
Successful and failed raw requests, logs and images are retained independently.
"""
import json
import os
from pathlib import Path
import subprocess
import time

from build_sd_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_flux2_trained import BUNDLE_ID, asset_path, inputs as asset_inputs, sha, verify
from sd_variants_capture import execute
from test_sd_variants_trained import image_stats

ROOT = Path(__file__).resolve().parents[1]
PROMPT_A = 'A small red toy robot standing beside a blue ceramic teapot on a wooden table, studio photograph, soft daylight, clean background'
PROMPT_B = 'A yellow sailboat on a calm blue lake below snow covered mountains, bright daylight, detailed landscape photograph'


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint(
        'tools/test_flux2_trained.py', 'tools/sd_variants_capture.py',
        'tools/test_sd_variants_trained.py', 'research/flux2_trained',
        'app/src/main/assets/recipe-templates.json', 'catalogue/model-bundles.json')}


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows CPU only')
    before = inputs(); lock = verify(); binary, compilation = build()
    bundle = next(b for b in json.loads((ROOT/'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles'] if b['id']==BUNDLE_ID)
    if bundle['components'] != lock['components']: raise ValueError('Catalogue and complete trained assets differ')
    folder = ROOT / 'build/flux2-trained-tests' / ('run-' + str(time.time_ns())); folder.mkdir(parents=True, exist_ok=False)
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    runs=[]; checks=[]; images={}; comparisons={}
    def check(value, description): checks.append(dict(passed=bool(value), description=description))
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        environment=dict(os.environ)
        environment['LMA_VOCAB_QWEN_MERGES']=alias(asset_path(next(c for c in lock['components'] if c['role']=='qwen_merges')))
        info, logs = execute([alias(binary), '--info'], environment, timeout=30)
        (folder/'info.stdout').write_bytes(logs[0]); (folder/'info.stderr').write_bytes(logs[1])
        check(info['returncode']==0 and len(info['events'])==1 and info['events'][0].get('revision')==compilation['source_revision'], 'Actual pinned production worker identity')
        for name, prompt, steps, cancel, error in [
            ('a',PROMPT_A,4,None,None), ('b',PROMPT_B,4,None,None),
            ('one-step',PROMPT_A,1,None,None), ('cancel-step1',PROMPT_A,4,1,None),
            ('empty-prompt','',4,None,'Invalid prompt or output'),
            ('wrong-task',PROMPT_A,4,None,'Unsupported diffusion task'),
            ('recovery-a',PROMPT_A,4,None,None)]:
            output=folder/(name+'.png')
            request=dict(schema='lma.engine-request/1',type='audio.generate' if name=='wrong-task' else 'image.generate',
                         pipeline='flux2_klein_4b',architecture='flux2_klein',samplingProfile='flux2_klein',
                         input=dict(prompt=prompt,negativePrompt=''),
                         parameters=dict(width=512,height=512,steps=steps,threads=6,seed=42,cfg=1,
                                         sampler='euler',scheduler='flux2',flowShift=0,vaeTiling=True),
                         components={c['role']:alias(asset_path(c)) for c in lock['components']},
                         loras=[],output=alias(output))
            path=folder/(name+'.json'); path.write_text(json.dumps(request,indent=2)+'\n',encoding='utf-8')
            print('Execute complete trained FLUX.2-klein:',name,flush=True)
            result, logs=execute([alias(binary),alias(path)],environment,sampler_steps=steps,cancel_step=cancel,timeout=7200)
            stdout=folder/(name+'.stdout');stderr=folder/(name+'.stderr');stdout.write_bytes(logs[0]);stderr.write_bytes(logs[1])
            item=dict(name=name,request=request,process=result,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr))
            (folder/(name+'-capture.json')).write_text(json.dumps(item,indent=2)+'\n',encoding='utf-8')
            check(not result['timed_out'] and not result['protocol_errors'] and not any(result['logs_truncated']),name+': bounded structured worker protocol')
            complete=[e for e in result['events'] if e.get('event')=='complete']
            if cancel:
                check(result['forced_host_termination'] and result['cancel_trigger']['step']==1 and result['cancel_to_exit_seconds']<5,name+': terminate after an actual completed sampler step')
                check(not complete and not output.exists(),name+': cancelled computation publishes no PNG')
            elif error:
                errors=[e.get('message') for e in result['events'] if e.get('event')=='error']
                check(result['returncode']!=0 and errors==[error] and not output.exists(),name+': actual structured failure and no output')
            else:
                check(result['returncode']==0 and len(complete)==1 and output.is_file(),name+': actual complete trained PNG')
                if output.is_file():
                    item['image']=image_stats(output);images[name]=output
                    check(item['image']['width']==512 and item['image']['height']==512 and max(item['image']['channel_stddev'])>1,name+': 512x512 nonuniform decoded pixels, not a quality gate')
                    check(complete[0].get('output')==alias(output) and complete[0].get('format')=='png',name+': exact output identity')
                actual=[e for e in result['events'] if e.get('event')=='progress' and e.get('stage')=='generating' and e.get('steps')==steps]
                check(any(e.get('step')==steps for e in actual),name+': actual final sampler step')
                check(result['resources']['observed'] and result['resources']['observed_peak_working_set_bytes']>0,name+': observed Windows process memory')
            runs.append(item)
            (folder/(name+'-result.json')).write_text(json.dumps(item,indent=2)+'\n',encoding='utf-8')
        from PIL import Image, ImageChops, ImageStat
        for right in ['b','one-step','recovery-a']:
            if 'a' not in images or right not in images: continue
            with Image.open(images['a']) as a,Image.open(images[right]) as b:
                delta=ImageChops.difference(a.convert('RGB'),b.convert('RGB')); stats=ImageStat.Stat(delta)
                comparisons[right]=dict(maximum=max(v[1] for v in delta.getextrema()),mean=sum(stats.mean)/3)
            check(comparisons[right]['maximum']==0 if right=='recovery-a' else comparisons[right]['maximum']>0,
                  'Exact recovery pixels' if right=='recovery-a' else right+': prompt/step changes actual pixels')
    finally:
        subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
    current(before)
    files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.iterdir()) if p.is_file()}
    report=dict(schema='lma.flux2-trained-host/1',selection_id='07',bundle_id=BUNDLE_ID,components=lock['components'],
                capture_directory=folder.relative_to(ROOT).as_posix(),compilation=compilation,runs=runs,comparisons=comparisons,files=files,
                checks=checks,passed=sum(c['passed'] for c in checks),host_execution_checks_passed=all(c['passed'] for c in checks),
                full_components_executed=True,production_worker_source_unmodified=True,physical_android=False,
                independent_numerics_accepted=False,image_quality_accepted=False,complete_target07_accepted=False,
                complete_release_accepted=False,input_fingerprint=before)
    for path in [folder/'results.json',folder.parent/'results.json']:
        path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'],checks=len(checks),runs=len(runs),outputs=len(images))),flush=True)
    if not report['host_execution_checks_passed']: raise RuntimeError('Inspect retained real FLUX.2-klein failures; no gate was relaxed')


if __name__=='__main__': main()
