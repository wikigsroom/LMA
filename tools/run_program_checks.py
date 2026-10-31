"""Run the bounded program suite. Never select trained-model or device tests."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/program-check-run'
GROUPS = [
    ['community', 'bundle_pause', 'document_input', 'api', 'workbench', 'recovery'],
    ['inputs', 'text', 'migration', 'scheduler', 'preparations', 'assemblies', 'diffusion', 'mnn'],
    ['hub', 'recipe_suggestions', 'speech_voices', 'sana_sprint', 'ltx098_official', 'ltx098_app', 'ltx098_app --multiscale'],
]


def group(names):
    results = []
    for name in names:
        parts = name.split()
        label = name.replace(' --', '-')
        started = time.monotonic()
        command = [sys.executable, str(ROOT / ('tools/test_' + parts[0] + '.py')), *parts[1:]]
        with (OUT / (label + '.log')).open('wb') as output:
            process = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                     env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        result = dict(suite=name, exit=process.returncode, seconds=round(time.monotonic() - started, 2))
        results.append(result)
        print(json.dumps(result), flush=True)
        if process.returncode:
            break  # A dependent test must not consume a failed predecessor's record.
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # HF and community suites consume backend's freshly compiled production classes.
    results = group(['backend'])
    if results[0]['exit']:
        raise SystemExit('Backend prerequisites failed; inspect build/program-check-run/backend.log.')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results.extend(item for batch in pool.map(group, GROUPS) for item in batch)
    passed = len(results) == 1 + sum(map(len, GROUPS)) and all(item['exit'] == 0 for item in results)
    report = dict(passed=passed, complete_trained_model_runs=0, virtualization_used=False, suites=results)
    (OUT / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if not passed:
        raise SystemExit('Inspect build/program-check-run/*.log; dependent groups stop at the first failure.')


if __name__ == '__main__':
    main()
