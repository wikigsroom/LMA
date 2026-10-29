"""Render measured host conversion evidence; never an App/device screenshot."""
import hashlib
import json
import os
from pathlib import Path
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR'] = str(ROOT / 'build/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    before = fingerprint('tools/plot_ltx098_prepare.py')
    path = ROOT / 'verification/development/ltx098-prepare.json'
    raw = path.read_bytes(); result = json.loads(raw)
    current(result['input_fingerprint'])
    assert result['passed'] and result['actual_trained_conversions'] == 1
    trained = result['trained']; native = trained['native']; memory = trained['resources']
    source_bytes = native['source_bytes']; output_bytes = native['output_bytes']
    peak = memory['observed_peak_working_set_bytes']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.spines.left': False})
    fig = plt.figure(figsize=(14.4, 6.8), facecolor='#f7f9fc')
    fig.text(.055, .91, 'Old LTX 0.9.8: native asset preparation', fontsize=23, weight='bold', color='#152c45')
    fig.text(.055, .855, 'Actual trained checkpoint • native Windows host • independent whole-file byte identity', color='#455b72')
    ax = fig.add_axes([.20,.39,.72,.32], facecolor='#f7f9fc')
    values = [source_bytes/1e9, output_bytes/1e9]
    ax.barh([1,0], values, color=['#597b9e','#168b76'], height=.46)
    ax.set_yticks([1,0], ['Source\nsafetensors', 'Converted DiT\nGGUF F16 / F32'])
    ax.tick_params(axis='y', length=0, pad=15); ax.set_xlim(0,7.3)
    ax.set_xlabel('File size (decimal GB)');ax.set_xticks([0,2,4,6]);ax.grid(axis='x',alpha=.16);ax.set_axisbelow(True)
    for y,value,n in zip([1,0],values,[source_bytes,output_bytes]):
        ax.text(value+.12,y,f'{value:.3f} GB',va='center',weight='bold',color='#152c45')
        ax.text(value+.12,y-.16,f'{n:,} bytes',va='center',fontsize=9,color='#455b72')
    fig.text(.055,.27,'715 trained DiT tensors',fontsize=15,weight='bold',color='#152c45')
    fig.text(.055,.22,'1,923,385,472 parameters • all 944 source tensors streamed and hashed',fontsize=11,color='#455b72')
    fig.text(.055,.15,f'Observed host peak working set: {peak/1024**2:.2f} MiB',fontsize=13,color='#168b76',weight='bold')
    fig.text(.055,.107,'4 MiB input chunks • up to 8 MiB converted chunks • no complete tensor allocation',fontsize=11,color='#455b72')
    fig.text(.055,.04,'SOURCE / HOST CHECK ONLY — Android compiled; App integration, phone execution and Release gates remain open.',fontsize=10,color='#923d39')
    directory = ROOT / 'docs/media/development'; directory.mkdir(exist_ok=True)
    png = directory / 'ltx098-native-prepare.png';fig.savefig(png,dpi=144,facecolor=fig.get_facecolor());plt.close(fig)
    current(before);data=png.read_bytes()
    receipt=dict(schema='lma.ltx098-native-prepare-media/1',evidence_sha256=hashlib.sha256(raw).hexdigest(),
                 source_bytes=source_bytes,output_bytes=output_bytes,host_peak_working_set_bytes=peak,
                 png_bytes=len(data),png_sha256=hashlib.sha256(data).hexdigest(),
                 ui_recording=False,physical_android=False,inference_acceptance=False,release_ready=False,
                 input_fingerprint=before)
    (directory / 'ltx098-native-prepare.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='input_fingerprint'}))


if __name__=='__main__':main()
