"""Compare production native SoulX primitives to pinned upstream PyTorch bodies.

Synthetic PCM, noise, F0 and estimator fixtures; no trained model/audio output.
Reference functions are AST-extracted without changing arithmetic/control flow.
"""
import ast, hashlib, json, math, os, subprocess, warnings
from pathlib import Path
import typing
import numpy as np
import torch
import torch.nn.functional as F
from evidence import fingerprint, current
from fetch_soulx_dsp import validate_sources, test_references, LOCK
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/soulx-dsp-tests'


def functions(path, names=None, constants=False, classes=False, env=None):
    tree=ast.parse(path.read_text(encoding='utf-8')); nodes=[]
    for node in tree.body:
        if (isinstance(node,ast.FunctionDef) and (names is None or node.name in names)) or (classes and isinstance(node,ast.ClassDef) and node.name in names):
            # librosa's cache decorator is an optimization; its body is unchanged.
            node.decorator_list=[d for d in node.decorator_list if not (isinstance(d,ast.Call) and isinstance(d.func,ast.Name) and d.func.id=='cache')]
            nodes.append(node)
        elif constants and isinstance(node,ast.Assign): nodes.append(node)
    future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
    module=ast.fix_missing_locations(ast.Module(body=[future]+nodes,type_ignores=[]))
    namespace=dict(torch=torch,np=np,F=F,math=math,warnings=warnings,Tensor=torch.Tensor,overload=typing.overload,Tuple=typing.Tuple,Optional=typing.Optional,Union=typing.Union,ParameterError=ValueError)
    namespace.update(env or {}); exec(compile(module,str(path),'exec'),namespace); return namespace


def compile_host():
    setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
    if not setup.is_file(): raise RuntimeError('Native MSVC host compiler required')
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive: raise RuntimeError('No free ASCII alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        command=OUT/'compile.cmd'; command.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'
            'cl /nologo /O2 /W4 /fp:precise /EHsc /std:c++17 /DNDEBUG /I../../build/native-src/kissfft '
            '../../research/soulx/dsp.cpp ../../tests/native/soulx_dsp_test.cpp ../../build/native-src/kissfft/kiss_fft.c ../../build/native-src/kissfft/kiss_fftr.c /Fe:soulx-dsp-test.exe\n',encoding='utf-8')
        result=subprocess.run(['cmd','/d','/c','compile.cmd'],cwd=drive+'/build/soulx-dsp-tests',capture_output=True,timeout=120)
        (OUT/'compile.log').write_bytes(result.stdout+result.stderr)
        if result.returncode: raise RuntimeError('Inspect build/soulx-dsp-tests/compile.log')
    finally: subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)


def main():
    lock=json.loads(LOCK.read_text(encoding='utf-8')); validate_sources(lock); refs=test_references(lock)
    inputs=fingerprint('research/soulx','tests/native/soulx_dsp_test.cpp','tools/test_soulx_dsp.py','tools/fetch_soulx_dsp.py','third_party/soulx-dsp-source-lock.json')
    OUT.mkdir(exist_ok=True); (OUT/'results.json').unlink(missing_ok=True); compile_host(); torch.set_num_threads(4)
    audio=ROOT/'build/native-src/soulx-podcast/soulxpodcast/utils/audio.py'
    convert=functions(refs/'librosa/librosa/core/convert.py',['hz_to_mel','mel_to_hz','mel_frequencies','fft_frequencies'])
    librosa=functions(refs/'librosa/librosa/filters.py',['mel'],env=convert)
    upstream=functions(audio,['audio_volume_normalize','mel_spectrogram','spectral_normalize_torch','dynamic_range_compression_torch'],env={'librosa_mel_fn':librosa['mel'],'mel_basis':{},'hann_window':{}})
    s3root=ROOT/'build/native-src/s3tokenizer/s3tokenizer'
    with np.load(s3root/'assets/mel_filters.npz',allow_pickle=False) as archive: filters=archive['mel_128'].copy()
    s3=functions(s3root/'utils.py',['log_mel_spectrogram'],env={'_mel_filters':lambda device,n:torch.from_numpy(filters).to(device)})
    kaldi=functions(refs/'torchaudio/torchaudio/compliance/kaldi.py',constants=True)
    sinc=functions(refs/'torchaudio/torchaudio/functional/functional.py',['_get_sinc_resample_kernel','_apply_sinc_resample_kernel','resample'],env={'_CPU':torch.device('cpu')})
    layers=ROOT/'build/native-src/soulx-podcast/soulxpodcast/models/modules/hifigan_components/layers.py'
    nsf=functions(layers,['SineGen2'],classes=True)['SineGen2'](24000,480,8,voiced_threshold=10)
    # Use the actual HiFT _stft/_istft methods without allocating its trained net.
    hift_tree=ast.parse((layers.parent.parent/'hifigan.py').read_text(encoding='utf-8'))
    hift_class=next(n for n in hift_tree.body if isinstance(n,ast.ClassDef) and n.name=='HiFTGenerator')
    hift_ns={'torch':torch}; methods=[n for n in hift_class.body if isinstance(n,ast.FunctionDef) and n.name in ['_stft','_istft']]
    exec(compile(ast.fix_missing_locations(ast.Module(body=methods,type_ignores=[])),str(layers.parent.parent/'hifigan.py'),'exec'),hift_ns)
    hift=typing.cast(typing.Any, type('SpectralReference',(),{})()); hift.istft_params={'n_fft':16,'hop_len':4}; hift.stft_window=torch.hann_window(16)
    metrics=[]; checks=0; processes=0
    def run(op,x,*extra):
        nonlocal processes
        tag=f'{processes:04d}'; src=OUT/(tag+'-input.f32'); dst=OUT/(tag+'-output.f32'); np.asarray(x,dtype='<f4').tofile(src)
        paths=[]
        for i,v in enumerate(extra):
            p=OUT/(tag+'-extra-'+str(i)+'.f32');np.asarray(v,dtype='<f4').tofile(p);paths.append(str(p))
        result=subprocess.run([str(OUT/'soulx-dsp-test.exe'),op,str(src),str(dst)]+paths,capture_output=True,text=True,encoding='utf-8',timeout=60);processes+=1
        if result.returncode: raise RuntimeError(op+': '+result.stderr)
        shapes=[json.loads(line) for line in result.stdout.splitlines()]
        if op=='reference':
            return [np.fromfile(str(dst)+'.'+suffix,dtype='<f4').reshape(s['rows'],s['cols']) for suffix,s in zip(['s3','flow','speaker'],shapes)]
        shape=shapes[-1]; return np.fromfile(dst,dtype='<f4').reshape(shape['rows'],shape['cols'])
    def compare(name,actual,expected,maximum,rmse=None):
        nonlocal checks
        expected=np.asarray(expected,dtype=np.float32)
        if actual.shape!=expected.shape: raise AssertionError((name,actual.shape,expected.shape))
        if not np.isfinite(actual).all(): raise AssertionError(name+' non-finite')
        delta=np.asarray(actual,dtype=np.float64)-expected; peak=float(np.max(np.abs(delta))); rms=float(np.sqrt(np.mean(delta**2)))
        if peak>maximum or (rmse is not None and rms>rmse): raise AssertionError((name,peak,rms,maximum,rmse))
        metrics.append(dict(name=name,shape=list(actual.shape),max_absolute_error=peak,rmse=rms,max_allowed=maximum,rmse_allowed=rmse)); checks+=3
    compare('S3 Slaney bank vs publisher npz',run('filters',[128]),filters,1e-8)
    compare('Flow Slaney bank vs librosa',run('filters',[80]),librosa['mel'](sr=24000,n_fft=1920,n_mels=80,fmin=0,fmax=8000),1e-8)
    rng=np.random.default_rng(9274)
    for index,length in enumerate([24000,24001,73123,360000]):
        pcm=(rng.standard_normal(length)*.06).astype('f4')
        if index==1: pcm*=.005
        pcm[0]=.2; pcm[-1]=-.15
        normalized=upstream['audio_volume_normalize'](torch.from_numpy(pcm.copy()))
        compare('volume-'+str(index),run('normalize',pcm),normalized[None,:],2e-7)
        resampled=sinc['resample'](torch.from_numpy(pcm),24000,16000)
        compare('sinc-'+str(index),run('resample',pcm),resampled.numpy()[None,:],3e-7)
        norm16=upstream['audio_volume_normalize'](resampled.clone()); tensor16=torch.as_tensor(norm16)
        expected_s3=s3['log_mel_spectrogram'](tensor16).numpy()
        expected_flow=upstream['mel_spectrogram'](torch.as_tensor(normalized)[None,:]).numpy()[0];expected_flow=expected_flow[:,:expected_flow.shape[1]//2*2]
        expected_speaker=kaldi['fbank'](tensor16[None,:],num_mel_bins=80,dither=0,sample_frequency=16000); expected_speaker-=expected_speaker.mean(dim=0,keepdim=True)
        combined=run('reference',pcm)
        # Distinct float32 FFT kernels can differ at quiet, narrow mel bins;
        # keep both a per-element bound and a much tighter aggregate bound.
        compare('S3-'+str(index),combined[0],expected_s3,5e-5,2e-6)
        compare('Flow-'+str(index),combined[1],expected_flow,2e-5,2e-6)
        # Log-power amplifies float32 FFT cancellation at quiet bins. Bound
        # individual differences to 1e-3 natural-log units and aggregate 2e-5.
        compare('CAMP CMN-'+str(index),combined[2],expected_speaker.numpy(),1e-3,2e-5)
    for index,pcm in enumerate([np.zeros(24000,'f4'),np.linspace(-2,2,24000,dtype='f4'),np.ones(15,dtype='f4')*.00001]):
        expected=upstream['audio_volume_normalize'](torch.from_numpy(pcm.copy()))
        compare('volume-edge-'+str(index),run('normalize',pcm),expected[None,:],2e-7)
    for frames in [1,7,103]:
        source=(rng.standard_normal(frames*480)*.03).astype('f4'); tensor=torch.from_numpy(source)[None,:]
        real,imag=hift_ns['_stft'](hift,tensor); expected=torch.cat([real,imag],dim=1)[0].numpy()
        compare('HiFT STFT-'+str(frames),run('stft',source),expected,2e-7)
        magnitude=torch.sqrt(real**2+imag**2);phase=torch.atan2(imag,real)
        wave=hift_ns['_istft'](hift,magnitude,phase).clamp(-.99,.99).numpy()
        compare('HiFT ISTFT-'+str(frames),run('istft',magnitude.numpy(),phase.numpy()),wave,2e-7)
    # Actual neural-output contract, including magnitude clipping and final PCM clamp.
    mag=torch.from_numpy((rng.random((1,9,241))*120).astype('f4'));phase=torch.from_numpy((rng.random((1,9,241))*6-3).astype('f4'))
    compare('HiFT spectral clipping',run('istft',mag.numpy(),phase.numpy()),hift_ns['_istft'](hift,mag,phase).clamp(-.99,.99).numpy(),2e-5)
    for frames in [1,7,50,1500,6000]:
        f0=np.asarray(([0,220,240,10,440,0,180]*((frames+6)//7))[:frames],dtype='f4')
        expanded=F.interpolate(torch.from_numpy(f0)[None,None,:],scale_factor=480,mode='nearest').transpose(1,2)
        # randn_like preserves the upstream transposed tensor's strides; a
        # contiguous randn of the same shape consumes/matches different values.
        torch.manual_seed(735); sines=nsf._f02sine(expanded*torch.arange(1,10)[None,None,:]); noise=torch.randn_like(sines)
        torch.manual_seed(735)
        expected=nsf(expanded)[0][0].numpy()
        compare('HiFT NSF-'+str(frames),run('nsf',f0,noise.numpy()),expected,2e-6,2e-7)
    for steps in [1,15,100]:
        times=1-torch.cos(torch.linspace(0,1,steps+1)*.5*torch.pi)
        compare('Flow cosine-'+str(steps),run('schedule',[steps]),times.numpy()[None,:],2e-7)
    # Extract the actual upstream Euler loop and feed its recorded velocities
    # to the native update primitive. The estimator is a non-model fixture.
    flow_path=layers.parent.parent/'flow.py';flow_ast=ast.parse(flow_path.read_text(encoding='utf-8'))
    cls=next(n for n in flow_ast.body if isinstance(n,ast.ClassDef) and n.name=='CausalConditionalCFM')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='solve_euler')
    ns={'torch':torch};exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),str(flow_path),'exec'),ns)
    recorded=[]
    def estimator(x,mask,mu,t,spks,cond,streaming):
        velocity=x*.2+mu*.3+cond*.1+spks.unsqueeze(-1)*.01+t[:,None,None]
        recorded.append(velocity.clone());return velocity
    fixture=type('FlowReference',(),{})();fixture.estimator=estimator;fixture.inference_cfg_rate=.7
    torch.manual_seed(247);initial=torch.randn(1,80,6); mu=torch.randn_like(initial); cond=torch.randn_like(initial);spk=torch.randn(1,80);mask=torch.ones(1,1,6)
    times=1-torch.cos(torch.linspace(0,1,16)*.5*torch.pi)
    expected=ns['solve_euler'](fixture,initial.clone(),times,mu,mask,spk,cond)
    state=initial.numpy().reshape(-1);t=times[0];dt=times[1]-times[0]
    for step,vel in enumerate(recorded):
        c,u=vel.numpy(); packed=np.concatenate([[float(dt),.7],state,c.reshape(-1),u.reshape(-1)])
        state=run('euler',packed).reshape(-1);t=t+dt
        if step<14:dt=times[step+2]-t
    compare('Actual upstream 15-step Flow Euler loop',state.reshape(1,80,6),expected.numpy(),5e-6)
    guarded=int(run('guards',[0])[0,0]); checks+=guarded
    if guarded<29:raise AssertionError('Guard assertions unexpectedly missing')
    cancelled=run('cancel',np.zeros(24000,'f4'));assert cancelled[0,0]>=5;checks+=1
    current(inputs)
    report=dict(passed=checks,actual_host_children=processes,metrics=metrics,guard_assertions=guarded,
        actual_upstream_function_bodies=True,upstream_s3_filter_asset_test_only=True,torch_version=torch.__version__,
        native_library_under_test=True,apk_runtime_used=False,synthetic_pcm_and_estimator=True,trained_checkpoints_loaded=0,
        generated_model_audio=False,model_inference=False,physical_android=False,engine_registered=False,
        input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['metrics','input_fingerprint']}))

if __name__=='__main__':main()
