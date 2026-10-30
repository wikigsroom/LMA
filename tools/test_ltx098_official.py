"""Bounded program oracles for original T5 file loading and old LTX multiscale math.

Only random small neural fixtures and publisher tokenizer/config metadata are used.
No complete trained model, trained video, phone or quality/endurance validation.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import types
from evidence import current, fingerprint
from build_ltx098_app import inputs as native_inputs, sha
from ltx098_official_profile import graph, lock

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/ltx098-official-tests'


def inputs():
    return native_inputs() | fingerprint('tools/test_ltx098_official.py', 'app/src/main/java/com/lma/app/core/LtxPixArtSpec.java',
        'app/src/main/java/com/lma/app/Ltx098Engine.java', 'app/src/main/assets/architectures/ltx098-upscaler.onnx',
        'catalogue/model-bundles.json', 'catalogue/model-assemblies.json')


def main():
    before = inputs()
    build = json.loads((ROOT/'build/ltx098-app-host/receipt.json').read_text(encoding='utf-8'))
    current(build['input_fingerprint'])
    assert build['input_fingerprint'] == native_inputs()
    binaries = {s['stage']: ROOT/s['path'] for s in build['stages']}
    for s in build['stages']:
        assert sha(ROOT/s['path']) == s['sha256']
    sys.path[:0] = [str(ROOT/'build/soulx-language-python'), str(ROOT/'build/soulx-python')]
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    import numpy as np
    import torch
    import onnxruntime as ort
    from safetensors.torch import save_file
    from transformers import T5Config, T5EncoderModel, T5Tokenizer
    torch.set_num_threads(2)
    OUT.mkdir(exist_ok=True)
    directory = OUT/('run-'+str(time.time_ns()))
    directory.mkdir()
    count = 0
    cases = []

    def check(ok, label):
        nonlocal count
        if not ok:
            raise AssertionError(label)
        count += 1

    def write(name, value):
        path = directory/name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return path

    def run(stage, args, success=True):
        result = subprocess.run([str(binaries[stage]), *map(str, args)], capture_output=True, timeout=45)
        try:
            record = json.loads(result.stdout.decode('utf-8').strip().splitlines()[-1])
        except Exception:
            raise AssertionError(result.stderr.decode('utf-8', errors='replace')[-2000:])
        check((result.returncode == 0) == success and record.get('ok', stage=='text') == success, 'Native protocol outcome')
        return record

    metadata = ROOT/'build/ltx098-official-metadata'
    for name in ['spiece.model', 'tokenizer_config.json', 'special_tokens_map.json']:
        source = metadata/('pixart-'+name)
        check(source.is_file(), 'Explicitly fetched small tokenizer input exists')
        shutil.copyfile(source, directory/name)
    tokenizer = T5Tokenizer.from_pretrained(str(directory), local_files_only=True, legacy=True)
    torch.manual_seed(173)
    config = T5Config(vocab_size=32128, d_model=32, d_kv=8, d_ff=64, num_layers=2, num_heads=4,
        feed_forward_proj='gated-gelu', dropout_rate=0, layer_norm_epsilon=1e-6, pad_token_id=0, eos_token_id=1)
    model = T5EncoderModel(config).eval()
    values = {k:v.detach().contiguous() for k,v in model.state_dict().items() if k != 'encoder.embed_tokens.weight'}
    values['shared.weight'] = model.encoder.embed_tokens.weight.detach().contiguous()
    names = sorted(values)
    index = {}
    for part in [1, 2]:
        selected = names[:len(names)//2] if part == 1 else names[len(names)//2:]
        filename = f'model-0000{part}-of-00002.safetensors'
        save_file({k:values[k] for k in selected}, str(directory/filename), metadata={'format':'pt'})
        index.update({k:filename for k in selected})
    write('model.safetensors.index.json', dict(weight_map=index))
    write('text-config.json', config.to_dict())
    prompts = ['hello world', '你好，世界。', '\u3000Mixed CASE & <b>text</b>\u00a0', '<extra_id_0> hello <extra_id_99>',
        'hello</s>', '</s>', '<unk> <pad>', '<extra_id_1><extra_id_2>', 'line\n\ttwo', '🙂 café', '', '  ', 'word '*350]
    for i, prompt in enumerate(prompts):
        request = write(f't5-{i}.json', dict(operation='encode', inputs=[dict(prompt=prompt)], max_tokens=256))
        target = directory/f't5-{i}.f32'
        record = run('text', [directory/'model.safetensors.index.json', directory/'tokenizer_config.json', request,
            target, '2', '--pixart', directory/'spiece.model', '--fixture'])
        tokens = tokenizer(prompt.strip(), max_length=256, truncation=True, add_special_tokens=True)['input_ids']
        check(record['items'][0]['tokens'] == tokens, 'Original PixArt tokenizer IDs: '+repr(prompt[:30]))
        with torch.no_grad():
            expected = model(input_ids=torch.tensor([tokens]), attention_mask=torch.ones(1,len(tokens))).last_hidden_state.numpy()
        actual = np.fromfile(target, dtype=np.float32).reshape(expected.shape)
        error = float(np.max(np.abs(actual-expected)))
        check(error < 3e-5, 'Mapped original T5 CPU graph matches original small HF forward')
        check(record['model_loads'] == record['model_unloads'], 'Mapped T5 model unloads')
        cases.append(dict(kind='random_small_t5', tokens=len(tokens), max_error=error))
    # Import the pinned publisher class unchanged, without package __init__ side effects.
    upstream = ROOT/'build/native-src/ltx-video'
    for name, suffix in [('ltx_video','ltx_video'), ('ltx_video.models','ltx_video/models'),
                         ('ltx_video.models.autoencoders','ltx_video/models/autoencoders')]:
        package = types.ModuleType(name)
        package.__path__ = [str(upstream/suffix)]
        sys.modules[name] = package
    module = importlib.import_module('ltx_video.models.autoencoders.latent_upsampler')
    torch.manual_seed(817)
    upsampler = module.LatentUpsampler(in_channels=128, mid_channels=32, num_blocks_per_stage=4, dims=3).eval()
    weights = directory/'ltx098-upscaler.onnx.data'
    save_file({k:v.detach().contiguous() for k,v in upsampler.state_dict().items()}, str(weights))
    with weights.open('rb') as stream:
        header_bytes = int.from_bytes(stream.read(8), 'little')
        header = json.loads(stream.read(header_bytes))
    architecture = graph(header, header_bytes=header_bytes)
    (directory/'ltx098-upscaler.onnx').write_bytes(architecture.SerializeToString())
    statistics = np.stack([np.linspace(-.4,.6,128,dtype=np.float32), np.linspace(.3,1.4,128,dtype=np.float32)])
    statistics.tofile(directory/'stage-00.onnx.data')
    for i, shape in enumerate([(1,128,2,2,3), (1,128,2,3,2), (1,128,3,2,2)]):
        low = torch.randn(shape)*.7
        mean = torch.from_numpy(statistics[0]).view(1,-1,1,1,1)
        std = torch.from_numpy(statistics[1]).view(1,-1,1,1,1)
        with torch.no_grad():
            high = (upsampler(low*std+mean)-mean)/std
            hs, hm = torch.std_mean(high, dim=(2,3,4), keepdim=True)
            rs, rm = torch.std_mean(low, dim=(2,3,4), keepdim=True)
            expected = ((high-hm)/hs*rs+rm).numpy()
        source = directory/f'low-{i}.f32'
        low.numpy().tofile(source)
        request = write(f'up-{i}.json', dict(operation='upsample', latent_shape=list(shape), latents=str(source), threads=2))
        target = directory/f'up-{i}.f32'
        record = run('vae', [directory, request, target, '--fixture'])
        actual = np.fromfile(target,dtype=np.float32).reshape(expected.shape)
        error = float(np.max(np.abs(actual-expected)))
        check(error < 2e-4, '72-tensor ONNX upscaler and AdaIN match unchanged publisher class')
        check(record['session_loads'] == record['session_unloads'] == record['graph_runs'] == record['max_live_sessions'] == 1, 'Sequential upscaler session released')
        check(record['adain'] and record['fixture'], 'Explicit program fixture identity')
        cases.append(dict(kind='random_small_upscaler', shape=shape, max_error=error))
        # The application flag cannot silently accept the synthetic file as official weights.
        run('vae', [directory, request, directory/f'rejected-{i}.f32'], success=False)
    # Real tensor utility: refinement re-noising/layout and final bilinear video resize.
    seed=41
    shape=(1,128,2,4,4)
    high=np.linspace(-1,1,int(np.prod(shape)),dtype=np.float32).reshape(shape)
    high.tofile(directory/'high.f32')
    request=write('refine.json',dict(operation='refine_noise',width=128,height=128,frames=9,fps=24,seed=seed,
        input=str(directory/'high.f32'),latents=str(directory/'refine.f32'),noise=str(directory/'decode-noise.f32')))
    record=run('tensors',[request])
    check(record['timestep']==.9094 and not record['matches_pytorch_seed'], 'Explicit refinement noise/RNG contract')
    check((directory/'refine.f32').stat().st_size==high.size*4==(directory/'decode-noise.f32').stat().st_size,'Complete refinement bridge extent')
    frames=torch.linspace(-2,2,3*9*192*256).reshape(1,3,9,192,256)
    frames.numpy().tofile(directory/'decoded.f32')
    request=write('frames.json',dict(operation='frames',width=160,height=128,frames=9,fps=24,input_width=256,input_height=192,
        input=str(directory/'decoded.f32'),output=str(directory/'frames.rgb')))
    run('tensors',[request])
    resized=torch.nn.functional.interpolate(frames.clamp(-1,1).permute(0,2,1,3,4).reshape(9,3,192,256),size=(128,160),mode='bilinear',align_corners=False)
    expected=(resized.clamp(-1,1)*.5+.5).mul(255).to(torch.uint8).permute(0,2,3,1).numpy()
    actual=np.frombuffer((directory/'frames.rgb').read_bytes()[28:],dtype=np.uint8).reshape(expected.shape)
    check(np.max(np.abs(actual.astype(int)-expected.astype(int)))<=1,'Native bilinear resize matches Torch align_corners=False to one RGB code')
    # Unsupported paths/cancellation/finiteness fail without a partial result.
    request=write('cancel.json',dict(operation='upsample',latent_shape=[1,128,2,2,3],latents=str(directory/'low-0.f32'),threads=2,cancel_file=str(directory/'cancel.flag')))
    (directory/'cancel.flag').write_bytes(b'cancel')
    run('vae',[directory,request,directory/'cancelled.f32','--fixture'],success=False)
    check(not (directory/'cancelled.f32').exists(),'Cancellation publishes no partial upscale')
    scheduler_module=importlib.import_module('ltx_video.schedulers.rf')
    executable=ROOT/'build/ltx098-app-host/sample/bin/lma_ltx098_multiscale_contract.exe'
    native=json.loads(subprocess.check_output([str(executable)],timeout=20))
    for pass_record in native['passes']:
        scheduler=scheduler_module.RectifiedFlowScheduler()
        expected_times=[.9094,.725,.4219] if pass_record['second'] else [1.,.9937,.9875,.9812,.975,.9094,.725]
        scheduler.set_timesteps(timesteps=expected_times)
        check(np.allclose(pass_record['schedule'],expected_times,rtol=0,atol=3e-8),'Exact publisher YAML first/second schedule')
        sample=torch.tensor([-.7,.1,.6,1.2]);velocity=torch.tensor([.3,-.6,.1,.8])
        for i,timestep in enumerate(scheduler.timesteps):
            sample=scheduler.step(velocity,timestep,sample,return_dict=False)[0]
            check(np.max(np.abs(sample.numpy()-np.asarray(pass_record['steps'][i],dtype=np.float32)))<2e-7,'Production RF update matches unchanged publisher scheduler')
    current(before)
    report=dict(schema='lma.ltx098-official-program-tests/1',passed=True,assertions=count,cases=cases,
        fixture_neural_graphs_only=True,complete_trained_model_runs=0,complete_model_downloads=0,complete_model_copies=0,
        model_inference=False,physicalAndroid=False,qualityAccepted=False,virtualization_used=False,input_fingerprint=before,
        python_versions=dict(torch=torch.__version__,onnxruntime=ort.__version__),source_identity=lock(),native_build=build,
        capture=directory.relative_to(ROOT).as_posix())
    (OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,assertions=count,complete_trained_model_runs=0,cases=len(cases))))


if __name__=='__main__':
    main()
