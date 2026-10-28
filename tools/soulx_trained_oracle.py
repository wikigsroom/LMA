"""Original full trained Flow/HiFT forward references with prepared S3/CAMP inputs.

Generated codes come from synthetic target PCM, never a language backbone;
these tests are acoustic reconstruction, not usable text-to-speech/quality.
"""
import json
from pathlib import Path
import numpy as np
import torch
from export_soulx import environment


def save(directory,name,value):
    value=value.detach().cpu().numpy().astype('<f4');value.tofile(directory/(name+'.f32'));return dict(file=name+'.f32',shape=list(value.shape))


def references(source,output):
    environment()
    from soulx_acoustic import strict_checkpoint
    from soulxpodcast.models.modules.flow import CausalMaskedDiffWithXvec
    from soulxpodcast.models.modules.hifigan import HiFTGenerator
    root=Path(__file__).resolve().parents[1];torch.set_num_threads(4);output.mkdir(parents=True,exist_ok=True)
    flow=CausalMaskedDiffWithXvec();strict_checkpoint(flow,source/'flow.pt')
    hift=HiFTGenerator();strict_checkpoint(hift,source/'hift.pt',generator_prefix=True)
    metadata=[]
    for index,(ref,target) in enumerate([(0,1),(1,0)]):
        original=root/'build/soulx-reference-tests/native-results'/('reference-'+str(ref))
        destination=root/'build/soulx-reference-tests/native-results'/('reference-'+str(target))
        codes=np.fromfile(original/'tokens.i64',dtype='<i8');generated=np.fromfile(destination/'tokens.i64',dtype='<i8')
        prompt=len(codes);total=prompt+len(generated)
        speaker=torch.from_numpy(np.fromfile(original/'speaker.f32',dtype='<f4').reshape(1,192))
        prompt_mel=torch.from_numpy(np.fromfile(original/'prompt-mel.f32',dtype='<f4').reshape(1,80,2*prompt)).transpose(1,2).contiguous()
        tokens=torch.from_numpy(np.r_[codes,generated].astype('<i8')[None,:])
        case=output/('case-'+str(index));case.mkdir(exist_ok=True);golden=case/'golden';golden.mkdir(exist_ok=True)
        tokens.numpy().astype('<i8').tofile(case/'tokens.i64');save(case,'speaker',speaker);save(case,'prompt-mel',prompt_mel.transpose(1,2).contiguous())
        shapes={};velocities=[]
        def capture(module,args,kwargs):
            shapes['flow_mu']=save(golden,'flow_mu',kwargs['mu']);shapes['flow_spks']=save(golden,'flow_spks',kwargs['spks'])
        def velocity(module,args,output):velocities.append(output.detach().clone())
        before=flow.decoder.register_forward_pre_hook(capture,with_kwargs=True);hook=flow.decoder.estimator.register_forward_hook(velocity)
        torch.manual_seed(1427+index);save(case,'flow-noise',torch.randn(1,80,total*2));torch.manual_seed(1427+index)
        with torch.inference_mode():
            mel,_=flow(tokens,torch.tensor([total]),prompt_mel,torch.tensor([prompt*2]),speaker,streaming=False,finalize=True)
            mel=mel[:,:,prompt*2:];shapes['mel']=save(golden,'mel',mel)
            f0=hift.f0_predictor(mel);shapes['f0']=save(golden,'f0',f0)
            expanded=hift.f0_upsamp(f0[:,None]).transpose(1,2);nsf=hift.m_source.l_sin_gen
            torch.manual_seed(1133+index);sines=nsf._f02sine(expanded*torch.arange(1,10)[None,None,:]);save(case,'nsf-noise',torch.randn_like(sines).contiguous())
            torch.manual_seed(1133+index);wave,source_wave=hift(mel);shapes['source']=save(golden,'source',source_wave);shapes['wave']=save(golden,'wave',wave)
        before.remove();hook.remove()
        for step,value in enumerate(velocities):shapes['flow_velocity_'+str(step)]=save(golden,'flow_velocity_'+str(step),value)
        (case/'input.json').write_text(json.dumps(dict(format='lma.soulx-acoustic-input/1',prompt_tokens=prompt,steps=15,threads=2,seed=1427+index,cfg=.7,inject_noise=True,trace=True)),encoding='utf-8')
        metadata.append(dict(directory=case.name,prompt_tokens=prompt,generated_tokens=len(generated),samples=wave.numel(),shapes=shapes,
            semantic_codes_from_trained_reference_models=True,semantic_codes_from_language_backbone=False,source_pcm_synthetic=True))
    (output/'cases.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8');return metadata


def isolate(source,output):
    """Hold native intermediate inputs fixed to locate backend FP32 drift."""
    environment()
    from soulx_acoustic import strict_checkpoint
    from soulxpodcast.models.modules.hifigan import HiFTGenerator
    torch.set_num_threads(4);hift=HiFTGenerator();strict_checkpoint(hift,source/'hift.pt',generator_prefix=True)
    cases=json.loads((output/'references/cases.json').read_text(encoding='utf-8'));metrics=[]
    for sequence,index in enumerate([0,1,0]):
        case=cases[index];prefix=output/'native-results'/('reconstruction-'+str(sequence));frames=case['samples']//480;columns=frames*120+1
        def tensor(stage,shape):return torch.from_numpy(np.fromfile(str(prefix)+'-'+stage+'.f32',dtype='<f4').reshape(shape))
        def compare(stage,actual,expected,peak_limit,rms_limit):
            delta=actual.detach().cpu().numpy().astype('f8')-expected.detach().cpu().numpy();peak=float(np.max(np.abs(delta)));rms=float(np.sqrt(np.mean(delta*delta)))
            assert peak<=peak_limit and rms<=rms_limit,(sequence,stage,peak,rms)
            metrics.append(dict(case=sequence,stage=stage,maximum_absolute_error=peak,rmse=rms,maximum_allowed=peak_limit,rmse_allowed=rms_limit))
        mel=tensor('mel',(1,80,frames));f0=tensor('f0',(1,frames));native_source=tensor('source',(1,1,case['samples']))
        wave=torch.from_numpy(np.fromfile(str(prefix)+'.f32',dtype='<f4').reshape(1,-1))
        with torch.inference_mode():
            compare('f0_same_mel',hift.f0_predictor(mel),f0,.001,.0004)
            torch.manual_seed(1133+index);original_source=hift.m_source(hift.f0_upsamp(f0[:,None]).transpose(1,2))[0].transpose(1,2)
            compare('source_same_f0',original_source,native_source,1e-6,2e-8)
            compare('decode_same_mel_and_source',hift.decode(mel,native_source),wave,1e-5,2e-6)
            magnitude=tensor('magnitude',(1,9,columns));phase=tensor('phase',(1,9,columns))
            compare('istft_same_spectra',torch.clamp(hift._istft(magnitude,phase),-.99,.99),wave,1e-6,1e-7)
    (output/'isolation.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8');return metrics


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--isolate',action='store_true');args=p.parse_args()
    print(json.dumps(isolate(args.source,args.output) if args.isolate else references(args.source,args.output)),flush=True)
