"""Package the complete program-only release under the explicit user validation policy."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from evidence import version
from program_evidence import check as program_check
from release_scope import check as scope_check

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
VERSION=version()
MEDIA=['community','release-workbench']

def sha(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def public_names():
 result=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True)
 names=sorted(set(result.stdout.decode('utf-8').strip('\0').split('\0')))
 blocked={'signing','build','dist','.git','node_modules','__pycache__','.gradle'}
 for name in names:
  p=Path(name)
  assert name and not p.is_absolute() and '..' not in p.parts and not set(p.parts)&blocked,name
  assert 'jniLibs' not in p.parts and p.parts[:2]!=('third_party','cache'),name
  assert p.suffix not in {'.p12','.jks','.keystore','.pem','.key','.gguf','.part','.idsig','.apk','.pyc'} and not p.name.startswith('.env'),name
  assert (ROOT/p).is_file() and (ROOT/p).stat().st_size < 25*1024*1024,name
 return names

def package():
 assert version()==VERSION
 evidence=program_check();matrix=scope_check();build=read(DIST/'build-info.json')
 notes=ROOT/('docs/releases/v'+VERSION+'.md')
 assert notes.exists() and VERSION in notes.read_text(encoding='utf-8')
 validation=dict(evidence,app='LMA',sha256=build['sha256'],bytes=build['bytes'],validation_mode='program_only',
  full_scope_program_implementation_complete=matrix['full_scope_program_implementation_complete'],
  selected_ids=[x['selection_id'] for x in matrix['selections']],model_weights_included=False,
  automatic_model_downloads=False,complete_trained_model_runs=0,physical_device_tests=0,
  phone_inference_tested=False,model_quality_accepted=False,background_endurance_tested=False,
  ui_uses_simulated_bridge=True,original_signing_identity=True,virtualization_used=False)
 write(DIST/'validation.json',validation)
 source=DIST/f'LMA-{VERSION}-source.zip'
 names=public_names()
 with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for name in names:archive.write(ROOT/name,'LMA/'+name)
 digest=sha(source)
 (DIST/(source.name+'.sha256')).write_text(digest+'  '+source.name+'\n',encoding='utf-8')
 index=dict(schema='lma.source-archive/1',version=VERSION,archive=source.name,sha256=digest,bytes=source.stat().st_size,
  model_weights_included=False,signing_material_included=False,native_binaries_included=False,
  files={name:dict(bytes=(ROOT/name).stat().st_size,sha256=sha(ROOT/name)) for name in names})
 write(DIST/'source-archive-manifest.json',index)
 return check()

def check(prepared=False):
 assert version()==VERSION
 evidence=program_check();matrix=scope_check();build=read(DIST/'build-info.json');validation=read(DIST/'validation.json')
 assert build['version']==validation['version']==VERSION and build['sha256']==validation['sha256']
 assert validation['validation_mode']=='program_only' and validation['full_scope_program_implementation_complete']
 assert validation['program_assertions']==evidence['program_assertions'] and validation['program_suites']==evidence['program_suites']
 for flag in ['model_weights_included','automatic_model_downloads','complete_trained_model_runs','physical_device_tests','phone_inference_tested','model_quality_accepted','background_endurance_tested','virtualization_used']:assert not validation[flag],flag
 index=read(DIST/'source-archive-manifest.json');source=DIST/index['archive'];assert sha(source)==index['sha256']
 assert set(index['files'])==set(public_names()),'Repackage after source/document changes'
 assert (DIST/(source.name+'.sha256')).read_text(encoding='utf-8').split()[0]==index['sha256']
 with zipfile.ZipFile(source) as archive:
  assert len(archive.namelist())==len(set(archive.namelist())) and set(archive.namelist())=={'LMA/'+n for n in index['files']}
  for name,item in index['files'].items():
   assert item==dict(bytes=(ROOT/name).stat().st_size,sha256=sha(ROOT/name)),'Stale archive source: '+name
   with archive.open('LMA/'+name) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256']
 if prepared:
  directory=DIST/('releases/v'+VERSION);manifest=read(directory/'release-manifest.json')
  assert manifest['version']==VERSION and manifest['prerelease'] and manifest['validation_mode']=='program_only'
  assert manifest['full_scope_program_implementation_complete'] and manifest['apk_sha256']==build['sha256']
  expected={x['name'] for x in manifest['assets']}|{'release-manifest.json'}
  if (directory/'publish-receipt.json').exists():expected.add('publish-receipt.json')
  assert set(p.name for p in directory.iterdir())==expected
  for item in manifest['assets']:
   path=directory/item['name'];assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256']
 result=dict(evidence,source_files=len(index['files']),source_archive=source.name,source_sha256=index['sha256'],prepared=prepared)
 write(ROOT/'build/program-release-check.json',result)
 return result

def prepare():
 check();directory=DIST/('releases/v'+VERSION);directory.mkdir(parents=True,exist_ok=True)
 build=read(DIST/'build-info.json');source=f'LMA-{VERSION}-source.zip'
 originals=[DIST/build['apk'],DIST/(build['apk']+'.sha256'),DIST/source,DIST/(source+'.sha256'),DIST/'validation.json',DIST/'build-info.json',DIST/'source-archive-manifest.json']
 names=[]
 for original in originals:shutil.copy2(original,directory/original.name);names.append(original.name)
 notes='RELEASE_NOTES.md';shutil.copy2(ROOT/('docs/releases/v'+VERSION+'.md'),directory/notes);names.append(notes)
 verification=f'LMA-{VERSION}-verification.zip'
 with zipfile.ZipFile(directory/verification,'w',zipfile.ZIP_DEFLATED) as archive:
  for p in sorted((ROOT/'verification/program').glob('*.json')):archive.write(p,'verification/program/'+p.name)
  for name in MEDIA:archive.write(ROOT/'docs/media/development'/name/'manifest.json','media/'+name+'/manifest.json')
  archive.write(ROOT/('catalogue/release-'+VERSION+'-implementation.json'),'implementation.json')
  archive.write(ROOT/'docs/proposals/program-validation-policy.json','validation-policy.json')
 names.append(verification)
 screenshots=f'LMA-{VERSION}-screenshots.zip'
 with zipfile.ZipFile(directory/screenshots,'w',zipfile.ZIP_DEFLATED) as archive:
  for name in MEDIA:
   base=ROOT/'docs/media/development'/name
   for item in read(base/'manifest.json')['screenshots']:archive.write(base/item['file'],name+'/'+item['file'])
 names.append(screenshots)
 for name in MEDIA:
  for extension in ['mp4','gif']:
   original=ROOT/'docs/media/development'/name/(name+'-ui.'+extension)
   target=f'LMA-{VERSION}-{name}.'+extension;shutil.copy2(original,directory/target);names.append(target)
 names.sort()
 (directory/'SHA256SUMS').write_text(''.join(sha(directory/n)+'  '+n+'\n' for n in names),encoding='utf-8');names.append('SHA256SUMS')
 manifest=dict(repository='wikigsroom/LMA',version=VERSION,tag='v'+VERSION,title='LMA v'+VERSION+' · Community models and content labels / 社区模型与内容标记',
  prerelease=True,notes='docs/releases/v'+VERSION+'.md',validation_mode='program_only',full_scope_program_implementation_complete=True,
  apk_sha256=build['sha256'],physical_device_tested=False,phone_inference_tested=False,background_endurance_tested=False,
  model_quality_accepted=False,media_uses_simulated_native_state=True,signing_material_included=False,model_weights_included=False,
  assets=[dict(name=n,bytes=(directory/n).stat().st_size,sha256=sha(directory/n)) for n in names])
 write(directory/'release-manifest.json',manifest)
 return check(prepared=True)
