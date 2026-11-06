"""Selected real-phone function-tool integration, SDK, queue and UI unload checks.

No downloads, personal conversation input, remote inference or credentials in
reports. Run only with explicit existing-model authorization. Model settings are
read, never replaced. Tests use a small public arithmetic fixture.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.request
from evidence import ROOT, fingerprint, version


def inputs():
    return fingerprint('tools/device_tools_probe.py', 'tests/android/com/lma/app/DeviceToolsProbe.java',
        'tests/android/AndroidManifest.xml', 'app/src/main/java/com/lma/app/ApiHost.java',
        'app/src/main/java/com/lma/app/core', 'app/src/main/java/com/lma/app/LmaService.java',
        'app/src/main/assets/app.js', 'app/src/main/assets/app.css', 'app/src/main/assets/index.html')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--model', default='m15')
    parser.add_argument('--allow-existing-model-inference', action='store_true')
    parser.add_argument('--smoke-only', action='store_true', help='Private preliminary SDK probe; does not export release evidence')
    args = parser.parse_args()
    if not args.allow_existing_model_inference: parser.error('Existing-model authorization is required')
    from openai import OpenAI
    adb = str(Path(os.environ['LOCALAPPDATA']) / 'Android/Sdk/platform-tools/adb.exe')
    private = ROOT/'build/dsh-device'; private.mkdir(parents=True, exist_ok=True)
    build = json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    def command(*values, timeout=150):
        r = subprocess.run([adb, '-s', args.serial, *map(str, values)], capture_output=True, timeout=timeout)
        if r.returncode: raise RuntimeError('Authorized physical-device operation failed')
        return r.stdout.decode('utf8', errors='replace')
    assert not args.serial.startswith('emulator-') and command('shell','getprop','ro.kernel.qemu').strip() != '1'
    apk = command('shell','pm','path','com.lma.app').strip().removeprefix('package:')
    assert command('shell','sha256sum',apk).split()[0] == build['sha256'], 'Install the exact current signed APK'
    def instrument(mode):
        raw = command('shell','am','instrument','-w','-e','mode',mode,'-e','model',args.model,
            'com.lma.app.acceptance/com.lma.app.DeviceToolsProbe',timeout=180)
        match = re.search(r'lma_tools=(\{[^\r\n]+\})',raw)
        if not match: raise RuntimeError('Missing physical runtime result; no raw private output exported')
        data = json.loads(match.group(1))
        if data['status'] != 'passed': raise RuntimeError(data.get('error','Physical runtime check failed'))
        return data
    first = instrument('startApi'); key = first.pop('apiKey'); settings = first.pop('settings')
    original_inventory = first['after']; original_profile = hashlib.sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()
    command('shell','am','start','-W','-n','com.lma.app/.MainActivity')
    forwarding = command('forward','tcp:0','tcp:'+str(first['port'])).strip()
    origin = 'http://127.0.0.1:'+forwarding
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def http(path, data=None, timeout=20):
        req=urllib.request.Request(origin+path,data=None if data is None else json.dumps(data).encode(),headers={
            'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with opener.open(req, timeout=timeout) as response: return response.status,json.load(response)
        except urllib.error.HTTPError as error: return error.code,json.load(error)
    def wait_health():
        for _ in range(80):
            try:
                status, health = http('/health')
                if status == 200: return health
            except (OSError, ValueError): pass
            time.sleep(.5)
        raise RuntimeError('Physical API listener did not recover')
    checks=[]; measurements=[]; client=None
    def check(condition,name):
        if not condition: raise RuntimeError('Physical tool check failed: '+name)
        checks.append(name); print(json.dumps({'passed':len(checks),'check':name}),flush=True)
    schema={'type':'object','properties':{'a':{'type':'integer'},'b':{'type':'integer'}},'required':['a','b'],'additionalProperties':False}
    tools=[{'type':'function','function':{'name':'lma_sum','description':'Return the sum of two integers. Executed only by the caller.','strict':True,'parameters':schema}},
           {'type':'function','function':{'name':'lma_unused','description':'Unrelated function; do not select it.','strict':True,'parameters':schema}}]
    choice={'type':'function','function':{'name':'lma_sum'}}
    prompt=[{'role':'user','content':'Call lma_sum with a=20 and b=22. Do not calculate it yourself.'}]
    kwargs=dict(model=args.model,tools=tools,tool_choice=choice,parallel_tool_calls=False,store=False,
        reasoning_effort='none',temperature=0,max_completion_tokens=192)
    def validate_call(calls):
        check(bool(calls) and len(calls)==1,'A native function tool call is returned')
        call=calls[0]; values=json.loads(call.function.arguments)
        check(call.function.name=='lma_sum' and values=={'a':20,'b':22},'Named choice and strict integer arguments match the request')
        return call,values
    try:
        wait_health()
        client=OpenAI(base_url=origin+'/v1',api_key=key,max_retries=0,timeout=600)
        check(any(m.id==args.model for m in client.models.list().data),'The existing installed model is published through the actual OpenAI SDK')
        started=time.monotonic(); parent=client.chat.completions.create(messages=prompt,**kwargs)
        call, values=validate_call(parent.choices[0].message.tool_calls)
        check(parent.choices[0].finish_reason=='tool_calls','Native completion terminates with finish_reason=tool_calls')
        measurements.append(dict(case='named_strict_tool',seconds=round(time.monotonic()-started,3),usage=parent.usage.model_dump() if parent.usage else None))
        if args.smoke_only:
            (private/'smoke.json').write_text(json.dumps(dict(checks=checks,measurements=measurements,apk_sha256=build['sha256']),indent=2)+'\n','utf8')
            return
        assistant={'role':'assistant','content':parent.choices[0].message.content,'tool_calls':[c.model_dump(exclude_none=True) for c in parent.choices[0].message.tool_calls]}
        messages=prompt+[assistant,{'role':'tool','tool_call_id':call.id,'content':str(values['a']+values['b'])}]
        started=time.monotonic(); resumed=client.chat.completions.create(messages=messages,**(kwargs|{'tool_choice':'auto'}))
        check(not resumed.choices[0].message.tool_calls and '42' in (resumed.choices[0].message.content or ''),'The caller executes the tool, returns its ID/result, and the model continues the conversation')
        measurements.append(dict(case='tool_result_resume',seconds=round(time.monotonic()-started,3),usage=resumed.usage.model_dump() if resumed.usage else None))
        started=time.monotonic(); streamed={}; finishes=[]; usage=None; chunks=0
        with client.chat.completions.create(messages=prompt,stream=True,stream_options={'include_usage':True},**kwargs) as stream:
            for chunk in stream:
                chunks+=1
                if chunk.usage: usage=chunk.usage.model_dump()
                for item in chunk.choices:
                    if item.finish_reason: finishes.append(item.finish_reason)
                    for fragment in item.delta.tool_calls or []:
                        part=streamed.setdefault(fragment.index,dict(id='',name='',arguments=''))
                        if fragment.id: part['id']=fragment.id
                        if fragment.function:
                            part['name']+=fragment.function.name or '';part['arguments']+=fragment.function.arguments or ''
        check(len(streamed)==1 and next(iter(streamed.values()))['id'] and next(iter(streamed.values()))['name']=='lma_sum','SDK streaming reassembles indexed tool IDs and function names')
        check(json.loads(next(iter(streamed.values()))['arguments'])=={'a':20,'b':22} and finishes==['tool_calls'] and usage is not None,'Strict streamed arguments, tool finish and final usage survive the physical gateway')
        measurements.append(dict(case='streamed_strict_tool',seconds=round(time.monotonic()-started,3),chunks=chunks,usage=usage))
        def child(_):
            child_client=OpenAI(base_url=origin+'/v1',api_key=key,max_retries=0,timeout=600)
            try: return child_client.chat.completions.create(messages=prompt,**kwargs)
            finally: child_client.close()
        started=time.monotonic(); peak=0; health_seconds=[]
        with ThreadPoolExecutor(max_workers=2) as pool:
            children=[pool.submit(child,i) for i in range(2)]
            while not all(f.done() for f in children):
                at=time.monotonic(); status,health=http('/health');health_seconds.append(time.monotonic()-at)
                peak=max(peak,health.get('textQueue',{}).get('requests',0));time.sleep(.2)
            results=[f.result() for f in children]
        check(all(r.choices[0].finish_reason=='tool_calls' for r in results),'Two concurrent child-agent requests queue successfully without the former busy 409')
        check(peak>=2 and max(health_seconds,default=99)<5,'Authenticated health remains responsive while text requests occupy the separate inference queue')
        measurements.append(dict(case='two_concurrent_children',seconds=round(time.monotonic()-started,3),peak_admitted=peak,health_max_seconds=round(max(health_seconds),3)))
        status,error=http('/v1/chat/completions',{'model':args.model,'messages':[{'role':'tool','tool_call_id':'orphan','content':'42'}]})
        check(status==400 and error['error'].get('param')=='messages[0].tool_call_id','Orphan tool results return a specific OpenAI-style validation error')
        unloaded=instrument('unload');unloaded.pop('apiKey',None);unloaded.pop('settings',None)
        checks.extend(unloaded['checks'])
        command('shell','am','start','-W','-n','com.lma.app/.MainActivity');health=wait_health()
        check(health['textState']=='stopped' and health['textQueue']['requests']==0,'Actual UI unload leaves the model stopped and the text queue empty')
        check(any(m.id==args.model for m in client.models.list().data),'Unload preserves the installed model in the published API catalogue')
        started=time.monotonic(); reloaded=client.chat.completions.create(messages=prompt,**kwargs)
        check(reloaded.choices[0].finish_reason=='tool_calls','An explicit subsequent API request reloads the installed model and generates a real tool call')
        measurements.append(dict(case='api_reload_after_unload',seconds=round(time.monotonic()-started,3)))
        final=instrument('inspect');final.pop('apiKey',None);profile=final.pop('settings')
        check(final['after']==original_inventory,'All original installed model assets and conversation history remain unchanged')
        check(hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest()==original_profile,'Per-model settings are unchanged by SDK, queue and unload tests')
        report=dict(schema='lma.physical-tools/1',version=version(),apk_sha256=build['sha256'],status='passed',
            checked_at=datetime.now(timezone.utc).isoformat(),device=dict(model=command('shell','getprop','ro.product.model').strip(),android=command('shell','getprop','ro.build.version.release').strip()),
            model_id=args.model,context=settings['context'],output_ceiling=settings['maxTokens'],requested_output_tokens=192,
            native_revision='b29c606e28a01b1bc8c1351026a0fa6e616bf6c4',checks=checks,passed=len(checks),measurements=measurements,
            phone_inference_tested=True,client_executed_tools=True,openai_sdk_tested=True,dsh_app_tested=False,
            same_android_phone=True,weights_downloaded=False,settings_preserved=True,installed_assets_preserved=True,
            model_quality_accepted=False,background_endurance_tested=False,virtualization_used=False,input_fingerprint=inputs(),
            limits=['One physical phone and one existing text model','DSH v1.4.76 application itself was not driven','Arithmetic tool fixtures do not establish agent quality, arbitrary tools or long-context reliability'])
        out=ROOT/('verification/releases/v'+version()+'/physical-tools.json');out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
        print(json.dumps({'status':'passed','checks':len(checks),'phone_model':args.model,'settings_preserved':True}),flush=True)
    finally:
        if client: client.close()
        command('forward','--remove','tcp:'+forwarding)
        key=''
        command('shell','am','start','-W','-n','com.lma.app/.MainActivity')


if __name__=='__main__':main()
