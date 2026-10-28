"""Explicit developer code/dependency preparation; no model downloads.

All downloads/cache/extracted code stay under this repository's build/ tree.
Host PyTorch CPU, NumPy, SciPy and standard HF/Python dependencies must already
be installed as described in the guide; this never changes global packages.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
from fetch_soulx_dsp import validate_sources
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python-dependencies',action='store_true',help='Explicitly install export-only pinned packages to build/soulx-python')
    args=parser.parse_args()
    lock=json.loads((ROOT/'third_party/soulx-acoustic-source-lock.json').read_text(encoding='utf-8'))
    validate_sources(lock)
    if args.python_dependencies:
        temporary=ROOT/'build/soulx-python-temp';temporary.mkdir(exist_ok=True)
        env=dict(os.environ,TMP=str(temporary),TEMP=str(temporary),TMPDIR=str(temporary))
        subprocess.run([sys.executable,'-m','pip','install','--no-deps','--target',str(ROOT/'build/soulx-python'),
            '--cache-dir',str(ROOT/'build/pip-cache'),'onnx==1.20.1','ml_dtypes==0.5.4',
            'einops==0.8.2','diffusers==0.29.2','librosa==0.11.0','soxr==1.0.0'],check=True,env=env)
    print('Developer code only; use export_soulx.py with explicitly selected LOCAL checkpoints. No model assets were downloaded.')

if __name__=='__main__':main()
