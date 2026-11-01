"""Explicit bounded inference on an authorized physical phone's already installed models.

Never downloads or copies model weights. Uses an owned cube image, private local
reports and an in-memory API key obtained from the app UI. No unlock credentials
are accepted or stored. Cancels only the job created by this invocation on timeout.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def phone_api(serial):
    import os
    adb = str(Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe')
    def command(*args, timeout=25):
        p = subprocess.run([adb, '-s', serial, *args], cwd=ROOT, capture_output=True,
            text=True, encoding='utf-8', errors='replace', timeout=timeout)
        if p.returncode: raise RuntimeError('Physical device command failed')
        return p.stdout
    if serial.startswith('emulator-') or command('shell', 'getprop', 'ro.kernel.qemu').strip() == '1':
        raise RuntimeError('Physical devices only')
    if re.search(r'^\s+showing=true\s*$', command('shell', 'dumpsys', 'window', 'policy'), re.M):
        raise RuntimeError('Unlock the authorized phone before the probe')
    command('shell', 'am', 'start', '-W', '-n', 'com.lma.app/.MainActivity')
    time.sleep(3)
    def ui():
        path = '/sdcard/Download/LMA-probe-ui.xml'
        try:
            for attempt in range(4):
                command('shell', 'uiautomator', 'dump', path)
                try:
                    raw = command('shell', 'cat', path)
                    if '<?xml' in raw: return ET.fromstring(raw[raw.index('<?xml'):])
                except (RuntimeError, ValueError, ET.ParseError): pass
                time.sleep(1)
            raise RuntimeError('App accessibility view is not ready; credentials are never logged')
        finally: command('shell', 'rm', '-f', path)
    def center(node):
        b = list(map(int, re.findall(r'\d+', node.get('bounds', ''))))
        if len(b) != 4: raise RuntimeError('Missing UI control bounds')
        return ((b[0]+b[2])//2, (b[1]+b[3])//2)
    def tap(point): command('shell', 'input', 'tap', *map(str, point))
    for attempt in range(5):
        document = ui()
        nav = [n for n in document.iter('node') if (n.get('text') or n.get('content-desc')) == '服务']
        if nav: break
        time.sleep(1)
    if not nav: raise RuntimeError('App navigation is not ready; no model task was submitted')
    tap(max((center(n) for n in nav), key=lambda p: p[1]))
    time.sleep(.5)
    # Restore the page top after earlier UI tests; otherwise the key can be above
    # the current scroll position and scrolling downward would never find it.
    for _ in range(2): command('shell', 'input', 'swipe', '950', '650', '950', '1850', '300')
    toggle = None
    for _ in range(5):
        document = ui()
        nodes = [n for n in document.iter('node') if (n.get('text') or n.get('content-desc')) == '显示或隐藏密钥']
        if nodes:
            toggle = center(nodes[0])
            if toggle[1] < 2050: break
        command('shell', 'input', 'swipe', '1000', '1750', '1000', '950', '300')
    if toggle is None: raise RuntimeError('Cannot locate the app API-key toggle; no credentials logged')
    key = ''
    try:
        tap(toggle)
        for node in ui().iter('node'):
            text = node.get('text') or node.get('content-desc') or ''
            if re.fullmatch(r'lma_[A-Za-z0-9]+', text): key = text
    finally: tap(toggle)
    if not key: raise RuntimeError('Cannot read API key from authorized UI')
    forwarding = command('forward', 'tcp:0', 'tcp:8080').strip()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(method, path, data=None, mime='application/json', extra=None, raw=False, timeout=25, detailed=False):
        headers = {'Authorization': 'Bearer '+key, 'Content-Type': mime}
        headers.update(extra or {})
        payload = json.dumps(data).encode() if isinstance(data, dict) else data
        req = urllib.request.Request('http://127.0.0.1:'+forwarding+path, data=payload, method=method, headers=headers)
        try:
            with opener.open(req, timeout=timeout) as r:
                content = r.read()
                if detailed: return (r.status, dict(r.headers), content)
                return content if raw else json.loads(content)
        except urllib.error.HTTPError as error:
            if detailed: return (error.code, dict(error.headers), error.read())
            body = json.load(error)
            raise RuntimeError('Phone API '+str(error.code)+': '+json.dumps(body, ensure_ascii=False)) from None
    # Explicit in-memory handoff for SDK/forwarding checks. Never serialize these.
    request.origin = 'http://127.0.0.1:'+forwarding
    request.api_key = key
    try: yield request, command
    finally:
        command('forward', '--remove', 'tcp:'+forwarding)
        request.api_key = ''
        request.origin = ''
        key = ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--budget-seconds', type=int, default=180)
    parser.add_argument('--backend', choices=('cpu', 'vulkan'))
    parser.add_argument('--steps', type=int, default=1, help='Video sampling steps, limited to 1–8 for bounded probes')
    parser.add_argument('--cfg', type=float, default=1, help='Video guidance, limited to 0–9 for bounded probes')
    parser.add_argument('--allow-existing-model-inference', action='store_true')
    args = parser.parse_args()
    if not args.allow_existing_model_inference: parser.error('Explicit existing-model inference authorization is required')
    if not 15 <= args.budget_seconds <= 600: parser.error('Budget must be 15–600 seconds')
    if not 1 <= args.steps <= 8 or not 0 <= args.cfg <= 9: parser.error('Video probe steps/CFG are outside the bounded range')
    directory = ROOT/'build/device-model-probes'/str(time.time_ns())
    directory.mkdir(parents=True)
    report = dict(bundle_id=args.bundle, physical_device=True, existing_trained_model=True,
        new_model_downloads=False, model_weights_copied=False, budget_seconds=args.budget_seconds,
        user_authorized_partial_model_validation=True, quality_accepted=False, stages=[])
    def save(): (directory/'result-private.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    job_id = ''
    with phone_api(args.serial) as (request, command):
        apk_path = next(line[8:] for line in command('shell','pm','path','com.lma.app').splitlines() if line.startswith('package:') and line.endswith('/base.apk'))
        report['apk_sha256'] = command('shell','sha256sum',apk_path).split()[0]
        if not re.fullmatch(r'[a-f0-9]{64}', report['apk_sha256']): raise RuntimeError('Cannot bind probe to the installed APK')
        report['device'] = {key:command('shell','getprop',prop).strip() for key,prop in dict(model='ro.product.model',manufacturer='ro.product.manufacturer',android='ro.build.version.release',api='ro.build.version.sdk').items()}
        models = request('GET', '/v1/models')['data']
        model = next(m for m in models if m['id'] == args.bundle and m['installed'])
        jobs = request('GET', '/v1/jobs')['data']
        if any(j['state'] not in ('succeeded', 'failed', 'cancelled', 'interrupted') for j in jobs):
            raise RuntimeError('Existing active jobs are preserved; no probe was submitted')
        mesh = '3d' in model['task_tags']
        if not mesh and 'video' not in model['task_tags']: raise RuntimeError('Only explicit mesh/video probes are supported')
        params = dict(model['parameters']['values'])
        if mesh:
            from PIL import Image, ImageDraw
            image = Image.new('RGBA', (512, 512), (255, 255, 255, 0)); draw = ImageDraw.Draw(image)
            draw.polygon([(128,180),(256,110),(384,180),(256,250)], fill=(255,184,78,255))
            draw.polygon([(128,180),(256,250),(256,400),(128,328)], fill=(214,105,40,255))
            draw.polygon([(256,250),(384,180),(384,328),(256,400)], fill=(245,142,48,255))
            fixture = directory/'owned-cube.png'; image.save(fixture); data = fixture.read_bytes()
            upload = request('POST', '/v1/uploads', dict(name='LMA-owned-cube.png', bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
            path = '/v1/uploads/'+upload['id']
            request('PUT', path, data, 'application/octet-stream', {'Upload-Offset': '0'})
            artifact = request('POST', path+'/complete', {})
            report['owned_input_artifact'] = artifact['id']
            input_value = dict(prompt='Generate a 3D asset from the selected local image.', artifacts=[dict(role='reference_image', artifactId=artifact['id'])])
            params.update(resolution=512, steps=1, faces=1000, atlas=256, threads=4, texture=False, guidance=1)
        else:
            input_value = dict(prompt='An orange cube rotating slowly on a plain white background.')
            params.update(width=128, height=128, frames=5, steps=args.steps, cfg=args.cfg, threads=4, vaeTiling=True, vaeTileSize=128)
            if args.backend: params['executionBackend'] = args.backend
        payload = dict(bundleId=args.bundle, type='mesh.generate' if mesh else 'video.generate', input=input_value, parameters=params, allowUnmeasured=True)
        report['request'] = payload
        report['preflight'] = request('POST', '/v1/jobs/preflight', payload)
        if not report['preflight'].get('canEnqueue'):
            report['outcome'] = 'preflight_rejected'; save()
            print(json.dumps(dict(outcome=report['outcome'], issues=report['preflight'].get('issues'), report=str(directory.relative_to(ROOT))), ensure_ascii=False), flush=True)
            return
        try:
            submitted = request('POST', '/v1/jobs', payload)
            job_id = submitted['id']; report['job_id'] = job_id; started = time.monotonic(); last_stage = None
            while True:
                job = request('GET', '/v1/jobs/'+job_id)
                report['last_job'] = job
                stage = (job['state'], job.get('stage'))
                if stage != last_stage:
                    last_stage = stage; report['stages'].append(dict(state=stage[0], stage=stage[1], elapsed_seconds=round(time.monotonic()-started, 2)))
                    print(json.dumps(dict(bundle=args.bundle, state=stage[0], stage=stage[1], elapsed_seconds=round(time.monotonic()-started, 2)), ensure_ascii=False), flush=True)
                save()
                if job['state'] in ('succeeded','failed','cancelled','interrupted'):
                    report['outcome'] = job['state']; break
                if time.monotonic()-started >= args.budget_seconds:
                    request('POST', '/v1/jobs/'+job_id+'/cancel', {}); report['outcome'] = 'bounded_timeout_cancel_requested'; break
                time.sleep(3)
            report['elapsed_seconds'] = round(time.monotonic()-started, 2)
        finally:
            if job_id:
                latest = request('GET', '/v1/jobs/'+job_id)
                if latest['state'] not in ('succeeded','failed','cancelled','interrupted'):
                    request('POST', '/v1/jobs/'+job_id+'/cancel', {})
                    for attempt in range(15):
                        time.sleep(.5); latest = request('GET', '/v1/jobs/'+job_id)
                        if latest['state'] in ('succeeded','failed','cancelled','interrupted'): break
                report['last_job'] = latest
                verified=[]
                if latest['state']=='succeeded':
                    for ident in latest['artifacts']:
                        meta=request('GET','/v1/artifacts/'+ident)
                        content=request('GET','/v1/artifacts/'+ident+'/content',raw=True)
                        digest=hashlib.sha256(content).hexdigest()
                        if len(content)!=meta['bytes'] or digest!=meta['sha256']: raise RuntimeError('Generated artifact identity mismatch')
                        output=directory/('owned-result.'+('glb' if mesh else 'mp4'));output.write_bytes(content)
                        verified.append(dict(bytes=len(content),sha256=digest,local_file=output.name,metadata=meta))
                report['verified_artifacts']=verified
            save()
        print(json.dumps(dict(outcome=report['outcome'], report=str(directory.relative_to(ROOT)), full_model_quality_accepted=False), ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
