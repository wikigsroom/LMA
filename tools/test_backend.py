"""Exercise production backend Java using host framework ports, real TLS and child processes.

No Android emulator, Docker, WSL or model inference. All dependencies/output stay in build/.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from evidence import fingerprint, current

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/backend-tests"
JSON_SHA = "3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").unlink(missing_ok=True)
    inputs = fingerprint("app/src/main/java", "tests/host", "tools/test_backend.py")
    dep = ROOT / "build/test-deps/json-20250517.jar"
    dep.parent.mkdir(parents=True, exist_ok=True)
    if not dep.exists():
        with urllib.request.urlopen("https://repo.maven.apache.org/maven2/org/json/json/20250517/json-20250517.jar", timeout=30) as response:
            dep.write_bytes(response.read(1024 * 1024))
    if hashlib.sha256(dep.read_bytes()).hexdigest() != JSON_SHA:
        raise ValueError("Host test dependency hash mismatch")
    java, javac, keytool = (shutil.which(name) for name in ("java", "javac", "keytool"))
    if not all((java, javac, keytool)): raise RuntimeError("JDK required")
    key = OUT / "loopback.p12"
    if not key.exists():
        subprocess.run([keytool, "-genkeypair", "-storetype", "PKCS12", "-keystore", str(key), "-alias", "loopback", "-keyalg", "RSA", "-keysize", "2048",
                        "-validity", "30", "-dname", "CN=localhost,O=LMA Test Only", "-ext", "SAN=DNS:localhost,IP:127.0.0.1", "-storepass", "lma-host-tests", "-keypass", "lma-host-tests"], cwd=ROOT, check=True, capture_output=True)
    run_dir = (OUT / "run").resolve()
    if run_dir.exists():
        assert OUT.resolve() in run_dir.parents and run_dir.name == "run"
        shutil.rmtree(run_dir)
    source_root = ROOT / "app/src/main/java/com/lma/app"
    sources = sorted((ROOT / "tests/host").rglob("*.java")) + sorted((source_root / "core").glob("*.java"))
    sources += [source_root / (name + ".java") for name in ("Store", "Downloads", "Net", "EngineHost", "ChatRunner")]
    classes = OUT / "classes"; classes.mkdir(exist_ok=True)
    response = OUT / "sources.rsp"
    response.write_text("\n".join('"' + p.as_posix() + '"' for p in sources), encoding="utf-8")
    subprocess.run([javac, "-J-Duser.language=en", "-encoding", "UTF-8", "-Xlint:-options", "--release", "8", "-cp", str(dep), "-d", str(classes), "@" + str(response)], cwd=ROOT, check=True)
    command = [java, "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8", "-Dsun.net.useExclusiveBind=false", "-cp", str(classes) + os.pathsep + str(dep), "com.lma.app.BackendTest", str(ROOT)]
    child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    try:
        output, _ = child.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        # Terminate only this test runner and its child fixture processes.
        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True)
        output, _ = child.communicate()
        (OUT / "output.txt").write_text(output, encoding="utf-8")
        raise RuntimeError("Backend test timed out; its process tree was stopped")
    (OUT / "output.txt").write_text(output, encoding="utf-8")
    print(output, end="")
    if child.returncode: raise RuntimeError("Backend checks failed")
    results = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    current(inputs)
    results["input_fingerprint"] = inputs
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": results["passed"], "phone_inference_tested": False, "framework": "explicit host adapters; not Android"}))


if __name__ == "__main__":
    main()
