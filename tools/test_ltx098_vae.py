"""Native CPU old-LTX trained decoder parity, lifecycle and failure checks.

Requires explicit prior export/references commands; never downloads assets.
This validates decoding, not text-to-video quality or Android execution.
"""
import copy, importlib.metadata, json, math, os, shutil, subprocess, sys, threading, time
from pathlib import Path
import numpy as np
from evidence import fingerprint, current
from ltx098_vae import inputs as export_inputs, sha, OUT as ASSETS
from build_ltx098_vae import inputs as build_inputs
from test_ltx098_text import execute

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/ltx098-vae-tests'
EXE = ROOT / 'build/ltx098-vae-host/bin/lma_ltx098_vae_cli.exe'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False) + '\n', encoding='utf-8')


def run():
    OUT.mkdir(exist_ok=True); (OUT / 'results.json').unlink(missing_ok=True)
    before = {**export_inputs(), **build_inputs(), **fingerprint('tools/test_ltx098_vae.py',
              'tools/test_ltx098_text.py', 'tools/fetch_ltx098_text.py', 'tools/build_ltx098_text.py')}
    build = json.loads((ROOT / 'build/ltx098-vae-host/receipt.json').read_text(encoding='utf-8'))
    current(build['input_fingerprint']); assert build['input_fingerprint'] == build_inputs()
    assert sha(EXE) == build['executable_sha256']
    manifest = json.loads((ASSETS / 'ltx098-vae.json').read_text(encoding='utf-8'))
    reference_dir = OUT / 'references'
    oracle = json.loads((reference_dir / 'references.json').read_text(encoding='utf-8'))
    for record in (manifest, oracle):
        current(record['input_fingerprint']); assert record['input_fingerprint'] == export_inputs()
    for item in manifest['assets']:
        path = ASSETS / item['file']
        assert path.parent == ASSETS and path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    for name, item in oracle['files'].items():
        path = reference_dir / name
        assert path.parent == reference_dir and path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    gates = json.loads((ROOT / 'third_party/ltx098-vae-source-lock.json').read_text(encoding='utf-8'))['gates']
    directory = OUT / 'native-results'
    if directory.exists():
        if directory.resolve().parent != OUT.resolve(): raise RuntimeError('Unsafe test cleanup target')
        shutil.rmtree(directory)
    directory.mkdir()
    checks = 0; children = 0; metrics = []; runs = []; guards = []

    def check(ok, message):
        nonlocal checks
        if not ok: raise AssertionError(message)
        checks += 1

    def request(case):
        return dict(operation='decode', latent_shape=case['latent_shape'],
                    latents=str(reference_dir / case['files']['latent']), noise=str(reference_dir / case['files']['noise']),
                    timestep=case['timestep'], noise_scale=case['noise_scale'], threads=4)

    def native(name, value, success=True, bundle=ASSETS, observe=False, raw=None, preserve=False):
        nonlocal children
        path = directory / (name + '.json'); target = directory / (name + '.f32')
        if raw is None: write(path, value)
        else: path.write_text(raw, encoding='utf-8')
        if preserve: target.write_bytes(b'existing-output')
        result, seconds, resource = execute([str(EXE), str(bundle), str(path), str(target)], timeout=900, observe=observe)
        children += 1
        (directory / (name + '.log')).write_bytes(result.stdout + result.stderr)
        check(bool(result.stdout.strip()), name + ': worker produced no protocol result')
        record = json.loads(result.stdout.strip().splitlines()[-1]); runs.append(dict(name=name, seconds=seconds, resources=resource, **record))
        check(record['ok'] == success and result.returncode == (0 if success else 1), name + ': unexpected worker result')
        check(record['session_loads'] == record['session_unloads'], name + ': session leak')
        check(record['max_live_sessions'] <= 1, name + ': overlapping VAE sessions')
        if success:
            check(record['graph_runs'] == record['session_loads'] == 9, 'Incomplete nine-stage decode')
            check(record['output_bytes'] == target.stat().st_size, 'Wrong output byte count')
        else:
            check(target.read_bytes() == b'existing-output' if preserve else not target.exists(), name + ': partial/overwritten output')
            guards.append(name)
        if observe: check(resource['observed'] and resource['samples'] > 0, 'Missing real child memory observations')
        return record, target

    def compare(name, actual, expected):
        a = np.fromfile(actual, dtype='<f4').astype(np.float64); b = np.fromfile(expected, dtype='<f4').astype(np.float64)
        check(a.shape == b.shape and a.size > 0 and np.isfinite(a).all() and np.isfinite(b).all(), name + ': invalid tensor')
        delta = a - b; absolute = float(np.max(np.abs(delta))); rmse = float(np.sqrt(np.mean(delta * delta)))
        relative = rmse / max(float(np.sqrt(np.mean(b * b))), 1e-12)
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        cosine = float(np.dot(a, b) / denom) if denom else float(np.array_equal(a, b))
        check(absolute <= gates['max_absolute_error'], name + ': absolute-error gate')
        check(relative <= gates['max_relative_rmse'], name + ': relative-RMSE gate')
        check(cosine >= gates['min_cosine'], name + ': cosine gate')
        metrics.append(dict(name=name, elements=a.size, max_absolute_error=absolute, rmse=rmse, relative_rmse=relative, cosine=cosine))

    for case in oracle['cases']:
        name = case['name']; value = request(case); trace = directory / (name + '-trace'); value['trace_dir'] = str(trace)
        print('Native trained VAE', name, flush=True)
        record, target = native(name, value, observe=True)
        check(record['output_shape'] == case['output_shape'], 'Wrong causal temporal/spatial output shape')
        compare(name + '-output', target, reference_dir / case['files']['output'])
        for i in range(9):
            kind = f'stage-{i:02d}' if i < 8 else 'output'
            compare(name + f'-stage-{i:02d}', trace / f'stage-{i:02d}.onnx.f32', reference_dir / case['files'][kind])
    case = oracle['cases'][0]; value = request(case)
    _, repeat = native('repeat-case-0', value)
    check(sha(repeat) == sha(directory / 'case-0.f32'), 'Repeated CPU decode changed output')

    base = request(case)
    invalid = [dict(base, operation='encode'), dict(base, unsupported=True), dict(base, latent_shape=[1, 64, 3, 2, 2]),
               dict(base, latent_shape=[1, 128, 0, 2, 2]), dict(base, latent_shape=[1, 128, 6, 2, 2]),
               dict(base, latent_shape=[1, 128, 3, 9, 2]), dict(base, latent_shape=[1, 128, 3, 2, 0]),
               dict(base, latent_shape=[1, 128, 3.0, 2, 2]), dict(base, threads=0), dict(base, threads=33),
               dict(base, timestep=-.01), dict(base, timestep=1.1), dict(base, noise_scale=-.1), dict(base, noise_scale=1.1),
               dict(base, noise='missing-local-tensor'), dict(base, cancel_file=''), dict(base, trace_dir=str(directory))]
    for i, bad in enumerate(invalid): native(f'guard-{i:02d}', bad, success=False)
    native('duplicate-key', base, success=False, raw=json.dumps(base)[:-1] + ',"threads":4}')
    native('nan-json', base, success=False, raw=json.dumps(dict(base, timestep=float('nan'))))
    native('preserve-output', base, success=False, preserve=True)
    flag = directory / 'pre-cancel.flag'; flag.touch()
    native('pre-cancel', dict(base, cancel_file=str(flag)), success=False)
    short = directory / 'short.f32'; short.write_bytes(b'\0' * 4)
    native('truncated-tensor', dict(base, latents=str(short)), success=False)
    nonfinite = directory / 'nan.f32'; values = np.zeros(math.prod(base['latent_shape']), dtype='<f4'); values[1] = np.nan; values.tofile(nonfinite)
    native('nonfinite-tensor', dict(base, noise=str(nonfinite)), success=False)
    fake = directory / 'wrong-bundle'; fake.mkdir()
    changed = copy.deepcopy(manifest); changed['source']['sha256'] = '0' * 64; write(fake / 'ltx098-vae.json', changed)
    native('wrong-checkpoint', base, success=False, bundle=fake)
    write(fake / 'ltx098-vae.json', manifest)
    native('missing-bundle-assets', base, success=False, bundle=fake)

    # Hardlink only immutable developer sidecars; copy graph metadata before
    # mutation so no original trained model bytes can be changed by a guard.
    sys.path.insert(0, str(ROOT / 'build/soulx-python'))
    import onnx
    check(importlib.metadata.version('onnx') == '1.20.1', 'Changed ONNX guard dependency')
    for item in manifest['assets']: os.link(ASSETS / item['file'], fake / item['file'])
    changed = copy.deepcopy(manifest); changed['assets'].append(changed['assets'][0])
    write(fake / 'ltx098-vae.json', changed)
    native('extra-asset', base, success=False, bundle=fake)
    changed = copy.deepcopy(manifest); changed['stages'][0]['file'] = '../stage-00.onnx'
    write(fake / 'ltx098-vae.json', changed)
    native('stage-path', base, success=False, bundle=fake)
    changed = copy.deepcopy(manifest); changed['assets'][0]['bytes'] += 1
    write(fake / 'ltx098-vae.json', changed)
    native('asset-size', base, success=False, bundle=fake)
    graph_path = fake / 'stage-00.onnx'; graph_path.unlink()
    for kind in ('external-traversal', 'external-out-of-range'):
        graph = onnx.load(str(ASSETS / 'stage-00.onnx'), load_external_data=False)
        tensor = graph.graph.initializer[0]
        for field in tensor.external_data:
            if kind == 'external-traversal' and field.key == 'location': field.value = '../stage-00.onnx.data'
            if kind == 'external-out-of-range' and field.key == 'offset': field.value = '1500000000'
        graph_path.write_bytes(graph.SerializeToString())
        changed = copy.deepcopy(manifest)
        for item in changed['assets']:
            if item['file'] == 'stage-00.onnx': item['bytes'] = graph_path.stat().st_size
        write(fake / 'ltx098-vae.json', changed)
        record, _ = native(kind, base, success=False, bundle=fake)
        check(record['session_loads'] == 0, 'Unsafe external data reached ORT session loading')

    # Interrupt a real ORT Run, not just the check immediately before Run.
    # A larger latent and one CPU thread keep the graph active long enough to
    # observe termination without depending on the small parity probes' speed.
    cancel_name = 'cancel-during-stage-1'; value = dict(base, threads=1)
    value['latent_shape'] = [1, 128, 5, 4, 4]
    generator = np.random.default_rng(98345)
    for key in ('latents', 'noise'):
        tensor_path = directory / (cancel_name + '-' + key + '.f32')
        generator.standard_normal(value['latent_shape']).astype('<f4').tofile(tensor_path)
        value[key] = str(tensor_path)
    flag = directory / (cancel_name + '.flag'); value['cancel_file'] = str(flag)
    path = directory / (cancel_name + '.json'); target = directory / (cancel_name + '.f32'); write(path, value)
    child = subprocess.Popen([str(EXE), str(ASSETS), str(path), str(target)], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = []; reached = threading.Event()
    def reader():
        for line in iter(child.stderr.readline, b''):
            lines.append(line)
            try: item = json.loads(line)
            except (ValueError, TypeError): continue
            if item.get('stage') == 'vae_compute' and item.get('index') == 1:
                time.sleep(.05)
                flag.touch(); reached.set()
    thread = threading.Thread(target=reader, daemon=True); thread.start()
    try:
        child.wait(timeout=900); stdout = child.stdout.read(); thread.join(timeout=5); children += 1
    finally:
        if child.poll() is None: child.kill(); child.wait(timeout=10)
    (directory / (cancel_name + '.log')).write_bytes(stdout + b''.join(lines))
    record = json.loads(stdout.strip().splitlines()[-1]); runs.append(dict(name=cancel_name, **record))
    check(reached.is_set() and not record['ok'] and child.returncode == 1 and not target.exists(), 'Actual computation cancellation failed')
    check(record['terminated_runs'] >= 1, 'ORT terminate callback did not interrupt an actual graph')
    check(record['session_loads'] == record['session_unloads'] == 2, 'Cancellation leaked decoder weights')
    guards.append(cancel_name)
    current(before)
    result = dict(schema='lma.ltx098-vae-tests/1', checks=checks, native_children=children, metrics=metrics,
                  guards=guards, runs=runs, gates=gates, original_publisher_decoder_forward=True,
                  trained_decoder_tensors=132, trained_decoder_parameters=552814641,
                  trained_checkpoint_loaded=True, host_model_inference_tested=True,
                  full_trained_decoder=True, complete_video_pipeline=False,
                  t5_executed=False, dit_executed=False, video_quality_tested=False,
                  engine_registered=False, packaged_in_apk=False, physical_android=False,
                  assets=manifest['assets'], oracle_files=oracle['files'], executable_sha256=sha(EXE),
                  backend='cpu', runtime_version=build['runtime']['version'], input_fingerprint=before)
    (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('checks', 'native_children', 'full_trained_decoder', 'complete_video_pipeline', 'physical_android')}), flush=True)


if __name__ == '__main__': run()
