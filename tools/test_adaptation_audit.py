"""Check completion evidence and reject incomplete release states without writes."""
import copy,hashlib,json
from pathlib import Path
from unittest.mock import patch
from evidence import ROOT,fingerprint,current
import audit_adaptations as audit

def identities():
 result={}
 for directory in ('verification/program','dist/releases/v0.3.5'):
  for path in (ROOT/directory).rglob('*'):
   if path.is_file():
    with path.open('rb') as stream:result[path.relative_to(ROOT).as_posix()]=dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())
 return result

def main():
 out=ROOT/'build/adaptation-audit-tests';out.mkdir(exist_ok=True);data=audit.require_complete();checks=[]
 inputs=fingerprint('tools/test_adaptation_audit.py','tools/audit_adaptations.py','tools/program_evidence.py','tools/complete_evidence.py','tools/program_release.py','research/portability/adaptation-current.json')
 before=identities();assert before;checks.append('complete_current_adapter_audit_passes')
 assert not data['unported_ids'] and not data['remaining_subset_implementation'];checks.append('no_required_code_gap_hidden')
 assert not data['full_benchmark_workflows_reproduced'] and data['complete_models_run']==data['phone_tests']==0;checks.append('CPU_profile_and_unmeasured_boundaries_preserved')
 cases=[]
 for name in audit.REQUIRED:
  bad=copy.deepcopy(data);bad['implemented_modules'].pop(name);cases.append(('missing_'+name,bad))
 for name in ('foreground','part-identification','pointcloud','surface','local-stages'):
  bad=copy.deepcopy(data);bad['implemented_modules'][name]['program_integrated']=False;cases.append(('missing_'+name,bad))
 for key in ('all_requested_adaptations_complete','all_benchmark_architectures_integrated'):
  bad=copy.deepcopy(data);bad[key]=False;cases.append((key,bad))
 bad=copy.deepcopy(data);bad['program_records'].pop(next(iter(bad['program_records'])));cases.append(('missing_required_receipt',bad))
 bad=copy.deepcopy(data);bad['program_records'][next(iter(bad['program_records']))]='0'*64;cases.append(('changed_required_receipt',bad))
 bad=copy.deepcopy(data);bad['remaining_subset_implementation']=['missing stage'];cases.append(('remaining_subset',bad))
 for name,bad in cases:
  try:audit.validate(bad)
  except (AssertionError,KeyError):checks.append(name+'_rejects')
  else:raise AssertionError('Accepted incomplete evidence: '+name)
 import program_evidence,program_release
 for name,action in [('evidence',program_evidence.export),('package',program_release.package),('prepare',program_release.prepare)]:
  # Feed a real invalid audit at the read boundary; no file/network mutation.
  with patch.object(audit,'check',side_effect=lambda:audit.validate(cases[0][1])):
   try:action()
   except RuntimeError as error:
    assert 'Complete adaptation Release is not ready' in str(error);checks.append(name+'_rejects_missing_adapter_before_writes')
   else:raise AssertionError('Incomplete release entrypoint accepted: '+name)
 assert before==identities();checks.append('published_evidence_and_release_assets_unchanged');current(inputs)
 result=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,immutable_files_checked=len(before),actual_release_entrypoints_executed=3,incomplete_release_actions_rejected=True,github_writes=0,completeModelsRun=0,physicalDeviceTests=0)
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=len(checks),immutable_files_checked=len(before))))

if __name__=='__main__':main()
