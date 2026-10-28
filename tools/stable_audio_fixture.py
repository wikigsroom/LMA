"""Code-only, 1x4 ADD/CAST FlatBuffer fixtures for the real LiteRT C API.

These graphs have no trained weights and cannot generate audio.
"""
import hashlib,importlib.util,io,json,urllib.request,zipfile
from pathlib import Path
import flatbuffers
ROOT=Path(__file__).resolve().parents[1]

def host_runtime(lock):
    s=lock['host_test_runtime'];out=ROOT/'build/stable-audio-tests';cache=ROOT/'build/litert-host-probe';out.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=True)
    p=cache/s['file']
    if not p.exists():
        with urllib.request.urlopen(s['url'],timeout=60) as response:data=response.read(50*1024*1024+1)
        if len(data)>50*1024*1024:raise RuntimeError('Host runtime archive too large')
        p.write_bytes(data)
    data=p.read_bytes()
    if hashlib.sha256(data).hexdigest()!=s['sha256']:raise RuntimeError('Official host runtime differs')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name,target in [('ai_edge_litert/libLiteRt.dll',out/'libLiteRt.dll'),('ai_edge_litert/schema_py_generated.py',out/'schema_py_generated.py')]:target.write_bytes(z.read(name))
    module_spec=importlib.util.spec_from_file_location('lma_litert_fixture_schema',out/'schema_py_generated.py');schema=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(schema)
    return out,schema

def graphs(schema,out):
    paths=[]
    for cast in [False,True]:
        m=schema.ModelT();m.version=3;m.description='LMA synthetic 1x4 CAST' if cast else 'LMA synthetic 1x4 ADD; no trained weights'
        op_code=schema.OperatorCodeT();op_code.builtinCode=schema.BuiltinOperator.CAST if cast else schema.BuiltinOperator.ADD;op_code.deprecatedBuiltinCode=op_code.builtinCode;op_code.version=1;m.operatorCodes=[op_code]
        graph=schema.SubGraphT();graph.name='main';graph.inputs=[0];graph.outputs=[1 if cast else 2];graph.tensors=[]
        for i in range(2 if cast else 3):
            t=schema.TensorT();t.name='tensor_'+str(i);t.shape=[1,4];t.type=schema.TensorType.INT64 if cast and i==0 else schema.TensorType.FLOAT32;t.buffer=1 if not cast and i==1 else 0;graph.tensors.append(t)
        op=schema.OperatorT();op.opcodeIndex=0;op.inputs=[0] if cast else [0,1];op.outputs=graph.outputs;op.builtinOptionsType=schema.BuiltinOptions.CastOptions if cast else schema.BuiltinOptions.AddOptions
        if cast:op.builtinOptions=schema.CastOptionsT();op.builtinOptions.inDataType=schema.TensorType.INT64;op.builtinOptions.outDataType=schema.TensorType.FLOAT32
        else:op.builtinOptions=schema.AddOptionsT();op.builtinOptions.fusedActivationFunction=schema.ActivationFunctionType.NONE
        graph.operators=[op];m.subgraphs=[graph];m.buffers=[schema.BufferT()]
        if not cast:
            import struct
            b=schema.BufferT();b.data=list(struct.pack('<4f',1,2,3,4));m.buffers.append(b)
        sig=schema.SignatureDefT();sig.signatureKey='serving_default';sig.subgraphIndex=0;sig.inputs=[];sig.outputs=[]
        for collection,name,index in [(sig.inputs,'input',0),(sig.outputs,'output',graph.outputs[0])]:
            t=schema.TensorMapT();t.name=name;t.tensorIndex=index;collection.append(t)
        m.signatureDefs=[sig];builder=flatbuffers.Builder(2048);root=m.Pack(builder);builder.Finish(root,file_identifier=b'TFL3');p=out/('tiny-cast.tflite' if cast else 'tiny-add.tflite');p.write_bytes(builder.Output());paths.append(p)
    return paths
