"""Run the bounded program suite. Never select trained-model or device tests."""
import argparse
from evidence import current
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/program-check-run'
RESUME = False
RECORD_NAMES={'inputs':'input','recipe_suggestions':'recipe-suggestion','speech_voices':'speech-voice','preparations':'preparation','assemblies':'assembly','ltx098_app --multiscale':'ltx098-multiscale-app'}
def reusable(name):
    path=ROOT/'build'/((RECORD_NAMES.get(name,name.replace('_','-')))+'-tests')/'results.json'
    try:
        record=json.loads(path.read_text(encoding='utf-8'));current(record.get('source_inputs',record.get('input_fingerprint',{})));return bool(record.get('passed',record.get('count',False)))
    except (OSError,ValueError,AssertionError):return False
GROUPS = [
    ['community', 'bundle_pause', 'document_input', 'api', 'openai_tools', 'api_publication', 'workbench', 'recovery'],
    ['inputs', 'text', 'migration', 'scheduler', 'preparations', 'assemblies', 'diffusion', 'mnn'],
    ['hub', 'recipe_suggestions', 'speech_voices', 'sana_sprint', 'ltx098_official', 'ltx098_app', 'ltx098_app --multiscale'],
]


def group(names):
    results = []
    for name in names:
        if RESUME and reusable(name):
            results.append(dict(suite=name,exit=0,reused_current_fingerprinted_record=True));print(json.dumps(results[-1]),flush=True);continue
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
    global RESUME
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--resume",action="store_true",help="Reuse only positive records whose source fingerprints are still exact");RESUME=parser.parse_args().resume
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
