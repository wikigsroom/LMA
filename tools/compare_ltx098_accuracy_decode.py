"""Decode a bound native precision trajectory with the unchanged trained VAE.

This explicit offline developer experiment retains the original full-chain
gates. Captured native T5/sampling outputs are checked before stage bridging;
no reference tensor is supplied to a native generation stage.
"""
import argparse
import json
import struct
import subprocess
import time
import uuid
from pathlib import Path

from compare_ltx098_accuracy_sampling import candidate_details, compare as review_sampling, inputs as sampling_inputs
from evidence import current, fingerprint
from fetch_ltx098_text import sha
from ltx098_pipeline import ASSETS, DECODER, TENSORS, Runner, write
from test_ltx098_text import execute

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**sampling_inputs(), **fingerprint('tools/compare_ltx098_accuracy_decode.py')}


def run(variant, reference, case_index, capture=None):
    before = inputs(); reference = reference.resolve()
    if not reference.is_relative_to(ROOT / 'build'): raise ValueError('Reference must stay below build/')
    base = ROOT / 'build/ltx098-text-accuracy-sampling'
    sampled_path = base / (variant + '-case-' + str(case_index) + '-results.json')
    sampled = json.loads(sampled_path.read_text(encoding='utf-8'))
    trajectory = ROOT / sampled['capture_directory']
    review_sampling(variant, reference, case_index, trajectory)
    sampled = json.loads(sampled_path.read_text(encoding='utf-8'))
    if sampled['input_fingerprint'] != sampling_inputs(): raise ValueError('Wrong sampling provenance')
    baseline = json.loads((ROOT / 'verification/development/ltx098-pipeline.json').read_text(encoding='utf-8'))
    current(baseline['input_fingerprint'])
    oracle = json.loads((reference / 'references.json').read_text(encoding='utf-8'))
    if oracle != baseline['original_oracle']: raise ValueError('Changed original reference')
    original = oracle['cases'][case_index]
    for name, identity in original['files'].items():
        path = reference / original['name'] / name
        if path.stat().st_size != identity['bytes'] or sha(path) != identity['sha256']:
            raise ValueError('Changed original tensor/media: ' + name)
    runner = Runner()  # Verify all external trained assets, native receipts and host media tools.
    if runner.assets != baseline['jobs'][case_index]['assets']: raise ValueError('Changed trained components')
    import numpy as np
    request = baseline['jobs'][case_index]['request']
    shape = {key: request[key] for key in ['width', 'height', 'frames', 'fps']}
    latent_shape = [1, 128, (shape['frames'] - 1) // 8 + 1, shape['height'] // 32, shape['width'] // 32]
    binding = dict(variant=variant, case=case_index, request=request,
                   candidate_sha256=sampled['candidate_sha256'],
                   candidate_caption_sha256=sampled['candidate_caption_sha256'],
                   sampling_latents_sha256=sha(trajectory / 'latents.f32'),
                   original_reference_sha256=sha(reference / 'references.json'))
    stage_records = []
    if capture is None:
        capture = ROOT / 'build/ltx098-text-accuracy-video' / ('run-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        capture.mkdir(parents=True, exist_ok=False)

        def invoke(name, executable, args, data):
            path = capture / (name + '.json'); write(path, data)
            print('Native accuracy decode stage', name, flush=True)
            process, seconds, resources = execute([str(executable)] + [str(x) for x in args(path)], timeout=1800, observe=True)
            (capture / (name + '.log')).write_bytes(process.stdout + process.stderr)
            if process.returncode: raise RuntimeError('Inspect captured native ' + name + '.log')
            if not resources['observed'] or not resources['samples']: raise ValueError('Missing child observations')
            item = json.loads(process.stdout.strip().splitlines()[-1])
            if item.get('ok') is False: raise ValueError('Native stage rejected request')
            stage_records.append(dict(stage=name, native=item, seconds=seconds, resources=resources,
                                      native_binary_sha256=sha(executable)))
            return item

        initial = capture / 'initial-tokens.f32'; noise = capture / 'decode-noise.f32'
        invoke('noise', TENSORS, lambda path: [path],
               dict(operation='noise', **shape, seed=request['seed'], latents=str(initial), noise=str(noise)))
        restored = capture / 'denoised-ncthw.f32'
        invoke('unpatchify', TENSORS, lambda path: [path],
               dict(operation='unpatchify', **shape, input=str(trajectory / 'latents.f32'), output=str(restored)))
        decoded = capture / 'decoded-ncthw.f32'
        invoke('vae', DECODER, lambda path: [ASSETS, path, decoded],
               dict(operation='decode', latent_shape=latent_shape, latents=str(restored), noise=str(noise),
                    timestep=.05, noise_scale=.025, threads=4))
        frames = capture / 'frames.lma'
        invoke('frames', TENSORS, lambda path: [path],
               dict(operation='frames', **shape, input=str(decoded), output=str(frames)))
        video = capture / 'video.mp4'
        process = subprocess.run([str(runner.ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
                                  '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size',
                                  f"{shape['width']}x{shape['height']}", '-framerate', str(shape['fps']), '-i', 'pipe:0',
                                  '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
                                  '-movflags', '+faststart', str(video)],
                                 input=frames.read_bytes()[28:], capture_output=True, timeout=120)
        (capture / 'media.log').write_bytes(process.stdout + process.stderr)
        if process.returncode: raise RuntimeError('Host media conversion failed')
        names = ['initial-tokens.f32', 'decode-noise.f32', 'denoised-ncthw.f32', 'decoded-ncthw.f32', 'frames.lma', 'video.mp4']
        names += [name + suffix for name in ['noise', 'unpatchify', 'vae', 'frames'] for suffix in ['.json', '.log']]
        names += ['media.log']
        raw = dict(binding=binding, stages=stage_records, files={name: dict(bytes=(capture / name).stat().st_size,
                    sha256=sha(capture / name)) for name in names}, input_fingerprint=before)
        write(capture / 'run.json', raw)
        reused = False
    else:
        capture = capture.resolve()
        if not capture.is_relative_to(ROOT / 'build'): raise ValueError('Capture must stay below build/')
        raw = json.loads((capture / 'run.json').read_text(encoding='utf-8'))
        current(raw['input_fingerprint'])
        if raw['input_fingerprint'] != before or raw['binding'] != binding: raise ValueError('Changed decode binding')
        stage_records = raw['stages']; reused = True
    for name, identity in raw['files'].items():
        path = capture / name
        if path.parent != capture or path.stat().st_size != identity['bytes'] or sha(path) != identity['sha256']:
            raise ValueError('Changed native decode capture')
    if [s['stage'] for s in stage_records] != ['noise', 'unpatchify', 'vae', 'frames']: raise ValueError('Incomplete decode stages')
    for stage in stage_records:
        if stage['native_binary_sha256'] != sha(DECODER if stage['stage'] == 'vae' else TENSORS):
            raise ValueError('Changed native decoder/tensor executable')
    for name in ['initial-tokens.f32', 'decode-noise.f32']:
        if raw['files'][name] != baseline['jobs'][case_index]['files'][name]: raise ValueError('Different native seeded noise')
    vae = stage_records[2]['native']
    if (vae['output_shape'] != [1, 3, shape['frames'], shape['height'], shape['width']] or
        vae['graph_runs'] != 9 or vae['session_loads'] != 9 or vae['session_unloads'] != 9 or vae['max_live_sessions'] != 1):
        raise ValueError('Incomplete trained VAE lifecycle')
    data = (capture / 'frames.lma').read_bytes()
    if data[:8] != b'LMAFRM1\0' or struct.unpack('<5I', data[8:28]) != (shape['width'], shape['height'], shape['frames'], shape['fps'], 3):
        raise ValueError('Wrong native frame container')
    rgb = np.frombuffer(data, dtype=np.uint8, offset=28).reshape(shape['frames'], shape['height'], shape['width'], 3)
    probe = subprocess.run([str(runner.ffprobe), '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                            'stream=codec_name,width,height,nb_read_frames,avg_frame_rate,duration:format=duration',
                            '-of', 'json', str(capture / 'video.mp4')], capture_output=True, check=True, timeout=120)
    metadata = json.loads(probe.stdout); stream = metadata['streams'][0]
    if (stream['codec_name'] != 'h264' or int(stream['nb_read_frames']) != shape['frames'] or
        stream['width'] != shape['width'] or stream['height'] != shape['height'] or stream['avg_frame_rate'] != str(shape['fps']) + '/1'):
        raise ValueError('Wrong host video metadata')
    candidate_file, _ = candidate_details(variant)
    if sha(candidate_file) != binding['candidate_sha256']: raise ValueError('Changed native text candidate record')
    candidate = json.loads(candidate_file.read_text(encoding='utf-8'))
    caption = ROOT / candidate['output_directory'] / ('case-' + str(case_index)) / 'caption.f32'
    if sha(caption) != binding['candidate_caption_sha256']: raise ValueError('Changed native caption')
    gates = baseline['gates']; metrics = []; failures = []
    for name, native, expected in [('caption.f32', caption, 'caption.f32'),
        ('denoised-tokens.f32', trajectory / 'latents.f32', 'sampling-step-7.f32'),
        ('denoised-ncthw.f32', capture / 'denoised-ncthw.f32', 'denoised-ncthw.f32'),
        ('decoded-ncthw.f32', capture / 'decoded-ncthw.f32', 'decoded-ncthw.f32')]:
        left = np.fromfile(native, dtype='<f4').astype(np.float64)
        right = np.fromfile(reference / original['name'] / expected, dtype='<f4').astype(np.float64)
        if left.shape != right.shape or not left.size or not np.isfinite(left).all() or not np.isfinite(right).all():
            raise ValueError('Invalid full-chain tensor')
        delta = left - right
        metric = dict(file=name, max_abs=float(abs(delta).max()), relative_rmse=float(np.linalg.norm(delta) / np.linalg.norm(right)),
                      cosine=float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right))))
        metric['passed'] = (metric['max_abs'] <= gates['full_chain_max_absolute_error'] and
                            metric['relative_rmse'] <= gates['full_chain_max_relative_rmse'] and metric['cosine'] >= gates['full_chain_min_cosine'])
        if not metric['passed']: failures.append(name)
        metrics.append(metric)
    expected_rgb = np.fromfile(reference / original['name'] / 'rgb.bin', dtype=np.uint8).reshape(rgb.shape)
    error = abs(rgb.astype(np.float64) - expected_rgb.astype(np.float64))
    rgb_metric = dict(max_error=float(error.max()), mean_error=float(error.mean()))
    rgb_metric['passed'] = rgb_metric['max_error'] <= gates['rgb_max_byte_error'] and rgb_metric['mean_error'] <= gates['rgb_mean_byte_error']
    if not rgb_metric['passed']: failures.append('rgb')
    current(before)
    report = dict(schema='lma.ltx098-accuracy-decode/1', binding=binding, metrics=metrics, rgb=rgb_metric, failures=failures,
                  full_chain_numeric_gate_passed=not failures, gates=gates, stages=stage_records, files=raw['files'],
                  assets=runner.assets, media=dict(runner.media, probe=metadata), capture_directory=capture.relative_to(ROOT).as_posix(),
                  capture_reused=reused, native_children_executed_this_invocation=0 if reused else 4,
                  captured_native_decode_children=4, t5_sampling_bound_to_native_captures=True,
                  reference_tensors_used_as_native_inputs=False, full_pipeline_accepted=False, video_quality_accepted=False,
                  physical_android=False, packaged_in_apk=False, engine_registered=False, acceptance_gates_changed=False,
                  input_fingerprint=before)
    base = ROOT / 'build/ltx098-text-accuracy-video'
    write(capture / 'results.json', report)
    write(base / (variant + '-case-' + str(case_index) + '-results.json'), report)
    print(json.dumps(dict(variant=variant, case=case_index, failures=failures, metrics=metrics, rgb=rgb_metric)), flush=True)
    return 0 if not failures else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['norm', 'activation', 'order', 'staging', 'f32'], required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--case', type=int, choices=[0, 1], default=0)
    parser.add_argument('--capture', type=Path, help='Revalidate an existing native decode capture')
    args = parser.parse_args()
    raise SystemExit(run(args.variant, args.reference, args.case, args.capture))
