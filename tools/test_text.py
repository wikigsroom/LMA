"""Verify production GGUF text queue contracts with actual host files, processes and local HTTP."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current
ROOT = Path(__file__).resolve().parents[1]


def main():
    names = ("TextEngine", "LocalEngine", "ModelSettings", "GgufMetadata")
    inputs = fingerprint("app/src/main/java/com/lma/app/core", *["app/src/main/java/com/lma/app/" + n + ".java" for n in names], "tests/text-host", "tests/host/android/util/AtomicFile.java", "app/src/main/assets/recipe-templates.json", "tools/test_text.py")
    dep = ROOT / "build/test-deps/json-20250517.jar"
    if hashlib.sha256(dep.read_bytes()).hexdigest() != "3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796": raise RuntimeError("Host JSON dependency changed")
    out = ROOT / "build/text-tests"; out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").unlink(missing_ok=True)
    run = out / "run"
    if run.exists():
        assert run.resolve().parent == out.resolve()
        shutil.rmtree(run)
    classes = out / "classes"; classes.mkdir(exist_ok=True)
    sources = sorted((ROOT / "app/src/main/java/com/lma/app/core").glob("*.java")) + sorted((ROOT / "tests/text-host").rglob("*.java"))
    sources += [ROOT / "app/src/main/java/com/lma/app" / (n + ".java") for n in names] + [ROOT / "tests/host/android/util/AtomicFile.java"]
    rsp = out / "sources.rsp"; rsp.write_text("\n".join('"' + p.as_posix() + '"' for p in sources), encoding="utf-8")
    subprocess.run([shutil.which("javac"), "-J-Duser.language=en", "-encoding", "UTF-8", "-Xlint:-options", "--release", "8", "-cp", str(dep), "-d", str(classes), "@" + str(rsp)], cwd=ROOT, check=True)
    command = [shutil.which("java"), "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8", "-cp", str(classes) + os.pathsep + str(dep), "com.lma.app.TextEngineTest", str(run), str(ROOT / "app/src/main/assets/recipe-templates.json")]
    child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    try: output, _ = child.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
        output, _ = child.communicate(); (out / "output.txt").write_text(output, encoding="utf-8"); raise RuntimeError("Text host test timed out; its process tree was stopped")
    (out / "output.txt").write_text(output, encoding="utf-8")
    if child.returncode: raise RuntimeError(output)
    report = json.loads(output.strip().splitlines()[-1]); current(inputs); report["input_fingerprint"] = inputs
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "input_fingerprint"}))


if __name__ == "__main__": main()
