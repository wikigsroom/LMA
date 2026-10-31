"""Extend the preserved benchmark audit with bounded RF Shape program evidence."""
import json
from pathlib import Path
from evidence import fingerprint,current
from fetch_shape_sources import verify
ROOT=Path(__file__).resolve().parents[1]
def main():
    lock=verify();data=json.loads((ROOT/'research/portability/audit-v0.3.3.json').read_text(encoding='utf-8'))
    data.update(app_version='0.3.4',prior_audit='research/portability/audit-v0.3.3.json',integrated_architectures=['trellis2','pixal3d','pixal3d_mv','triposg','partcrafter'])
    targets=[x for x in data['unported_configurations'] if x['id'] in ['D11','D12']]
    assert [x['revision'] for x in targets]==[x['revision'] for x in lock['sources']]
    for item,source in zip(targets,lock['sources']):
        item.update(program_integrated=True,integration_status='matched_onnx_cpu_image_to_shape_subset',remaining_implementation=[],source_files=source['files'],
          program_scope='DINOv2 -> RF/part DiT -> cached SDF VAE -> bounded uniform-grid marching tetrahedra -> internal multipart GLB',
          acquisition='user_selected_local_export_import_only; no verified public matched download package',
          exclusions=['automatic image segmentation','point-cloud VAE encoder','part-count VLM','texture generation','Flash/octree mesh extraction','desktop stylization pipeline'],
          full_trained_export_tested=False,phone_inference_tested=False,quality_accepted=False,
          decoder_export_source_adaptation='PartCrafter torch_cluster.fps import becomes an explicit rejecting encoder guard; decoder instructions unchanged' if item['id']=='D12' else 'portable attention preserves publisher QKV packing')
    data['ported_configurations']=targets;data['unported_configurations']=[x for x in data['unported_configurations'] if x['id'] not in ['D11','D12']]
    for case in data['cases']:
        if case['number'] in [11,12,15,16]:case.update(program_integrated=True,current_scope='matched_onnx_cpu_shape_only_import; scene uses scene checkpoint; not exact benchmark reproduction')
    data.update(upstream_code_executed=True,upstream_execution_scope='randomly initialized tiny source-architecture graphs only; no trained model',
      evidence=['verification/program/shape.json','verification/program/shape-android.json','verification/program/expansion.json','verification/program/ui.json'],
      conclusion='Matched RF Shape CPU program paths are implemented. Seven benchmark configurations in six groups still need native ports; phone memory, speed, full export and model quality remain unmeasured.',
      input_fingerprint=fingerprint('research/portability/audit-v0.3.3.json','tools/audit_shape.py','third_party/rf-shape-source-lock.json','native/rf_shape','tools/shape_graphs.py','tools/export_shape.py','tools/test_shape.py','app/src/main/java/com/lma/app/core/RfShapeSpec.java'))
    current(data['input_fingerprint']);(ROOT/'research/portability/audit-v0.3.4.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(ported=len(targets),remaining=len(data['unported_configurations']),trained_models=0)))
if __name__=='__main__':main()
