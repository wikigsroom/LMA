"""Extract linear UniPC updates from pinned Diffusers, without learned models.

UniPC is affine/linear in tensor state when dynamic thresholding is disabled.
Probing independent basis channels preserves its predictor/corrector, history,
warmup and final-order schedule without installing Python in the Android APK.
"""
import importlib.metadata
import math


def prepare(config,steps):
    import torch
    from diffusers import UniPCMultistepScheduler
    s=UniPCMultistepScheduler.from_config({**config,'timestep_spacing':'trailing'})
    s.set_timesteps(steps)
    # Diffusers 0.35.1's float np.arange occasionally includes an extra zero
    # endpoint (61 of 1000 steps), yielding timestep -1. Keep the requested
    # positive timesteps and its declared final sigma, never run that endpoint.
    corrected=len(s.timesteps)!=steps
    if corrected:
        assert len(s.timesteps)==steps+1 and int(s.timesteps[-1])==-1
        s.timesteps=s.timesteps[:steps]
        s.sigmas=torch.cat((s.sigmas[:steps],s.sigmas[-1:]))
    assert len(s.timesteps)==steps and bool((s.timesteps>=0).all())
    return s,corrected


def profiles(config, maximum=100):
    import torch
    from diffusers import UniPCMultistepScheduler
    assert importlib.metadata.version('diffusers')=='0.35.1'
    assert 1<=maximum<=100
    config={**config,'timestep_spacing':'trailing'}
    assert not config.get('thresholding',False)
    assert config.get('prediction_type','epsilon')=='epsilon'
    assert config.get('predict_x0',True) is True
    assert 1<=int(config.get('solver_order',2))<=3
    result=dict(schema='lma.linear-unipc/1',diffusersVersion='0.35.1',slots=['sample','noise','last_sample','model_latest','model_previous','model_oldest'],profiles={})
    basis=torch.eye(6,dtype=torch.float32)
    for steps in range(1,maximum+1):
        s,corrected=prepare(config,steps)
        rows=[]
        for i,t in enumerate(s.timesteps):
            order=s.config.solver_order
            s._step_index=i
            s.lower_order_nums=min(i,order)
            s.this_order=min(order,steps-i+1,i) if s.config.lower_order_final else min(order,i)
            s.last_sample=basis[2:3].clone() if i else None
            s.model_outputs=[None]*order
            s.timestep_list=[None]*order
            for back in range(min(i,order)):
                s.model_outputs[-(back+1)]=basis[3+back:4+back].clone()
                s.timestep_list[-(back+1)]=s.timesteps[i-1-back]
            converted=s.convert_model_output(basis[1:2],sample=basis[0:1])
            output=s.step(basis[1:2],t,basis[0:1],return_dict=False)[0]
            row=dict(timestep=float(t),sample=output.flatten().tolist(),lastSample=s.last_sample.flatten().tolist(),model=converted.flatten().tolist())
            assert all(math.isfinite(x) and abs(x)<1e8 for k in ('sample','lastSample','model') for x in row[k])
            rows.append(row)
        result['profiles'][str(steps)]=dict(initialNoiseSigma=float(s.init_noise_sigma),trailingEndpointCorrected=corrected,rows=rows)
    return result
