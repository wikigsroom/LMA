"""Run the production diffusion source with explicitly acquired SD1.5 assets.

Native Windows CPU evidence only. No asset download, Android execution, App
installation, quality certification, or Release acceptance occurs here.
"""
import ctypes
import json
import math
import os
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path

from build_sd_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_sd15_trained import asset_path, inputs as asset_inputs, sha, verify

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = [
    'A red ceramic teapot on a wooden table, studio photograph, soft light',
    'A small sailboat on a blue lake, snow covered mountain, landscape photograph',
]


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint('tools/test_sd15_trained.py')}


def execute(command, environment, cancel_step=None, timeout=3600):
    """Observe and terminate only the directly owned native Windows child."""
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ['PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage']]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    start = time.perf_counter()
    child = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    handle = kernel.OpenProcess(0x410, False, child.pid)
    events = []; messages = queue.Queue(); captured = [bytearray(), bytearray()]
    errors = []; truncated = [False, False]
    resources = dict(observed=False, samples=0, interval_ms=20,
                     observed_peak_working_set_bytes=0, sampled_peak_private_bytes=0,
                     gpu_memory_measured=False, physical_device_memory_measured=False)

    def read(stream, index):
        try:
            for line in iter(stream.readline, b''):
                if len(captured[index]) + len(line) <= 2 * 1024 * 1024:
                    captured[index].extend(line)
                else: truncated[index] = True
                if index == 0:
                    try:
                        value = json.loads(line)
                        if not isinstance(value, dict): raise ValueError('Non-object stdout')
                        messages.put(value)
                    except (ValueError, UnicodeError): errors.append('Non-protocol stdout')
        finally: stream.close()

    readers = [threading.Thread(target=read, args=(stream, index), daemon=True)
               for index, stream in enumerate([child.stdout, child.stderr])]
    for reader in readers: reader.start()
    cancelled = False; timed_out = False; cancel_seconds = None; trigger = None
    try:
        while True:
            while not messages.empty():
                value = messages.get_nowait(); events.append(value)
                is_sample = (value.get('event') == 'progress' and value.get('stage') == 'generating'
                             and value.get('steps') == 20 and 0 <= value.get('step', -1) <= 20)
                if is_sample and value['step'] % 5 == 0:
                    print('Observed actual sampler progress', value['step'], '/ 20', flush=True)
                if (cancel_step is not None and not cancelled and is_sample and value['step'] >= cancel_step
                    and child.poll() is None):
                    trigger = value; cancelled = True; cancel_seconds = time.perf_counter()
                    child.kill()
            if handle:
                counter = Counters(); counter.cb = ctypes.sizeof(counter)
                if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counter), counter.cb):
                    resources['observed'] = True; resources['samples'] += 1
                    resources['observed_peak_working_set_bytes'] = max(
                        resources['observed_peak_working_set_bytes'], counter.PeakWorkingSetSize)
                    resources['sampled_peak_private_bytes'] = max(
                        resources['sampled_peak_private_bytes'], counter.PrivateUsage)
            if child.poll() is not None: break
            if time.perf_counter() - start > timeout:
                timed_out = True; child.kill(); child.wait(timeout=10); break
            time.sleep(.02)
        child.wait(timeout=10)
    finally:
        if child.poll() is None: child.kill(); child.wait(timeout=10)
        for reader in readers: reader.join(timeout=10)
        if handle: kernel.CloseHandle(handle)
    while not messages.empty(): events.append(messages.get_nowait())
    if any(reader.is_alive() for reader in readers): raise RuntimeError('Owned log reader did not stop')
    return dict(returncode=child.returncode, seconds=time.perf_counter() - start,
                events=events, protocol_errors=errors, logs_truncated=truncated,
                cancelled=cancelled, timed_out=timed_out, cancel_trigger=trigger,
                cancel_to_exit_seconds=None if cancel_seconds is None else time.perf_counter() - cancel_seconds,
                resources=resources), [bytes(data) for data in captured]


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows host test only')
    before = inputs(); selected = verify(); executable, compilation = build()
    acquisition_path = ROOT / 'build/sd15-trained/receipt.json'
    acquisition = json.loads(acquisition_path.read_text(encoding='utf-8'))
    current(acquisition['input_fingerprint'])
    if acquisition['bundle_id'] != selected['id']: raise ValueError('Different asset receipt')
    folder = ROOT / 'build/sd15-trained-tests' / ('run-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII path alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    jobs = []; controls = []; files = {}; failures = []
    parameters = dict(width=512, height=512, steps=20, cfg=7.0, sampler='euler',
                      scheduler='discrete', seed=42, threads=4, vaeTiling=True, flowShift=0)
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        environment = os.environ.copy()
        components = {item['role']: alias(asset_path(item)) for item in selected['components']}
        environment['LMA_VOCAB_CLIP_MERGES'] = components['clip_merges']
        info, logs = execute([alias(executable), '--info'], environment, timeout=30)
        (folder / 'info.stdout').write_bytes(logs[0]); (folder / 'info.stderr').write_bytes(logs[1])
        expected_info = dict(schema='lma.engine/1', engine='sd_cpp', revision=compilation['source_revision'],
                             backend='cpu', bundled_model_data=False, generation_tested=False)
        if info['returncode'] or info['events'] != [expected_info] or info['protocol_errors']:
            raise ValueError('Unexpected unchanged worker identity')

        def request(prompt, output):
            return dict(schema='lma.engine-request/1', pipeline='sd15', architecture='sd15',
                        samplingProfile='standard', type='image.generate', output=alias(output),
                        input=dict(prompt=prompt, negativePrompt='blurry, distorted, low quality'),
                        parameters=dict(parameters), components=dict(components), loras=[])

        def invoke(name, value, cancel_step=None):
            path = folder / (name + '.json')
            path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
            print('Execute real SD1.5 production source:', name, flush=True)
            result, logs = execute([alias(executable), alias(path)], environment, cancel_step=cancel_step)
            (folder / (name + '.stdout')).write_bytes(logs[0]); (folder / (name + '.stderr')).write_bytes(logs[1])
            result['name'] = name; result['request_sha256'] = sha(path)
            print(json.dumps(dict(name=name, returncode=result['returncode'], seconds=result['seconds'],
                                  cancelled=result['cancelled'], events=len(result['events']))), flush=True)
            return result

        for name, mutation, expected in [
            ('bad-schema', lambda r: r.update(schema='unknown'), 'Unsupported engine request version'),
            ('empty-prompt', lambda r: r['input'].update(prompt=''), 'Invalid prompt or output'),
            ('bad-threads', lambda r: r['parameters'].update(threads=0), 'Native parameter out of bounds: threads')]:
            output = folder / (name + '.png'); value = request(PROMPTS[0], output); mutation(value)
            result = invoke(name, value)
            result['passed'] = (result['returncode'] == 1 and not result['protocol_errors'] and
                                result['events'] == [dict(event='error', message=expected)] and not output.exists())
            controls.append(result)
            if not result['passed']: failures.append(name)

        from PIL import Image, ImageStat
        for name, case, cancel_step in [('prompt-a', 0, None), ('prompt-b', 1, None),
                                         ('cancel-after-step', 0, 1), ('recovery-a', 0, None)]:
            output = folder / (name + '.png'); value = request(PROMPTS[case], output)
            result = invoke(name, value, cancel_step)
            result.update(case=case, prompt=PROMPTS[case], parameters=dict(parameters), output_exists=output.exists())
            phase = None; phase_consistent = True
            for event in result['events']:
                if event.get('event') == 'stage': phase = event['stage']
                elif event.get('event') == 'progress':
                    phase_consistent = phase_consistent and phase in ['loading', 'generating'] and event['stage'] == phase
            result['progress_phase_consistent'] = phase_consistent
            result['loading_progress_events'] = sum(item.get('event') == 'progress' and item.get('stage') == 'loading' for item in result['events'])
            result['generation_progress_events'] = sum(item.get('event') == 'progress' and item.get('stage') == 'generating' for item in result['events'])
            progress = [item for item in result['events'] if item.get('event') == 'progress'
                        and item.get('stage') == 'generating' and item.get('steps') == 20]
            complete = [item for item in result['events'] if item.get('event') == 'complete']
            result['sampling_steps_observed'] = [item.get('step') for item in progress]
            if cancel_step is not None:
                result['passed'] = (result['cancelled'] and result['returncode'] != 0 and not complete
                                    and not output.exists() and not result['timed_out']
                                    and not result['protocol_errors'] and not any(result['logs_truncated']) and phase_consistent)
                controls.append(result)
            else:
                result['passed'] = (result['returncode'] == 0 and not result['protocol_errors']
                                    and not result['timed_out'] and not any(result['logs_truncated']) and phase_consistent
                                    and len(complete) == 1 and complete[0] == dict(event='complete', output=alias(output),
                                        format='png', width=512, height=512) and output.is_file()
                                    and result['sampling_steps_observed'] == list(range(21)))
                if output.is_file():
                    with Image.open(output) as image:
                        image.load(); rgb = image.convert('RGB'); stats = ImageStat.Stat(rgb)
                        result['image'] = dict(width=image.width, height=image.height, format=image.format,
                                               mode=image.mode, sha256=sha(output), bytes=output.stat().st_size,
                                               channel_mean=stats.mean, channel_stddev=stats.stddev,
                                               extrema=rgb.getextrema(), entropy=rgb.entropy())
                        result['passed'] = result['passed'] and image.format == 'PNG' and image.size == (512, 512)
                        result['passed'] = result['passed'] and all(math.isfinite(x) and x > 1 for x in stats.stddev)
                jobs.append(result)
            (folder / (name + '-capture.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            if not result['passed']: failures.append(name)
            if result['timed_out']: break
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    current(before)
    for path in sorted(folder.iterdir()):
        if path.is_file(): files[path.name] = dict(bytes=path.stat().st_size, sha256=sha(path))
    aba = len(jobs) == 3 and all(job.get('image') for job in jobs) and jobs[0]['image']['sha256'] == jobs[2]['image']['sha256']
    different = len(jobs) >= 2 and all(job.get('image') for job in jobs[:2]) and jobs[0]['image']['sha256'] != jobs[1]['image']['sha256']
    if not aba: failures.append('A-B-A image determinism')
    if not different: failures.append('distinct prompts produced distinct images')
    report = dict(schema='lma.sd15-trained-host/1', bundle=selected, compilation=compilation,
                  acquisition_receipt_sha256=sha(acquisition_path), acquisition=acquisition,
                  info=info, jobs=jobs, controls=controls, files=files,
                  capture_directory=folder.relative_to(ROOT).as_posix(),
                  aba_bitwise_identical=bool(aba), distinct_prompt_images=bool(different),
                  failures=failures, host_execution_checks_passed=not failures,
                  trained_model_executed=any(job.get('image') for job in jobs),
                  production_worker_source_unmodified=True, production_vocabulary_source_unmodified=True,
                  external_vocabulary=True, backend='cpu', fixture=False,
                  all_assets_already_present=True, asset_download_attempted=False,
                  android_compiled=False, physical_android=False, app_executed=False,
                  semantic_quality_accepted=False, device_resource_fit_accepted=False,
                  android_background_accepted=False, complete_release_accepted=False,
                  input_fingerprint=before)
    (folder / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (folder.parent / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(failures=failures, aba_bitwise_identical=bool(aba), distinct_prompt_images=bool(different),
                          capture_directory=report['capture_directory'])), flush=True)
    if failures: raise SystemExit(1)


if __name__ == '__main__': main()
