"""Physical phone API and native Go forwarding checks with the actual OpenAI SDK.

Uses only already installed models and owned benign fixtures. Phone credentials
remain in RAM; the forwarding harness uses explicit fixture client identities.
It is not a live production Sub2API database/billing acceptance test.
"""
import argparse
import base64
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
import urllib.error
import urllib.request
import uuid

import httpx
from openai import OpenAI
from PIL import Image
from device_model_probe import phone_api
from evidence import ROOT, current, fingerprint, version


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    args=parser.parse_args()
    directory=ROOT/'build/device-sdk-integration'/str(time.time_ns())
    directory.mkdir(parents=True)
    inputs=fingerprint('app/src/main/java','app/src/main/assets/app.js',
        'integrations/sub2api','tools/device_sdk_integration.py','tools/device_model_probe.py')
    report=dict(schema='lma.physical-sdk-integration/1',version=version(),
        physical_device=True,virtualization_used=False,inference_location='same_android_phone',
        openai_sdk_version=importlib.metadata.version('openai'),checks=[],outputs=[],
        model_downloads=0,quality_accepted=False,background_endurance_verified=False,
        gateway_authentication='explicit Alice/Bob client fixtures; not production authentication',
        production_sub2api_deployment_tested=False,input_fingerprint=inputs)
    def save(): (directory/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def check(name,passed):
        report['checks'].append(dict(name=name,passed=bool(passed)));save()
        print(json.dumps(dict(check=name,passed=bool(passed))),flush=True)
        if not passed: raise RuntimeError('Physical integration check failed: '+name)
    child=None
    try:
        with phone_api(args.serial) as (phone,command):
            installed=command('shell','pm','path','com.lma.app').strip().removeprefix('package:')
            report['apk_sha256']=command('shell','sha256sum',installed).split()[0]
            build=json.loads((ROOT/'dist/build-info.json').read_text(encoding='utf8'))
            check('Exact final signed APK installed',report['apk_sha256']==build['sha256'])
            report['device']={k:command('shell','getprop',v).strip() for k,v in
                [('manufacturer','ro.product.manufacturer'),('model','ro.product.model'),('android','ro.build.version.release'),('api','ro.build.version.sdk')]}
            def raw(origin,key,method,path,body=None,headers=None):
                h={'Authorization':'Bearer '+key};h.update(headers or {})
                if isinstance(body,dict):body=json.dumps(body).encode();h['Content-Type']='application/json'
                req=urllib.request.Request(origin+path,data=body,method=method,headers=h)
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                try:
                    with opener.open(req,timeout=150) as r:return r.status,dict(r.headers),r.read()
                except urllib.error.HTTPError as e:return e.code,dict(e.headers),e.read()
            def sdk(origin,key):return OpenAI(base_url=origin+'/v1',api_key=key,max_retries=0,timeout=150,http_client=httpx.Client(trust_env=False))
            catalogue=phone('GET','/v1/models');report['models']=[dict(id=m['id'],operations=m['x_lma']['operations']) for m in catalogue['data']]
            speech=next(m['id'] for m in catalogue['data'] if 'speech.synthesize' in m['x_lma']['operations'])
            image=next(m['id'] for m in catalogue['data'] if 'image.generate' in m['x_lma']['operations'])
            mesh=next(m['id'] for m in catalogue['data'] if 'mesh.generate' in m['x_lma']['operations'])
            def start_gateway():
                env={**os.environ,'LMA_PROBE_PHONE_ORIGIN':phone.origin,'LMA_PROBE_PHONE_KEY':phone.api_key,'LMA_PROBE_DIRECTORY':str(directory/'private-gateway')}
                p=subprocess.Popen([str(ROOT/'build/sub2api-gateway-tests/lma-gateway-probe.exe')],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
                line=p.stdout.readline()
                if not line:raise RuntimeError('Native forwarding harness did not start')
                port=json.loads(line)['port']
                return p,'http://127.0.0.1:'+str(port)
            child,gateway=start_gateway()
            report['gateway_implementation']='integrations/sub2api/localgateway; native Windows Go, no virtualization'
            command('shell','input','keyevent','3');command('shell','input','keyevent','223')
            started_off=time.monotonic()
            with sdk(phone.origin,phone.api_key) as direct,sdk(gateway,'lma-probe-alice') as forwarded:
                direct_models=list(direct.models.list());forward_models=list(forwarded.models.list())
                check('Actual SDK discovers every eligible model directly and through forwarding',{m.id for m in direct_models}=={m.id for m in forward_models}=={m['id'] for m in catalogue['data']})
                check('Actual SDK retrieves an unloaded model detail',direct.models.retrieve(speech).id==speech)
                code,headers,_=phone('GET','/v1/models',detailed=True)
                etag=next(v for k,v in headers.items() if k.lower()=='etag')
                check('Phone catalogue ETag and HEAD are bodyless',phone('GET','/v1/models',extra={'If-None-Match':etag},detailed=True)[::2]==(304,b'') and phone('HEAD','/v1/models',detailed=True)[2]==b'')
                samples=[]
                for _ in range(30):
                    t=time.perf_counter();phone('GET','/v1/models');samples.append((time.perf_counter()-t)*1000)
                report['catalogue_latency_ms']=dict(samples=30,median=statistics.median(samples),p95=sorted(samples)[28],maximum=max(samples),transport='USB ADB TCP forwarding; includes client/transport overhead')
                speech_key='sdk-speech-'+uuid.uuid4().hex
                speech_args=dict(model=speech,input='你好，欢迎使用手机本地模型接口。',voice='default',response_format='wav',extra_body=dict(lma=dict(allow_unmeasured=True,parameters=dict(threads=2))),extra_headers={'Idempotency-Key':speech_key})
                t=time.monotonic()
                response=forwarded.audio.speech.with_raw_response.create(**speech_args)
                wav=response.parse().read();job_id=response.headers['x-lma-job-id']
                speech_time=time.monotonic()-t
                check('Actual SDK speech returns genuine WAV bytes through the gateway',wav[:4]==b'RIFF' and wav[8:12]==b'WAVE' and response.headers['content-type'].startswith('audio/wav'))
                (directory/'sdk-speech.wav').write_bytes(wav)
                report['outputs'].append(dict(file='sdk-speech.wav',model=speech,operation='speech.synthesize',elapsed_seconds=speech_time,bytes=len(wav),sha256=hashlib.sha256(wav).hexdigest(),quality_accepted=False))
                replay=forwarded.audio.speech.with_raw_response.create(**speech_args)
                check('A successful SDK retry reuses one physical phone job',replay.headers['x-lma-job-id']==job_id and replay.parse().read()==wav)
                code,_,b=raw(gateway,'lma-probe-alice','GET','/v1/lma/jobs/'+job_id)
                job=json.loads(b);check('Forwarded job and output IDs hide phone IDs',code==200 and job['id']==job_id and job_id.startswith('lma_job_') and len(job['outputs'])>0)
                artifact=job['outputs'][0]['id'];content='/v1/lma/artifacts/'+artifact+'/content'
                check('Other callers cannot read or cancel an owned job',all(raw(gateway,'lma-probe-bob',m,'/v1/lma/jobs/'+job_id)[0]==404 for m in ('GET','DELETE')))
                check('Other callers cannot read an owned artifact',raw(gateway,'lma-probe-bob','GET',content)[0]==404)
                code,h,b=raw(gateway,'lma-probe-alice','GET',content,headers={'Range':'bytes=0-31'})
                check('Forwarded Range returns the exact WAV slice',code==206 and b==wav[:32] and any(k.lower()=='content-range' for k in h))
                code,_,b=raw(gateway,'lma-probe-alice','GET',content,headers={'Range':'bytes=0-31','If-Range':'"stale"'})
                check('Forwarded stale If-Range returns the complete artifact',code==200 and b==wav)
                code,_,b=raw(gateway,'lma-probe-bob','GET','/v1/lma/jobs')
                check('Shared phone history is filtered before forwarding',code==200 and job_id not in b.decode() and len(json.loads(b)['data'])==0)
                b=io.BytesIO();Image.new('RGB',(64,64),'orange').save(b,format='PNG');fixture=b.getvalue()
                code,_,b=raw(gateway,'lma-probe-alice','POST','/v1/lma/uploads',dict(model=mesh,name='owned-sdk-cube.png',bytes=len(fixture),sha256=hashlib.sha256(fixture).hexdigest()))
                upload=json.loads(b)['id'];up='/v1/lma/uploads/'+upload
                check('Owned upload is bound to one caller and phone',code==202 and raw(gateway,'lma-probe-bob','GET',up)[0]==404)
                code,_,_=raw(gateway,'lma-probe-alice','PUT',up,fixture,{'Content-Type':'application/octet-stream','Upload-Offset':'1'})
                check('An out-of-bounds upload is rejected before writing',code==400)
                code,_,_=raw(gateway,'lma-probe-alice','PUT',up,fixture[:len(fixture)//2],{'Content-Type':'application/octet-stream','Upload-Offset':'1'})
                check('A conflicting valid-range offset fails before writing',code==409)
                check('Rejected upload chunks preserve the committed offset',json.loads(raw(gateway,'lma-probe-alice','GET',up)[2])['received']==0)
                code,_,b=raw(gateway,'lma-probe-alice','PUT',up,fixture,{'Content-Type':'application/octet-stream','Upload-Offset':'0'})
                check('Forwarded binary upload preserves offset and bytes',code==200 and json.loads(b)['received']==len(fixture))
                code,_,b=raw(gateway,'lma-probe-alice','POST',up+'/complete',{})
                input_id=json.loads(b)['id'];check('Upload completion returns an owned input artifact',code==200 and input_id.startswith('lma_artifact_'))
                payload=dict(model=mesh,type='mesh.generate',input=dict(artifacts=[dict(role='reference_image',artifactId=input_id)]),parameters=dict(steps=1,threads=2,resolution=512,faces=1000,texture=False,atlas=256),allowUnmeasured=True)
                code,_,b=raw(gateway,'lma-probe-alice','POST','/v1/lma/jobs/preflight',payload)
                check('Image-only 3D preflight needs no fabricated user prompt',code==200 and json.loads(b)['canEnqueue'])
                code,_,b=raw(gateway,'lma-probe-bob','POST','/v1/lma/jobs',payload,{'Idempotency-Key':'owned-input'})
                check('Another caller cannot attach the uploaded input',code==404)
                own_key='sdk-cancel-'+uuid.uuid4().hex
                code,_,b=raw(gateway,'lma-probe-alice','POST','/v1/lma/jobs',payload,{'Idempotency-Key':own_key})
                owned=json.loads(b)['id'];check('A real queued job is admitted through the extension',code==202)
                code,_,b=raw(gateway,'lma-probe-alice','POST','/v1/lma/jobs/'+owned+'/cancel',{})
                check('Explicit cancellation applies only to the owned job',code==200)
                for _ in range(30):
                    code,_,b=raw(gateway,'lma-probe-alice','GET','/v1/lma/jobs/'+owned)
                    if json.loads(b)['state'] in ('cancelled','interrupted','failed'):break
                    time.sleep(1)
                check('Cancellation reaches a terminal state on the phone',json.loads(b)['state']=='cancelled')
                code,_,b=raw(gateway,'lma-probe-alice','GET','/v1/lma/jobs/'+owned+'/events',headers={'Accept':'text/event-stream','Last-Event-ID':'0'})
                check('Shared gateway SSE rewrites only the owned phone events',code==200 and owned.encode() in b and b'job_fixture' not in b)
                t=time.monotonic()
                image_response=direct.images.with_raw_response.generate(model=image,prompt='An orange cube on a plain white background.',size='128x128',n=1,response_format='b64_json',extra_body=dict(lma=dict(allow_unmeasured=True,parameters=dict(steps=1,threads=4,cfg=4,seed=1234))),extra_headers={'Idempotency-Key':'sdk-image-'+uuid.uuid4().hex})
                png=base64.b64decode(image_response.parse().data[0].b64_json,validate=True)
                with Image.open(io.BytesIO(png)) as im:check('Actual SDK image response contains a decodable PNG',im.format=='PNG' and im.size==(128,128))
                (directory/'sdk-image.png').write_bytes(png)
                report['outputs'].append(dict(file='sdk-image.png',model=image,operation='image.generate',elapsed_seconds=time.monotonic()-t,bytes=len(png),sha256=hashlib.sha256(png).hexdigest(),quality_accepted=False))
            child.terminate();child.wait(timeout=10);child,gateway=start_gateway()
            with sdk(gateway,'lma-probe-alice') as restored:
                replay=restored.audio.speech.with_raw_response.create(**speech_args)
                check('Gateway restart preserves job binding and generation idempotency',replay.headers['x-lma-job-id']==job_id and replay.parse().read()==wav)
                check('Gateway restart preserves caller isolation',raw(gateway,'lma-probe-bob','GET',content)[0]==404)
            report['screen_off_api_seconds']=round(time.monotonic()-started_off,3)
            power=command('shell','dumpsys','power')
            check('SDK generation and forwarding completed while the phone remained asleep','mWakefulness=Asleep' in power or 'mWakefulness=Dozing' in power)
            command('shell','input','keyevent','224')
        current(inputs);report['status']='passed';report['passed']=len(report['checks']);save()
        print(json.dumps(dict(report=str((directory/'report.json').relative_to(ROOT)),passed=report['passed'])),flush=True)
    except Exception as e:
        # Never serialize exception bodies that could contain client headers.
        report['status']='failed';report['error_type']=type(e).__name__;save();raise RuntimeError('Physical SDK checks failed; inspect allowlisted report') from None
    finally:
        if child is not None and child.poll() is None:child.terminate();child.wait(timeout=10)


if __name__=='__main__':main()
