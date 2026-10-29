"""Production old-LTX queue/engine on native Windows. --trained uses existing local assets only."""
import argparse,json,os,shutil,subprocess,time
from pathlib import Path
from evidence import fingerprint,current
from build_ltx098_app import inputs as native_inputs,sha

ROOT=Path(__file__).resolve().parents[1]
NAMES=('Store','Downloads','Net','ApiHost','EngineHost','ChatRunner','HubClient','HubCatalog','ModelSettings','GgufMetadata','LocalEngine','LocalJobs','NativeWorker','NativeStages','Ltx098Engine')

def inputs():
    return native_inputs()|fingerprint('app/src/main/java/com/lma/app/core',*[f'app/src/main/java/com/lma/app/{n}.java' for n in NAMES],
        'tests/host','tests/sd-host/com/lma/app/VideoEncoder.java','tests/ltx-app','tools/test_ltx098_app.py',
        'catalogue/model-bundles.json','catalogue/model-assemblies.json','app/src/main/assets/models.json','app/src/main/assets/recipe-templates.json')

def main(trained=False):
    before=inputs();receipt=json.loads((ROOT/'build/ltx098-app-host/receipt.json').read_text(encoding='utf-8'));current(receipt['input_fingerprint'])
    out=ROOT/'build'/('ltx098-app-trained' if trained else 'ltx098-app-tests');out.mkdir(exist_ok=True)
    directory=out/('run-'+str(time.time_ns()));directory.mkdir()
    libraries=directory/'libraries';libraries.mkdir()
    for stage in receipt['stages']:
        source=ROOT/stage['path']
        if source.stat().st_size!=stage['bytes'] or sha(source)!=stage['sha256']:raise RuntimeError('Changed host native stage')
        os.link(source,libraries/('liblma-ltx098-app-'+stage['stage']+'.so'))
    os.link(ROOT/'build/ltx098-app-host/vae/bin/onnxruntime.dll',libraries/'onnxruntime.dll')
    assets={}
    if trained:
        bundle=next(b for b in json.loads((ROOT/'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles'] if b['id']=='ltx098_runtime_google_q5_v2')
        preparation=json.loads((ROOT/'build/ltx098-vae-prepare-tests/results.json').read_text(encoding='utf-8'))
        manifest=ROOT/preparation['artifacts_directory']/'prepared/ltx098-vae.json'
        if not manifest.resolve().is_relative_to(ROOT/'build/ltx098-vae-prepare-tests'):raise RuntimeError('Unexpected local VAE preparation directory')
        for component in bundle['components']:
            role=component['role']
            path=manifest if role=='vae_manifest' else ROOT/('build/ltx098-trained/converted/ltx098-dit.gguf' if role=='diffusion_model' else 'build/ltx098-text-assets/originals/t5-v1_1-xxl-encoder-Q5_K_M.gguf' if role=='text_encoder' else 'build/ltx098-text-assets/oracle/tokenizer_config.json' if role=='tokenizer_config' else 'build/ltx098-vae-assets/'+component['path'])
            if not path.is_file() or path.stat().st_size!=component['bytes'] or sha(path)!=component['sha256']:raise RuntimeError('Complete explicit existing local asset required: '+role)
            print('Verified existing local asset: '+role,flush=True)
            assets[role]=path
        historical=json.loads((ROOT/'build/ltx098-pipeline-tests/results.json').read_text(encoding='utf-8'))
        assets['prompt']=historical['jobs'][0]['request']['prompt']
    dependency=ROOT/'build/test-deps/json-20250517.jar'
    if sha(dependency)!='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796':raise RuntimeError('Changed test JSON library')
    sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))
    sources += [p for p in sorted((ROOT/'tests/host').rglob('*.java')) if p.name!='LocalJobs.java']
    sources += [ROOT/'app/src/main/java/com/lma/app'/f'{n}.java' for n in NAMES]
    sources += [ROOT/'tests/sd-host/com/lma/app/VideoEncoder.java']+sorted((ROOT/'tests/ltx-app').rglob('*.java'))
    classes=directory/'classes';classes.mkdir();response=directory/'sources.rsp';response.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8')
    result=subprocess.run([shutil.which('javac'),'-encoding','UTF-8','-Xlint:-options','--release','8','-cp',str(dependency),'-d',str(classes),'@'+str(response)],capture_output=True,timeout=120)
    (directory/'compile.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Inspect '+str(directory.relative_to(ROOT))+'/compile.log')
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise RuntimeError('Native host media tools missing')
    drive=next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No private ASCII alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        def alias(path):return drive+'/'+path.relative_to(ROOT).as_posix()
        assets={k:alias(v) if isinstance(v,Path) else v for k,v in assets.items()}
        selected=directory/'selected-existing-assets.json';selected.write_text(json.dumps(assets),encoding='utf-8')
        command=[shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-Dstderr.encoding=UTF-8','-Duser.language=en','-cp',alias(classes)+os.pathsep+alias(dependency),'com.lma.app.LtxAppTest',drive+'/',alias(directory/'data'),alias(libraries),str(trained).lower(),alias(selected),ffmpeg,ffprobe]
        print('Production queue/engine '+('complete trained chain' if trained else 'synthetic neural stage controls')+': '+str(directory.relative_to(ROOT)),flush=True)
        with (directory/'java.stdout').open('xb') as stdout,(directory/'java.stderr').open('xb') as stderr:
            child=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr)
            try:code=child.wait(timeout=7500 if trained else 600)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True);child.wait(timeout=30);raise RuntimeError('Test deadline reached; owned process tree stopped')
        if code:raise RuntimeError('Inspect '+str(directory.relative_to(ROOT))+'/java.stderr')
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    report=json.loads((directory/'data/results.json').read_text(encoding='utf-8'))
    if trained:
        bridges=report['runs'][0]['bridgeFiles'];original=historical['jobs'][0]['files']
        report['prior_original_native_chain_comparison']={name:dict(current=value,original=original[name],byte_identical=value==original[name]) for name,value in bridges.items()}
        report['original_numerical_acceptance_passed']=historical['numerical_acceptance_passed']
        report['original_failures_preserved']=historical['failures']
        report['actual_trained_jobs']=1;report['captured_frames']=str((directory/'data/captured/frames.lma').relative_to(ROOT)).replace('\\','/')
        report['captured_video']=str((directory/'data/captured/video.mp4').relative_to(ROOT)).replace('\\','/')
        report['asset_receipts']=[dict(role=c['role'],bytes=c['bytes'],sha256=c['sha256']) for c in bundle['components']]
    report['native_build']=receipt;report['host_media_tools']={k:sha(Path(v)) for k,v in [('ffmpeg',ffmpeg),('ffprobe',ffprobe)]}
    report['capture']=str(directory.relative_to(ROOT)).replace('\\','/');report['passed']=True;current(before);report['input_fingerprint']=before
    (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k in ['assertions','passed','modelInference','productionEngineAndQueue','actual_trained_jobs','numericalAccepted','qualityAccepted','physicalAndroid']}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trained',action='store_true');main(parser.parse_args().trained)
