"""Run actual host C++ reference parsing and Java Nano workspace/worker contracts; no model inference."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current
from native_payload import engine_files

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != "nt": raise RuntimeError("Native Windows host checks only")
    inputs = fingerprint("app/src/main/java/com/lma/app/core", "app/src/main/java/com/lma/app/NativeWorker.java", "app/src/main/java/com/lma/app/LocalEngine.java", "app/src/main/java/com/lma/app/MossNanoEngine.java", "native/moss_nano", "tests/moss-host", "tests/native/onnx_external_test.cpp", "tests/tts-host/com/lma/app/LmaApp.java", "tools/test_moss_nano.py", "tools/native_payload.py", "app/src/main/assets/recipe-templates.json", "third_party/engine-lock.json")
    output = ROOT / "build/moss-nano-tests"; output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").unlink(missing_ok=True)
    run = output / "run"
    if run.exists():
        assert run.resolve().parent == output.resolve()
        shutil.rmtree(run)
    classes = output / "classes"; classes.mkdir(exist_ok=True)
    dependency = ROOT / "build/test-deps/json-20250517.jar"
    if hashlib.sha256(dependency.read_bytes()).hexdigest() != "3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796": raise RuntimeError("Host JSON dependency changed")
    sources = sorted((ROOT / "app/src/main/java/com/lma/app/core").glob("*.java")) + sorted((ROOT / "tests/moss-host").rglob("*.java"))
    sources += [ROOT / "app/src/main/java/com/lma/app" / (name + ".java") for name in ("NativeWorker", "LocalEngine", "MossNanoEngine")]
    sources += [ROOT / "tests/tts-host/com/lma/app/LmaApp.java", ROOT / "tests/host/android/util/AtomicFile.java"]
    response = output / "sources.rsp"; response.write_text("\n".join('"' + p.as_posix() + '"' for p in sources), encoding="utf-8")
    subprocess.run([shutil.which("javac"), "-J-Duser.language=en", "-encoding", "UTF-8", "-Xlint:-options", "--release", "8", "-cp", str(dependency), "-d", str(classes), "@" + str(response)], cwd=ROOT, check=True)
    result = subprocess.run([shutil.which("java"), "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8", "-Duser.language=en", "-cp", str(classes) + os.pathsep + str(dependency), "com.lma.app.MossNanoTest", str(run), str(ROOT / "app/src/main/assets/recipe-templates.json")], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    if result.returncode: raise RuntimeError(result.stdout + result.stderr)
    java = json.loads(result.stdout.strip().splitlines()[-1])
    setup = Path(os.environ.get("LMA_VCVARS", r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"))
    if not setup.is_file(): raise RuntimeError("Set LMA_VCVARS to an installed native Windows C++ toolchain setup script")
    exe = output / "onnx-external-test.exe"
    command = output / "compile-native.cmd"
    command.write_text('@echo off\ncall "' + str(setup) + '" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++17 /EHsc /W4 "../../tests/native/onnx_external_test.cpp" /Fe:onnx-external-test.exe /Fo:onnx-external-test.obj\n', encoding="ascii")
    compile_result = subprocess.run(["cmd", "/d", "/c", command.name], cwd=output, capture_output=True, timeout=90)
    (output / "native-compile.log").write_bytes(compile_result.stdout + compile_result.stderr)
    if compile_result.returncode: raise RuntimeError("Host C++ compilation failed; inspect build/moss-nano-tests/native-compile.log")
    result = subprocess.run([str(exe)], cwd=output, capture_output=True, text=True, timeout=30)
    if result.returncode: raise RuntimeError(result.stdout + result.stderr)
    native = json.loads(result.stdout.strip())
    ort = {"file": "shared.so", "sha256": "a" * 64, "bytes": 32, "android_api_notes": [27]}
    engines = [{"engine": name, "file": name + ".so", "sha256": "b" * 64, "bytes": 64, "dependencies": [copy.deepcopy(ort)]} for name in ("first", "second")]
    assert len(engine_files(engines)) == 3
    payload = 1
    for key, value in (("sha256", "c" * 64), ("bytes", 33), ("android_api_notes", [28]), ("file", "first.so"), ("file", "../outside.so"), ("file", "C:outside.so")):
        invalid = copy.deepcopy(engines); invalid[1]["dependencies"][0][key] = value
        try: engine_files(invalid)
        except RuntimeError: payload += 1
        else: raise AssertionError("Native dependency conflict accepted")
    report = {"passed": java["passed"] + native["passed"] + payload, "java_contracts": java, "native_parser": native, "shared_dependency_checks": payload,
        "physical_device": False, "model_inference": False, "input_fingerprint": inputs}
    current(inputs)
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "input_fingerprint"}))


if __name__ == "__main__": main()
