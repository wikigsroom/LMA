"""Current program evidence for unfinished adaptation development, not a Release."""
import argparse,hashlib,json,shutil
from pathlib import Path
from evidence import current,fingerprint,version
from preparation_build_inputs import build_inputs
from program_evidence import SOURCES,MINIMUM,counted,CERTIFICATE
from audit_adaptations import check as audit_check
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'verification/adaptation'
RECORDS={**SOURCES,'f5-frontend.json':'build/f5-frontend-tests/results.json','material.json':'build/material-tests/results.json',
    'paint.json':'build/paint-tests/results.json','paint-export.json':'build/paint-export-tests/results.json','ultratex-attention.json':'build/ultratex-attention-tests/results.json',
    'adaptation-audit.json':'build/adaptation-audit-tests/results.json'}
LIMITS={**MINIMUM,'expansion':592,'ui':687,'f5-frontend':6671,'material':61,'paint':227,'paint-export':17,'ultratex-attention':47,'adaptation-audit':9}


def read(p):return json.loads(p.read_text('utf-8'))
def identity(p):
    with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(bytes=p.stat().st_size,sha256=digest)


def export():
    OUT.mkdir(exist_ok=True)
    items={}
    for name,source in RECORDS.items():
        p=ROOT/source;shutil.copyfile(p,OUT/name);items[name]=dict(source=source,**identity(OUT/name))
    from release_scope import check as scope_check
    scope_check();audit_check()
    media=ROOT/'docs/media/development/material/manifest.json'
    d=dict(schema='lma.adaptation-program-checkpoint/1',version=version(),development_only=True,release_ready=False,
        all_requested_adaptations_complete=False,validation_mode='program_only',complete_models_downloaded=0,complete_models_run=0,
        physical_device_tests=0,phone_inference_tested=False,background_endurance_tested=False,virtualization_used=False,
        sources=items,scope='catalogue/release-'+version()+'-implementation.json',audit='research/portability/adaptation-current.json',
        media=dict(path=media.relative_to(ROOT).as_posix(),**identity(media)),
        previous_published_program_evidence='verification/program/status.json',previous_published_version='0.3.5',
        previous_evidence_is_current_validation=False,
        input_fingerprint=fingerprint('tools/adaptation_evidence.py','tools/audit_adaptations.py','tools/release_scope.py',
            'tools/check_repository.py','tools/program_release.py','tools/program_evidence.py','research/portability/adaptation-current.json',
            'catalogue/release-'+version()+'-implementation.json','docs/proposals/program-validation-policy.json'))
    (OUT/'status.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8');return check()


def check():
    d=read(OUT/'status.json');current(d['input_fingerprint']);assert d['version']==version()
    assert d['development_only'] and not d['release_ready'] and not d['all_requested_adaptations_complete']
    assert not any(d[k] for k in ('complete_models_downloaded','complete_models_run','physical_device_tests','phone_inference_tested','background_endurance_tested','virtualization_used','previous_evidence_is_current_validation'))
    audit=audit_check();assert audit['unported_ids']==['D04','D05','D08','D09','D10']
    from release_scope import check as scope_check
    scope=scope_check();assert scope['frozen_scope_program_implementation_complete'] and not scope['full_scope_program_implementation_complete']
    assert set(d['sources'])==set(RECORDS)
    records={}
    for name,item in d['sources'].items():
        p=OUT/name;assert item==dict(source=RECORDS[name],**identity(p));v=read(p)
        current(v.get('source_inputs',v.get('input_fingerprint')));records[name]=v
    counts={n:counted(n,records[n+'.json']) for n in LIMITS}
    for name,minimum in LIMITS.items():assert counts[name]>=minimum,name
    b,p,l=[records[n+'.json'] for n in ('build','package','lint')]
    assert b['version']==version() and b['input_fingerprint']==build_inputs() and b['signatures_verified']
    assert identity(ROOT/'dist'/b['apk'])==dict(bytes=b['bytes'],sha256=b['sha256'])
    assert b['sha256']==p['sha256']==l['applicationApkSha256'] and p['signing_certificate_sha256']==CERTIFICATE
    assert p['native_libraries_verified']==40 and p['all_native_dependencies_resolved'] and p['all_elf_load_segments_16k_aligned'] and p['final_apk_zip_alignment_verified'] and p['packaged_ui_matches_source'] and p['apk_signatures_independently_verified']
    assert l['errors']==0 and not records['ui.json']['errors']
    for name in ('speech-extra-android.json','spatial-android.json'):
        n=records[name];assert n['abi']=='arm64-v8a' and n['android_api_notes']==[28] and not n['model_inference_tested'] and not n['physical_device_tests']
    assert records['f5-frontend.json']['exactSegmentation'] and records['f5-frontend.json']['exactPinyinTokens'] and records['f5-frontend.json']['exactVocabularyIds']
    assert not records['ultratex-attention.json']['fullUltraTexAdapter']
    assert records['adaptation-audit.json']['release_actions_rejected'] and not records['adaptation-audit.json']['github_writes']
    for name in ('paint.json','paint-export.json','material.json','ultratex-attention.json'):
        assert records[name]['completeModelsRun']==0
    m=ROOT/d['media']['path'];assert identity(m)=={k:d['media'][k] for k in ('bytes','sha256')};media=read(m);current(media['input_fingerprint'])
    assert media['version']==version() and media['browser_closed'] and not media['browser_errors'] and not media['model_inference'] and not media['android_device'] and not media['weights_downloaded']
    for f in media['files']:assert identity(m.parent/f['file'])=={k:f[k] for k in ('bytes','sha256')}
    return dict(version=version(),development_only=True,release_ready=False,all_requested_adaptations_complete=False,
        program_suites=len(counts),program_assertions=sum(counts.values()),unported_ids=audit['unported_ids'],apk=b['apk'],sha256=b['sha256'],lint_errors=l['errors'],lint_warnings=len(l['warnings']),screenshots=len(media['screenshots']),browser_closed=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--export',action='store_true');a=p.parse_args();print(json.dumps(export() if a.export else check()))
