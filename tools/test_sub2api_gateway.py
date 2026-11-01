"""Compile and check the native Go capability gateway; no inference or virtualization."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import ROOT, current, fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--go',type=Path,default=ROOT/'build/toolchains/go1.27.3/go/bin/go.exe')
    parser.add_argument('--upstream-source',type=Path)
    args=parser.parse_args()
    go=args.go.resolve();out=ROOT/'build/sub2api-gateway-tests';out.mkdir(parents=True,exist_ok=True)
    inputs=fingerprint('integrations/sub2api','tools/apply_sub2api.py','tools/test_sub2api_gateway.py')
    p=subprocess.run([str(go),'test','-timeout=30s','-count=1','-json','./...'],cwd=ROOT/'integrations/sub2api/localgateway',capture_output=True,text=True,encoding='utf-8',timeout=180)
    (out/'output.jsonl').write_text(p.stdout+p.stderr,encoding='utf-8')
    if p.returncode:raise RuntimeError('Native gateway checks failed; inspect build/sub2api-gateway-tests/output.jsonl')
    events=[json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
    checks=[e['Test'] for e in events if e.get('Action')=='pass' and e.get('Test')]
    assert len(checks)>=8
    upstream=False
    if args.upstream_source:
        source=args.upstream_source.resolve();package=source/'backend/internal/pkg/lmalocal'
        for f in (ROOT/'integrations/sub2api/localgateway').glob('*.go'):
            assert (package/f.name).read_bytes()==f.read_bytes(),'Patched gateway source is stale'
        for name in ('lma_local.go','lma_local_test.go'):
            assert (source/'backend/internal/server/routes'/name).read_bytes()==(ROOT/'integrations/sub2api'/(name+'.txt')).read_bytes()
        env={**os.environ,'GOPROXY':'https://goproxy.cn,direct','GOMODCACHE':str(ROOT/'build/toolchains/gomodcache')}
        p=subprocess.run([str(go),'test','./internal/server/routes','-run','^TestLMA','-count=1','-json'],cwd=source/'backend',env=env,capture_output=True,text=True,encoding='utf-8',timeout=1800)
        (out/'sub2api-routes.jsonl').write_text(p.stdout+p.stderr,encoding='utf-8')
        if p.returncode:raise RuntimeError('Pinned Sub2API integration check failed; inspect sub2api-routes.jsonl')
        tests=[json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
        names=[e['Test'] for e in tests if e.get('Action')=='pass' and e.get('Test')]
        assert 'TestLMAOptInGroupRouting' in names
        checks+=names;upstream=True
    current(inputs)
    result=dict(schema='lma.sub2api-program-tests/1',passed=len(checks),checks=checks,input_fingerprint=inputs,
        native_go=True,actual_http_fixtures=True,pinned_sub2api_route_adapter_tested=upstream,
        upstream_commit='dece26153621959ccd7635814f4b2d08304e681a',
        authentication_scope='Existing Sub2API auth chain retained; Gin route test uses an explicit auth-context fixture. Not live DB/subscription/billing acceptance.',
        production_deployment_changed=False,model_inference=False,physical_device=False,virtualization_used=False)
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    subprocess.run([str(go),'build','-o',str(out/'lma-gateway-probe.exe'),'./cmd/probe'],cwd=ROOT/'integrations/sub2api/localgateway',check=True,timeout=180)
    print(json.dumps({k:result[k] for k in ('passed','pinned_sub2api_route_adapter_tested','model_inference')}))


if __name__=='__main__':main()
