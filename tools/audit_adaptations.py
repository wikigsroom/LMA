"""Require implemented, compiled and freshly checked adapters before release.

Program-only validation never substitutes for missing implementation. The
published v0.3.5 audit is immutable; this is the current CPU-profile audit.
"""
import argparse,hashlib,json
from pathlib import Path
from evidence import fingerprint,current,version
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/portability/adaptation-current.json'
REQUIRED=['D04','D05','D08','D09','D10']
MODULES={
 'F5-frontend':dict(source=['native/speech_extra/f5_official.hpp','tools/export_f5_frontend.py','app/src/main/java/com/lma/app/core/AudioCppSpec.java'],templates=['f5_v1_official_frontend_cpu_v1'],tests={'f5-frontend-tests':6671}),
 'D04':dict(source=['native/spatial/ultratex.hpp','native/spatial/text_tokens.hpp','native/spatial/typed_graph.hpp','tools/export_ultratex.py','tools/ultratex_flows.py','tools/ultratex_codecs.py','app/src/main/java/com/lma/app/core/UltraTexSpec.java'],templates=['ultratex_flux1_onnx_cpu_v1','ultratex_flux2_onnx_cpu_v1'],tests={'ultratex-tests':106,'ultratex-flow-tests':107}),
 'D05':dict(source=['native/spatial/uniforge.hpp','native/spatial/cascade.hpp','native/spatial/view_router.hpp','tools/export_uniforge.py','tools/uniforge_components.py','app/src/main/java/com/lma/app/core/UniForgeSpec.java'],templates=['uniforge3d_onnx_cpu_v1'],tests={'uniforge-tests':18,'uniforge-component-tests':78,'view-router-tests':48,'fdg-tests':72,'fdg-mesh-tests':80}),
 'D07-Paint':dict(source=['native/spatial/material.hpp','native/spatial/texture.hpp','tools/export_paint.py','app/src/main/java/com/lma/app/core/MaterialSpec.java'],templates=['hunyuan3d_21_paint_onnx_cpu_v1'],tests={'paint-tests':227,'paint-export-tests':17}),
 'D08':dict(source=['native/spatial/sam.hpp','native/spatial/sam_math.hpp','native/spatial/sam_pose.hpp','native/spatial/flexicubes.hpp','tools/export_sam.py','tools/sam_components.py','tools/sam_conditioner.py','tools/depth_components.py','app/src/main/java/com/lma/app/core/SamSpec.java'],templates=['sam3d_objects_onnx_cpu_v1'],tests={'sam-tests':68,'sam-component-tests':74,'sam-conditioner-tests':42,'sam-export-tests':25,'sam-math-tests':60,'sam-pose-tests':32,'depth-component-tests':25,'depth-postprocess-tests':78,'flexicubes-tests':139}),
 'D09':dict(source=['native/spatial/sam_sampling.hpp','native/spatial/depth.hpp','tools/sam_portable.py','tools/depth_components.py'],templates=['mv_sam3d_da3_onnx_cpu_v1'],tests={'sam-tests':68,'sam-component-tests':74,'sam-export-tests':25,'sam-math-tests':60,'depth-component-tests':25,'depth-postprocess-tests':78}),
 'D10':dict(source=['native/spatial/supra.hpp','native/spatial/supra_observation.hpp','tools/export_supra.py','tools/supra_components.py','app/src/main/java/com/lma/app/core/SupraSpec.java'],templates=['supratex_onnx_cpu_v1'],tests={'supra-tests':16,'supra-component-tests':52,'fdg-tests':72,'fdg-mesh-tests':80}),
 'foreground':dict(source=['native/vision/foreground.hpp','tools/export_foreground.py','tools/vision_components.py','app/src/main/java/com/lma/app/VisionEngine.java'],templates=['isnet_dis_onnx_cpu_v1'],tests={'vision-tests':29}),
 'part-identification':dict(source=['native/vision/vlm.hpp','app/src/main/java/com/lma/app/core/VisionSpec.java'],templates=['vlm_parts_gguf_cpu_v1'],tests={'vision-tests':29}),
 'pointcloud':dict(source=['native/rf_shape/pointcloud.hpp','tools/export_pointcloud.py','tools/pointcloud_graphs.py','app/src/main/java/com/lma/app/core/PointCloudSpec.java'],templates=['triposg_points_onnx_cpu_v1','partcrafter_points_onnx_cpu_v1'],tests={'pointcloud-tests':35}),
 'surface':dict(source=['native/rf_shape/surface.hpp','tools/prepare_surface_cpu.py','tools/fetch_surface_sources.py','app/src/main/java/com/lma/app/core/SurfaceSpec.java'],templates=[],tests={'surface-tests':21}),
 'local-stages':dict(source=['app/src/main/java/com/lma/app/PreparationEngine.java','app/src/main/java/com/lma/app/core/StructuredInput.java','tests/expansion-host/com/lma/app/PreparationTest.java'],templates=[],tests={'expansion-tests':875}),
}
RECEIPTS=['build/spatial-build-info.json','build/shape-build-info.json','build/vision-build-info.json']

def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def inputs():return fingerprint('tools/audit_adaptations.py','native/spatial','native/rf_shape','native/vision','app/src/main/java','app/src/main/assets/recipe-templates.json','docs/proposals/multimodal-release-scope.json',*[p for m in MODULES.values() for p in m['source']])
def count(d):
 p=d.get('passed');assert p,'Program suite did not pass'
 if isinstance(p,int) and not isinstance(p,bool):return p
 for key in ('count','checks','assertions'):
  x=d.get(key)
  if isinstance(x,int):return x
  if isinstance(x,list):return len(x)
 raise AssertionError('Missing assertion count')
def required_records():return sorted(set(RECEIPTS+['build/'+n+'/results.json' for m in MODULES.values() for n in m['tests']]))
def validate_records():
 records={}
 for name in required_records():
  p=ROOT/name;assert p.is_file(),'Missing program/build evidence: '+name
  d=json.loads(p.read_text('utf-8'));current(d.get('source_inputs',d.get('input_fingerprint',{})))
  assert d.get('source_inputs') or d.get('input_fingerprint'),'Missing source identity: '+name
  if name in RECEIPTS:
   assert d['abi']=='arm64-v8a' and d['android_api_notes']==[28]
   lib=ROOT/'app/src/main/jniLibs/arm64-v8a'/d['file'];assert lib.stat().st_size==d['bytes'] and hashlib.sha256(lib.read_bytes()).hexdigest()==d['sha256']
  else:
   minimum=max(m['tests'].get(Path(name).parent.name,0) for m in MODULES.values());assert count(d)>=minimum,name
  for key in ('completeModelsRun','completeModelsDownloaded','phoneTests','physicalDeviceTests','physical_device_tests','model_inference_tested','virtualizationUsed','virtualization_used'):
   assert not d.get(key,False),'Unexpected validation scope: '+name+' '+key
  records[name]=digest(name)
 return records

def export():
 templates={t['id'] for t in json.loads((ROOT/'app/src/main/assets/recipe-templates.json').read_text('utf-8'))['templates']}
 for m in MODULES.values():
  assert set(m['templates'])<=templates,m['templates']
  for path in m['source']:assert (ROOT/path).is_file(),path
 records=validate_records();scope=json.loads((ROOT/'docs/proposals/multimodal-release-scope.json').read_text('utf-8'))
 data=dict(schema='lma.adaptation-audit/2',version=version(),previous_release='0.3.5',previous_audit='research/portability/audit-v0.3.5.json',
  implemented_modules={k:dict(v,program_integrated=True,complete_trained_model_tested=False,phone_inference_tested=False) for k,v in MODULES.items()},
  required_adapter_ids=REQUIRED,unported_configurations=[],unported_ids=[],remaining_subset_implementation=[],program_records=records,
  preserved_scope=dict(features=['F-'+str(i).zfill(2) for i in range(1,13)],selections=scope['selected_ids'],moss_subtargets=9,lora_base_families=['sd15','sdxl'],recommended=['m08','m06','m01'],text=True),
  all_requested_adaptations_complete=True,all_benchmark_architectures_integrated=True,full_benchmark_workflows_reproduced=False,
  implementation_scope='Versioned bounded CPU profiles with strict matched assets; not every publisher CUDA workflow or arbitrary HF architecture',
  profile_boundaries='docs/ADAPTER_PROFILES.md',remaining_document='docs/REMAINING_ADAPTATION.md',
  public_matched_complete_packages_verified=False,complete_models_run=0,phone_tests=0,validation_mode='program_only',input_fingerprint=inputs())
 OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8');return check()
def validate(data):
 current(data['input_fingerprint']);assert data['input_fingerprint']==inputs()
 assert data['schema']=='lma.adaptation-audit/2' and data['version']==version()
 assert data['required_adapter_ids']==REQUIRED and set(data['implemented_modules'])==set(MODULES)
 assert all(data['implemented_modules'][k]['program_integrated'] and all(data['implemented_modules'][k][field]==MODULES[k][field] for field in ('source','templates','tests')) for k in MODULES)
 assert data['program_records']==validate_records(),'Changed required program evidence'
 assert data['all_requested_adaptations_complete'] and data['all_benchmark_architectures_integrated']
 assert not data['unported_ids'] and not data['unported_configurations'] and not data['remaining_subset_implementation']
 assert data['complete_models_run']==data['phone_tests']==0 and not data['full_benchmark_workflows_reproduced']
 return data
def check():return validate(json.loads(OUT.read_text('utf-8')))
def require_complete():
 try:return check()
 except (AssertionError,FileNotFoundError,KeyError) as error:raise RuntimeError('Complete adaptation Release is not ready: required adapter code, builds and current program checks must all pass. '+str(error)) from error

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--require-complete',action='store_true');a=p.parse_args();d=check() if a.check else export()
 if a.require_complete:require_complete()
 print(json.dumps(dict(version=d['version'],all_requested_adaptations_complete=d['all_requested_adaptations_complete'],unported_ids=d['unported_ids'])))
