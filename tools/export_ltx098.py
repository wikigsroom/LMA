"""Explicit local old-LTX checkpoint to streaming F16/F32 DiT GGUF conversion.

No downloads. Model assets are external; no weights/tokenizer enter the App.
"""
import argparse,json,shutil,tempfile
from pathlib import Path
import numpy as np
from ltx098_assets import Checkpoint,PREFIX,gguf_header,layout_sha,sha,validate_transformer
from evidence import fingerprint,current

def convert(checkpoint_path,output,fixture=False):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Output directory already exists; preserve user assets')
    inputs=fingerprint('tools/ltx098_assets.py','tools/export_ltx098.py','third_party/ltx098-source-lock.json')
    checkpoint_path=Path(checkpoint_path);source_stat=checkpoint_path.stat()
    checkpoint=Checkpoint(checkpoint_path);config,items=validate_transformer(checkpoint,fixture);source_sha=sha(checkpoint.path)
    output.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.ltx098-convert-',dir=output.parent))
    try:
        header,plan,payload=gguf_header(config,items,source_sha);path=stage/'ltx098-dit.gguf'
        with path.open('wb') as stream:
            stream.write(header)
            for name,half,size in plan:
                array=checkpoint.array(PREFIX+name)
                if half:
                    if np.max(np.abs(array))>65504.:raise ValueError('Dense weights exceed F16 representable range')
                    array=array.astype('<f2')
                raw=array.tobytes();assert len(raw)==size;stream.write(raw);stream.write(b'\0'*((-size)%32))
        if path.stat().st_size!=len(header)+payload:raise ValueError('Incomplete converted GGUF')
        receipt=dict(schema='lma.ltx098-converted-dit/1',source_file=checkpoint.path.name,source_bytes=checkpoint.length,source_sha256=source_sha,source_header_sha256=checkpoint.header_sha256,transformer_tensors=len(items),transformer_parameters=sum(np.prod(v['shape'],dtype=np.int64).item() for v in items.values()),layout_sha256=layout_sha(items),file=path.name,bytes=path.stat().st_size,sha256=sha(path),dense_weight_dtype='F16',other_parameters_dtype='F32',synthetic_parameters=fixture,complete_video_pipeline=False,packaged_in_apk=False,input_fingerprint=inputs)
        (stage/'conversion.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        final_stat=checkpoint_path.stat()
        if (final_stat.st_ino,final_stat.st_size,final_stat.st_mtime_ns)!=(source_stat.st_ino,source_stat.st_size,source_stat.st_mtime_ns):raise ValueError('Checkpoint changed during conversion')
        current(inputs);stage.rename(output)
        return receipt
    finally:
        if stage.exists():
            if stage.resolve().parent!=output.parent or not stage.name.startswith('.ltx098-convert-'):raise RuntimeError('Unsafe conversion cleanup')
            shutil.rmtree(stage)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--checkpoint',required=True,type=Path);parser.add_argument('--output-dir',required=True,type=Path);parser.add_argument('--fixture',action='store_true');args=parser.parse_args()
    record=convert(args.checkpoint,args.output_dir,args.fixture);print(json.dumps({k:v for k,v in record.items() if k!='input_fingerprint'}))

if __name__=='__main__':main()
