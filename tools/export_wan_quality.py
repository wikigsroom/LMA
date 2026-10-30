"""Archive exact retained Wan experiments; never refresh their original provenance.

Only the aggregation is current. Individual native Windows runs keep their actual
compilation and source fingerprints, including failed quality and resource limits.
"""
import argparse
import json
from pathlib import Path
import shutil

from evidence import current, fingerprint, version
from fetch_wan_trained import sha
from test_wan_trained import frame_stats

ROOT = Path(__file__).resolve().parents[1]


def local(value):
    path = (ROOT/value).resolve()
    if not path.is_relative_to(ROOT/'build'): raise ValueError('Use retained project-owned captures')
    return path


def main():
    from PIL import Image, ImageDraw
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('baseline','untiled','temporal','tile512','flow8','latents'):
        parser.add_argument('--'+key,required=True,help='Retained complete run directory')
    args=parser.parse_args()
    archive=ROOT/'verification/research/wan-quality';archive.mkdir(parents=True,exist_ok=True)
    media=ROOT/'docs/media/development/wan-quality';media.mkdir(parents=True,exist_ok=True)
    original_inputs=[];records={};files={};rows=[]
    for key in ('baseline','untiled','temporal','tile512','flow8','latents','official-vae'):
        folder=local(args.latents if key=='official-vae' else getattr(args,key))
        source=folder/('reference.json' if key=='official-vae' else 'result.json')
        target=archive/(key+'.json'); data=source.read_bytes()
        if target.exists() and target.read_bytes()!=data: raise ValueError('Never overwrite a different archived experiment')
        target.write_bytes(data);records[key]=report=json.loads(data)
        files[key]=dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target),bytes=len(data),
                        current_execution=False,original_provenance_preserved=True)
        original_inputs.append(source.relative_to(ROOT).as_posix())
        if key not in ('latents','official-vae'):
            request=report['request']; p=request['parameters']
            raw=folder/Path(request['output'].replace('\\','/')).name
            stats=frame_stats(raw)
            if stats['sha256']!=report['output']['sha256'] or report['process']['returncode']!=0: raise ValueError('Retained output changed')
            if tuple(stats[k] for k in ('width','height','frames','fps'))!=(512,288,17,8): raise ValueError('Full geometry must be retained')
            rows.append(dict(name=key,parameters=p,worker_sha256=report['compilation']['sha256'],rgb_sha256=stats['sha256'],
                             seconds=report['process']['seconds'],windows_observed_peak_working_set_bytes=report['process']['resources']['observed_peak_working_set_bytes'],
                             visible_later_frame_artifacts=True,video_quality_accepted=False))
            original_inputs.append(raw.relative_to(ROOT).as_posix())
    latent=records['latents'];ref=records['official-vae']
    if latent['generation_completed'] or latent['process']['returncode']==0: raise ValueError('Capture intentionally stops before video decode')
    if ref['capture_sha256']!=files['latents']['sha256'] or ref['latent_sha256']!=latent['latent']['sha256']: raise ValueError('Independent reference capture differs')
    if not ref['strict_weight_loading'] or ref['device']!='cpu' or ref['dtype']!='float32': raise ValueError('Unexpected reference method')
    if ref['comparison']['sha256']!=records['untiled']['output']['sha256']: raise ValueError('Independent comparison differs')
    if ref['source']['revision']!='9737cba9c1c3c4d04b33fcad41c111989865d315': raise ValueError('Unreviewed upstream reference')
    for key in ('untiled','temporal','tile512'):
        if records[key]['output']['sha256']!=records['untiled']['output']['sha256']: raise ValueError('Retained identical-output observation changed')
    # All three displayed frames are real generated frames, not repaired artwork.
    images=[Image.open(local(args.untiled)/'contact.png').convert('RGB'),
            Image.open(local(args.latents)/'official-vae.png').convert('RGB')]
    canvas=Image.new('RGB',(1536,696),(15,26,40));draw=ImageDraw.Draw(canvas)
    draw.text((8,8),'SAME ACTUAL LATENTS / CPP VAE ABOVE / OFFICIAL CPU VAE BELOW / BOTH QUALITY UNACCEPTED',fill='white')
    for index,img in enumerate(images):canvas.paste(img,(0,40+index*328));img.close()
    canvas.save(media/'vae-comparison.png')
    images=None
    legacy=ROOT/'docs/media/development/wan-trained'
    for old,new in [('default-frames.png','legacy-default-frames.png'),('default.gif','legacy-default.gif'),('default.mp4','legacy-default.mp4')]:
        destination=media/new
        if destination.exists() and destination.read_bytes()!=(legacy/old).read_bytes(): raise ValueError('Preserve original failed-quality media')
        shutil.copyfile(legacy/old,destination)
    original_inputs += [str((local(args.latents)/name).relative_to(ROOT)) for name in ['denoised.f32','official-vae.rgb','reference.json']]
    defaults=json.loads((ROOT/'research/wan_trained/catalogue-bundle.json').read_text(encoding='utf-8'))['parameters']['fields']
    if defaults['vaeTileSize']['default']!=128 or defaults['vaeTemporalTiling']['default'] is not False: raise ValueError('Do not silently increase default memory demand')
    inputs=fingerprint('tools/export_wan_quality.py','research/wan_latent_probe','tools/probe_wan_latents.py',
                       'tools/probe_wan_quality.py','research/wan_trained/catalogue-bundle.json',
                       'native/sd_worker.cpp','native/sd_policy.hpp',*original_inputs,
                       *[r['path'] for r in files.values()],
                       *[p.relative_to(ROOT).as_posix() for p in media.iterdir() if p.is_file()])
    report=dict(schema='lma.wan-quality-diagnosis/1',version=version(),aggregation_current=True,
                original_captures_are_current_validation=False,original_captures=files,experiments=rows,
                independent_vae_comparison=ref['comparison'],official_vae_revision=ref['source']['revision'],
                default_decoder=dict(vaeTileSize=128,vaeTemporalTiling=False),
                conclusion='Later-frame artifacts persist in the unchanged official F32 CPU VAE. Decoder tiling and MP4 composition do not explain this sample; full generator numerics/model quality remain unresolved.',
                media=[dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(media.iterdir()) if p.is_file()],
                physical_android=False,android_codec_tested=False,independent_diffusion_numerics_accepted=False,
                video_quality_accepted=False,resource_acceptance=False,complete_target16_accepted=False,
                complete_release_accepted=False,input_fingerprint=inputs)
    current(inputs)
    out=ROOT/'build/wan-quality/summary.json';out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(experiments=len(rows),archived_reports=len(files),quality_accepted=False,
                          reference_max_byte_error=ref['comparison']['maximum_absolute_byte_error'])))


if __name__=='__main__':main()
