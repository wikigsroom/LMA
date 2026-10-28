"""Offline conversion of explicitly selected original SoulX reference ONNX files.

The complete graph and tensor bytes are preserved, externalized into fixed
sidecars. No weights are initialized, model architecture reduced, or data
downloaded. Output assets remain user data, never an APK build input.
"""
import argparse,hashlib,importlib.metadata,json,os,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTRACTS={
    's3':dict(original='speech_tokenizer_v2.onnx',file='reference-s3.onnx',opset=17,
              inputs=[('feats',1,[1,128,-1]),('feats_length',6,[1])],outputs=[('indices',6,[1,-1])]),
    'speaker':dict(original='campplus.onnx',file='reference-speaker.onnx',opset=14,
              inputs=[('input',1,[1,-1,80])],outputs=[('output',1,[1,192])])}
FORMAT='lma.soulx-reference-onnx/1'


def environment():
    sys.path.insert(0,str(ROOT/'build/soulx-python'))
    if importlib.metadata.version('onnx')!='1.20.1':raise RuntimeError('Use pinned ONNX1.20.1')


def asset(path,role):
    digest=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
    return dict(role=role,file=path.name,bytes=path.stat().st_size,sha256=digest.hexdigest())


def contract(graph,role):
    from onnx.external_data_helper import _get_all_tensors
    expected=CONTRACTS[role]
    if [(x.domain,x.version) for x in graph.opset_import]!=[('',expected['opset'])]:raise RuntimeError('Unsupported reference ONNX opset/domain')
    # External inputs must be the two selected original ONNXs, with no
    # undeclared tensor files, custom-domain kernels or training subgraphs.
    if graph.training_info or any(t.external_data or t.data_location==1 for t in _get_all_tensors(graph)):raise RuntimeError('Expected self-contained inference ONNX')
    if any(n.domain for n in graph.graph.node):raise RuntimeError('Custom reference operators are unsupported')
    for direction in ['inputs','outputs']:
        actual=getattr(graph.graph,'input' if direction=='inputs' else 'output')
        if len(actual)!=len(expected[direction]):raise RuntimeError('Wrong reference graph IO count')
        for item,(name,dtype,shape) in zip(actual,expected[direction]):
            tensor=item.type.tensor_type
            if item.name!=name or tensor.elem_type!=dtype or len(tensor.shape.dim)!=len(shape):raise RuntimeError('Wrong reference graph IO name/type/rank')
            for dim,wanted in zip(tensor.shape.dim,shape):
                if dim.HasField('dim_value') and (wanted<0 or dim.dim_value!=wanted):raise RuntimeError('Wrong reference graph static/time dimension')


def convert(source,output):
    environment();import onnx
    source=source.resolve();output=output.resolve()
    if output.exists():raise RuntimeError('Output must be a new directory; existing assets are preserved')
    for item in CONTRACTS.values():
        p=source/item['original']
        if not p.is_file() or not 1<=p.stat().st_size<=600*1024*1024:raise RuntimeError('Missing/oversized explicitly selected reference model')
    output.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.soulx-ref-',dir=output.parent))
    originals=[];assets=[];layouts=[]
    try:
        for role,item in CONTRACTS.items():
            path=source/item['original'];originals.append(asset(path,role))
            model=onnx.load(str(path),load_external_data=False);contract(model,role)
            def identity(model):
                # Loading external data may explicitly set the proto2 DEFAULT
                # enum. Normalize that presence bit, not graph/tensor values.
                from onnx.external_data_helper import _get_all_tensors
                for tensor in _get_all_tensors(model):
                    if tensor.data_location==0:tensor.ClearField('data_location')
                return hashlib.sha256(model.SerializeToString()).hexdigest()
            original_identity=identity(model)
            name=item['file'];onnx.save_model(model,str(stage/name),save_as_external_data=True,
                all_tensors_to_one_file=True,location=name+'.data',size_threshold=0,convert_attribute=False)
            # Prove this operation preserves the complete graph/tensor bytes.
            loaded=onnx.load(str(stage/name),load_external_data=True)
            if original_identity!=identity(loaded):raise RuntimeError('Reference conversion altered graph/tensors')
            onnx.checker.check_model(str(stage/name))
            layouts.append(dict(role=role,nodes=len(model.graph.node),initializers=len(model.graph.initializer),
                initializer_values=sum(__import__('math').prod(t.dims) for t in model.graph.initializer),opset=item['opset'],
                graph_tensor_identity_sha256=original_identity))
            del model,loaded
            assets.extend([asset(stage/name,role),asset(stage/(name+'.data'),role+'_data')])
        lock=json.loads((ROOT/'third_party/soulx-reference-source-lock.json').read_text(encoding='utf-8'))
        known={x['file']:x for x in lock['publisher_models']}
        matches=[x['sha256']==known[x['file']]['sha256'] and x['bytes']==known[x['file']]['bytes'] for x in originals]
        record=dict(format=FORMAT,architecture='soulx_reference_s3_v2_campplus',contracts=CONTRACTS,
            sources=originals,assets=assets,layouts=layouts,publisher_hashes_match=all(matches),
            reference_samples_min=24000,reference_samples_max=360000,sample_rate=24000,channels=1,
            semantic_codes=6561,speaker_dimensions=192,weights_initialized=False,model_assets_packaged_in_apk=False,
            full_graph_tensor_identity_verified=True,full_soulx_pipeline=False)
        (stage/'soulx-reference.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');stage.rename(output)
        return record
    finally:
        if stage.exists():
            if stage.resolve().parent!=output.parent:raise RuntimeError('Unsafe staging cleanup target')
            shutil.rmtree(stage)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();record=convert(args.source_dir,args.output_dir)
    print(json.dumps({k:v for k,v in record.items() if k not in ['contracts','sources','assets']}))
