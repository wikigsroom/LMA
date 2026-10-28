"""Trained acoustic reconstruction using native prepared S3/CAMP references.

No text, language backbone, human voice sample, APK endpoint or phone execution.
All four model components require explicit developer preparation beforehand.
"""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from evidence import fingerprint,current
from export_soulx import environment
from fetch_soulx_reference import sha
from fetch_soulx_trained import verify,DIRECTORY
from soulx_native_checks import compile_host
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/soulx-trained-tests'


def execute(command,log,timeout=600):
    result=subprocess.run([str(x) for x in command],cwd=ROOT,capture_output=True,timeout=timeout)
    log.write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Inspect '+str(log.relative_to(ROOT)))


def main():
    environment();OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    trained=verify();reference=json.loads((ROOT/'build/soulx-reference-tests/results.json').read_text(encoding='utf-8'))
    current(reference['input_fingerprint']);assert reference['trained_reference_components_loaded']==2 and reference['passed']>=145
    inputs=fingerprint('research/soulx_acoustic','research/soulx_ort','research/soulx','research/soulx_reference','native/moss_nano/onnx_external.hpp',
        'tools/test_soulx_trained.py','tools/soulx_trained_oracle.py','tools/export_soulx.py','tools/soulx_acoustic.py','tools/soulx_native_checks.py',
        'tools/fetch_soulx_trained.py','tools/fetch_soulx_reference.py','tools/fetch_soulx_dsp.py',
        'third_party/soulx-trained-assets.json','third_party/soulx-acoustic-source-lock.json','third_party/soulx-reference-source-lock.json')
    lock=json.loads((ROOT/'third_party/soulx-acoustic-source-lock.json').read_text(encoding='utf-8'))
    pack=OUT/'pack';receipt=OUT/'conversion-receipt.json'
    export_inputs=fingerprint('tools/export_soulx.py','tools/soulx_acoustic.py','third_party/soulx-acoustic-source-lock.json','third_party/soulx-trained-assets.json')
    valid=False
    if receipt.exists():
        old=json.loads(receipt.read_text(encoding='utf-8'))
        if old['input_fingerprint']==export_inputs:
            valid=all((pack/name).is_file() and sha(pack/name)==digest for name,digest in old['files'].items())
    if not valid:
        if pack.exists():
            if pack.resolve().parent!=OUT.resolve():raise RuntimeError('Unsafe trained test cache cleanup')
            shutil.rmtree(pack)
        print('Execute production exporter with publisher TRAINED Flow/HiFT checkpoints',flush=True)
        execute([sys.executable,'tools/export_soulx.py','--checkpoint-dir',DIRECTORY,'--output-dir',pack],OUT/'export.log')
        receipt.write_text(json.dumps(dict(input_fingerprint=export_inputs,files={p.name:sha(p) for p in pack.iterdir() if p.is_file()}),indent=2)+'\n',encoding='utf-8')
    manifest=json.loads((pack/'soulx-acoustic.json').read_text(encoding='utf-8'))
    assert manifest['synthetic_parameters'] is None and not manifest['complete_soulx_model']
    known={m['file']:m for m in trained['models']}
    assert all(x['sha256']==known[x['file']]['sha256'] and x['bytes']==known[x['file']]['bytes'] for x in manifest['checkpoint_sources'])
    print('Original trained upstream forward: native reference codes/speaker/mel and synthetic target PCM codes',flush=True)
    execute([sys.executable,'tools/soulx_trained_oracle.py','--source',DIRECTORY,'--output',OUT/'references'],OUT/'references.log')
    cases=json.loads((OUT/'references/cases.json').read_text(encoding='utf-8'));exe=compile_host(lock,OUT,'soulx_acoustic')
    results=OUT/'native-results';results.mkdir(exist_ok=True);runs=[];metrics=[];passed=4
    for sequence,index in enumerate([0,1,0]):
        case=cases[index];output=results/('reconstruction-'+str(sequence)+'.f32');output.unlink(missing_ok=True)
        result=subprocess.run([str(exe),str(pack),str(OUT/'references'/case['directory']),str(output)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        (results/(output.stem+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        if not result.stdout.strip():raise RuntimeError('Trained native process failed before receipt')
        record=json.loads(result.stdout.strip().splitlines()[-1]);runs.append(record)
        assert result.returncode==0 and record['ok'] and record['graph_runs']==18 and record['session_loads']==4 and record['session_unloads']==4 and record['max_live_sessions']==1;passed+=6
        assert record['samples']==case['samples'] and record['synthetic_parameters_declared'] is None;passed+=2
        for stage,item in case['shapes'].items():
            actual_path=output if stage=='wave' else results/(output.stem+'-'+stage+'.f32')
            actual=np.fromfile(actual_path,dtype='<f4').reshape(item['shape']);expected=np.fromfile(OUT/'references'/case['directory']/'golden'/item['file'],dtype='<f4').reshape(item['shape'])
            delta=np.asarray(actual,dtype=np.float64)-expected;peak=float(np.max(np.abs(delta)));rms=float(np.sqrt(np.mean(delta*delta)))
            # Trained F0 has measured sub-millihertz FP32 backend differences.
            # Their phase accumulation needs a separate reconstruction gate;
            # retain the original tighter untrained-suite limits unchanged.
            limit=.001 if stage=='wave' else .002 if stage.startswith('flow_velocity') or stage in ['mel','f0'] else .0005
            assert np.isfinite(actual).all() and peak<=limit,(sequence,stage,peak,rms,limit)
            item_metric=dict(case=sequence,stage=stage,shape=item['shape'],maximum_absolute_error=peak,rmse=rms,maximum_allowed=limit)
            if stage=='wave':
                signal=float(np.sqrt(np.mean(np.asarray(expected,dtype=np.float64)**2)));snr=float(20*np.log10(signal/max(rms,1e-30)))
                assert rms<=1e-4 and snr>=50,(sequence,'wave reconstruction SNR/RMSE',rms,snr)
                item_metric.update(rmse_allowed=1e-4,snr_db=snr,snr_minimum_db=50);passed+=2
            metrics.append(item_metric);passed+=3
        wave=np.fromfile(output,dtype='<f4');assert np.std(wave)>1e-6 and np.max(np.abs(wave))<=.990001;passed+=2
    print('Isolate original HiFT with IDENTICAL native mel/F0/source/spectra',flush=True)
    execute([sys.executable,'tools/soulx_trained_oracle.py','--source',DIRECTORY,'--output',OUT,'--isolate'],OUT/'isolation.log')
    isolation=json.loads((OUT/'isolation.json').read_text(encoding='utf-8'));assert len(isolation)==12;passed+=len(isolation)*2
    current(inputs);current(reference['input_fingerprint'])
    record=dict(passed=passed,actual_host_children=3,actual_ort_graph_runs=sum(r['graph_runs'] for r in runs),
        successful_acoustic_reconstructions=3,max_live_sessions=max(r['max_live_sessions'] for r in runs),
        trained_acoustic_checkpoints_loaded=2,trained_reference_components_used=2,publisher_acoustic_models=trained['models'],
        reference_evidence_fingerprint=reference['input_fingerprint'],production_converter_executed=True,original_upstream_forward_executed=True,
        semantic_codes_source='trained_s3_from_synthetic_target_pcm',semantic_codes_from_language_backbone=False,
        runtime_version=lock['host_runtime']['version'],runtime_sha256=lock['host_runtime']['sha256'],assets=manifest['assets'],metrics=metrics,isolation=isolation,runs=runs,
        reference_inputs=[{k:c[k] for k in ['prompt_tokens','generated_tokens','samples']} for c in cases],
        trained_text_to_speech=False,full_soulx_inference=False,speech_quality_tested=False,real_person_audio_used=False,
        physical_android=False,apk_runtime_used=False,engine_registered=False,input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['publisher_acoustic_models','reference_evidence_fingerprint','assets','metrics','isolation','runs','input_fingerprint']}),flush=True)

if __name__=='__main__':main()
