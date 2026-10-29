"""Stage the archived SD-Turbo experiment in its original ignored path; execute only with --execute.

This is a Windows developer replay, never an Android model-acquisition prerequisite.
No downloads, package installs, environment changes or existing capture deletion.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from fetch_sd_distilled_trained import selected

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    directory=ROOT/'build/sd-distilled-asset-probe';directory.mkdir(parents=True,exist_ok=True)
    archive=ROOT/'research/sd_distilled_trained/experiments/probe_sd_turbo.py';target=directory/archive.name
    if target.exists() and target.read_bytes()!=archive.read_bytes():raise ValueError('Preserve differing existing developer experiment')
    if not target.exists():target.write_bytes(archive.read_bytes())
    fields=['id','repository','revision','path','bytes','sha256','url','public_metadata_sha256']
    assets=[{k:a[k] for k in fields} for a in selected()['assets'][:2]]
    plan=directory/'asset-plan.json'
    if plan.exists():
        if json.loads(plan.read_text(encoding='utf-8'))['assets']!=assets:raise ValueError('Preserve different existing asset plan')
    else:plan.write_text(json.dumps(dict(schema='lma.private-sd-distilled-developer-plan/1',assets=assets),indent=2)+'\n',encoding='utf-8')
    if not args.execute:
        print('Archived source and immutable asset choices staged; no model opened, downloaded or executed.');return
    print('Run five complete SD-Turbo native cases with already verified assets; each capture is retained.',flush=True)
    subprocess.run([sys.executable,str(target)],cwd=ROOT,check=True,timeout=21600)


if __name__=='__main__':main()
