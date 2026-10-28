"""Actual trained S3/CAMP CPU checks, isolated from complete SoulX/phone gates.

The two publisher models must already have been explicitly downloaded.
Original upstream audio math and ORIGINAL inline publisher ONNX graphs form
the references. Native children use the production converted external graphs.
"""
import argparse,copy,gc,hashlib,json,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from evidence import fingerprint,current
from export_soulx_reference import convert,environment
from fetch_soulx_reference import verify_models,LOCK,sha
from fetch_soulx_dsp import validate_sources,test_references
from soulx_native_checks import compile_host
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/soulx-reference-tests'


def models(lock):
    original=ROOT/'build/soulx-reference-models/originals';verify_models(lock,original)
    keys=fingerprint('tools/export_soulx_reference.py','third_party/soulx-reference-source-lock.json')
    cache=OUT/'conversion-receipt.json';pack=OUT/'pack';valid=False
    if cache.exists():
        saved=json.loads(cache.read_text(encoding='utf-8'))
        if saved['input_fingerprint']==keys:
            valid=all((pack/name).is_file() and sha(pack/name)==digest for name,digest in saved['files'].items())
    if not valid:
        if pack.exists():
            if pack.resolve().parent!=OUT.resolve():raise RuntimeError('Unsafe developer cache cleanup')
            shutil.rmtree(pack)
        print('Externalize COMPLETE trained publisher reference graphs; verify exact graph/tensor identity',flush=True)
        record=convert(original,pack)
        cache.write_text(json.dumps(dict(input_fingerprint=keys,files={p.name:sha(p) for p in pack.iterdir() if p.is_file()}),indent=2)+'\n',encoding='utf-8')
    else:record=json.loads((pack/'soulx-reference.json').read_text(encoding='utf-8'))
    assert record['publisher_hashes_match'] and record['full_graph_tensor_identity_verified'] and not record['weights_initialized']
    return original,pack,record


def references(original):
    import torch,onnxruntime as ort
    from test_soulx_dsp import functions
    dsp_lock=json.loads((ROOT/'third_party/soulx-dsp-source-lock.json').read_text(encoding='utf-8'));refs=test_references(dsp_lock)
    torch.set_num_threads(4)
    convert_math=functions(refs/'librosa/librosa/core/convert.py',['hz_to_mel','mel_to_hz','mel_frequencies','fft_frequencies'])
    librosa=functions(refs/'librosa/librosa/filters.py',['mel'],env=convert_math)
    audio=ROOT/'build/native-src/soulx-podcast/soulxpodcast/utils/audio.py'
    upstream=functions(audio,['audio_volume_normalize','mel_spectrogram','spectral_normalize_torch','dynamic_range_compression_torch'],env={'librosa_mel_fn':librosa['mel'],'mel_basis':{},'hann_window':{}})
    s3root=ROOT/'build/native-src/s3tokenizer/s3tokenizer'
    with np.load(s3root/'assets/mel_filters.npz',allow_pickle=False) as archive:filters=archive['mel_128'].copy()
    s3=functions(s3root/'utils.py',['log_mel_spectrogram'],env={'_mel_filters':lambda device,n:torch.from_numpy(filters).to(device)})
    kaldi=functions(refs/'torchaudio/torchaudio/compliance/kaldi.py',constants=True)
    sinc=functions(refs/'torchaudio/torchaudio/functional/functional.py',['_get_sinc_resample_kernel','_apply_sinc_resample_kernel','resample'],env={'_CPU':torch.device('cpu')})
    cases=[]
    for index,length in enumerate([24000,29537,360000]):
        case=OUT/('case-'+str(index));case.mkdir(exist_ok=True)
        rng=np.random.default_rng(391+index);t=np.arange(length,dtype=np.float64)/24000
        pcm=(rng.standard_normal(length)*.04+.04*np.sin(2*np.pi*(160*t+18*t*t))).astype('<f4');pcm.tofile(case/'pcm.f32')
        (case/'input.json').write_text(json.dumps(dict(format='lma.soulx-reference-input/1',threads=2,trace=True)),encoding='utf-8')
        signal=torch.from_numpy(pcm.copy());pcm16=upstream['audio_volume_normalize'](sinc['resample'](signal,24000,16000))
        with torch.inference_mode():
            semantic=s3['log_mel_spectrogram'](pcm16).numpy()[None,:]
            speaker=kaldi['fbank'](pcm16[None,:],num_mel_bins=80,dither=0,sample_frequency=16000);speaker-=speaker.mean(dim=0,keepdim=True)
            flow=upstream['mel_spectrogram'](upstream['audio_volume_normalize'](signal)[None,:]).numpy();flow=flow[:,:,:flow.shape[2]//2*2]
        cases.append(dict(directory=case,samples=length,features=dict(s3_features=semantic,speaker_features=speaker.numpy()[None,:],flow_features=flow)))
    def session(path):
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC;options.enable_cpu_mem_arena=False;options.enable_mem_pattern=False;options.log_severity_level=4
        return ort.InferenceSession(str(path),options,providers=['CPUExecutionProvider'])
    # Original self-contained publisher graphs, never the converted outputs.
    print('Execute ORIGINAL trained S3Tokenizer v2 publisher graph',flush=True)
    semantic=session(original/'speech_tokenizer_v2.onnx')
    for case in cases:
        features=case['features'];codes=semantic.run(None,{'feats':features['s3_features'],'feats_length':np.array([features['s3_features'].shape[2]],dtype=np.int32)})[0]
        assert codes.dtype==np.int32 and codes.shape==(1,(features['s3_features'].shape[2]+3)//4)
        count=min(codes.shape[1],features['flow_features'].shape[2]//2)
        case.update(raw_tokens=codes.shape[1],tokens=codes[0,:count].astype('<i8'),prompt_mel=features['flow_features'][:,:,:count*2])
    del semantic;gc.collect();print('Execute ORIGINAL trained CAMPPlus publisher graph',flush=True)
    speaker=session(original/'campplus.onnx')
    for case in cases:case['speaker']=speaker.run(None,{'input':case['features']['speaker_features']})[0]
    del speaker;gc.collect();return cases


def main():
    parser=argparse.ArgumentParser();parser.parse_args();environment();OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    inputs=fingerprint('research/soulx_reference','research/soulx_ort','research/soulx','native/moss_nano/onnx_external.hpp',
        'tools/test_soulx_reference.py','tools/export_soulx_reference.py','tools/fetch_soulx_reference.py','tools/soulx_native_checks.py',
        'tools/test_soulx_dsp.py','tools/fetch_soulx_dsp.py','third_party/soulx-reference-source-lock.json','third_party/soulx-dsp-source-lock.json')
    lock=json.loads(LOCK.read_text(encoding='utf-8'));validate_sources(lock)
    original,pack,manifest=models(lock);exe=compile_host(lock,OUT,'soulx_reference');cases=references(original)
    passed=3;children=0;runs=[];metrics=[]
    results=OUT/'native-results';results.mkdir(exist_ok=True)
    def native(input_dir,name,ok=True,model_dir=pack):
        nonlocal children,passed
        output=results/name
        if output.exists():
            if output.resolve().parent!=results.resolve():raise RuntimeError('Unsafe native test output cleanup')
            shutil.rmtree(output)
        result=subprocess.run([str(exe),str(model_dir),str(input_dir),str(output)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        (results/(name+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8');children+=1
        if not result.stdout.strip():raise RuntimeError('Native reference failed before receipt: '+name)
        record=json.loads(result.stdout.strip().splitlines()[-1]);runs.append(dict(name=name,**record))
        assert record['ok']==ok and (result.returncode==0)==ok,(name,record)
        assert record['session_loads']==record['session_unloads'];passed+=2
        if not ok:assert not output.exists();passed+=1
        return output,record
    for sequence,index in enumerate([0,1,2,0]):
        case=cases[index];out,record=native(case['directory'],'reference-'+str(sequence))
        assert record['graph_runs']==2 and record['session_loads']==2 and record['max_live_sessions']==1 and record['tokens']==len(case['tokens']);passed+=4
        actual=np.fromfile(out/'tokens.i64',dtype='<i8');assert np.array_equal(actual,case['tokens']);passed+=1
        expected={**case['features'],'speaker':case['speaker'],'prompt_mel':case['prompt_mel']}
        for stage,value in expected.items():
            file='prompt-mel.f32' if stage=='prompt_mel' else stage+'.f32'
            actual=np.fromfile(out/file,dtype='<f4').reshape(value.shape);delta=np.asarray(actual,dtype=np.float64)-value
            peak=float(np.max(np.abs(delta)));rms=float(np.sqrt(np.mean(delta*delta)))
            limit,rms_limit=(1e-3,2e-5) if stage=='speaker_features' else (2e-3,2e-4) if stage=='speaker' else (5e-5,2e-6)
            assert np.isfinite(actual).all() and peak<=limit and rms<=rms_limit,(sequence,stage,peak,rms)
            metrics.append(dict(case=sequence,stage=stage,shape=list(value.shape),maximum_absolute_error=peak,rmse=rms,maximum_allowed=limit,rmse_allowed=rms_limit));passed+=3
        assert record['raw_tokens']==case['raw_tokens'] and record['raw_flow_frames']==case['features']['flow_features'].shape[2];passed+=2
    guard=OUT/'guard';guard.mkdir(exist_ok=True);base=json.loads((cases[0]['directory']/'input.json').read_text(encoding='utf-8'))
    def request(config,pcm):
        (guard/'input.json').write_text(json.dumps(config),encoding='utf-8');np.asarray(pcm,dtype='<f4').tofile(guard/'pcm.f32')
    original_pcm=np.fromfile(cases[0]['directory']/'pcm.f32',dtype='<f4')
    bad_pcm=original_pcm.copy();bad_pcm[0]=np.nan
    high_pcm=original_pcm.copy();high_pcm[0]=1.01
    for name,config,pcm in [('threads-zero',{**base,'threads':0},original_pcm),('threads-large',{**base,'threads':33},original_pcm),
        ('short',base,original_pcm[:-1]),('long',base,np.zeros(360001,'f4')),('nonfinite',base,bad_pcm),('amplitude',base,high_pcm)]:
        request(config,pcm);_,record=native(guard,'invalid-'+name,False);assert record['graph_runs']==0;passed+=1
    long_pcm=np.fromfile(cases[2]['directory']/'pcm.f32',dtype='<f4')
    for mode in ['cancel_before','cancel_after_s3','cancel_during_s3','cancel_during_speaker']:
        request({**base,'mode':mode,'trace':False},long_pcm);_,record=native(guard,mode,False);assert 'cancelled' in record['error'];passed+=1
        if mode.startswith('cancel_during'):assert record['terminated_runs']==1;passed+=1
    import onnx
    broken=OUT/'broken-pack';broken.mkdir(exist_ok=True);shutil.copyfile(pack/'soulx-reference.json',broken/'soulx-reference.json')
    graph=onnx.load(str(pack/'reference-s3.onnx'),load_external_data=False)
    for tensor in graph.graph.initializer:
        if tensor.external_data:
            for entry in tensor.external_data:
                if entry.key=='location':entry.value='../escape.data'
            break
    onnx.save_model(graph,str(broken/'reference-s3.onnx'))
    _,record=native(cases[0]['directory'],'external-escape',False,broken);assert record['graph_runs']==0 and 'External tensor' in record['error'];passed+=1
    current(inputs)
    report=dict(passed=passed,actual_host_children=children,actual_ort_graph_runs=sum(r['graph_runs'] for r in runs),
        actual_ort_terminations=sum(r['terminated_runs'] for r in runs),successful_references=4,max_live_sessions=max(r['max_live_sessions'] for r in runs),
        trained_reference_components_loaded=2,publisher_models=lock['publisher_models'],complete_graph_tensor_identity_verified=manifest['full_graph_tensor_identity_verified'],
        original_publisher_graphs_used_for_references=True,upstream_audio_function_bodies=True,synthetic_pcm=True,
        reference_samples=[c['samples'] for c in cases],layouts=manifest['layouts'],assets=manifest['assets'],metrics=metrics,runs=runs,
        runtime_version=lock['host_runtime']['version'],runtime_sha256=lock['host_runtime']['sha256'],
        full_soulx_inference=False,language_backbone_executed=False,speech_generated=False,model_audio_quality_tested=False,
        physical_android=False,apk_runtime_used=False,engine_registered=False,input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['publisher_models','layouts','assets','metrics','runs','input_fingerprint']}),flush=True)

if __name__=='__main__':main()
