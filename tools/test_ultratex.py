"""Random actual architectures -> local export -> production native PBR task.

Program checks only. No full trained model, phone/emulator or model download.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import warnings
from evidence import ROOT,fingerprint,current

OUT=ROOT/'build/ultratex-tests'


def main():
    sys.path[:0]=[str(ROOT/'build/ultratex-python'),str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    import torch
    import numpy as np
    import onnxruntime as ort
    import sentencepiece as spm
    from tokenizers import Tokenizer,models,pre_tokenizers,normalizers,processors,decoders,AddedToken
    from tokenizers.pre_tokenizers import ByteLevel
    from transformers import CLIPTextConfig,CLIPTextModel,T5Config,T5EncoderModel,Qwen3Config,Qwen3Model,T5Tokenizer,PreTrainedTokenizerFast
    from ultratex_codecs import autoencoder,Encode,Decode,Clip,T5,Qwen,export_codec,export_text
    from ultratex_flows import architecture,export
    from export_ultratex import manifest,rename_graph
    from shape_graphs import export_graph
    from safetensors.torch import save_file
    from test_spatial import write_mesh
    torch.manual_seed(1476);torch.set_num_threads(2);OUT.mkdir(exist_ok=True)
    inputs=fingerprint('native/spatial','native/rf_shape','tools/test_ultratex.py','tools/ultratex_codecs.py',
        'tools/ultratex_catalogue.py','tools/ultratex_flows.py','tools/export_ultratex.py','tools/ultratex_attention.py',
        'third_party/ultratex-flow-source-lock.json','tests/expansion-native/text_tokens.cpp','tests/expansion-native/ultratex.cpp')
    checks=[]
    def check(name,value,**extra):
        assert value,(name,extra);checks.append(dict(case=name,**extra))
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(file):return alias+'/'+file.resolve().relative_to(ROOT).as_posix()
    def tokens(request,success=True):
        path=OUT/'tokens.json';path.write_text(json.dumps(request,ensure_ascii=False),'utf-8')
        p=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_text_contract.exe'),native(path)],capture_output=True,text=True,encoding='utf-8',timeout=20)
        assert (p.returncode==0)==success,p.stderr
        return json.loads(p.stdout) if success else None
    def compare_graph(model,args,path,names,outname):
        with torch.inference_mode():expected=model(*args).numpy()
        export_graph(model,args,path,names,outname,{})
        session=ort.InferenceSession(str(path),options,providers=['CPUExecutionProvider'])
        got=session.run(None,{n:v.numpy() for n,v in zip(names,args)})[0]
        error=float(np.max(np.abs(got-expected)));check(path.parent.name+'_'+path.stem,np.allclose(got,expected,atol=3e-5,rtol=3e-4),maximumError=error)
    try:
        def operation(name,**values):
            file=OUT/'operation.json';file.write_text(json.dumps(dict(schema='lma.engine-request/1',operation=name,**values)),'utf-8')
            result=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_ultratex_contract.exe'),native(file)],capture_output=True,text=True,encoding='utf-8',timeout=20)
            assert result.returncode==0,result.stderr
            return json.loads(result.stdout)
        tiles=np.arange(6*2*2*3,dtype=np.float32).reshape(6,3,2,2)
        layout=operation('layout',tiles=tiles.reshape(6,-1).tolist(),side=2,channels=3)
        expected=np.concatenate([np.concatenate([tiles[i] for i in row],axis=2) for row in ((0,1,3),(2,4,5))],axis=1)
        check('publisher_atlas_order',np.array_equal(layout['atlas'],expected.reshape(-1)))
        check('publisher_chw_to_btd',np.array_equal(layout['tokens'],expected.transpose(1,2,0).reshape(-1)))
        check('atlas_roundtrip',np.array_equal(layout['tiles'],tiles.reshape(6,-1)))
        ids=np.stack(np.meshgrid(np.arange(4)+4,np.arange(6)+6,indexing='ij'),axis=-1)
        ids=np.concatenate([np.zeros((4,6,1)),ids],axis=-1)
        check('distinct_height_width_position_offsets',np.array_equal(layout['ids'],ids.reshape(-1)))
        from ultratex_flows import source
        import ast,math,__future__
        file,content=source('ultratex/backbones/flux1/sampling.py')
        functions=[n for n in ast.parse(content).body if isinstance(n,ast.FunctionDef) and n.name in ('get_schedule','get_lin_function','time_shift')]
        namespace=dict(torch=torch,math=math)
        exec(compile(ast.Module(body=functions,type_ignores=[]),str(file),'exec',flags=__future__.annotations.compiler_flag),namespace)
        schedule=namespace['get_schedule']
        for size in (32,128,512):
            for steps in (1,7,25):
                got=operation('schedule',steps=steps,size=size)['schedule']
                expected=schedule(steps,(size*3//8)*(size*2//8)//256,shift=True)
                check('publisher_shifted_euler_'+str((size,steps)),np.allclose(got,expected,atol=3e-7,rtol=3e-7))
        from PIL import Image
        rng=np.random.default_rng(316)
        for side in (2,4,8):
            for kind in ('empty','one_pixel','random'):
                alpha=np.zeros((64,64),dtype=np.uint8)
                if kind=='one_pixel':alpha[17,33]=255
                if kind=='random':alpha=rng.integers(0,256,(64,64),dtype=np.uint8)
                reduced=np.asarray(Image.fromarray(alpha).resize((side,side),Image.Resampling.BILINEAR))>0
                dilated=torch.nn.functional.max_pool2d(torch.nn.functional.pad(torch.tensor(reduced,dtype=torch.float32)[None,None],(1,0,1,0)),2,1)[0,0].numpy()
                got=operation('mask',alpha=(alpha.astype(np.float32)/255).reshape(-1).tolist(),size=64,side=side)['mask']
                check('pil_bilinear_aa_default_anchor_'+str((side,kind)),np.array_equal(got,dilated.reshape(-1)))
        # Tiny generated SentencePiece, not a publisher vocabulary or dictionary.
        corpus=OUT/'corpus.txt';corpus.write_text(('a blue ceramic object with rough red steel texture. 你好 世界 工具 材质\n')*20,'utf-8')
        spm.SentencePieceTrainer.train(input=native(corpus),model_prefix=native(OUT/'toy'),vocab_size=64,
            normalization_rule_name='identity',hard_vocab_limit=False,bos_id=-1,eos_id=1,pad_id=0,unk_id=2,minloglevel=2)
        piece=spm.SentencePieceProcessor(model_file=native(OUT/'toy.model'));vocab=piece.get_piece_size()+100
        reference=T5Tokenizer(vocab_file=native(OUT/'toy.model'),legacy=True,extra_ids=100)
        for text in ('','blue object','你好 世界','  a\nred\tobject  ','<extra_id_0> blue <extra_id_99>', 'a <extra_id_1>texture','<extra_id_bad> blue <extra_id_2>', '<extra_id_01> <extra_id_3>', 'blue '*512):
            request=dict(kind='t5',path=native(OUT/'toy.model'),text=text,length=32,vocab=vocab)
            got=tokens(request);expected=reference(text,max_length=32,truncation=True,padding='max_length')
            check('sentencepiece_'+repr(text),got['ids']==expected['input_ids'] and got['mask']==expected['attention_mask'],got=got['ids'],expected=expected['input_ids'])
        alphabet=sorted(ByteLevel.alphabet());base={x:i for i,x in enumerate(alphabet)}
        for special in ('<unk>','<bos>','<eos>','<|im_start|>','<|im_end|>'):base[special]=len(base)
        for qwen in (False,True):
            tokenizer=Tokenizer(models.BPE(vocab=base,merges=[],unk_token='<unk>',end_of_word_suffix=''))
            tokenizer.pre_tokenizer=pre_tokenizers.ByteLevel(add_prefix_space=False,use_regex=True)
            tokenizer.decoder=decoders.ByteLevel();tokenizer.normalizer=normalizers.NFC()
            tokenizer.add_special_tokens([AddedToken(x,special=True,normalized=False) for x in ('<unk>','<bos>','<eos>','<|im_start|>','<|im_end|>')])
            if not qwen:tokenizer.post_processor=processors.TemplateProcessing(single='<bos> $A <eos>',special_tokens=[('<bos>',base['<bos>']),('<eos>',base['<eos>'])])
            file=OUT/('qwen-tokenizer.json' if qwen else 'clip-tokenizer.json');tokenizer.save(str(file))
            fast=PreTrainedTokenizerFast(tokenizer_object=tokenizer,pad_token='<eos>',bos_token=None if qwen else '<bos>',eos_token=None if qwen else '<eos>')
            for text in ('','blue object','你好 e\u0301 🙂','a'*900):
                actual='<|im_start|>user\n'+text+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n' if qwen else text
                got=tokens(dict(kind='bpe',path=native(file),text=text,length=77,vocab=len(base),pad=base['<eos>'],qwen=qwen))
                expected=fast(actual,max_length=77,truncation=True,padding='max_length')
                check('bpe_'+str(qwen)+'_'+str(len(text)),got['ids']==expected['input_ids'] and got['mask']==expected['attention_mask'])
        for name,change in [('missing_model',dict(path=native(OUT/'absent.model'))),('oversize_length',dict(length=513)),('vocab_mismatch',dict(vocab=10))]:
            r=dict(kind='t5',path=native(OUT/'toy.model'),text='blue',length=32,vocab=vocab);r.update(change);tokens(r,False);check(name,True)
        picture=OUT/'reference.png'
        from PIL import Image
        im=Image.new('RGBA',(59,47),(0,0,0,0));im.paste((140,80,35,255),(10,8,49,39));im.save(picture)
        mesh=OUT/'input.glb';write_mesh(mesh,vertices=[[-1,-1,-1],[1,-1,-1],[0,1,-1],[0,0,1]],faces=[[0,2,1],[0,1,3],[1,2,3],[2,0,3]])
        for family in ('flux1','flux2'):
            directory=OUT/family;directory.mkdir(exist_ok=True);size=32;channels=64 if family=='flux1' else 128
            vaecfg=dict(resolution=32,in_channels=3,ch=32,out_ch=3,ch_mult=[1,1,1,1],num_res_blocks=1,z_channels=channels//4)
            if family=='flux1':vaecfg.update(scale_factor=.3611,shift_factor=.1159)
            vae=autoencoder(family,vaecfg)
            if family=='flux2':
                with torch.no_grad():
                    vae.bn.running_mean.copy_(torch.randn(channels)*.1)
                    vae.bn.running_var.copy_(torch.rand(channels)+.3)
            noise=torch.randn((1,16,4,4) if family=='flux1' else (1,128,2,2));pixels=torch.randn(1,3,size,size)
            if family=='flux2':
                with torch.no_grad():
                    expected=vae.encode(pixels);got=Encode(vae,family)(pixels,noise)
                check('flux2_publisher_bn',torch.allclose(expected,got,atol=2e-6,rtol=3e-5),maximumError=float((expected-got).abs().max()))
            compare_graph(Encode(vae,family),(pixels,noise),directory/'vae_encoder.onnx',['image','noise'],'latents')
            latent=Encode(vae,family)(pixels,noise)
            for name in ('albedo_decoder','mr_decoder'):
                compare_graph(Decode(vae,family),(latent,),directory/(name+'.onnx'),['latents'],'image')
            if family=='flux1':
                clip=CLIPTextModel(CLIPTextConfig(vocab_size=len(base),hidden_size=8,intermediate_size=16,num_hidden_layers=1,num_attention_heads=2,max_position_embeddings=77,pad_token_id=base['<eos>'],bos_token_id=base['<bos>'],eos_token_id=base['<eos>'],attention_dropout=0)).eval()
                text=T5EncoderModel(T5Config(vocab_size=vocab,d_model=12,d_ff=24,num_layers=1,num_heads=2,d_kv=6,dropout_rate=0)).eval()
                text.config._attn_implementation='eager';clip.config._attn_implementation='eager'
                compare_graph(Clip(clip),(torch.ones(1,77,dtype=torch.int64),),directory/'clip.onnx',['input_ids'],'pooled_text')
                compare_graph(T5(text),(torch.ones(1,512,dtype=torch.int64),),directory/'text.onnx',['input_ids'],'text')
                shutil.copyfile(OUT/'toy.model',directory/'t5.model');shutil.copyfile(OUT/'clip-tokenizer.json',directory/'clip-tokenizer.json')
                textcfg=dict(textWidth=12,textVocab=vocab,textPad=0,textLength=512,clipWidth=8,clipVocab=len(base),clipPad=base['<eos>'],clipLength=77)
            else:
                qc=Qwen3Config(vocab_size=len(base),hidden_size=8,intermediate_size=16,num_hidden_layers=27,num_attention_heads=1,num_key_value_heads=1,head_dim=8,max_position_embeddings=512,pad_token_id=base['<eos>'],attention_dropout=0)
                qc._attn_implementation='eager';text=Qwen3Model(qc).eval()
                for filled in (1,37,511,512):
                    ids=torch.randint(0,len(base),(1,512));mask=(torch.arange(512)[None]<filled).long()
                    with torch.no_grad():
                        original=text(input_ids=ids,attention_mask=mask,output_hidden_states=True,use_cache=False,return_dict=True)
                        expected=torch.cat([original.hidden_states[i] for i in (9,18,27)],dim=-1)
                        actual=Qwen(text)(ids,mask)
                    check('qwen_publisher_mask_'+str(filled),torch.allclose(actual,expected,atol=2e-6,rtol=3e-5))
                compare_graph(Qwen(text),(torch.ones(1,512,dtype=torch.int64),torch.ones(1,512,dtype=torch.int64)),directory/'text.onnx',['input_ids','attention_mask'],'text')
                shutil.copyfile(OUT/'qwen-tokenizer.json',directory/'qwen-tokenizer.json')
                textcfg=dict(textWidth=24,textVocab=len(base),textPad=base['<eos>'],textLength=512)
            fc=dict(in_channels=channels,context_in_dim=textcfg['textWidth'],hidden_size=64,num_heads=4,depth=1,depth_single_blocks=1,
                axes_dim=[4,6,6] if family=='flux1' else [4,4,4,4],theta=10000,mlp_ratio=2.)
            fc.update(vec_in_dim=8,qkv_bias=True,guidance_embed=True) if family=='flux1' else fc.update(use_guidance_embed=False)
            flow,_=architecture(family,fc,bfloat16=False)
            source=directory/'selected-sources';source.mkdir(exist_ok=True)
            (source/'flow.json').write_text(json.dumps(fc),'utf-8');(source/'vae.json').write_text(json.dumps(vaecfg),'utf-8')
            save_file(flow.state_dict(),str(source/'flow.safetensors'))
            save_file(vae.state_dict(),str(source/'vae.safetensors'))
            mr_state={k:v.clone() for k,v in vae.decoder.state_dict().items()}
            mr_state[next(iter(mr_state))].add_(.0001);save_file(mr_state,str(source/'mr-decoder.safetensors'))
            if family=='flux1':
                clip.save_pretrained(source/'clip',safe_serialization=True);text.save_pretrained(source/'t5',safe_serialization=True)
                shutil.copyfile(OUT/'clip-tokenizer.json',source/'clip/tokenizer.json');shutil.copyfile(OUT/'toy.model',source/'t5/spiece.model')
                lora_names=('double_blocks.0.processor.qkv_lora1.down.weight','double_blocks.0.processor.qkv_lora1.up.weight')
            else:
                text.save_pretrained(source/'qwen',safe_serialization=True);shutil.copyfile(OUT/'qwen-tokenizer.json',source/'qwen/tokenizer.json')
                lora_names=('base_model.model.double_blocks.0.img_attn.qkv.lora_A.default.weight','base_model.model.double_blocks.0.img_attn.qkv.lora_B.default.weight')
            for material in ('albedo','mr'):
                save_file({lora_names[0]:torch.randn(2,64)*.01,lora_names[1]:torch.randn(192,2)*.01},str(source/(material+'-lora.safetensors')))
            for name in ('albedo','mr'):
                temp=directory/'flow.onnx';temp.unlink(missing_ok=True)
                with warnings.catch_warnings():warnings.simplefilter('ignore');export(flow,family,fc,temp)
                target=directory/(name+'_flow.onnx');target.unlink(missing_ok=True);(directory/(target.name+'.data')).unlink(missing_ok=True);rename_graph(temp,target)
            cfg=dict(schema='lma.ultratex-export/1',pipeline='ultratex_'+family,dtype='float32',opset=17,source=dict(repository='yiboz2001/UltraTex',revision='a726678f3f3631fe2c5e3d1fb4597114784c7a8b'),imageSize=32,latentChannels=channels,cameraRig='lma_orthographic_y_up_six_v1',guidanceEmbedding=family=='flux1',**textcfg)
            (directory/'ultratex-config.json').write_text(json.dumps(cfg),'utf-8');manifest(directory,cfg,[])
            bundle=json.loads((directory/'lma-bundle.json').read_text('utf-8'));components={}
            for c in bundle['components']:
                f=directory/c['path'];check(family+'_component_'+c['role'],f.stat().st_size==c['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==c['sha256'] and not c['url']);components[c['role']]=native(f)
            command=dict(schema='lma.engine-request/1',type='mesh.generate',pipeline=cfg['pipeline'],workspace=native(directory),components=components,
                prompt='a blue ceramic object',referenceImage=native(picture),sourceMesh=native(mesh),parameters=dict(threads=2,steps=2,seed=7,guidance=3.5,atlas=256))
            def worker(request,success):
                file=directory/'request.json';file.write_text(json.dumps(request),'utf-8')
                r=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_spatial.exe'),native(file)],capture_output=True,text=True,encoding='utf-8',timeout=90)
                (directory/'worker.log').write_text(r.stdout+r.stderr,'utf-8');assert (r.returncode==0)==success,(r.returncode,r.stdout[-1000:],r.stderr[-1000:])
                return [json.loads(x) for x in r.stdout.splitlines() if x.startswith('{')]
            for prune in (True,False) if family=='flux2' else (True,):
                output=directory/('pruned.glb' if prune else 'full.glb');output.unlink(missing_ok=True);r=copy.deepcopy(command);r.update(output=native(output));
                if family=='flux2':r['parameters']['dropBackground']=prune
                events=worker(r,True);data=output.read_bytes();length=struct.unpack_from('<I',data,12)[0];glb=json.loads(data[20:20+length])
                check(family+'_production_worker_'+str(prune),events[-1]['event']=='complete' and len(glb['images'])==2 and 'TEXCOORD_0' in glb['meshes'][0]['primitives'][0]['attributes'])
                check(family+'_material_stages_'+str(prune),{x['stage'] for x in events if x['event']=='stage'}>={'encoding_text','sampling_albedo','sampling_mr','baking_material'})
            for name,change in [('missing_decoder',lambda r:r['components'].pop('mr_decoder')),('unknown_field',lambda r:r['parameters'].update(remote=True)),('missing_mesh',lambda r:r.pop('sourceMesh'))]:
                r=copy.deepcopy(command);output=directory/'invalid.glb';output.unlink(missing_ok=True);r['output']=native(output);change(r);worker(r,False);check(family+'_'+name,not output.exists())
            cli_output=directory/'cli-export'
            if cli_output.exists():assert cli_output.parent==directory;shutil.rmtree(cli_output)
            cli=[sys.executable,str(ROOT/'tools/export_ultratex.py'),'--family',family,'--image-size','32','--float-attention','--output',str(cli_output)]
            for flag,file in [('flow-config','flow.json'),('flow-weights','flow.safetensors'),('vae-config','vae.json'),('vae-weights','vae.safetensors'),('albedo-lora','albedo-lora.safetensors'),('mr-lora','mr-lora.safetensors'),('mr-decoder','mr-decoder.safetensors')]:cli+=['--'+flag,str(source/file)]
            for encoder in (('clip','t5') if family=='flux1' else ('qwen',)):cli+=['--'+encoder,str(source/encoder)]
            env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(str(ROOT/p) for p in ('build/ultratex-python','build/shape-reference-python','build/spatial-reference-python','tools'))
            completed=subprocess.run(cli,capture_output=True,text=True,encoding='utf-8',env=env,timeout=180)
            (directory/'cli.log').write_text(completed.stdout+completed.stderr,'utf-8');check(family+'_actual_cli',completed.returncode==0,tail=completed.stderr[-1200:])
            prepared=json.loads((cli_output/'lma-bundle.json').read_text('utf-8'));r=copy.deepcopy(command)
            r.update(workspace=native(cli_output),components={c['role']:native(cli_output/c['path']) for c in prepared['components']},output=native(directory/'cli.glb'))
            (directory/'cli.glb').unlink(missing_ok=True);events=worker(r,True);check(family+'_actual_cli_production_worker',events[-1]['event']=='complete')
            hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in cli_output.iterdir()}
            rejected=subprocess.run(cli,capture_output=True,text=True,encoding='utf-8',env=env,timeout=20)
            check(family+'_cli_preserves_existing',rejected.returncode!=0 and hashes=={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in cli_output.iterdir()})
            if family=='flux2':
                guided=directory/'with-guidance'
                if guided.exists():assert guided.parent==directory;shutil.rmtree(guided)
                guided.mkdir()
                for component in bundle['components']:shutil.copyfile(directory/component['path'],guided/component['path'])
                guided_config=copy.deepcopy(cfg);guided_config['guidanceEmbedding']=True
                (guided/'ultratex-config.json').write_text(json.dumps(guided_config),'utf-8')
                flow_config=copy.deepcopy(fc);flow_config['use_guidance_embed']=True
                network,_=architecture('flux2',flow_config,bfloat16=False)
                for material in ('albedo','mr'):
                    for suffix in ('','.data'):(guided/(material+'_flow.onnx'+suffix)).unlink(missing_ok=True)
                    with warnings.catch_warnings():warnings.simplefilter('ignore');export(network,'flux2',flow_config,guided/'flow.onnx')
                    rename_graph(guided/'flow.onnx',guided/(material+'_flow.onnx'))
                manifest(guided,guided_config,[])
                prepared=json.loads((guided/'lma-bundle.json').read_text('utf-8'));r=copy.deepcopy(command)
                r.update(workspace=native(guided),components={c['role']:native(guided/c['path']) for c in prepared['components']},output=native(directory/'guided.glb'))
                (directory/'guided.glb').unlink(missing_ok=True);events=worker(r,True)
                check('flux2_guidance_embedding_with_cfg',events[-1]['event']=='complete')
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    result=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsDownloaded=0,completeModelsRun=0,randomNeuralGraphs=True,actualNativeWorker=True,actualExportCli=True,pipelines=['ultratex_flux1','ultratex_flux2'],physicalDeviceTests=0,virtualizationUsed=False)
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModelsRun=0)))


if __name__=='__main__':main()
