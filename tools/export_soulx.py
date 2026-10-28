"""Explicit offline SoulX flow.pt/hift.pt conversion; never downloads a model."""
import argparse,json,os,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def environment():
    # All optional developer dependencies stay in the designated workspace.
    sys.path[:0]=[str(ROOT/'build/soulx-python'),str(ROOT/'build/native-src/soulx-podcast')]
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from fetch_soulx_dsp import validate_sources
    lock=json.loads((ROOT/'third_party/soulx-acoustic-source-lock.json').read_text(encoding='utf-8'))
    if any(not (ROOT/'build/native-src'/source['name']).is_dir() for source in lock['sources']):
        raise RuntimeError('Prepare pinned code explicitly with tools/prepare_soulx_acoustic.py before offline conversion')
    validate_sources(lock)
    import hashlib,importlib.metadata
    for name,digest in lock['python_sources'].items():
        path=ROOT/'build/soulx-python'/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise RuntimeError('Pinned export dependency differs: '+name)
    for name,version in lock['python_versions'].items():
        if importlib.metadata.version(name)!=version:raise RuntimeError('Wrong export dependency: '+name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint-dir',required=True,type=Path,help='Explicit local directory with ORIGINAL flow.pt and hift.pt')
    parser.add_argument('--output-dir',required=True,type=Path,help='New directory for converted USER assets; never an APK input')
    parser.add_argument('--synthetic-fixture',action='store_true',help='Explicitly mark UNTRAINED developer fixtures; no model-quality evidence')
    args=parser.parse_args();environment()
    from soulx_acoustic import FlowEncoder,FlowEstimator,HiFTSpectrum,strict_checkpoint,freeze_weight_norm,export_graph,source_weights,write_manifest,asset
    import torch,gc
    from soulxpodcast.models.modules.flow import CausalMaskedDiffWithXvec
    from soulxpodcast.models.modules.hifigan import HiFTGenerator
    source=args.checkpoint_dir.resolve();output=args.output_dir.resolve()
    if output.exists():raise RuntimeError('Output must be a new directory; existing assets are preserved')
    for name in ['flow.pt','hift.pt']:
        if not (source/name).is_file():raise RuntimeError('Missing explicitly selected checkpoint: '+name)
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.soulx-export-',dir=output.parent));torch.set_num_threads(4)
    try:
        sources=[asset(source/n,n) for n in ['flow.pt','hift.pt']]
        flow=CausalMaskedDiffWithXvec();strict_checkpoint(flow,source/'flow.pt')
        print('Export complete Flow encoder',flush=True);export_graph('flow_encoder',FlowEncoder(flow),stage)
        print('Export complete Flow estimator',flush=True);export_graph('flow_estimator',FlowEstimator(flow.decoder.estimator),stage)
        del flow;gc.collect()
        hift=HiFTGenerator();strict_checkpoint(hift,source/'hift.pt',generator_prefix=True);freeze_weight_norm(hift)
        source_weights(hift,stage)
        print('Export complete HiFT F0 predictor',flush=True);export_graph('hift_f0',hift.f0_predictor,stage)
        print('Export complete HiFT neural spectra',flush=True);export_graph('hift_spectrum',HiFTSpectrum(hift),stage)
        write_manifest(stage,sources,True if args.synthetic_fixture else None);stage.rename(output)
        print('Converted USER assets: '+str(output)+'; full SoulX/phone validation remains required',flush=True)
    finally:
        if stage.exists():
            if stage.resolve().parent!=output.parent:raise RuntimeError('Unsafe export cleanup target')
            shutil.rmtree(stage)

if __name__=='__main__':main()
