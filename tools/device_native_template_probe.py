"""Weight-free Android parser check using the exact packaged shared libraries.

Explicit phone use only. The synthetic 41 tools execute no commands; all owned
device files and the temporary Windows build alias are removed in finally.
"""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from evidence import ROOT,fingerprint,version
from build_llama_chat_runtime import verify_patch_record,prepare_source


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serial',required=True);args=parser.parse_args()
    assert not args.serial.startswith('emulator-')
    verify_patch_record();prepare_source()
    build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    out=ROOT/'build/device-native-template';out.mkdir(exist_ok=True)
    adb=str(Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe');base=[adb,'-s',args.serial]
    def command(*parts):return subprocess.run(base+list(parts),capture_output=True,check=True,timeout=60).stdout
    installed=command('shell','pm','path','com.lma.app').decode().strip().removeprefix('package:')
    assert command('shell','sha256sum',installed).decode().split()[0]==build['sha256']
    cache=out/'CMakeCache.txt';match=re.search(r'CMAKE_HOME_DIRECTORY:INTERNAL=([A-Z]):/',cache.read_text('utf8')) if cache.exists() else None
    drive=match[1]+':' if match else next(c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists())
    assert not Path(drive+'/').exists()
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        cmake=drive+'/build/toolchain/cmake-3.31.6/bin/cmake.exe';target=drive+'/build/device-native-template'
        commands=[[cmake,'-S',drive+'/tests/native/chat-template-probe','-B',target,'-G','Ninja',
                   '-DCMAKE_MAKE_PROGRAM='+drive+'/build/toolchain/cmake-3.31.6/bin/ninja.exe',
                   '-DCMAKE_TOOLCHAIN_FILE='+drive+'/build/toolchain/android-ndk-r30/build/cmake/android.toolchain.cmake',
                   '-DANDROID_ABI=arm64-v8a','-DANDROID_PLATFORM=android-28','-DANDROID_STL=c++_static','-DCMAKE_BUILD_TYPE=Release',
                   '-DLMA_LLAMA_SOURCE='+drive+'/build/native-src/llama-chat-runtime','-DLMA_BASE_RUNTIME='+drive+'/app/src/main/jniLibs/arm64-v8a'],
                  [cmake,'--build',target,'-j','2']]
        for i,c in enumerate(commands):
            r=subprocess.run(c,capture_output=True);(out/('build-'+str(i)+'.log')).write_bytes(r.stdout+r.stderr)
            assert r.returncode==0,'Inspect build/device-native-template compile log'
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    remote='/data/local/tmp/lma-parser-'+build['sha256'][:12]
    assert re.fullmatch(r'/data/local/tmp/lma-parser-[a-f0-9]{12}',remote)
    native=ROOT/'app/src/main/jniLibs/arm64-v8a';files=[];checks=[]
    def push(path,name):
        files.append(remote+'/'+name);command('push',str(path),remote+'/'+name)
    schema={'type':'object','properties':{'value':{'type':'integer'}},'required':['value'],'additionalProperties':False}
    tools=[{'type':'function','function':{'name':'lma_tool_'+str(i),'description':'Synthetic parser fixture only','parameters':schema}} for i in range(41)]
    first='{"name":"lma_tool_40","arguments":{"value":42}}';second=first.replace('lma_tool_40','lma_tool_0').replace('42','43')
    template=ROOT/'app/src/main/assets/chat-templates/dolphin3-chatml-tools-v2.jinja'
    libraries={}
    try:
        command('shell','mkdir','-p',remote)
        for name in ['libllama-common.so','libllama.so','libggml.so','libggml-base.so']:
            p=native/name;push(p,name);digest=hashlib.sha256(p.read_bytes()).hexdigest()
            assert command('shell','sha256sum',remote+'/'+name).decode().split()[0]==digest
            libraries[name]=digest
        push(out/'lma_chat_template_probe','probe');command('shell','chmod','700',remote+'/probe');push(template,'template.jinja')
        positives=[(label,first+sep+second,[42,43]) for label,sep in [('space',' '),('newline','\n'),('double-newline','\n\n'),('adjacent',''),('comma',', ')]]
        positives += [('final-open-envelope',first[:-1],[42]),('final-envelope-comma',first[:-1]+', \n',[42]),('parallel-final-envelope',first+'\n'+second[:-1]+',',[42,43])]
        negatives=[('missing-name','{"arguments":{"value":42},'),('missing-arguments','{"name":"lma_tool_40",'),
                   ('incomplete-arguments',first[:-2]),('incomplete-string','{"name":"lma_tool_40","arguments":{"value":"unfinished'),
                   ('extra-result',first[:-1]+',"result":"invented"}'),('nonfinal-envelope',first[:-1]+'\n'+second)]
        for label,generated,expected in positives:
            q={'messages':[{'role':'user','content':'Synthetic parser fixture; no execution'}],'tools':tools,'tool_choice':'auto','generated':generated}
            p=out/'request.json';p.write_text(json.dumps(q),'utf8');push(p,'request.json')
            data=command('shell','LD_LIBRARY_PATH='+remote+' '+remote+'/probe '+remote+'/template.jinja '+remote+'/request.json')
            d=json.loads(data);calls=d['parsed']['tool_calls']
            assert [c['function'] for c in calls]==[{'name':'lma_tool_40' if value==42 else 'lma_tool_0','arguments':json.dumps({'value':value},separators=(',',':'))} for value in expected]
            assert all(t['function']['name'] in d['prompt'] for t in tools)
            checks.append(label+': actual Android packaged parser preserves complete names/arguments and all 41 declarations')
        for label,generated in negatives:
            q={'messages':[{'role':'user','content':'Synthetic parser fixture; no execution'}],'tools':tools,'tool_choice':'auto','generated':generated}
            p=out/'request.json';p.write_text(json.dumps(q),'utf8');push(p,'request.json')
            result=subprocess.run(base+['shell','LD_LIBRARY_PATH='+remote+' '+remote+'/probe '+remote+'/template.jinja '+remote+'/request.json'],capture_output=True,timeout=60)
            assert result.returncode==1 and b'does not match' in result.stderr+result.stdout,label+': malformed final tool output must fail'
            checks.append(label+': actual Android packaged parser rejects incomplete arguments or disallowed fields without an executable call')
        report=dict(schema='lma.physical-native-template/1',version=version(),apk_sha256=build['sha256'],passed=len(checks),checks=checks,
                    libraries=libraries,physical_device=True,model_inference_tested=False,synthetic_output=True,commands_executed=False,
                    downloaded_model_weights=False,virtualization_used=False,owned_device_files_cleaned=True,
                    input_fingerprint=fingerprint('tools/device_native_template_probe.py','tests/native/chat-template-probe','native/chat-runtime','tools/build_llama_chat_runtime.py','third_party/runtime-lock.json','third_party/patches/0002-bare-json-parallel-tools.patch'))
    finally:
        command('shell','rm','-f',*sorted(set(files)));command('shell','rmdir',remote)
    path=ROOT/('verification/releases/v'+version()+'/physical-native-template.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps({'passed':len(checks),'actual_android_parser':True,'model_inference_tested':False}))


if __name__=='__main__':main()
