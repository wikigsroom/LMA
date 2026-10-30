"""Exercise the production queue, resident text host, chat and HTTP through one execution slot.

Host framework/resource/media ports and literal child protocols provide no phone/model evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]


def main():
    names = ("Store", "Downloads", "InputImports", "Net", "ApiHost", "EngineHost", "ChatRunner", "HubClient", "HubCatalog", "ModelSettings", "GgufMetadata", "LocalEngine", "LocalJobs", "NativeWorker", "DeviceResourceProbe")
    inputs = fingerprint("app/src/main/java/com/lma/app/core", *["app/src/main/java/com/lma/app/" + n + ".java" for n in names], "tests/host", "tests/scheduler-host", "tests/PreparationTest.java", "app/src/main/assets/models.json", "app/src/main/assets/recipe-templates.json", "tools/test_scheduler.py")
    dep = ROOT / "build/test-deps/json-20250517.jar"
    assert hashlib.sha256(dep.read_bytes()).hexdigest() == "3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796"
    out = ROOT / "build/scheduler-tests"; out.mkdir(exist_ok=True)
    (out / "results.json").unlink(missing_ok=True)
    run = out / "run"
    if run.exists():
        assert run.resolve().parent == out.resolve()
        shutil.rmtree(run)
    classes = out / "classes"; classes.mkdir(exist_ok=True)
    sources = sorted((ROOT / "app/src/main/java/com/lma/app/core").glob("*.java"))
    sources += [p for p in sorted((ROOT / "tests/host").rglob("*.java")) if p.name != "LocalJobs.java"]
    sources += sorted((ROOT / "tests/scheduler-host").rglob("*.java"))
    sources += [ROOT / "tests/PreparationTest.java"]
    sources += [ROOT / "app/src/main/java/com/lma/app" / (n + ".java") for n in names]
    rsp = out / "sources.rsp"; rsp.write_text("\n".join('"' + p.as_posix() + '"' for p in sources), encoding="utf-8")
    subprocess.run([shutil.which("javac"), "-J-Duser.language=en", "-encoding", "UTF-8", "-Xlint:-options", "--release", "8", "-cp", str(dep), "-d", str(classes), "@" + str(rsp)], cwd=ROOT, check=True)
    command = [shutil.which("java"), "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8", "-cp", str(classes) + os.pathsep + str(dep), "com.lma.app.SchedulerTest", str(ROOT), str(run)]
    child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    try: output, _ = child.communicate(timeout=150)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
        output, _ = child.communicate(); (out / "output.txt").write_text(output, encoding="utf-8"); raise RuntimeError("Scheduler checks timed out; fixture process tree stopped")
    (out / "output.txt").write_text(output, encoding="utf-8")
    if child.returncode: raise RuntimeError(output)
    report = json.loads(output.strip().splitlines()[-1]); current(inputs); report["input_fingerprint"] = inputs
    (out / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("input_fingerprint", "checks")}))


if __name__ == "__main__": main()
