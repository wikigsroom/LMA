"""Run production multimodal data/job contracts on native host Java, without model inference."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/foundation-tests"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dependency = ROOT / "build/test-deps/json-20250517.jar"
    if not dependency.exists():
        raise RuntimeError("Run tools/test_backend.py first to fetch the pinned org.json test dependency")
    import hashlib
    if hashlib.sha256(dependency.read_bytes()).hexdigest() != "3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796":
        raise RuntimeError("Host org.json dependency hash mismatch")
    inputs = fingerprint("app/src/main/java/com/lma/app/core", "catalogue/model-bundles.json", "tests/FoundationTest.java", "tests/CuratedDiffusionTest.java", "research/sd_variants_trained/manifests", "research/sd_distilled_trained/sd_turbo_q8_0.json", "tests/AdapterTest.java", "tests/RecipeTest.java", "tests/BundleUpdateTest.java", "app/src/main/assets/recipe-templates.json", "tests/host/android/util/AtomicFile.java", "tools/test_foundation.py")
    run = OUT / "run"
    if run.exists():
        assert run.resolve().parent == OUT.resolve()
        shutil.rmtree(run)
    run.mkdir()
    classes = OUT / "classes"
    classes.mkdir(exist_ok=True)
    sources = sorted((ROOT / "app/src/main/java/com/lma/app/core").glob("*.java"))
    sources += [ROOT / "tests/FoundationTest.java", ROOT / "tests/CuratedDiffusionTest.java", ROOT / "tests/AdapterTest.java", ROOT / "tests/RecipeTest.java", ROOT / "tests/BundleUpdateTest.java", ROOT / "tests/host/android/util/AtomicFile.java"]
    response = OUT / "sources.rsp"
    response.write_text("\n".join('"' + p.as_posix() + '"' for p in sources), encoding="utf-8")
    subprocess.run([shutil.which("javac"), "-J-Duser.language=en", "-encoding", "UTF-8", "-Xlint:-options", "--release", "8", "-cp", str(dependency), "-d", str(classes), "@" + str(response)], cwd=ROOT, check=True)
    completed = subprocess.run([shutil.which("java"), "-Dfile.encoding=UTF-8", "-cp", str(classes) + os.pathsep + str(dependency), "com.lma.app.FoundationTest", str(run), str(ROOT / "catalogue/model-bundles.json"), str(ROOT / "app/src/main/assets/recipe-templates.json")], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=90)
    print(completed.stdout, end="")
    if completed.returncode:
        print(completed.stderr, file=sys.stderr)
        raise RuntimeError("Foundation checks failed")
    results = json.loads(completed.stdout.strip().splitlines()[-1])
    current(inputs)
    results["input_fingerprint"] = inputs
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
