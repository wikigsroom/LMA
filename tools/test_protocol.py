"""Compile the actual protocol code and run failure-oriented JVM checks."""
from pathlib import Path
import shutil
import subprocess
import json
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/protocol-tests"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "results.json").unlink(missing_ok=True)
inputs = fingerprint("app/src/main/java/com/lma/app/core/Protocol.java", "tests/ProtocolTest.java", "tools/test_protocol.py")
java = shutil.which("java")
javac = shutil.which("javac")
if not java or not javac:
    raise RuntimeError("A JDK is required")
subprocess.run([javac, "-J-Duser.language=en", "-Xlint:-options", "-encoding", "UTF-8", "--release", "8", "-d", str(OUT),
                str(ROOT / "app/src/main/java/com/lma/app/core/Protocol.java"), str(ROOT / "tests/ProtocolTest.java")], check=True, cwd=ROOT)
result = subprocess.run([java, "-cp", str(OUT), "ProtocolTest"], check=True, cwd=ROOT, capture_output=True, text=True)
(ROOT / "build/protocol-test-results.txt").write_text(result.stdout, encoding="utf-8")
current(inputs)
(OUT / "results.json").write_text(json.dumps({"summary": result.stdout.strip(), "input_fingerprint": inputs}, indent=2) + "\n", encoding="utf-8")
print(result.stdout.strip())
