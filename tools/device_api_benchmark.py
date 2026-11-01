"""Explicit full API integration and bounded inference on an authorized physical phone.

Uses existing installed assets only. Preserves personal jobs and saved model settings.
Reports owned outputs separately from protocol success and subjective model quality.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import threading
import time
import uuid
from device_model_probe import phone_api

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = ('succeeded', 'failed', 'cancelled', 'interrupted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--run-existing-models', action='store_true')
    parser.add_argument('--mesh-budget-seconds', type=int, default=0, help='Optional explicit test cancellation budget; 0 means no generation deadline')
    parser.add_argument('--only', nargs='*', choices=('image', 'speech', 'video', 'mesh'))
    parser.add_argument('--model', help='Limit inference to this published installed model ID')
    args = parser.parse_args()
    if not args.run_existing_models: parser.error('Explicit physical-model execution is required')
    if args.mesh_budget_seconds < 0: parser.error('A test budget cannot be negative')
    directory = ROOT/'build/device-api-benchmark'/str(time.time_ns())
    directory.mkdir(parents=True)
    report = dict(schema='lma.physical-api-benchmark/1', started_at=time.time(), physical_device=True,
        virtualization_used=False, inference_location='same_android_phone', model_downloads=0,
        user_settings_changed=False, checks=[], benchmarks=[], quality_accepted=False)
    def save():
        (directory/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    def check(value, name, **details):
        report['checks'].append(dict(name=name, passed=bool(value), **details)); save()
        print(json.dumps(dict(check=name, passed=bool(value)), ensure_ascii=False), flush=True)
        if not value: raise RuntimeError('Physical API check failed: '+name)
    stop = threading.Event()
    with phone_api(args.serial) as (request, command):
        def status(method, path, data=None, **kwargs):
            code, headers, body = request(method, path, data, detailed=True, **kwargs)
            return code, {k.lower(): v for k,v in headers.items()}, body
        apk = next(line[8:] for line in command('shell','pm','path','com.lma.app').splitlines() if line.startswith('package:') and line.endswith('/base.apk'))
        report['apk_sha256'] = command('shell','sha256sum',apk).split()[0]
        assert re.fullmatch('[a-f0-9]{64}', report['apk_sha256'])
        report['device'] = {key:command('shell','getprop',prop).strip() for key,prop in dict(model='ro.product.model',manufacturer='ro.product.manufacturer',android='ro.build.version.release',api='ro.build.version.sdk',soc='ro.soc.model').items()}
        report['version'] = request('GET','/health')['version']
        jobs = request('GET','/v1/jobs')['data']
        if any(j['state'] not in TERMINAL for j in jobs): raise RuntimeError('Existing active tasks are preserved; wait before testing')
        before_count=len(jobs)
        code, headers, body = status('GET','/v1/models'); catalogue=json.loads(body); models=catalogue['data']
        report['catalogue'] = catalogue
        check(code==200 and len(models)>0, 'Installed multimodal peers are automatically advertised', count=len(models))
        check(status('GET','/v1/models',extra={'If-None-Match':headers['etag']})[0]==304,'Catalogue ETag returns 304')
        check(status('HEAD','/v1/models')[2]==b'','Catalogue HEAD has no body')
        check(status('GET','/health',extra={'Authorization':'Bearer invalid-test-key'})[0]==401,'Wrong caller key is rejected')
        check(status('GET','/v1/models',extra={'Origin':'https://example.invalid'})[0]==403,'Browser origin is rejected')
        check(status('GET','/v1/models/not_installed')[0]==404,'Uninstalled model is unavailable without download')
        check(request('GET','/v1/capabilities')['execution']=='same_android_phone','Capabilities identify phone-local execution')
        for m in models:
            detail=request('GET','/v1/models/'+m['id'])
            check(detail['id']==m['id'] and detail['x_lma']['publication']['eligible'],'Published model details match inventory', model=m['id'])
        timings=[]
        for _ in range(50):
            start=time.perf_counter(); request('GET','/v1/models'); timings.append((time.perf_counter()-start)*1000)
        report['catalogue_latency_ms']=dict(samples=len(timings),median=statistics.median(timings),p95=sorted(timings)[int(.95*(len(timings)-1))],maximum=max(timings),transport='USB ADB TCP forwarding; includes transport/client overhead')
        report['missing_generation_operations'] = sorted(set(('text.generate','audio.generate'))-{op for m in models for op in m['x_lma']['operations']})
        samples=[]
        def resource_sample():
            result=dict(at=time.time())
            try:
                mem=command('shell','cat','/proc/meminfo'); result['system_available_kib']=int(re.search(r'MemAvailable:\s+(\d+)',mem)[1]);result['system_total_kib']=int(re.search(r'MemTotal:\s+(\d+)',mem)[1])
                cpu=command('shell','cat','/proc/stat').splitlines()[0].split()[1:]; result['system_cpu_ticks']=list(map(int,cpu))
                battery=command('shell','dumpsys','battery'); result['battery_temperature_c']=int(re.search(r'temperature:\s+(\d+)',battery)[1])/10
                ps=command('shell','dumpsys','meminfo','com.lma.app'); match=re.search(r'TOTAL PSS:\s+(\d+)',ps)
                if match: result['app_process_pss_kib']=int(match[1])
            except Exception:result['sample_incomplete']=True
            return result
        report['baseline_resources']=resource_sample()
        def sampling():
            while not stop.wait(5): samples.append(resource_sample())
        sampler=threading.Thread(target=sampling,daemon=True);sampler.start()
        input_artifact=None
        try:
            for task,operation in [('speech','speech.synthesize'),('image','image.generate'),('video','video.generate'),('mesh','mesh.generate')]:
                if args.only and task not in args.only:continue
                for model in [m for m in models if operation in m['x_lma']['operations'] and (not args.model or m['id']==args.model)]:
                    mid=model['id']; params={}; key='physical-'+uuid.uuid4().hex; job_id=''; started=time.monotonic()
                    bench=dict(model=mid,operation=operation,started_at=time.time(),quality_accepted=False,stages=[]); report['benchmarks'].append(bench);save()
                    try:
                        prompt='An orange cube on a clean white background.'
                        if task=='speech':
                            payload=dict(model=mid,input='你好，这是手机本地模型接口测试。',voice='default',response_format='wav',lma=dict(allow_unmeasured=True,parameters=dict(threads=2)))
                            path='/v1/audio/speech'; budget=0
                        elif task=='image':
                            params=dict(steps=4,threads=4,cfg=4,seed=1234)
                            payload=dict(model=mid,prompt=prompt,n=1,size='256x256',response_format='b64_json',lma=dict(allow_unmeasured=True,parameters=params))
                            path='/v1/images/generations'; budget=0
                        else:
                            params=dict(threads=4,steps=4,width=128,height=128,frames=49,fps=8,cfg=1,executionBackend='cpu',vaeTiling=True,vaeTileSize=128)
                            inputs=dict(prompt=prompt); budget=0
                            if task=='mesh':
                                if input_artifact is None:
                                    from PIL import Image, ImageDraw
                                    image=Image.new('RGBA',(512,512),(255,255,255,0)); draw=ImageDraw.Draw(image)
                                    draw.polygon([(128,180),(256,110),(384,180),(256,250)],fill=(255,184,78,255));draw.polygon([(128,180),(256,250),(256,400),(128,328)],fill=(214,105,40,255));draw.polygon([(256,250),(384,180),(384,328),(256,400)],fill=(245,142,48,255))
                                    b=io.BytesIO();image.save(b,format='PNG');data=b.getvalue();(directory/'owned-cube.png').write_bytes(data)
                                    u=request('POST','/v1/lma/uploads',dict(model=mid,name='LMA-owned-cube.png',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())); up='/v1/lma/uploads/'+u['id']
                                    check(request('PUT',up,data,'application/octet-stream',{'Upload-Offset':'0'})['received']==len(data),'Namespaced upload accepts owned fixture bytes')
                                    input_artifact=request('POST',up+'/complete',{})['id']
                                inputs=dict(artifacts=[dict(role='reference_image',artifactId=input_artifact)])
                                params=dict(resolution=512,steps=1,faces=1000,atlas=256,threads=6,texture=False,guidance=1,seed=1234);budget=args.mesh_budget_seconds
                            payload=dict(model=mid,type=operation,input=inputs,parameters=params,allowUnmeasured=True);path='/v1/lma/jobs'
                            preflight=request('POST',path+'/preflight',payload);bench['preflight_can_enqueue']=preflight['canEnqueue']
                            if not preflight['canEnqueue']:
                                bench['outcome']='preflight_rejected';bench['issues']=preflight.get('issues');save();continue
                        bench['request']=payload;save()
                        code,h,body=status('POST',path,payload,extra={'Idempotency-Key':key},timeout=135)
                        bench['initial_http_status']=code;job_id=h.get('x-lma-job-id','')
                        if code>=400 and code!=504:
                            bench['outcome']='api_error';bench['error']=json.loads(body);save();continue
                        if path.endswith('/jobs'):job_id=json.loads(body)['id']
                        if not job_id:raise RuntimeError('A generation response must identify its durable job')
                        bench['job_id']=job_id
                        replay_code,_,replay=status('POST',path,payload,extra={'Idempotency-Key':key},timeout=135)
                        bench['replay_http_status']=replay_code
                        check(replay_code in (200,202,504),'Generation retry safely reuses the admitted request',model=mid)
                        if task=='video': command('shell','input','keyevent','KEYCODE_SLEEP'); bench['screen_off_during_inference']=True
                        while True:
                            job=request('GET','/v1/lma/jobs/'+job_id);stage=job.get('stage')
                            if not bench['stages'] or bench['stages'][-1]['stage']!=stage:bench['stages'].append(dict(stage=stage,elapsed_seconds=round(time.monotonic()-started,3)));save();print(json.dumps(dict(model=mid,stage=stage),ensure_ascii=False),flush=True)
                            if job['state'] in TERMINAL:break
                            if budget > 0 and time.monotonic()-started>budget:
                                request('POST','/v1/lma/jobs/'+job_id+'/cancel',{});bench['bounded_timeout']=True
                                for _ in range(120):
                                    time.sleep(.5);job=request('GET','/v1/lma/jobs/'+job_id)
                                    if job['state'] in TERMINAL:break
                                break
                            time.sleep(2)
                        bench['outcome']=job['state'];bench['elapsed_seconds']=round(time.monotonic()-started,3);bench['error']=job.get('error');bench['effective_parameters']=job.get('effective_parameters');bench['outputs']=[]
                        native_job=request('GET','/v1/jobs/'+job_id)
                        details=native_job.get('engineExecution',{})
                        bench['worker_diagnostics']={k:details[k] for k in ('workerExitCode','workerCompleteEvent','workerDiagnosticCode','pipeline','backend') if k in details}
                        for artifact in job.get('outputs',[]):
                            data=request('GET',artifact['content_path'],raw=True);digest=hashlib.sha256(data).hexdigest()
                            check(digest==artifact['sha256'] and len(data)==artifact['bytes'],'Generated artifact bytes match committed phone hash',model=mid)
                            suffix={'image/png':'png','audio/wav':'wav','video/mp4':'mp4','model/gltf-binary':'glb'}.get(artifact['mime'],'bin');file=directory/(mid+'.'+suffix);file.write_bytes(data)
                            bench['outputs'].append(dict(mime=artifact['mime'],bytes=len(data),sha256=digest,file=file.name,metadata=artifact.get('metadata')))
                            if task=='video': check(artifact.get('metadata',{}).get('durationMs',0)>5000,'Generated video exceeds five seconds',model=mid)
                            if len(data)>16:
                                rc,rh,rb=status('GET',artifact['content_path'],extra={'Range':'bytes=0-15'})
                                check(rc==206 and rb==data[:16],'Phone artifact supports exact resumable byte ranges',model=mid)
                                check(status('GET',artifact['content_path'],extra={'Range':'bytes=0-15','If-Range':'"obsolete"'})[0]==200,'Stale phone If-Range restarts with a full artifact',model=mid)
                        events=request('GET','/v1/lma/jobs/'+job_id+'/events');check(isinstance(events.get('events'),list),'Task event cursor is readable',model=mid)
                        conflict=dict(payload);conflict['model']='different'
                        check(status('POST',path,conflict,extra={'Idempotency-Key':key})[0]==409,'A reused key with changed input conflicts',model=mid)
                    except Exception as error:
                        bench['outcome']='test_error';bench['error']=re.sub(r'(?:/data/|/storage/|[A-Z]:\\)\S+','[private path]',str(error))[:1000]
                        if job_id:
                            try:
                                if request('GET','/v1/lma/jobs/'+job_id)['state'] not in TERMINAL:request('POST','/v1/lma/jobs/'+job_id+'/cancel',{})
                            except Exception: pass
                    finally:
                        bench['elapsed_seconds']=round(time.monotonic()-started,3);save()
                        print(json.dumps(dict(model=mid,outcome=bench.get('outcome'),elapsed_seconds=bench['elapsed_seconds']),ensure_ascii=False),flush=True)
            command('shell','input','keyevent','KEYCODE_SLEEP'); lock_start=time.monotonic(); probes=0
            for _ in range(30):
                if request('GET','/health')['status']=='ok':probes+=1
                time.sleep(2)
            report['screen_off_service']=dict(seconds=round(time.monotonic()-lock_start,3),successful_health_requests=probes,sustained_endurance_test=False)
            check(probes==30,'Service remains responsive across a bounded screen-off period')
            report['history_preserved']=len(request('GET','/v1/jobs')['data'])>=before_count
        finally:
            stop.set();sampler.join(timeout=25);report['resource_samples']=samples
            report['resource_measurement_scope']='System MemAvailable and whole-device CPU ticks; app-process PSS excludes native child engines and is not model peak RAM.'
            report['finished_at']=time.time();report['passed_program_checks']=sum(c['passed'] for c in report['checks']);save()
            command('shell','input','keyevent','KEYCODE_WAKEUP')
    print(json.dumps(dict(report=str(directory.relative_to(ROOT)),benchmarks=[dict(model=b['model'],outcome=b.get('outcome'),seconds=b.get('elapsed_seconds')) for b in report['benchmarks']],passed_program_checks=report['passed_program_checks']),ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
