"""Exercise an installed physical LMA phone through direct LAN HTTP, without forwarding.

ADB only configures the authorized UI, discovers wlan0, records package identity,
and controls screen state. Every API byte uses a native IPv4 TCP connection bound
to the caller-selected physical PC address. Credentials stay in memory. Existing
models/settings/history are preserved; only explicitly owned test jobs are cleaned.
"""
import argparse
import base64
import hashlib
import http.client
import io
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import statistics
import socket
import subprocess
import time
import uuid
import wave
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from PIL import Image, ImageDraw
from evidence import ROOT, current, fingerprint


TERMINAL = {'succeeded', 'failed', 'cancelled', 'interrupted'}


class PhoneUI:
    def __init__(self, serial):
        self.adb = str(Path(os.environ['LOCALAPPDATA']) / 'Android/Sdk/platform-tools/adb.exe')
        self.serial = serial

    def command(self, *args):
        p = subprocess.run([self.adb, '-s', self.serial, *map(str, args)], cwd=ROOT,
                           capture_output=True, timeout=30)
        if p.returncode:
            raise RuntimeError('Authorized physical-device control failed')
        return p.stdout.decode('utf8', errors='replace')

    def dump(self):
        path = '/sdcard/Download/LMA-lan-http-ui.xml'
        try:
            self.command('shell', 'uiautomator', 'dump', path)
            raw = self.command('shell', 'cat', path)
            return ET.fromstring(raw[raw.index('<?xml'):])
        finally:
            self.command('shell', 'rm', '-f', path)

    @staticmethod
    def text(node):
        return node.get('text') or node.get('content-desc') or ''

    @staticmethod
    def bounds(node):
        values = list(map(int, re.findall(r'\d+', node.get('bounds', ''))))
        if len(values) != 4:
            raise RuntimeError('Missing visible UI bounds')
        return values

    def tap(self, node):
        x1, y1, x2, y2 = self.bounds(node)
        navigation = self.text(node) in {'模型库', '对话', '任务', '服务', '设置'} and y1 >= 2000
        if y2 <= y1 or y2 >= 2200 or (not navigation and y2 >= 2030):
            raise RuntimeError('Required UI control is not visible')
        self.command('shell', 'input', 'tap', (x1+x2)//2, (y1+y2)//2)

    def find(self, text, class_name=None):
        return [n for n in self.dump().iter('node') if self.text(n) == text and
                (not class_name or n.get('class') == class_name)]

    def service(self):
        self.command('shell', 'input', 'keyevent', 224)
        if re.search(r'^\s+showing=true\s*$', self.command('shell', 'dumpsys', 'window', 'policy'), re.M):
            raise RuntimeError('Unlock the authorized phone before running this test')
        self.command('shell', 'am', 'start', '-W', '-n', 'com.lma.app/.MainActivity')
        time.sleep(3)
        for _ in range(5):
            nav = self.find('服务')
            if nav:
                self.tap(max(nav, key=lambda n: self.bounds(n)[1]))
                break
            time.sleep(1)
        else:
            raise RuntimeError('LMA navigation is unavailable')
        for _ in range(2):
            self.command('shell', 'input', 'swipe', 950, 650, 950, 1850, 300)

    def key(self):
        for _ in range(5):
            nodes = self.find('显示或隐藏密钥')
            if nodes and self.bounds(nodes[0])[3] < 2030:
                toggle = nodes[0]
                break
            self.command('shell', 'input', 'swipe', 1000, 1750, 1000, 1250, 300)
        else:
            raise RuntimeError('API-key control is unavailable')
        try:
            self.tap(toggle)
            key = next((self.text(n) for n in self.dump().iter('node')
                        if re.fullmatch(r'lma_[A-Za-z0-9]+', self.text(n))), '')
        finally:
            self.tap(toggle)
        if not key:
            raise RuntimeError('Authorized UI did not provide a key')
        return key

    def screenshot(self, directory):
        for _ in range(2):
            self.command('shell', 'input', 'swipe', 950, 650, 950, 1850, 300)
        view = self.dump()
        assert not any(re.search(r'lma_[A-Za-z0-9]+', self.text(n)) for n in view.iter('node'))
        capture = subprocess.run([self.adb, '-s', self.serial, 'exec-out', 'screencap', '-p'],
                                 capture_output=True, timeout=30, check=True)
        picture = Image.open(io.BytesIO(capture.stdout)).convert('RGB')
        draw = ImageDraw.Draw(picture)
        draw.rectangle((0, 0, picture.width, 100), fill='#f4f5f7')
        masks = 0
        for n in view.iter('node'):
            if re.search(r'(?:\d{1,3}\.){3}\d{1,3}', self.text(n)):
                x1, y1, x2, y2 = self.bounds(n)
                if y1 < picture.height and y2 > y1:
                    draw.rectangle((x1, y1, x2, min(y2, picture.height)), fill='#e7e9ec')
                    draw.text((x1+8, y1+8), 'LAN address hidden', fill='#34383e')
                    masks += 1
        file = directory/'lan-enabled-redacted.png'
        picture.save(file)
        return dict(file=file.name, bytes=file.stat().st_size,
                    sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                    physical_screenshot=True, private_address_masks=masks,
                    api_key_visible=False, status_bar_masked=True)


class LanHTTP:
    def __init__(self, source, target, port, key):
        self.source, self.target, self.port, self.key = source, target, port, key
        self.connections = []

    def request(self, method, path, body=None, headers=None, auth=True, timeout=30, sse=False):
        assert path.startswith('/') and not path.startswith('//')
        h = {'Authorization': 'Bearer '+self.key} if auth else {}
        h.update(headers or {})
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode('utf8')
            h['Content-Type'] = 'application/json'
        conn = http.client.HTTPConnection(self.target, self.port, timeout=timeout,
                                          source_address=(self.source, 0))
        started = time.perf_counter()
        try:
            conn.connect()
            local, peer = conn.sock.getsockname(), conn.sock.getpeername()
            assert local[0] == self.source and peer == (self.target, self.port)
            conn.request(method, path, body=body, headers=h)
            response = conn.getresponse()
            if sse:
                chunks = []
                while len(chunks) < 40:
                    line = response.readline(65537)
                    if not line:
                        break
                    assert len(line) <= 65536
                    chunks.append(line)
                    if line in (b'\n', b'\r\n') and any(x.startswith(b'data:') for x in chunks):
                        break
                data = b''.join(chunks)
            else:
                data = response.read(32*1024*1024+1)
                assert len(data) <= 32*1024*1024
            self.connections.append(dict(local=list(local), peer=list(peer), method=method,
                path=path, status=response.status, elapsed_ms=(time.perf_counter()-started)*1000))
            return response.status, {k.lower():v for k,v in response.getheaders()}, data
        finally:
            conn.close()

    def json(self, method, path, body=None, headers=None):
        code, _, data = self.request(method, path, body, headers)
        assert code in (200, 202), 'Unexpected HTTP status '+str(code)
        return json.loads(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--upgrade-baseline', help='Private pre-upgrade model/settings/port receipt; credentials excluded')
    parser.add_argument('--source-address', required=True, help='IPv4 of the physical PC network adapter')
    parser.add_argument('--enable-lan', action='store_true', help='Explicitly enable LAN in the phone UI and leave it enabled')
    parser.add_argument('--run-existing-models', action='store_true', help='Run installed image/speech models; no downloads')
    parser.add_argument('--screen-off-seconds', type=int, default=60)
    args = parser.parse_args()
    if not args.run_existing_models or not args.enable_lan:
        parser.error('Explicit --enable-lan and --run-existing-models are required')
    if not 10 <= args.screen_off_seconds <= 300:
        parser.error('Screen-off HTTP sampling must be 10–300 seconds')
    source = ipaddress.IPv4Address(args.source_address)
    if not source.is_private or source.is_loopback or source.is_link_local:
        parser.error('Use the actual private IPv4 of the physical PC adapter')
    directory = ROOT/'build/device-lan-http'/str(time.time_ns())
    directory.mkdir(parents=True)
    inputs = fingerprint('tools/device_lan_http.py', 'app/src/main/java',
                         'app/src/main/assets/app.js', 'app/src/main/assets/engine-builds.json')
    report = dict(schema='lma.physical-lan-http/1', status='running', started_at=time.time(),
        input_fingerprint=inputs, checks=[], outputs=[], virtualization_used=False,
        model_downloads=0, remote_inference=False, proxy_used=False, adb_port_forward_used=False,
        transport='Native PC HTTP over the physical LAN to phone wlan0; no proxy/tunnel/forward',
        generation_deadline_seconds=None, new_video_generated=False, quality_accepted=False,
        background_endurance_tested=False)
    def save():
        (directory/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    def check(name, value):
        report['checks'].append(dict(name=name, passed=bool(value))); save()
        print(json.dumps(dict(check=name, passed=bool(value))), flush=True)
        if not value:
            raise RuntimeError('LAN HTTP check failed: '+name)
    ui = PhoneUI(args.serial)
    client = None
    owned = set()
    created = []
    before = None
    try:
        check('Authorized physical phone, without emulator',not args.serial.startswith('emulator-') and ui.command('shell','getprop','ro.kernel.qemu').strip()!='1')
        forward_before = ui.command('forward', '--list')
        address = ui.command('shell','ip','-4','addr','show','wlan0')
        network = ipaddress.IPv4Interface(re.search(r'\binet (\d+\.\d+\.\d+\.\d+/\d+)', address)[1])
        check('PC physical address and phone wlan0 share a private subnet', source in network.network and source!=network.ip and network.ip.is_private)
        ui.service()
        report['setup_stage']='enable_lan'
        switches = ui.find('允许局域网访问', 'android.widget.CheckBox')
        assert len(switches)==1
        urls=[ui.text(n) for n in ui.dump().iter('node') if re.fullmatch(r'http://[0-9.]+:[0-9]+/v1',ui.text(n))]
        assert len(urls)==1
        displayed=urlsplit(urls[0]);port=displayed.port
        report["api_port"]=port
        if json.loads((ROOT/"dist/build-info.json").read_text(encoding="utf8"))["version"] == "0.3.13":
            check("Upgraded service advertises the five-digit default 52187",port==52187)
            refused = False
            try:
                with socket.create_connection((str(network.ip),8080),timeout=3,source_address=(str(source),0)):
                    pass
            except ConnectionRefusedError:
                refused = True
            check("Former default 8080 no longer accepts LAN connections",refused)
        # This WebView exposes checked=false even for the enabled custom switch.
        # Its rendered base URL follows the persisted LAN preference reliably.
        report['lan_ui_initially_enabled'] = not ipaddress.IPv4Address(displayed.hostname).is_loopback
        if not report['lan_ui_initially_enabled']:
            ui.tap(switches[0]); time.sleep(1)
        if ui.find('启动接口'):
            ui.tap(ui.find('启动接口')[0]); time.sleep(1)
        report['lan_enabled_by_test'] = not report['lan_ui_initially_enabled']
        # Actual listening/routing is established by the TCP endpoints below;
        # WebView accessibility checkbox state alone is not used as proof.
        report['setup_stage']='read_key'
        key = ui.key()
        client = LanHTTP(str(source), str(network.ip), port, key); key = ''
        report['setup_stage']='verify_package_and_tcp'
        installed = next(line[8:] for line in ui.command('shell','pm','path','com.lma.app').splitlines() if line.startswith('package:') and line.endswith('/base.apk'))
        report['apk_sha256'] = ui.command('shell','sha256sum',installed).split()[0]
        build = json.loads((ROOT/'dist/build-info.json').read_text(encoding='utf8'))
        check('Installed signed APK matches the stable release', report['apk_sha256']==build['sha256'])
        report['device']={k:ui.command('shell','getprop',v).strip() for k,v in [('model','ro.product.model'),('android','ro.build.version.release'),('api','ro.build.version.sdk'),('soc','ro.soc.model')]}
        health = client.json('GET','/health'); report['version']=health['version']
        check('LAN health confirms phone-local execution',health['status']=='ok' and health['execution']=='same_android_phone' and health['version']==build['version'])
        check('Missing key is rejected over LAN',client.request('GET','/v1/models',auth=False)[0]==401)
        check('Wrong key is rejected over LAN',client.request('GET','/v1/models',headers={'Authorization':'Bearer invalid-lan-fixture'})[0]==401)
        check('Browser origins are rejected over LAN',client.request('GET','/v1/models',headers={'Origin':'https://example.invalid'})[0]==403)
        code,h,data=client.request('GET','/v1/models'); catalogue=json.loads(data);models=catalogue['data']
        check('Installed configured models are advertised on the LAN',code==200 and len(models)>0 and all(m['x_lma']['publication']['eligible'] for m in models))
        report['published_models']=len(models)
        report['published_operation_counts']={op:sum(op in m['x_lma']['operations'] for m in models) for op in sorted({op for m in models for op in m['x_lma']['operations']})}
        check('Catalogue conditional GET is 304 and bodyless',client.request('GET','/v1/models',headers={'If-None-Match':h['etag']})[::2]==(304,b''))
        check('Catalogue HEAD has no body',client.request('HEAD','/v1/models')[2]==b'')
        for index,m in enumerate(models,1):
            detail=client.json('GET','/v1/models/'+m['id'])
            check('Advertised model detail '+str(index)+' retains schema and settings',detail['id']==m['id'] and detail['x_lma']['parameter_schema']==m['x_lma']['parameter_schema'] and detail['parameters']==m['parameters'])
        check('Capabilities declare no fixed generation wall-time limit',client.json('GET','/v1/capabilities')['limits']['generation_wall_time_seconds'] is None)
        check('Uninstalled model is unavailable without download',client.request('GET','/v1/models/not-installed-lan-fixture')[0]==404)
        before=client.json('GET','/v1/jobs')['data'];assert all(j['state'] in TERMINAL for j in before),'Preserve existing active work'
        before_ids={j['id'] for j in before}
        models_before={m['id']:m['parameters'] for m in models}
        if args.upgrade_baseline:
            baseline=json.loads(Path(args.upgrade_baseline).read_text(encoding='utf8'))
            check("Signed upgrade migrated the former 8080 default",baseline['pre_upgrade_port']==8080 and port==52187)
            check("Upgrade preserves every installed model and its configured parameters",baseline['models']==models_before)
            check("Upgrade preserves existing user task history",set(baseline['history_ids'])<=before_ids)
            check("Upgrade preserves the existing API credential",baseline['key_identity']==hashlib.sha256(client.key.encode()).hexdigest())
            report['upgrade_verified']=True
            report['previous_default_port']=baseline['pre_upgrade_port']
        speech=next(m['id'] for m in models if 'speech.synthesize' in m['x_lma']['operations'])
        image=next(m['id'] for m in models if 'image.generate' in m['x_lma']['operations'])
        mesh=next(m['id'] for m in models if 'mesh.generate' in m['x_lma']['operations'])
        video=next(m['id'] for m in models if 'video.generate' in m['x_lma']['operations'])
        latency=[]
        for _ in range(30):
            t=time.perf_counter();client.json('GET','/v1/models');latency.append((time.perf_counter()-t)*1000)
        report['catalogue_latency_ms']=dict(samples=len(latency),median=statistics.median(latency),p95=sorted(latency)[math.ceil(.95*len(latency))-1],maximum=max(latency))
        check('Thirty direct LAN discovery requests succeed',len(latency)==30)
        invalid=dict(model=image,prompt='Owned LAN fixture',n=2,response_format='b64_json')
        check('Unsupported image batch is rejected before enqueue',client.request('POST','/v1/images/generations',invalid)[0]==400)
        check('Rejected generation does not create a task',{j['id'] for j in client.json('GET','/v1/jobs')['data']}==before_ids)
        vp=dict(model=video,type='video.generate',input=dict(prompt='An orange cube on white.'),parameters=dict(width=128,height=128,frames=49,fps=8,steps=4,threads=4,executionBackend='cpu'),allowUnmeasured=True)
        check('Longer-than-five-second video request passes LAN preflight',client.json('POST','/v1/lma/jobs/preflight',vp)['canEnqueue'])

        # Keep the phone screen off for actual generation as well as health calls.
        report['media']=ui.screenshot(directory)
        ui.command('shell','input','keyevent',3);ui.command('shell','input','keyevent',223)
        off=time.monotonic()
        def await_job(jid):
            stage=None
            while True:
                j=client.json('GET','/v1/lma/jobs/'+jid)
                if j.get('stage')!=stage:
                    stage=j.get('stage');print(json.dumps(dict(owned_job_stage=stage)),flush=True)
                if j['state'] in TERMINAL:return j
                time.sleep(1)

        body=dict(model=speech,type='speech.synthesize',input=dict(prompt='你好，这是局域网本地接口验证。'),parameters=dict(threads=2),allowUnmeasured=True)
        request_key='lan-speech-'+uuid.uuid4().hex
        started=time.monotonic();code,_,raw=client.request('POST','/v1/lma/jobs',body,{'Idempotency-Key':request_key})
        job=json.loads(raw);jid=job['id'];owned.add(jid);created.append(jid)
        check('LAN async speech is admitted with 202',code==202)
        replay=client.json('POST','/v1/lma/jobs',body,{'Idempotency-Key':request_key})
        check('LAN replay reuses the original job',replay['id']==jid)
        changed=dict(body);changed['input']=dict(prompt='A different owned request.')
        check('Changed body with the same key conflicts',client.request('POST','/v1/lma/jobs',changed,{'Idempotency-Key':request_key})[0]==409)
        # Queue and cancel only a second owned speech task; it cannot consume the
        # user's models/settings or run a heavy 3D test unexpectedly.
        queued=client.json('POST','/v1/lma/jobs',body,{'Idempotency-Key':'lan-cancel-'+uuid.uuid4().hex});cancelled_id=queued['id'];owned.add(cancelled_id);created.append(cancelled_id)
        check('An independent owned task is admitted',cancelled_id!=jid)
        client.json('POST','/v1/lma/jobs/'+cancelled_id+'/cancel',{})
        cancelled=await_job(cancelled_id)
        check('LAN cancellation reaches the owned terminal state',cancelled['state']=='cancelled')
        speech_job=await_job(jid)
        check('New phone-local speech completes via LAN',speech_job['state']=='succeeded' and len(speech_job['outputs'])==1)
        artifact=speech_job['outputs'][0];code,_,wav=client.request('GET',artifact['content_path'])
        with wave.open(io.BytesIO(wav),'rb') as audio:
            duration=audio.getnframes()/audio.getframerate();channels=audio.getnchannels();rate=audio.getframerate()
        check('Downloaded WAV is valid and matches the phone SHA',code==200 and duration>0 and hashlib.sha256(wav).hexdigest()==artifact['sha256'] and len(wav)==artifact['bytes'])
        (directory/'lan-speech.wav').write_bytes(wav)
        report['outputs'].append(dict(file='lan-speech.wav',operation='speech.synthesize',elapsed_seconds=round(time.monotonic()-started,3),duration_seconds=duration,channels=channels,sample_rate=rate,bytes=len(wav),sha256=artifact['sha256'],quality_accepted=False))
        speech_body=dict(model=speech,input='你好，这是局域网标准语音接口验证。',voice='default',response_format='wav',lma=dict(allow_unmeasured=True,parameters=dict(threads=2)))
        started=time.monotonic()
        code,h,wav2=client.request('POST','/v1/audio/speech',speech_body,{'Idempotency-Key':'lan-standard-speech-'+uuid.uuid4().hex},timeout=150)
        jid2=h.get('x-lma-job-id');assert jid2;owned.add(jid2);created.append(jid2)
        if code==504:
            sj2=await_job(jid2);assert sj2['state']=='succeeded';code,h,wav2=client.request('GET',sj2['outputs'][0]['content_path'])
        check('OpenAI speech route returns WAV over raw LAN HTTP',code==200 and h.get('content-type','').startswith('audio/wav') and wav2[:4]==b'RIFF' and wav2[8:12]==b'WAVE')
        artifact2=client.json('GET','/v1/lma/jobs/'+jid2)['outputs'][0]
        with wave.open(io.BytesIO(wav2),'rb') as audio:
            duration2=audio.getnframes()/audio.getframerate();rate2=audio.getframerate();channels2=audio.getnchannels()
        check('Standard WAV is valid and matches its phone artifact',duration2>0 and hashlib.sha256(wav2).hexdigest()==artifact2['sha256'])
        (directory/'lan-standard-speech.wav').write_bytes(wav2)
        report['outputs'].append(dict(file='lan-standard-speech.wav',operation='speech.synthesize',route='/v1/audio/speech',elapsed_seconds=round(time.monotonic()-started,3),duration_seconds=duration2,channels=channels2,sample_rate=rate2,bytes=len(wav2),sha256=artifact2['sha256'],quality_accepted=False))
        output_key='lan-image-'+uuid.uuid4().hex
        image_body=dict(model=image,prompt='An orange cube on a plain white background.',n=1,size='128x128',response_format='b64_json',lma=dict(allow_unmeasured=True,parameters=dict(steps=1,threads=4,cfg=4,seed=1234)))
        started=time.monotonic();code,h,raw=client.request('POST','/v1/images/generations',image_body,{'Idempotency-Key':output_key},timeout=150)
        jid=h.get('x-lma-job-id');assert jid;owned.add(jid);created.append(jid)
        if code==504:
            image_job=await_job(jid);assert image_job['state']=='succeeded';png=client.request('GET',image_job['outputs'][0]['content_path'])[2]
        else:
            assert code==200;png=base64.b64decode(json.loads(raw)['data'][0]['b64_json'],validate=True)
            image_job=client.json('GET','/v1/lma/jobs/'+jid)
        with Image.open(io.BytesIO(png)) as im:
            check('LAN image route produces a new decodable PNG',im.format=='PNG' and im.size==(128,128))
        artifact=image_job['outputs'][0]
        check('New PNG matches committed artifact SHA',hashlib.sha256(png).hexdigest()==artifact['sha256'])
        (directory/'lan-image.png').write_bytes(png)
        report['outputs'].append(dict(file='lan-image.png',operation='image.generate',elapsed_seconds=round(time.monotonic()-started,3),bytes=len(png),sha256=artifact['sha256'],width=128,height=128,steps=1,quality_accepted=False))
        check('Successful LAN image replay returns the same job',client.request('POST','/v1/images/generations',image_body,{'Idempotency-Key':output_key},timeout=150)[1].get('x-lma-job-id')==jid)
        cp=artifact['content_path'];full=client.request('GET',cp);etag=full[1]['etag']
        check('Authenticated artifact GET returns exact PNG bytes',full[0]==200 and full[2]==png)
        rc,rh,rb=client.request('GET',cp,headers={'Range':'bytes=0-31'})
        check('LAN Range preserves exact bytes and Content-Range',rc==206 and rb==png[:32] and rh['content-range']==f'bytes 0-31/{len(png)}')
        check('Matching If-Range retains partial download',client.request('GET',cp,headers={'Range':'bytes=0-31','If-Range':etag})[0]==206)
        check('Stale If-Range restarts a full download',client.request('GET',cp,headers={'Range':'bytes=0-31','If-Range':'"stale-lan-test"'})[::2]==(200,png))
        check('Artifact conditional GET is 304',client.request('GET',cp,headers={'If-None-Match':etag})[0]==304)
        check('Artifact HEAD has no body',client.request('HEAD',cp)[2]==b'')
        check('Artifact download rejects a missing key',client.request('GET',cp,auth=False)[0]==401)
        check('Task events are readable over LAN',isinstance(client.json('GET','/v1/lma/jobs/'+jid+'/events')['events'],list))
        rc,rh,rb=client.request('GET','/v1/lma/jobs/'+jid+'/events',headers={'Accept':'text/event-stream','Last-Event-ID':'0'},sse=True)
        check('Direct LAN SSE emits a real framed event',rc==200 and rh.get('content-type','').startswith('text/event-stream') and b'data:' in rb)

        # Transfer an owned image in actual binary chunks, then exercise typed
        # image-only 3D preflight without running the costly 3D model.
        upload=client.json('POST','/v1/lma/uploads',dict(model=mesh,name='owned-lan-cube.png',bytes=len(png),sha256=hashlib.sha256(png).hexdigest()))
        up='/v1/lma/uploads/'+upload['id']
        check('Out-of-bounds binary upload fails before writing',client.request('PUT',up,png,{'Content-Type':'application/octet-stream','Upload-Offset':'1'})[0]==400)
        check('Valid-range wrong upload offset conflicts',client.request('PUT',up,png[:32],{'Content-Type':'application/octet-stream','Upload-Offset':'1'})[0]==409)
        check('Rejected chunks do not advance the upload',client.json('GET',up)['received']==0)
        offset=0
        while offset<len(png):
            chunk=png[offset:offset+8192];code,_,raw=client.request('PUT',up,chunk,{'Content-Type':'application/octet-stream','Upload-Offset':str(offset)});offset+=len(chunk)
            assert code==200 and json.loads(raw)['received']==offset
        check('LAN binary chunks preserve offset and total length',offset==len(png))
        uploaded=client.json('POST',up+'/complete',{})
        check('Upload completion verifies the input SHA',uploaded['sha256']==hashlib.sha256(png).hexdigest())
        mp=dict(model=mesh,type='mesh.generate',input=dict(artifacts=[dict(role='reference_image',artifactId=uploaded['id'])]),parameters=dict(steps=12,guidance=7.5,threads=6,resolution=512,faces=1000,texture=False,atlas=256),allowUnmeasured=True)
        check('Image-only 3D preflight accepts typed LAN upload',client.json('POST','/v1/lma/jobs/preflight',mp)['canEnqueue'])
        expected_video=json.loads((ROOT/'docs/media/benchmarks/v0.3.12/manifest.json').read_text(encoding='utf8'))['original_video_sha256']
        existing=client.json('GET','/v1/lma/artifacts')['data']
        old_video=next(a for a in existing if a.get('sha256')==expected_video and a.get('mime')=='video/mp4')
        path='/v1/lma/artifacts/'+old_video['id']+'/content'
        code,_,mp4=client.request('GET',path)
        check('Previously verified video downloads unchanged over LAN',code==200 and hashlib.sha256(mp4).hexdigest()==expected_video)
        (directory/'existing-video.mp4').write_bytes(mp4)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=nb_frames:format=duration','-of','json',str(directory/'existing-video.mp4')],text=True,encoding='utf8'))
        check('Downloaded existing video is genuinely longer than five seconds',float(probe['format']['duration'])>5 and int(probe['streams'][0]['nb_frames'])==49)
        check('Existing video Range returns real byte slices',client.request('GET',path,headers={'Range':'bytes=16-47'})[::2]==(206,mp4[16:48]))
        report['existing_video']=dict(newly_generated=False,duration_seconds=float(probe['format']['duration']),frames=49,bytes=len(mp4),sha256=expected_video)
        health_calls=0
        until=time.monotonic()+args.screen_off_seconds
        while time.monotonic()<until:
            assert client.json('GET','/health')['status']=='ok';health_calls+=1;time.sleep(2)
        power=ui.command('shell','dumpsys','power')
        report['screen_off']=dict(seconds=round(time.monotonic()-off,3),post_generation_health_requests=health_calls,minimum_post_generation_seconds=args.screen_off_seconds)
        check('LAN generation and health complete with the screen asleep','mWakefulness=Asleep' in power or 'mWakefulness=Dozing' in power)
        # Back up only the cancelled fixture job, then remove its history. Keep
        # successful artifacts and every unrelated user record.
        (directory/'cancelled-job-private.json').write_text(json.dumps(cancelled,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        check('Only the owned cancelled fixture history is removed',client.request('DELETE','/v1/lma/jobs/'+cancelled_id)[0]==200)
        after_ids={j['id'] for j in client.json('GET','/v1/jobs')['data']}
        check('All pre-existing user task records are preserved',before_ids<=after_ids)
        after=client.json('GET','/v1/models')['data']
        check('Installed models and saved parameters are unchanged',{m['id']:m['parameters'] for m in after}==models_before)
        check('This test creates no ADB port forward',ui.command('forward','--list')==forward_before)
        check('Every API connection uses the physical LAN endpoints',len(client.connections)>100 and all(c['local'][0]==str(source) and c['peer']==[str(network.ip),port] for c in client.connections))
        report['http_requests']=len(client.connections)
        report['tcp_endpoints_verified']=True
        report['lan_left_enabled']=True
        report['user_history_preserved']=True
        report['model_settings_preserved']=True
        report['status']='passed';report['passed']=len(report['checks']);report['finished_at']=time.time()
        current(inputs);save()
        print(json.dumps(dict(report=str((directory/'report.json').relative_to(ROOT)),passed=report['passed'],http_requests=report['http_requests'])),flush=True)
    except Exception as exc:
        report['status']='failed';report['error_type']=type(exc).__name__;save()
        raise RuntimeError('LAN HTTP integration failed; inspect the allowlisted report') from None
    finally:
        if client:
            (directory/'connection-proof-private.json').write_text(json.dumps(client.connections,indent=2)+'\n',encoding='utf8')
            if report['status']!='passed':
                for jid in owned:
                    try:
                        if client.json('GET','/v1/lma/jobs/'+jid)['state'] not in TERMINAL:
                            client.json('POST','/v1/lma/jobs/'+jid+'/cancel',{})
                    except Exception:
                        pass
            client.key=''
        # Wake only; lock credentials are never accepted or stored by this tool.
        ui.command('shell','input','keyevent',224)


if __name__=='__main__':
    main()
