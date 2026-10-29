"""Explicit offline developer-host execution of the real old-LTX components.

Single scale, Q5_K_M Google T5 variant, fixed eight-step linear-quadratic RF.
Not the publisher's multiscale/PixArt/prompt-enhancement default. No download,
App registration, phone execution or quality acceptance is implied.
"""
import argparse, importlib.metadata, json, shutil, struct, subprocess, time
from pathlib import Path
import numpy as np
from evidence import current, fingerprint
from ltx098_vae import sha
from test_ltx098_text import execute

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'build/ltx098-vae-assets'
LOCK = ROOT / 'third_party/ltx098-pipeline-source-lock.json'
ENCODER = ROOT / 'build/ltx098-text-host/bin/lma_ltx098_text_cli.exe'
SAMPLER = ROOT / 'build/ltx098-host-vulkan/lma_ltx098_sample.exe'
DECODER = ROOT / 'build/ltx098-vae-host/bin/lma_ltx098_vae_cli.exe'
TENSORS = ROOT / 'build/ltx098-tensors-host/bin/lma_ltx098_tensors.exe'
T5 = ROOT / 'build/ltx098-text-assets/originals/t5-v1_1-xxl-encoder-Q5_K_M.gguf'
TOKENIZER = ROOT / 'build/ltx098-text-assets/oracle/tokenizer_config.json'
DIT = ROOT / 'build/ltx098-trained/converted/ltx098-dit.gguf'


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False) + '\n', encoding='utf-8')


def inputs():
    return fingerprint('research/ltx098_pipeline', 'research/ltx098_text', 'research/ltx098',
                       'research/ltx098_vae', 'research/soulx_ort', 'research/soulx/dsp.hpp',
                       'native/moss_nano/onnx_external.hpp', 'tools/ltx098_pipeline.py',
                       'tools/build_ltx098_tensors.py', 'tools/ltx098_vae.py', 'tools/ltx098_assets.py',
                       'tools/ltx098_fixture.py', 'tools/build_ltx098.py', 'tools/build_ltx098_text.py',
                       'tools/build_ltx098_vae.py', 'tools/fetch_ltx098_text.py', 'tools/export_ltx098.py',
                       'tools/test_ltx098_text.py', 'tools/evidence.py',
                       'third_party/ltx098-pipeline-source-lock.json', 'third_party/ltx098-source-lock.json',
                       'third_party/ltx098-trained-assets.json', 'third_party/ltx098-text-source-lock.json',
                       'third_party/ltx098-vae-source-lock.json', 'third_party/soulx-acoustic-source-lock.json')


def validate(request):
    if type(request) != dict or set(request) - {'prompt', 'seed', 'width', 'height', 'frames', 'fps', 'cancel_file'}:
        raise ValueError('Unsupported pipeline request key')
    if not isinstance(request.get('prompt'), str) or not request['prompt'].strip() or len(request['prompt'].encode('utf-8')) > 65536:
        raise ValueError('Expected a nonempty UTF-8 prompt within 64 KiB')
    for key, low, high in [('seed', 0, 2147483647), ('width', 64, 256), ('height', 64, 256), ('frames', 9, 33), ('fps', 1, 60)]:
        if type(request.get(key)) != int or not low <= request[key] <= high:
            raise ValueError('Pipeline integer outside bounds: ' + key)
    if request['width'] % 32 or request['height'] % 32 or (request['frames'] - 1) % 8:
        raise ValueError('Unsupported old-LTX latent grid')
    if 'cancel_file' in request and (not isinstance(request['cancel_file'], str) or not request['cancel_file']):
        raise ValueError('Invalid local cancellation path')


class Runner:
    def __init__(self):
        self.before = inputs()
        if importlib.metadata.version('numpy') != '2.4.2': raise RuntimeError('Changed pinned NumPy')
        self.lock = json.loads(LOCK.read_text(encoding='utf-8'))
        self.assets = []
        for exe, name, field in [(TENSORS, 'ltx098-tensors-host', 'executable_sha256'),
                                 (ENCODER, 'ltx098-text-host', 'executable_sha256'),
                                 (SAMPLER, 'ltx098-host-vulkan', 'sampler_binary_sha256'),
                                 (DECODER, 'ltx098-vae-host', 'executable_sha256')]:
            record = json.loads((ROOT / 'build' / name / 'receipt.json').read_text(encoding='utf-8'))
            current(record['input_fingerprint'])
            if sha(exe) != record[field]: raise ValueError('Changed native component: ' + name)
        text = json.loads((ROOT / 'third_party/ltx098-text-source-lock.json').read_text(encoding='utf-8'))
        conversion = json.loads((DIT.parent / 'conversion.json').read_text(encoding='utf-8'))
        current(conversion['input_fingerprint'])
        if conversion['bytes'] != 3849516416 or conversion['sha256'] != 'ef29c886b36f8a1dbc6693002256049407e512da7a61bf2cc750f1d4d2277ebf':
            raise ValueError('Different pinned converted DiT weights')
        if conversion['synthetic_parameters'] or conversion['transformer_tensors'] != 715 or conversion['transformer_parameters'] != 1923385472:
            raise ValueError('Expected complete trained old-LTX DiT')
        vae = json.loads((ASSETS / 'ltx098-vae.json').read_text(encoding='utf-8')); current(vae['input_fingerprint'])
        verified_vae = json.loads((ROOT / 'verification/development/ltx098-vae.json').read_text(encoding='utf-8'))
        if vae['assets'] != verified_vae['assets']: raise ValueError('Different trained VAE assets')
        expected = [(T5, text['model']), (DIT, conversion)]
        expected += [(TOKENIZER, next(x for x in text['oracle_assets'] if x['file'] == 'tokenizer_config.json'))]
        expected += [(ASSETS / x['file'], x) for x in vae['assets']]
        print('Verify all external trained components; no download', flush=True)
        for path, item in expected:
            if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
                raise ValueError('Missing/changed external pipeline asset: ' + path.name)
            self.assets.append(dict(file=path.name, bytes=item['bytes'], sha256=item['sha256']))
        found = shutil.which('ffmpeg')
        if not found: raise RuntimeError('Native host FFmpeg required for developer media validation only')
        self.ffmpeg = Path(found); self.ffprobe = self.ffmpeg.with_name('ffprobe.exe')
        if not self.ffprobe.is_file(): raise RuntimeError('Missing matching native host ffprobe')
        self.media = dict(backend='host_ffmpeg_libx264_not_android_mediacodec',
                          ffmpeg_sha256=sha(self.ffmpeg), ffprobe_sha256=sha(self.ffprobe))
        current(self.before)

    def generate(self, request, directory):
        validate(request); current(self.before)
        directory = directory.resolve()
        if not directory.is_relative_to((ROOT / 'build').resolve()): raise ValueError('Developer output must stay below project build/')
        directory.mkdir(parents=True, exist_ok=False)
        cancel = Path(request['cancel_file']) if 'cancel_file' in request else None
        def cancelled():
            if cancel and cancel.exists(): raise RuntimeError('Pipeline cancelled')
        stage_records = []; total_start = time.perf_counter()
        shape = {key: request[key] for key in ('width', 'height', 'frames', 'fps')}
        optional = dict(cancel_file=str(cancel)) if cancel else {}
        latent_shape = [1, 128, (shape['frames'] - 1) // 8 + 1, shape['height'] // 32, shape['width'] // 32]
        count = int(np.prod(latent_shape)); final_paths = [directory / 'frames.lma', directory / 'video.mp4']

        def invoke(name, exe, args, data, output=None):
            cancelled(); path = directory / (name + '.json'); write(path, data)
            command = [str(exe)] + [str(x) for x in args(path)]
            print('Native pipeline stage', name, flush=True)
            process, seconds, resources = execute(command, timeout=1800, observe=True)
            (directory / (name + '.log')).write_bytes(process.stdout + process.stderr)
            if process.returncode:
                raise RuntimeError('Native pipeline stage failed; inspect ' + str((directory / (name + '.log')).relative_to(ROOT)))
            item = json.loads(process.stdout.strip().splitlines()[-1])
            if item.get('ok') is False or output and not output.is_file(): raise RuntimeError('Incomplete native pipeline stage: ' + name)
            if not resources['observed'] or not resources['samples']: raise RuntimeError('Missing actual child resource observations')
            device = [line.strip() for line in process.stderr.decode('utf-8', errors='replace').splitlines() if 'ggml_vulkan:' in line]
            stage_records.append(dict(stage=name, seconds=seconds, resources=resources, native=item, vulkan_device_identity=device))
            cancelled(); return item

        try:
            initial = directory / 'initial-tokens.f32'; noise = directory / 'decode-noise.f32'
            invoke('noise', TENSORS, lambda path: [path], dict(operation='noise', **shape, seed=request['seed'], latents=str(initial), noise=str(noise), **optional), initial)
            embedded = directory / 'caption.f32'
            encoded = invoke('text', ENCODER, lambda path: [T5, TOKENIZER, path, embedded, 4],
                             dict(operation='encode', inputs=[dict(prompt=request['prompt'])], max_tokens=256, **optional), embedded)
            if encoded.get('fixture') or not encoded['model_inference'] or encoded['layers'] != 24 or len(encoded['items']) != 1:
                raise ValueError('Expected complete trained T5 execution')
            caption = encoded['items'][0]; tokens = len(caption['tokens'])
            if not 1 <= tokens <= 256 or caption['mask'] != [1] * tokens or caption['offset_bytes'] != 0 or caption['shape'] != [1, tokens, 4096] or caption['bytes'] != tokens * 4096 * 4 or embedded.stat().st_size != caption['bytes']:
                raise ValueError('T5 embedding shape/byte mismatch')
            context = np.fromfile(embedded, dtype='<f4')
            latents = np.fromfile(initial, dtype='<f4')
            if not np.isfinite(context).all() or latents.size != count: raise ValueError('Invalid stage bridge tensor')
            denoised = directory / 'denoised-tokens.f32'
            sampled = invoke('sampling', SAMPLER, lambda path: [DIT, path, denoised, 'vulkan', 4],
                             dict(operation='sample', **shape, text_tokens=tokens, latents=latents.tolist(), context=context.tolist(),
                                  text_mask=caption['mask'], **optional), denoised)
            if sampled['fixture'] or not sampled['model_executed'] or sampled['backend'] != 'vulkan' or sampled['layers'] != 28 or sampled['steps'] != 8 or sampled['parameters'] != 1923385472 or sampled['layout'] != 'batch_tokens_channels' or denoised.stat().st_size != count * 4:
                raise ValueError('Incomplete trained DiT trajectory')
            restored = directory / 'denoised-ncthw.f32'
            invoke('unpatchify', TENSORS, lambda path: [path], dict(operation='unpatchify', **shape, input=str(denoised), output=str(restored), **optional), restored)
            decoded = directory / 'decoded-ncthw.f32'
            record = invoke('vae', DECODER, lambda path: [ASSETS, path, decoded],
                            dict(operation='decode', latent_shape=latent_shape, latents=str(restored), noise=str(noise), timestep=.05, noise_scale=.025, threads=4, **optional), decoded)
            if record['output_shape'] != [1, 3, shape['frames'], shape['height'], shape['width']] or record['graph_runs'] != 9 or record['session_loads'] != record['session_unloads'] or record['max_live_sessions'] != 1:
                raise ValueError('Decoder stage lifetime mismatch')
            frames = directory / 'frames.lma'
            packed = invoke('frames', TENSORS, lambda path: [path], dict(operation='frames', **shape, input=str(decoded), output=str(frames), **optional), frames)
            raw = frames.read_bytes()
            if raw[:8] != b'LMAFRM1\0' or struct.unpack('<5I', raw[8:28]) != (shape['width'], shape['height'], shape['frames'], shape['fps'], 3):
                raise ValueError('Wrong Android frame container header')
            rgb = np.frombuffer(raw, dtype=np.uint8, offset=28).reshape(shape['frames'], shape['height'], shape['width'], 3)
            video = directory / 'video.mp4'; cancelled()
            result = subprocess.run([str(self.ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                                     '-video_size', f"{shape['width']}x{shape['height']}", '-framerate', str(shape['fps']), '-i', 'pipe:0', '-an',
                                     '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)],
                                    input=raw[28:], capture_output=True, timeout=120)
            (directory / 'media.log').write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError('Host MP4 conversion failed')
            cancelled()
            probe = subprocess.run([str(self.ffprobe), '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                                    'stream=codec_name,width,height,nb_read_frames,avg_frame_rate,duration:format=duration', '-of', 'json', str(video)], capture_output=True, check=True, timeout=120)
            metadata = json.loads(probe.stdout); stream = metadata['streams'][0]
            if stream['codec_name'] != 'h264' or int(stream['nb_read_frames']) != shape['frames'] or stream['width'] != shape['width'] or stream['height'] != shape['height'] or stream['avg_frame_rate'] != str(shape['fps']) + '/1':
                raise ValueError('Host MP4 validation failed')
            cancelled(); current(self.before)
            files = {name: dict(bytes=(directory / name).stat().st_size, sha256=sha(directory / name)) for name in
                     ['initial-tokens.f32', 'decode-noise.f32', 'caption.f32', 'denoised-tokens.f32', 'denoised-ncthw.f32', 'decoded-ncthw.f32', 'frames.lma', 'video.mp4']}
            result = dict(schema='lma.ltx098-host-pipeline/1', request={k: v for k, v in request.items() if k != 'cancel_file'}, stages=stage_records, files=files,
                          text_tokens=tokens, prompt_truncated=caption['truncated'], shape=shape,
                          seconds=time.perf_counter() - total_start, assets=self.assets, media=dict(self.media, probe=metadata),
                          rgb_statistics=dict(mean=float(rgb.mean()), std=float(rgb.std()), frame_mad=[float(np.abs(rgb[i].astype(float) - rgb[i-1]).mean()) for i in range(1, len(rgb))]),
                          actual_prompt_conditioning=True, full_trained_host_text_to_frames=True, host_mp4_generated=True,
                          official_pixart_weight_identity_compared=False, official_multiscale_default_reproduced=False,
                          video_quality_accepted=False, engine_registered=False, packaged_in_apk=False, physical_android=False,
                          remote_inference=False, virtualization_used=False, input_fingerprint=self.before)
            write(directory / 'pipeline.json', result); return result
        except BaseException:
            for path in final_paths: path.unlink(missing_ok=True)
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt', required=True); parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--width', type=int, default=256); parser.add_argument('--height', type=int, default=256)
    parser.add_argument('--frames', type=int, default=33); parser.add_argument('--fps', type=int, default=24)
    parser.add_argument('--output', required=True, type=Path); args = parser.parse_args()
    record = Runner().generate(dict(prompt=args.prompt, seed=args.seed, width=args.width, height=args.height, frames=args.frames, fps=args.fps), args.output)
    print(json.dumps({k: record[k] for k in ['seconds', 'shape', 'text_tokens', 'host_mp4_generated', 'physical_android']}), flush=True)
