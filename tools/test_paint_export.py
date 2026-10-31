"""Exercise the real offline CLI with random architecture fixtures, no trained weights."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from evidence import fingerprint,current
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/paint-export-tests'


def main():
    sys.path[:0]=[str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    import torch
    from diffusers import AutoencoderKL
    from transformers import Dinov2Config,Dinov2Model
    from safetensors.torch import save_file
    from paint_graphs import construct
    from paint_reference import rrdb
    torch.set_num_threads(2);torch.manual_seed(7423);OUT.mkdir(exist_ok=True)
    inputs=fingerprint('tools/test_paint_export.py','tools/export_paint.py','tools/paint_reference.py','tools/paint_graphs.py','tools/paint_sampler.py','tools/paint_catalogue.py','tools/export_spatial.py','tools/spatial_reference.py','third_party/paint-source-lock.json','third_party/spatial-shape-source-lock.json')
    uc=dict(sample_size=8,in_channels=4,out_channels=4,layers_per_block=1,block_out_channels=[64,64],down_block_types=['CrossAttnDownBlock2D','DownBlock2D'],up_block_types=['UpBlock2D','CrossAttnUpBlock2D'],cross_attention_dim=1024,attention_head_dim=1,norm_num_groups=32)
    unet=OUT/'unet';unet.mkdir(exist_ok=True);(unet/'config.json').write_text(json.dumps(uc),'utf-8')
    model,_=construct(uc);save_file({k:v.contiguous().clone() for k,v in model.state_dict().items()},str(unet/'diffusion_pytorch_model.safetensors'));del model
    vae=AutoencoderKL(in_channels=3,out_channels=3,down_block_types=['DownEncoderBlock2D']*4,up_block_types=['UpDecoderBlock2D']*4,block_out_channels=[32]*4,layers_per_block=1,latent_channels=4,norm_num_groups=32,sample_size=64)
    vae.save_pretrained(OUT/'vae',safe_serialization=True);del vae
    image=Dinov2Model(Dinov2Config(hidden_size=1536,num_hidden_layers=1,num_attention_heads=24,mlp_ratio=1/24,image_size=28,patch_size=14));image.save_pretrained(OUT/'dino',safe_serialization=True);del image
    # Exact production RRDB architecture, initialized randomly. No learned
    # checkpoint is acquired or run; the CLI only traces a bounded 64px graph.
    sr=rrdb()(3,3,scale=4,num_feat=64,num_block=23,num_grow_ch=32);torch.save({'params_ema':sr.state_dict()},OUT/'upscaler.pth');del sr
    (OUT/'scheduler.json').write_text(json.dumps(dict(num_train_timesteps=1000,beta_start=.00085,beta_end=.012,beta_schedule='scaled_linear',prediction_type='epsilon')),'utf-8')
    output=OUT/'export'
    if output.exists():assert output.resolve().parent==OUT.resolve();shutil.rmtree(output)
    command=[sys.executable,str(ROOT/'tools/export_paint.py'),'--unet',str(unet),'--vae',str(OUT/'vae'),'--dino',str(OUT/'dino'),'--scheduler',str(OUT/'scheduler.json'),'--upscaler',str(OUT/'upscaler.pth'),'--image-size','64','--output',str(output)]
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')])}
    r=subprocess.run(command,capture_output=True,env=env,timeout=180);(OUT/'export.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,'Inspect build/paint-export-tests/export.log'
    checks=[]
    def check(case,value):assert value,case;checks.append(case)
    b=json.loads((output/'lma-bundle.json').read_text('utf-8'));check('real_cli_manifest',b['pipeline']=='hunyuan3d_21_paint' and b['evidence']['acquisition']=='import_only')
    for c in b['components']:
        f=output/c['path'];check('actual_bytes_'+c['role'],c['bytes']==f.stat().st_size and hashlib.sha256(f.read_bytes()).hexdigest()==c['sha256'] and c['url']=='')
    cfg=json.loads((output/'material-config.json').read_text('utf-8'));check('real_config',cfg['imageSize']==64 and cfg['dinoSize']==28 and cfg['dinoWidth']==1536 and cfg['views']==6)
    sampler=json.loads((output/'sampler.json').read_text('utf-8'));check('all_sampler_profiles',len(sampler['profiles'])==100 and len(sampler['profiles']['61']['rows'])==61)
    receipt=json.loads((output/'export-receipt.json').read_text('utf-8'));check('receipt_scope',not receipt['network'] and receipt['exportTracingExecutesDummyForwards'] and not receipt['completeModelInferenceTested'])
    r=subprocess.run(command,capture_output=True,env=env,timeout=20);check('existing_assets_preserved',r.returncode!=0)
    current(inputs);report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsDownloaded=0,completeModelsRun=0,randomNeuralGraphs=True,physicalDeviceTests=0,virtualizationUsed=False)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModelsRun=0)))


if __name__=='__main__':main()
