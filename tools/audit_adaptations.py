"""Trace development completion without reclassifying missing ports as tests."""
import argparse,copy,hashlib,json
from pathlib import Path
from evidence import fingerprint,current,version
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/portability/adaptation-current.json'
PENDING=['D04','D05','D08','D09','D10']


def export():
    old=json.loads((ROOT/'research/portability/audit-v0.3.5.json').read_text('utf-8'))
    remaining=[copy.deepcopy(x) for x in old['unported_configurations'] if x['id'] in PENDING]
    assert [x['id'] for x in remaining]==PENDING
    for row in remaining:
        row.update(program_integrated=False,building_blocks_are_complete_model_adapter=False)
        if row['id']=='D04':row['shared_cpu_building_blocks']=['CPU raster / UV / PBR bake','block sparse attention / smooth-key selection / online softmax']
    templates=json.loads((ROOT/'app/src/main/assets/recipe-templates.json').read_text('utf-8'))['templates']
    ids={t['id'] for t in templates}
    assert {'hunyuan3d_21_paint_onnx_cpu_v1','f5_v1_official_frontend_cpu_v1'}<=ids
    implemented={
        'f5_official_frontend':dict(source=['native/speech_extra/f5_official.hpp','tools/export_f5_frontend.py','app/src/main/java/com/lma/app/core/AudioCppSpec.java'],scope='Pinned segmentation, pronunciation, tone sandhi, F5 text formatting / vocabulary IDs; explicit linguistic asset'),
        'hunyuan3d_21_paint':dict(source=['native/spatial/material.hpp','native/spatial/texture.hpp','tools/paint_graphs.py','tools/export_paint.py','app/src/main/java/com/lma/app/core/MaterialSpec.java','app/src/main/java/com/lma/app/ExpansionEngine.java'],scope='Reference PNG + GLB -> six local material views -> PBR GLB; independent CPU raster / seam fill; disclosed differences from publisher CUDA postprocessing'),
        'ultratex_bsa_operator':dict(source=['native/spatial/block_attention.hpp','native/spatial/sparse_ort.hpp','tools/ultratex_attention.py'],scope='Shared CPU operator only, not a complete UltraTex adapter')}
    for entry in implemented.values():
        for file in entry['source']:assert (ROOT/file).is_file(),file
        entry.update(complete_trained_model_tested=False,phone_inference_tested=False)
    scope=json.loads((ROOT/'docs/proposals/multimodal-release-scope.json').read_text('utf-8'))
    data=dict(schema='lma.adaptation-audit/1',version=version(),previous_release='0.3.5',previous_audit='research/portability/audit-v0.3.5.json',
        implemented_modules=implemented,unported_configurations=remaining,unported_ids=PENDING,remaining_document='docs/REMAINING_ADAPTATION.md',
        preserved_scope=dict(features=['F-'+str(i).zfill(2) for i in range(1,13)],selections=scope['selected_ids'],moss_subtargets=9,lora_base_families=['sd15','sdxl'],recommended=['m08','m06','m01'],text=True),
        all_requested_adaptations_complete=False,all_benchmark_architectures_integrated=False,full_benchmark_workflows_reproduced=False,
        remaining_subset_implementation=['automatic segmentation','VLM part identification','pointcloud input','original Flash/octree extraction','textures outside disclosed geometry subsets'],
        public_matched_complete_packages_verified=False,complete_models_run=0,phone_tests=0,validation_mode='program_only',
        input_fingerprint=fingerprint('tools/audit_adaptations.py','research/portability/audit-v0.3.5.json','native/spatial','native/speech_extra',
            'tools/paint_catalogue.py','tools/paint_graphs.py','tools/export_paint.py','tools/export_f5_frontend.py','tools/ultratex_attention.py',
            'app/src/main/java/com/lma/app/core/MaterialSpec.java','app/src/main/java/com/lma/app/core/AudioCppSpec.java','app/src/main/java/com/lma/app/ExpansionEngine.java',
            'docs/proposals/multimodal-release-scope.json','app/src/main/assets/recipe-templates.json'))
    current(data['input_fingerprint']);OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8');return check()


def check():
    data=json.loads(OUT.read_text('utf-8'));current(data['input_fingerprint'])
    assert data['version']==version() and data['unported_ids']==PENDING and [x['id'] for x in data['unported_configurations']]==PENDING
    assert not data['all_requested_adaptations_complete'] and not data['all_benchmark_architectures_integrated']
    assert all(x['remaining_implementation'] and not x['program_integrated'] for x in data['unported_configurations'])
    assert data['complete_models_run']==data['phone_tests']==0
    return data


def require_complete():
    data=check()
    if not data['all_requested_adaptations_complete'] or data['unported_ids'] or data['remaining_subset_implementation']:
        raise RuntimeError('Complete adaptation Release is not ready: implement '+', '.join(data['unported_ids'])+' and the disclosed subset gaps. Program-only validation does not waive missing code. See docs/REMAINING_ADAPTATION.md.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--require-complete',action='store_true');a=p.parse_args()
    d=check() if a.check else export()
    if a.require_complete:require_complete()
    print(json.dumps(dict(version=d['version'],all_requested_adaptations_complete=d['all_requested_adaptations_complete'],unported_ids=d['unported_ids'])))
