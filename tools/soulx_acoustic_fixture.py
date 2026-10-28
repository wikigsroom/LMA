"""UNTRAINED complete-architecture fixtures and actual upstream CPU references."""
import gc,json
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from export_soulx import environment


def checkpoints(directory):
    environment()
    from soulxpodcast.models.modules.flow import CausalMaskedDiffWithXvec
    from soulxpodcast.models.modules.hifigan import HiFTGenerator
    torch.set_num_threads(4);torch.manual_seed(713);directory.mkdir(parents=True,exist_ok=True)
    flow=CausalMaskedDiffWithXvec().eval();flow_count=sum(p.numel() for p in flow.parameters());torch.save(flow.state_dict(),directory/'flow.pt');del flow;gc.collect()
    hift=HiFTGenerator().eval();hift_count=sum(p.numel() for p in hift.parameters())
    # Exercise the voiced NSF branch using a known fixture F0 bias; this is
    # deliberately synthetic, not a claim about any publisher checkpoint.
    with torch.no_grad():hift.f0_predictor.classifier.bias.fill_(220)
    torch.save({'generator.'+k:v for k,v in hift.state_dict().items()},directory/'hift.pt')
    return dict(flow_parameters=flow_count,hift_parameters=hift_count,trained=False)


def save(directory,name,tensor):
    value=tensor.detach().cpu().numpy().astype('<f4');value.tofile(directory/(name+'.f32'))
    return dict(file=name+'.f32',shape=list(value.shape))


def references(checkpoint_dir,directory):
    environment()
    from soulx_acoustic import strict_checkpoint
    from soulxpodcast.models.modules.flow import CausalMaskedDiffWithXvec
    from soulxpodcast.models.modules.hifigan import HiFTGenerator
    torch.set_num_threads(4);directory.mkdir(parents=True,exist_ok=True)
    flow=CausalMaskedDiffWithXvec();strict_checkpoint(flow,checkpoint_dir/'flow.pt')
    hift=HiFTGenerator();strict_checkpoint(hift,checkpoint_dir/'hift.pt',generator_prefix=True)
    metadata=[]
    for index,(prompt,total) in enumerate([(3,9),(4,17)]):
        case=directory/('case-'+str(index));case.mkdir(exist_ok=True);golden=case/'golden';golden.mkdir(exist_ok=True)
        torch.manual_seed(953+index);tokens=torch.randint(0,6561,(1,total));speaker=torch.randn(1,192)
        prompt_mel=torch.randn(1,prompt*2,80)*.25
        tokens.numpy().astype('<i8').tofile(case/'tokens.i64');save(case,'speaker',speaker);save(case,'prompt-mel',prompt_mel.transpose(1,2).contiguous())
        shapes={};velocities=[]
        def capture(module,args,kwargs):
            shapes['flow_mu']=save(golden,'flow_mu',kwargs['mu']);shapes['flow_spks']=save(golden,'flow_spks',kwargs['spks'])
        def velocity(module,args,output):velocities.append(output.detach().clone())
        before=flow.decoder.register_forward_pre_hook(capture,with_kwargs=True);hook=flow.decoder.estimator.register_forward_hook(velocity)
        torch.manual_seed(243+index);initial=torch.randn(1,80,total*2);save(case,'flow-noise',initial)
        torch.manual_seed(243+index)
        with torch.inference_mode():
            mel,_=flow(tokens,torch.tensor([total]),prompt_mel,torch.tensor([prompt*2]),speaker,streaming=False,finalize=True)
            mel=mel[:,:,prompt*2:];shapes['mel']=save(golden,'mel',mel)
            f0=hift.f0_predictor(mel);shapes['f0']=save(golden,'f0',f0)
            expanded=hift.f0_upsamp(f0[:,None]).transpose(1,2);nsf=hift.m_source.l_sin_gen
            torch.manual_seed(735+index);sines=nsf._f02sine(expanded*torch.arange(1,10)[None,None,:]);noise=torch.randn_like(sines)
            save(case,'nsf-noise',noise.contiguous())
            torch.manual_seed(735+index);wave,source=hift(mel)
            shapes['source']=save(golden,'source',source);shapes['wave']=save(golden,'wave',wave)
        before.remove();hook.remove()
        for step,v in enumerate(velocities):shapes['flow_velocity_'+str(step)]=save(golden,'flow_velocity_'+str(step),v)
        request=dict(format='lma.soulx-acoustic-input/1',prompt_tokens=prompt,steps=15,threads=2,seed=243+index,cfg=.7,inject_noise=True,trace=True)
        (case/'input.json').write_text(json.dumps(request,indent=2)+'\n',encoding='utf-8')
        metadata.append(dict(directory=case.name,total_tokens=total,prompt_tokens=prompt,shapes=shapes,samples=wave.numel(),synthetic_parameters=True))
    (directory/'cases.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    return metadata


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['checkpoints','references']);parser.add_argument('directory',type=Path);parser.add_argument('--checkpoint-dir',type=Path)
    args=parser.parse_args()
    result=checkpoints(args.directory) if args.mode=='checkpoints' else references(args.checkpoint_dir,args.directory)
    print(json.dumps(result),flush=True)
