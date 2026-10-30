"""Validate Sana-Sprint program contracts, tokenizer and bounded arithmetic graphs.

No complete neural checkpoint, image generation or phone inference. Tokenizer
metadata is read from build/sana-program-source, never included in the APK.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/sana-sprint-tests'
METADATA = ROOT/'build/sana-program-source'


def oracle():
    os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
    sys.path.insert(0,str(ROOT/'build/sana-reference-python'))
    import torch
    from diffusers import SCMScheduler
    import diffusers.schedulers.scheduling_scm as scm
    import tokenizers
    torch.set_num_threads(2)
    source = Path(scm.__file__)
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='5e3407521c573e7df0788cd68802c7acd5ec0180762296d03326d8cb10b46466'
    tokenizer_file=METADATA/'tokenizer.json'; piece=METADATA/'tokenizer.model'
    assert hashlib.sha256(tokenizer_file.read_bytes()).hexdigest()=='5f7eee611703c5ce5d1eee32d9cdcfe465647b8aff0c1dfb3bed7ad7dbb05060'
    assert hashlib.sha256(piece.read_bytes()).hexdigest()=='61a7b147390c64585d6c3543dd6fc636906c9af3865a5548f27f31aee1d4c8e2'
    tokenizer=tokenizers.Tokenizer.from_file(str(tokenizer_file))
    # Extract the literal instruction from the pinned publisher pipeline, without
    # importing or constructing any neural-model pipeline.
    import ast
    pipeline=ROOT/'build/sana-reference-python/diffusers/pipelines/sana/pipeline_sana_sprint.py'
    assert hashlib.sha256(pipeline.read_bytes()).hexdigest()=='c682dcf3f30d07d8bd18d95f30b901782f0248738f0a5cc7b832e2f14349428c'
    tree=ast.parse(pipeline.read_text(encoding='utf-8'))
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='__call__')
    defaults=dict(zip([x.arg for x in call.args.args][-len(call.args.defaults):],call.args.defaults))
    instruction='\n'.join(ast.literal_eval(defaults['complex_human_instruction']))
    assert len(tokenizer.encode(instruction).ids)==208
    samples=['','a cat','中文风景，水墨画。','Hello café 👩🏽‍🚀!','two  spaces\tand\nlines','<bos>cat<eos>', '<pad><unk><mask><unused0>', '[@BOS@]<start_of_turn>user<end_of_turn>', '١٢٣ İ Ελληνικά', 'a\u00a0b\u2003c', 'e\u0301 vs é', '    ']
    tokens=[dict(text=text,ids=tokenizer.encode(text).ids) for text in samples+[instruction]]
    prompts=[]
    for text in samples[1:]+['cat '*700]:
        ids=tokenizer.encode(instruction+text).ids; active=min(len(ids),506)
        prompts.append(dict(text=text,ids=(ids[:506]+[0]*506)[:506],active=active,truncated=len(ids)>506))
    results=[]; original=scm.randn_tensor
    try:
        for steps in range(1,5):
            scheduler=SCMScheduler(); scheduler.set_timesteps(steps,intermediate_timesteps=1.3 if steps==2 else None)
            cases=[]
            for i in range(steps):
                x=torch.tensor([-.7,.2,0.,1.3,-2.1,.01,4.2]); prediction=torch.tensor([.2,-.4,.9,0.,2.,-1.1,.1]); noise=torch.tensor([.01,.7,-1.2,0.,.3,1.7,-.3])
                time=scheduler.timesteps[i]; t=torch.sin(time)/(torch.cos(time)+torch.sin(time)); scale=torch.sqrt(t*t+(1-t)*(1-t))
                model_input=x/.5*scale; velocity=((1-2*t)*model_input+(1-2*t+2*t*t)*prediction)/scale*.5
                scm.randn_tensor=lambda *a,**kw:noise
                previous,denoised=scheduler.step(velocity,time,x,return_dict=False)
                cases.append(dict(sample=x.tolist(),prediction=prediction.tolist(),noise=noise.tolist(),time=float(time),next=float(scheduler.timesteps[i+1]),model_input=model_input.tolist(),previous=previous.tolist(),denoised=denoised.tolist()))
            results.append(dict(steps=steps,schedule=scheduler.timesteps.tolist(),cases=cases))
    finally: scm.randn_tensor=original
    data=dict(scm=results,tokens=tokens,prompts=prompts)
    (OUT/'oracle.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return dict(scheduler='unmodified diffusers 0.35.1 SCMScheduler.step',scheduler_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        tokenizers_version=tokenizers.__version__,torch_version=torch.__version__,scm_steps=10,tokenizer_cases=len(tokens)+len(prompts),
        complete_model_weights=False,neural_pipeline_constructed=False)


def main():
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'results.json').unlink(missing_ok=True)
    inputs=fingerprint('native/mnn','tools/build_mnn.py','tools/build_mnn_host.py','tools/sana_sprint_profile.py','tools/test_sana_sprint.py',
        'third_party/mnn-source-lock.json','third_party/moss-nano-source-lock.json','tests/native/sana_sprint_test.cpp',
        'tests/mnn-host','app/src/main/java/com/lma/app/core','app/src/main/java/com/lma/app/MnnEngine.java',
        'catalogue/model-bundles.json','catalogue/sana-sprint-evidence.json')
    reference=oracle()
    jar=ROOT/'build/test-deps/json-20250517.jar'; classes=OUT/'classes'; classes.mkdir(exist_ok=True)
    assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    files=list((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+[ROOT/'tests/host/android/util/AtomicFile.java',ROOT/'tests/mnn-host/com/lma/app/SanaSprintTest.java']
    rsp=OUT/'sources.rsp'; rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in files),encoding='utf-8')
    subprocess.run([shutil.which('javac'),'-J-Duser.language=en','-encoding','UTF-8','--release','8','-cp',str(jar),'-d',str(classes),'@'+str(rsp)],check=True,cwd=ROOT)
    java=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(jar),
        'com.lma.app.SanaSprintTest','catalogue/model-bundles.json','build/sana-program-source/sprint-gemma-meta.json','build/sana-sprint-tests/invalid.json'],cwd=ROOT,capture_output=True,encoding='utf-8',timeout=60)
    (OUT/'java-output.txt').write_text(java.stdout+java.stderr,encoding='utf-8')
    if java.returncode: raise RuntimeError(java.stdout+java.stderr)
    java_result=json.loads(java.stdout.strip().splitlines()[-1])
    from build_mnn_host import build
    executable, receipt=build()
    revision=receipt['source_revision']; compiled=ROOT/'build/mnn-host-compile'/revision
    cache=(compiled/'CMakeCache.txt').read_text(encoding='utf-8')
    drive=next(line.split('=',1)[1][:2].upper() for line in cache.splitlines() if line.startswith('CMAKE_CACHEFILE_DIR:INTERNAL='))
    if drive[0] not in 'TUVWXYZ' or Path(drive+'/').exists():raise RuntimeError('Native MNN build is busy')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        setup=os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        command=[drive+'/build/toolchain/cmake-3.31.6/bin/cmake.exe','--build',drive+'/build/mnn-host-compile/'+revision,'--target','lma_sana_sprint_program_test','-j','4']
        script=OUT/'compile.cmd';script.write_text('@echo off\ncall "'+setup+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n',encoding='utf-8')
        result=subprocess.run(['cmd','/d','/c',str(script)],cwd=ROOT,capture_output=True,timeout=180)
        (OUT/'native-compile.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Inspect build/sana-sprint-tests/native-compile.log')
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    native=compiled/'lma_sana_sprint_program_test.exe'
    result=subprocess.run([str(native),'build/sana-sprint-tests/oracle.json','build/sana-program-source/tokenizer.model','build/sana-sprint-tests/graphs'],cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=90)
    (OUT/'native-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Inspect build/sana-sprint-tests/native-output.txt')
    native_result=json.loads(result.stdout.strip().splitlines()[-1])
    # Exercise the actual production process protocol without loading model graphs.
    handshake=subprocess.run([str(executable),'--info'],cwd=ROOT,capture_output=True,text=True,timeout=20)
    assert handshake.returncode==0 and json.loads(handshake.stdout)['engine']=='mnn_diffusion'
    invalid=dict(schema='lma.engine-request/1',type='image.generate',pipeline='sana_sprint_06b_mnn_v1',input=dict(prompt='cat',negativePrompt=''),parameters=dict(width=512,height=1024,steps=2,threads=4,guidance=4.5,seed=42),workspace='build/sana-sprint-tests/graphs',output='build/sana-sprint-tests/must-not-exist.png')
    request=OUT/'native-invalid.json'; request.write_text(json.dumps(invalid),encoding='utf-8')
    failure=subprocess.run([str(executable),'build/sana-sprint-tests/native-invalid.json'],cwd=ROOT,capture_output=True,text=True,timeout=20)
    assert failure.returncode!=0 and json.loads(failure.stdout)['event']=='error' and not (OUT/'must-not-exist.png').exists()
    current(inputs)
    report=dict(passed=java_result['passed']+native_result['passed']+2,java=java_result,native=native_result,reference=reference,
        production_worker_handshake=True,production_parameter_rejection=True,bounded_graphs=2,trained_model_execution=False,
        complete_model_downloaded=False,model_inference=False,physical_android=False,image_generation=False,
        host_worker_sha256=receipt['sha256'],program_test_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))


if __name__=='__main__': main()
