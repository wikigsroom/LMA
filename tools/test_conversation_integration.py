"""Use freshly compiled production metadata/gateway classes; no model inference or Android codecs."""
import json,os,shutil,subprocess
from evidence import ROOT,fingerprint,current
def main():
    out=ROOT/'build/conversation-integration';out.mkdir(parents=True,exist_ok=True);(out/'results.json').unlink(missing_ok=True)
    inputs=fingerprint('app/src/main/java','tests/host','app/src/main/assets/capabilities.json','app/src/main/assets/vision-presets.json','tests/ConversationIntegrationTest.java','tools/test_conversation_integration.py')
    current(json.loads((ROOT/'build/backend-tests/results.json').read_text(encoding='utf-8'))['input_fingerprint'])
    dep=ROOT/'build/test-deps/json-20250517.jar';classes=out/'classes';classes.mkdir(exist_ok=True);cp=os.pathsep.join(map(str,[ROOT/'build/backend-tests/classes',dep]))
    subprocess.run([shutil.which('javac'),'-encoding','UTF-8','--release','11','-cp',cp,'-d',str(classes),str(ROOT/'tests/ConversationIntegrationTest.java')],check=True,cwd=ROOT)
    run=out/'run'
    if run.exists():assert run.resolve().parent==out.resolve();shutil.rmtree(run)
    result=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-cp',os.pathsep.join([str(classes),cp]),'com.lma.app.ConversationIntegrationTest',str(ROOT),str(run)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=45)
    (out/'output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    record=json.loads(result.stdout.strip().splitlines()[-1]);record['input_fingerprint']=inputs;current(inputs);(out/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k!='input_fingerprint'}))
if __name__=='__main__':main()
