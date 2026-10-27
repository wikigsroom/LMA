"""Check actual TTS Java contracts and native worker ownership using explicit host child fixtures."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current
ROOT=Path(__file__).resolve().parents[1]


def main():
    inputs=fingerprint("app/src/main/java/com/lma/app/core", "app/src/main/java/com/lma/app/NativeWorker.java", "app/src/main/java/com/lma/app/LocalEngine.java", "app/src/main/java/com/lma/app/SherpaEngine.java", "tests/tts-host", "tools/test_tts.py", "catalogue/model-bundles.json")
    dep=ROOT/"build/test-deps/json-20250517.jar"
    if hashlib.sha256(dep.read_bytes()).hexdigest()!="3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796": raise RuntimeError("Host JSON dependency changed")
    out=ROOT/"build/tts-tests";out.mkdir(parents=True,exist_ok=True)
    (out/"results.json").unlink(missing_ok=True)
    run=out/"run"
    if run.exists():
        assert run.resolve().parent==out.resolve()
        shutil.rmtree(run)
    classes=out/"classes";classes.mkdir(exist_ok=True)
    sources=sorted((ROOT/"app/src/main/java/com/lma/app/core").glob("*.java"))+sorted((ROOT/"tests/tts-host").rglob("*.java"))
    sources += [ROOT/"app/src/main/java/com/lma/app"/(n+".java") for n in ("NativeWorker","LocalEngine","SherpaEngine")]
    sources += [ROOT/"tests/host/android/util/AtomicFile.java"]
    rsp=out/"sources.rsp";rsp.write_text("\n".join('"'+p.as_posix()+'"' for p in sources),encoding="utf-8")
    subprocess.run([shutil.which("javac"),"-J-Duser.language=en","-encoding","UTF-8","-Xlint:-options","--release","8","-cp",str(dep),"-d",str(classes),"@"+str(rsp)],cwd=ROOT,check=True)
    result=subprocess.run([shutil.which("java"),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-Duser.language=en","-cp",str(classes)+os.pathsep+str(dep),"com.lma.app.TtsTest",str(run),str(ROOT/"catalogue/model-bundles.json")],cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=90)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    report=json.loads(result.stdout.strip().splitlines()[-1]);current(inputs);report["input_fingerprint"]=inputs
    (out/"results.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="input_fingerprint"}))


if __name__=="__main__":main()
