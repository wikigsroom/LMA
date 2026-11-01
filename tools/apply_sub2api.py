"""Apply the opt-in LMA group extension to the exact audited Sub2API v0.2.19 source.

No credentials, database/account edits, execution or deployment. Refuses an unknown upstream.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = 'dece26153621959ccd7635814f4b2d08304e681a'
ORIGINAL = '8fd2ebf61aeb2e6b7b79976b0d44ab1b46178e803b225139f3401af123021be4'


def apply(target):
    target = target.resolve()
    backend = target / 'backend'
    route = backend/'internal/server/routes/gateway.go'
    original = route.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    if digest != ORIGINAL:
        raise RuntimeError('Upstream gateway differs from the audited commit; refusing to overwrite changes')
    text = original.decode('utf-8')
    newline = '\r\n' if '\r\n' in text else '\n'
    anchor = '\tgateway.Use(groupModelAllowlist)'+newline
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor+'\tgateway.Use(lmaLocalGatewayMiddleware())'+newline+
        '\tgateway.POST("/audio/speech", lmaLocalUnavailable)'+newline+
        '\tgateway.GET("/capabilities", lmaLocalUnavailable)'+newline+
        '\tgateway.HEAD("/capabilities", lmaLocalUnavailable)'+newline+
        '\tgateway.Any("/lma/*lmaPath", lmaLocalUnavailable)'+newline+
        '\tgateway.HEAD("/models", lmaLocalUnavailable)'+newline+
        '\tgateway.HEAD("/models/:model", lmaLocalUnavailable)'+newline)
    package = backend/'internal/pkg/lmalocal'
    if package.exists(): raise RuntimeError('LMA package already exists; review it before applying again')
    package.mkdir(parents=True)
    sources = ROOT/'integrations/sub2api/localgateway'
    for path in sources.glob('*.go'):
        shutil.copyfile(path, package/path.name)
    middleware = backend/'internal/server/routes/lma_local.go'
    if middleware.exists(): raise RuntimeError('LMA route adapter already exists')
    middleware.write_bytes((ROOT/'integrations/sub2api/lma_local.go.txt').read_bytes())
    test = middleware.with_name('lma_local_test.go')
    test.write_bytes((ROOT/'integrations/sub2api/lma_local_test.go.txt').read_bytes())
    route.write_bytes(text.encode('utf-8'))
    return dict(upstream_commit=UPSTREAM, original_route_sha256=ORIGINAL,
        patched_route_sha256=hashlib.sha256(route.read_bytes()).hexdigest(), opt_in_only=True,
        files=[str(p.relative_to(target)).replace('\\','/') for p in [route,middleware,test,*sorted(package.glob('*.go'))]],
        deployed=False, credentials_read=False, database_modified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--record',type=Path)
    args=parser.parse_args()
    result=apply(args.source)
    if args.record:
        args.record.parent.mkdir(parents=True,exist_ok=True)
        args.record.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
