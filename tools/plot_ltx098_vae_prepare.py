"""Show actual prepared-asset decoder outputs; synthetic inputs, no phone footage."""
import hashlib
import json
import math
import os
from pathlib import Path
from evidence import fingerprint,current
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'build/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    before=fingerprint('tools/plot_ltx098_vae_prepare.py')
    path=ROOT/'verification/development/ltx098-vae-prepare.json';raw=path.read_bytes();result=json.loads(raw)
    current(result['input_fingerprint']);assert result['passed'] and result['actual_trained_decode_jobs']==4
    directory=ROOT/result['artifacts_directory'];assert directory.resolve().is_relative_to((ROOT/'build').resolve())
    oracle=result['original_reference'];reference_dir=ROOT/'build/ltx098-vae-tests/references'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
    fig,axes=plt.subplots(4,3,figsize=(15.5,10.6),gridspec_kw={'width_ratios':[1,1,1.65]})
    fig.set_facecolor('#f7f9fc');fig.subplots_adjust(left=.055,right=.96,bottom=.12,top=.77,wspace=.1,hspace=.32)
    fig.text(.055,.95,'Old LTX VAE: decoding with natively prepared assets',fontsize=23,weight='bold',color='#152c45')
    fig.text(.055,.902,'Actual trained decoder • synthetic latent inputs • host ORT CPU • no prompt-to-video or phone acceptance',fontsize=12,color='#923d39')
    peak=result['conversion_resources']['observed_peak_working_set_bytes']/1024**2
    fig.text(.055,.853,f'18 assets / 2.212 GB match Python bytes • 134 learned source tensors • preparation peak {peak:.2f} MiB (host)',color='#455b72')
    sources=[]
    for row,case in enumerate(oracle['cases']):
        name=case['name'];assert name==f'case-{row}'
        original=reference_dir/case['files']['output'];native=directory/(name+'.f32')
        original_raw=original.read_bytes();native_raw=native.read_bytes()
        ref=oracle['files'][case['files']['output']]
        assert len(original_raw)==ref['bytes'] and hashlib.sha256(original_raw).hexdigest()==ref['sha256']
        shape=case['output_shape'];assert len(native_raw)==len(original_raw)==math.prod(shape)*4
        a=np.frombuffer(native_raw,dtype='<f4').astype(np.float64);b=np.frombuffer(original_raw,dtype='<f4').astype(np.float64)
        delta=a-b;maximum=float(np.max(np.abs(delta)));relative=float(np.sqrt(np.mean(delta*delta)))/max(float(np.sqrt(np.mean(b*b))),1e-12)
        metric=next(m for m in result['metrics'] if m['case']==name and m['stage']==9)
        assert math.isclose(maximum,metric['max_absolute_error'],rel_tol=1e-12,abs_tol=1e-15)
        assert math.isclose(relative,metric['relative_rmse'],rel_tol=1e-12,abs_tol=1e-15)
        center=shape[2]//2
        for col,blob in enumerate([original_raw,native_raw]):
            frame=np.frombuffer(blob,dtype='<f4').reshape(shape)[0,:,center].transpose(1,2,0)
            rgb=((np.clip(frame,-1,1)+np.float32(1))*np.float32(127.5)).astype(np.uint8)
            axes[row,col].imshow(rgb,interpolation='nearest');axes[row,col].axis('off')
        axes[row,2].axis('off');axes[row,2].text(.02,.94,f'{shape[2]} frames • {shape[4]} × {shape[3]} RGB',weight='bold',fontsize=14,color='#152c45',va='top')
        axes[row,2].text(.02,.70,f'Full-output max |error|: {maximum:.6g}\nRelative RMSE: {relative:.6g}\n9 sequential sessions loaded / unloaded',linespacing=1.65,color='#455b72',va='top')
        sources.append(dict(case=name,frame=center,native_file=native.relative_to(ROOT).as_posix(),native_bytes=len(native_raw),
                            native_sha256=hashlib.sha256(native_raw).hexdigest(),original_file=case['files']['output'],
                            original_sha256=ref['sha256'],metric=metric))
    axes[0,0].set_title('Original PyTorch decoder',fontsize=13,pad=14)
    axes[0,1].set_title('Native decoder / prepared assets',fontsize=13,pad=14)
    axes[0,2].set_title('Geometry and raw F32 comparison',fontsize=13,pad=14,loc='left')
    fig.text(.055,.064,'Display clips values to [-1, 1]; numerical comparisons use every raw F32 element. Images do not establish generation quality.',fontsize=10,color='#455b72')
    fig.text(.055,.031,'SOURCE / HOST ONLY — ARM64 compiled; production App, phone execution and complete Release gates remain open.',fontsize=10,color='#923d39')
    out=ROOT/'docs/media/development';png=out/'ltx098-vae-prepared-decode.png';fig.savefig(png,dpi=144,facecolor=fig.get_facecolor());plt.close(fig)
    current(before);data=png.read_bytes()
    receipt=dict(schema='lma.ltx098-vae-prepared-media/1',evidence_sha256=hashlib.sha256(raw).hexdigest(),sources=sources,
                 png_bytes=len(data),png_sha256=hashlib.sha256(data).hexdigest(),host_preparation_peak_bytes=result['conversion_resources']['observed_peak_working_set_bytes'],
                 native_children_executed_this_tool=0,capture_reused=True,synthetic_latent_inputs=True,
                 ui_recording=False,physical_android=False,prompt_to_video_quality_accepted=False,release_ready=False,input_fingerprint=before)
    (out/'ltx098-vae-prepared-decode.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['input_fingerprint','sources']}),flush=True)


if __name__=='__main__':main()
