"""Full-architecture UNTRAINED acoustic graphs: actual native ORT/CPU checks.

No language/reference model, publisher checkpoint, APK binding or phone evidence.
"""
import argparse,copy,hashlib,importlib.metadata,json,os,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
from evidence import fingerprint,current
from export_soulx import environment
from soulx_native_checks import compile_host
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/soulx-acoustic-tests'


def run(command,log,timeout=300):
    result=subprocess.run([str(x) for x in command],cwd=ROOT,capture_output=True,timeout=timeout)
    log.write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Command failed; inspect '+str(log.relative_to(ROOT)))
    return result.stdout.decode('utf-8',errors='replace')


def assets(directory,record):
    for item in record['assets']:
        path=directory/item['file']
        if path.parent!=directory or not path.is_file() or path.stat().st_size!=item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:return False
    return True


def fixtures(force=False):
    keys=fingerprint('tools/soulx_acoustic.py','tools/export_soulx.py','tools/soulx_acoustic_fixture.py','third_party/soulx-acoustic-source-lock.json')
    cache=OUT/'fixture-receipt.json';valid=False
    if cache.exists() and not force:
        saved=json.loads(cache.read_text(encoding='utf-8'))
        if saved['input_fingerprint']==keys:
            valid=all((OUT/name).exists() and hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest for name,digest in saved['files'].items())
    if valid:return json.loads((OUT/'references/cases.json').read_text(encoding='utf-8'))
    # Remove only this tool's generated test directories, never the workspace
    # or caller assets. Rebuilding is required for a changed export/fixture pin.
    for name in ['pack','checkpoints','references']:
        path=OUT/name
        if path.exists():
            if path.resolve().parent!=OUT.resolve():raise RuntimeError('Unsafe fixture cleanup target')
            shutil.rmtree(path)
    print('Create UNTRAINED complete Flow/HiFT parameters',flush=True)
    result=run([sys.executable,'tools/soulx_acoustic_fixture.py','checkpoints',OUT/'checkpoints'],OUT/'fixture-build.log')
    counts=json.loads(result.strip().splitlines()[-1]);assert counts==dict(flow_parameters=112549360,hift_parameters=20821295,trained=False)
    print('Execute production offline converter for four complete networks',flush=True)
    run([sys.executable,'tools/export_soulx.py','--checkpoint-dir',OUT/'checkpoints','--output-dir',OUT/'pack','--synthetic-fixture'],OUT/'export.log',600)
    manifest=json.loads((OUT/'pack/soulx-acoustic.json').read_text(encoding='utf-8'))
    assert manifest['synthetic_parameters'] is True and not manifest['complete_soulx_model'] and assets(OUT/'pack',manifest)
    print('Execute original upstream Flow/HiFT forward methods',flush=True)
    run([sys.executable,'tools/soulx_acoustic_fixture.py','references',OUT/'references','--checkpoint-dir',OUT/'checkpoints'],OUT/'references.log',600)
    files={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for name in ['pack','checkpoints','references'] for p in (OUT/name).rglob('*') if p.is_file()}
    cache.write_text(json.dumps(dict(input_fingerprint=keys,files=files,counts=counts),indent=2)+'\n',encoding='utf-8')
    return json.loads((OUT/'references/cases.json').read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rebuild-fixtures',action='store_true');args=parser.parse_args()
    environment();OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    inputs=fingerprint('research/soulx_acoustic','research/soulx_ort','research/soulx','native/moss_nano/onnx_external.hpp','tools/soulx_acoustic.py','tools/export_soulx.py','tools/fetch_soulx_dsp.py','tools/soulx_acoustic_fixture.py','tools/test_soulx_acoustic.py','tools/soulx_native_checks.py','third_party/soulx-acoustic-source-lock.json')
    lock=json.loads((ROOT/'third_party/soulx-acoustic-source-lock.json').read_text(encoding='utf-8'))
    cases=fixtures(args.rebuild_fixtures);exe=compile_host(lock,OUT,'soulx_acoustic');checks=0;children=0;graphs=0;metrics=[];runs=[]
    result_dir=OUT/'native-results';result_dir.mkdir(exist_ok=True)
    def native(case,name,expected_ok=True,model_dir=None):
        nonlocal children,graphs,checks
        target=result_dir/(name+'.f32');target.unlink(missing_ok=True)
        result=subprocess.run([str(exe),str(model_dir or OUT/'pack'),str(case),str(target)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        (result_dir/(name+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8');children+=1
        if not result.stdout.strip():raise RuntimeError('Native worker failed before a result: '+name)
        record=json.loads(result.stdout.strip().splitlines()[-1]);runs.append(dict(name=name,**record));graphs+=record['graph_runs']
        if record['ok']!=expected_ok or bool(result.returncode)==expected_ok:raise AssertionError((name,record,result.stderr))
        if not expected_ok:
            assert not target.exists() and record['session_loads']==record['session_unloads'];checks+=2
        return target,record
    for index in [0,1,0]:
        case=cases[index];name='synthesis-'+str(children)
        path,record=native(OUT/'references'/case['directory'],name)
        assert record['samples']==case['samples'] and record['graph_runs']==18 and record['session_loads']==4 and record['session_unloads']==4 and record['max_live_sessions']==1 and record['synthetic_parameters_declared'] is True;checks+=6
        for key,shape in case['shapes'].items():
            actual_path=path if key=='wave' else result_dir/(path.stem+'-'+key+'.f32')
            actual=np.fromfile(actual_path,dtype='<f4').reshape(shape['shape']);expected=np.fromfile(OUT/'references'/case['directory']/'golden'/shape['file'],dtype='<f4').reshape(shape['shape'])
            if not np.isfinite(actual).all():raise AssertionError(key+' nonfinite')
            error=np.asarray(actual,dtype=np.float64)-expected;peak=float(np.max(np.abs(error)));rms=float(np.sqrt(np.mean(error**2)))
            tolerance=.002 if key.startswith('flow_velocity') or key=='mel' else .002 if key=='f0' else .0005
            if peak>tolerance:raise AssertionError((name,key,peak,rms,tolerance))
            metrics.append(dict(case=name,stage=key,shape=shape['shape'],maximum_absolute_error=peak,rmse=rms,maximum_allowed=tolerance));checks+=3
        wave=np.fromfile(path,dtype='<f4');assert len(wave)>0 and np.max(np.abs(wave))<=.990001 and np.std(wave)>1e-5;checks+=3
    base=OUT/'references'/cases[0]['directory'];original=json.loads((base/'input.json').read_text(encoding='utf-8'))
    guards=OUT/'guard-input';guards.mkdir(exist_ok=True)
    for filename in ['tokens.i64','speaker.f32','prompt-mel.f32','flow-noise.f32','nsf-noise.f32']:shutil.copyfile(base/filename,guards/filename)
    for field,value in [('steps',0),('threads',0),('cfg',-1),('seed',-2),('prompt_tokens',0)]:
        request=copy.deepcopy(original);request[field]=value;(guards/'input.json').write_text(json.dumps(request),encoding='utf-8')
        _,record=native(guards,'invalid-'+field,False);assert record['graph_runs']==0;checks+=1
    for mode in ['cancel_before_run','cancel_flow','cancel_during_run']:
        request=copy.deepcopy(original);request['mode']=mode;request['trace']=False
        (guards/'input.json').write_text(json.dumps(request),encoding='utf-8');_,record=native(guards,mode,False)
        assert 'cancelled' in record['error'];checks+=1
        if mode=='cancel_during_run':assert record['terminated_runs']==1;checks+=1
    # Asset integrity belongs to the existing bundle/lease layer. Here validate
    # native external-tensor location/range and graph signature rejection.
    import onnx
    broken=OUT/'broken-pack';broken.mkdir(exist_ok=True)
    shutil.copyfile(OUT/'pack/soulx-acoustic.json',broken/'soulx-acoustic.json')
    graph=onnx.load(str(OUT/'pack/flow-encoder.onnx'),load_external_data=False)
    for tensor in graph.graph.initializer:
        if tensor.data_location==onnx.TensorProto.EXTERNAL:
            for field in tensor.external_data:
                if field.key=='location':field.value='../outside.data'
            break
    onnx.save_model(graph,str(broken/'flow-encoder.onnx'))
    _,record=native(base,'external-escape',False,broken);assert record['graph_runs']==0 and 'External tensor' in record['error'];checks+=1
    current(inputs)
    manifest=json.loads((OUT/'pack/soulx-acoustic.json').read_text(encoding='utf-8'))
    report=dict(passed=checks,actual_host_children=children,actual_ort_graph_runs=graphs,successful_syntheses=3,
        full_flow_parameters=112549360,full_hift_parameters=20821295,reduced_network=False,synthetic_parameters=True,
        production_converter_executed=True,actual_upstream_forward_references=True,actual_ort_terminations=sum(r['terminated_runs'] for r in runs),
        max_live_sessions=max(r['max_live_sessions'] for r in runs),runtime_version=lock['host_runtime']['version'],
        python_versions={name:importlib.metadata.version(name) for name in ['torch','numpy','onnx','diffusers','einops']},
        runtime_sha256=lock['host_runtime']['sha256'],assets=manifest['assets'],runs=runs,metrics=metrics,
        trained_checkpoints_loaded=0,full_soulx_inference=False,model_audio_quality_tested=False,physical_android=False,
        apk_runtime_used=False,engine_registered=False,input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['assets','runs','metrics','input_fingerprint']}),flush=True)

if __name__=='__main__':main()
