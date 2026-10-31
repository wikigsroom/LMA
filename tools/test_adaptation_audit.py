"""Exercise real release entrypoints while required adapters remain missing.

They must fail before changing the immutable release or its published evidence.
No build, model run, device, network request or GitHub write is performed.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
from evidence import fingerprint,current
from audit_adaptations import check
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/adaptation-audit-tests'


def identities():
    result={}
    for directory in ('verification/program','dist/releases/v0.3.5'):
        for p in (ROOT/directory).rglob('*'):
            if p.is_file():
                with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
                result[p.relative_to(ROOT).as_posix()]=dict(bytes=p.stat().st_size,sha256=digest)
    return result


def main():
    OUT.mkdir(exist_ok=True);audit=check();assert audit['unported_ids'] and not audit['all_requested_adaptations_complete']
    inputs=fingerprint('tools/test_adaptation_audit.py','tools/audit_adaptations.py','tools/program_evidence.py','tools/program_release.py','research/portability/adaptation-current.json')
    before=identities();assert before,'Published evidence must exist for the immutability regression'
    cases=[]
    for label,argv in [('evidence',[str(ROOT/'tools/program_evidence.py'),'--export']),
        ('package',['-c',"import sys;sys.path.insert(0,'tools');import program_release;program_release.package()"]),
        ('prepare',['-c',"import sys;sys.path.insert(0,'tools');import program_release;program_release.prepare()"])]:
        run=subprocess.run([sys.executable,*argv],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        assert run.returncode!=0 and 'Complete adaptation Release is not ready' in run.stderr,(label,run.stdout,run.stderr)
        assert all(x in run.stderr for x in audit['unported_ids']),label
        assert before==identities(),'Rejected '+label+' modified published evidence/assets'
        cases.extend([dict(case=label+'_rejects_missing_code'),dict(case=label+'_lists_all_unported_ids'),dict(case=label+'_preserves_published_files')])
    current(inputs)
    result=dict(passed=len(cases),checks=cases,input_fingerprint=inputs,immutable_files_checked=len(before),
        actual_release_entrypoints_executed=3,release_actions_rejected=True,github_writes=0,completeModelsRun=0,physicalDeviceTests=0)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n','utf-8');print(json.dumps({k:result[k] for k in ('passed','immutable_files_checked','github_writes')}))


if __name__=='__main__':main()
