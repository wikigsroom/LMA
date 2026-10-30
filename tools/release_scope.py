"""Trace the complete frozen v0.3.0 scope to shipped recipes and production code."""
import json
from pathlib import Path
from evidence import current, fingerprint, version

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'catalogue/release-0.3.0-implementation.json'
TARGETS = {
 '01': ['sd15_checkpoint_cpu_v1','sd15_split_cpu_v1'],
 '02': ['sd15_lora_cpu_v1','sdxl_lora_cpu_v1'],
 '03': ['sd21_turbo_checkpoint_cpu_v1','sd15_lcm_checkpoint_cpu_v1','sdxl_lcm_checkpoint_cpu_v1','sd15_lcm_lora_cpu_v1','sdxl_lcm_lora_cpu_v1'],
 '04': ['sana_sprint_06b_mnn_cpu_v1','sana_edit_mnn_cpu_v1'],
 '05': ['sdxl_checkpoint_cpu_v1','sdxl_split_cpu_v1'],
 '06': ['z_image_turbo_split_cpu_v1'], '07': ['flux2_klein_4b_split_cpu_v1'], '08': ['qwen_image_21_split_cpu_v1'],
 '09': ['moss_nano_cpu_v1'], '10': ['kokoro_en_cpu_v1','piper_vits_en_cpu_v1','matcha_en_cpu_v1'],
 '11': ['qwen3_tts_06b_base_cpu_v1'],
 '12': ['moss_delay_firstclass_cpu_v1','moss_local_v15_cpu_v1','moss_soundeffect_v2_cpu_v1','moss_tts_openmoss_cpu_v1','moss_tts_v15_openmoss_cpu_v1','moss_ttsd_openmoss_cpu_v1','moss_voicegen_openmoss_cpu_v1','moss_soundeffect_openmoss_cpu_v1','moss_local_v10_rq_cpu_v1','moss_realtime_rq_cpu_v1'],
 '13': ['soulx_podcast_cpu_v1'], '14': ['stable_audio_small_litert_v1'],
 '16': ['wan21_13b_split_cpu_v1','wan21_13b_split_vulkan_v1'],
 '17': ['ltx098_pixart_multiscale_v1','ltx098_single_scale_google_q5_v1']}
FEATURES = {
 'F-01': ['HubCatalog','HubClient','core/RecipeCatalogue','core/RecipeSuggestions'],
 'F-02': ['core/BundleStore','core/BundleTransfers','core/BundleUpdates','core/ComponentIntegrity'],
 'F-03': ['core/ModelBundle','LocalEngines','core/TaskRequests'],
 'F-04': ['NativeWorker','NativeStages','Ltx098Engine','MnnEngine','SdEngine','SherpaEngine','MossNanoEngine','QwenTtsEngine','MossDelayEngine','OpenMossEngine','MossRqEngine','SoulxEngine','StableAudioEngine'],
 'F-05': ['ModelSettings','GgufMetadata','core/ParameterSchema','core/LtxPixArtSpec'],
 'F-06': ['LocalJobs','core/JobStore','core/ProcessControl'],
 'F-07': ['DeviceResourceProbe','core/ExecutionGate','core/ResourceWatch'],
 'F-08': ['LmaService','BootReceiver','core/JobStore','core/ArtifactStore'],
 'F-09': ['core/ArtifactStore','VideoEncoder','core/TaskDrafts'],
 'F-10': ['ApiHost','core/LocalApi','core/InputUploads','core/AudioStreams'],
 'F-11': ['Store','core/BundleStore','ModelSettings'],
 'F-12': ['core/ModelBundle','core/TaskRequests']}

def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def inputs():return fingerprint('tools/release_scope.py','docs/proposals/multimodal-release-scope.json','docs/proposals/program-validation-policy.json','app/src/main/java','app/src/main/assets/recipe-templates.json','app/src/main/assets/model-bundles.json','app/src/main/assets/model-assemblies.json','third_party/engine-lock.json')

def export():
 assert version()=='0.3.0'
 scope=read('docs/proposals/multimodal-release-scope.json')
 templates={x['id']:x for x in read('app/src/main/assets/recipe-templates.json')['templates']}
 assert set(templates)==set(sum(TARGETS.values(),[])+['text_gguf_cpu_v1'])
 assert list(TARGETS)==scope['selected_ids'] and len(templates)==38
 targets=[]
 for entry in scope['entries']:
  key=entry['selection_id']
  targets.append(dict(selection_id=key,name=entry['display_name'],tasks=entry['task_tags'],templates=TARGETS[key],frozen_subtargets=[x['model'] for x in entry.get('subtargets',[])],program_integration=True,physical_device_validated=False,quality_accepted=False))
 features=[dict(id=k,source_files=['app/src/main/java/com/lma/app/'+v+'.java' for v in values],program_implementation=True) for k,values in FEATURES.items()]
 for feature in features:
  for name in feature['source_files']:assert (ROOT/name).is_file(),name
 data=dict(schema='lma.release-implementation/1',version=version(),validation_mode='program_only',scope='docs/proposals/multimodal-release-scope.json',features=features,selections=targets,preserved_text_template='text_gguf_cpu_v1',recipe_templates=len(templates),model_bundles=len(read('app/src/main/assets/model-bundles.json')['bundles']),extension_engine_families=len(read('third_party/engine-lock.json')['engines']),full_scope_program_implementation_complete=True,missing_required_program_targets=[],all_selected_models_tested=False,phone_inference_tested=False,quality_accepted=False,background_endurance_tested=False,input_fingerprint=inputs())
 OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return check()

def check():
 data=read(OUT.relative_to(ROOT));current(data['input_fingerprint']);assert data['input_fingerprint']==inputs()
 assert data['full_scope_program_implementation_complete'] and not data['missing_required_program_targets']
 assert [x['selection_id'] for x in data['selections']]==list(TARGETS)
 assert [x['id'] for x in data['features']]==list(FEATURES)
 assert len(next(x for x in data['selections'] if x['selection_id']=='12')['frozen_subtargets'])==9
 assert data['recipe_templates']==38 and data['model_bundles']==23 and data['extension_engine_families']==12
 return data

if __name__=='__main__':
 d=export();print(json.dumps({k:d[k] for k in ['version','recipe_templates','model_bundles','extension_engine_families','full_scope_program_implementation_complete']}))
