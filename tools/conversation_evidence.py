"""Export bounded UI regression evidence without inventing a phone latency measurement."""
import hashlib,json
from evidence import ROOT,current,fingerprint,version

MEDIA = 'docs/media/conversation-v' + version()

def main():
    source=ROOT/'build/conversation-ui/results.json';ui=json.loads(source.read_text(encoding='utf-8'))
    current(ui['input_fingerprint'])
    assert ui['version']==version() and ui['browser_closed'] and ui['passed']>=30
    checks=[
        'Fresh default stays dark when the system theme is light',
        '1000 mixed messages mount only the newest 60',
        '100 indexed assets do not start media players or GLB decoding',
        'Message blocks hold managed references without media bytes',
        'Streaming preserves unchanged row and content DOM identity',
        'A streamed token mutates only its target message',
        'Cursor paging replaces the bounded viewport without losing older history',
        'Production pages have no unhandled script errors',
    ]
    assert set(checks)<=set(ui['checks']) and ui['fixture']==dict(sessions=100,messages=1000,artifacts=100,mounted=60)
    build=json.loads((ROOT/'dist/build-info.json').read_text(encoding='utf-8'));assert build['version']==version()
    media=json.loads((ROOT/MEDIA/'manifest.json').read_text(encoding='utf-8'));current(media['input_fingerprint'])
    for f in media['files']:
        path=ROOT/MEDIA/f['file']
        assert path.stat().st_size==f['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256']
    record=dict(schema='lma.program-ui-regression/1',version=version(),passed=len(checks),checks=checks,
        apk_sha256=build['sha256'],fixture=ui['fixture'],ui_uses_simulated_bridge=True,
        current_physical_performance_measured=False,physical_device_tests=0,model_inference=False,
        measurement_scope='Eight executable program regressions; no phone latency, codec, inference or endurance measurement',
        input_fingerprint=fingerprint('tools/conversation_evidence.py','build/conversation-ui/results.json',MEDIA+'/manifest.json',*ui['input_fingerprint']))
    out=ROOT/'build/device-tests';out.mkdir(parents=True,exist_ok=True)
    (out/'ui-performance.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=len(checks),current_physical_performance_measured=False)))

if __name__=='__main__':main()
