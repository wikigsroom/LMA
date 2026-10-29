"""Execute production Nano C++ with pinned user-style assets on native Windows.

No downloads, Android execution, reference-audio cloning or quality certification.
Host termination is distinct from Android cooperative cancellation/lifecycle tests.
"""
import ctypes
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid
import wave

from build_moss_nano_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_moss_nano_trained import inputs as asset_inputs, path_for, sha, verify

ROOT = Path(__file__).resolve().parents[1]
CASES = [('prompt-a', 0, '今天的天空很蓝，我们一起去公园散步。'),
         ('prompt-b', 0, '这是一段新的本地语音，模型正在朗读不同的文字。'),
         ('voice-change', 1, '今天的天空很蓝，我们一起去公园散步。'),
         ('english', 8, 'The sun is shining. Let us take a walk in the park.'),
         ('japanese', 11, '今日はいい天気です。一緒に公園を散歩しましょう。')]


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint('tools/test_moss_nano_trained.py')}


def execute(command, cancel_step=None, timeout=600):
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in
            ['PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
             'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage']]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True); psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]; kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    start = time.perf_counter(); child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    handle = kernel.OpenProcess(0x410, False, child.pid); messages = queue.Queue(); captured = [bytearray(), bytearray()]
    errors = []; truncated = [False, False]; events = []; cancel_at = None; trigger = None; timed_out = False
    resources = dict(observed=False, samples=0, interval_ms=20, observed_peak_working_set_bytes=0,
                     sampled_peak_private_bytes=0, gpu_memory_measured=False, physical_device_memory_measured=False)

    def read(stream, index):
        try:
            for line in iter(stream.readline, b''):
                if len(captured[index]) + len(line) <= 2 * 1024 * 1024: captured[index].extend(line)
                else: truncated[index] = True
                if index == 0:
                    try:
                        value = json.loads(line)
                        if not isinstance(value, dict): raise ValueError('Non-object stdout')
                        messages.put(value)
                    except (ValueError, UnicodeError): errors.append('Non-protocol stdout')
        finally: stream.close()

    readers = [threading.Thread(target=read, args=(stream, index), daemon=True) for index, stream in enumerate([child.stdout, child.stderr])]
    for reader in readers: reader.start()
    try:
        while True:
            while not messages.empty():
                value = messages.get_nowait(); events.append(value)
                if (cancel_step is not None and cancel_at is None and value.get('event') == 'progress'
                    and value.get('stage') == 'synthesizing' and value.get('step', 0) >= cancel_step and child.poll() is None):
                    cancel_at = time.perf_counter(); trigger = value; child.kill()
            if handle:
                counter = Counters(); counter.cb = ctypes.sizeof(counter)
                if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counter), counter.cb):
                    resources['observed'] = True; resources['samples'] += 1
                    resources['observed_peak_working_set_bytes'] = max(resources['observed_peak_working_set_bytes'], counter.PeakWorkingSetSize)
                    resources['sampled_peak_private_bytes'] = max(resources['sampled_peak_private_bytes'], counter.PrivateUsage)
            if child.poll() is not None: break
            if time.perf_counter() - start > timeout: timed_out = True; child.kill(); child.wait(timeout=10); break
            time.sleep(.02)
        child.wait(timeout=10)
    finally:
        if child.poll() is None: child.kill(); child.wait(timeout=10)
        for reader in readers: reader.join(timeout=10)
        if handle: kernel.CloseHandle(handle)
    while not messages.empty(): events.append(messages.get_nowait())
    if any(reader.is_alive() for reader in readers): raise RuntimeError('Owned log reader did not exit')
    return dict(returncode=child.returncode, seconds=time.perf_counter() - start, events=events,
                protocol_errors=errors, logs_truncated=truncated, timed_out=timed_out,
                forced_host_termination=cancel_at is not None, cancel_trigger=trigger,
                cancel_to_exit_seconds=None if cancel_at is None else time.perf_counter() - cancel_at,
                android_cooperative_cancellation_tested=False, resources=resources), [bytes(x) for x in captured]


def audio_stats(path):
    import numpy as np
    with wave.open(str(path), 'rb') as stream:
        channels, width, rate, frames = stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()
        pcm = stream.readframes(frames)
    values = np.frombuffer(pcm, dtype='<i2').astype(np.float64) / 32768
    return dict(format='WAV', channels=channels, sample_width=width, sample_rate=rate, samples=frames,
                seconds=frames / rate, rms=float(np.sqrt(np.mean(values * values))), peak=float(abs(values).max()),
                clipping_fraction=float(np.mean(abs(values) >= 32767 / 32768)),
                nonzero_samples=int(np.count_nonzero(values)), bytes=path.stat().st_size, sha256=sha(path))


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows host only')
    before = inputs(); lock = verify(); binary, compilation = build()
    acquisition_path = ROOT / 'build/moss-nano-trained/receipt.json'; acquisition = json.loads(acquisition_path.read_text(encoding='utf-8'))
    current(acquisition['input_fingerprint'])
    folder = ROOT / 'build/moss-nano-trained-tests' / ('run-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8]); folder.mkdir(parents=True)
    workspace = folder / 'workspace'; components = {}
    for item in lock['components']:
        group = 'codec' if item['role'].startswith('codec_') else 'tts'; target = workspace / group / item['path']; target.parent.mkdir(parents=True, exist_ok=True)
        os.link(path_for(item), target); components[item['role']] = target
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free private ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    jobs = []; controls = []; failures = []
    parameters = dict(threads=4, speaker=0, maxFrames=375, maxInputTokens=1024, seed=1234)
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        info, logs = execute([alias(binary), '--info'], timeout=30)
        (folder / 'info.stdout').write_bytes(logs[0]); (folder / 'info.stderr').write_bytes(logs[1])
        expected = dict(schema='lma.native-worker/1', engine='moss_nano_ort', pipeline='moss_nano', backend='cpu',
                        modelData='user_selected_components', sourceRevision=compilation['sources']['moss-nano'], onnxruntime='1.28.0')
        if info['returncode'] or info['events'] != [expected] or info['protocol_errors']: raise RuntimeError('Wrong production worker/runtime identity')

        def request(speaker, prompt, output):
            return dict(schema='lma.engine-request/1', type='speech.synthesize', pipeline='moss_nano',
                        input=dict(prompt=prompt), parameters=dict(parameters, speaker=speaker),
                        components={role: alias(path) for role, path in components.items()}, workspace=alias(workspace), output=alias(output))

        def invoke(name, value, cancel_step=None):
            path = folder / (name + '.json'); path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print('Execute trained Nano production source:', name, flush=True)
            result, logs = execute([alias(binary), alias(path)], cancel_step)
            for suffix, data in zip(['stdout', 'stderr'], logs): (folder / (name + '.' + suffix)).write_bytes(data)
            result.update(name=name, request_sha256=sha(path), parameters=value['parameters'], prompt=value['input']['prompt'])
            return result

        def persist(result):
            (folder / (result['name'] + '-capture.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({key: result.get(key) for key in ['name', 'passed', 'returncode', 'seconds', 'audio', 'failure_reason']}, ensure_ascii=False), flush=True)

        for name, mutate, error in [
            ('bad-schema', lambda r: r.update(schema='unknown'), 'Unsupported MOSS Nano worker request'),
            ('bad-speaker', lambda r: r['parameters'].update(speaker=18), "Selected voice exceeds this model's actual voice count"),
            ('token-budget', lambda r: r['parameters'].update(maxInputTokens=1), 'Narration exceeds the selected token budget or cannot be tokenized'),
            ('bad-frame-limit', lambda r: r['parameters'].update(maxFrames=1501), 'MOSS Nano parameter exceeds application bounds'),
            ('outside-workspace', lambda r: r['components'].update(text_tokenizer=alias(path_for(next(x for x in lock['components'] if x['role'] == 'text_tokenizer')))), 'Component is outside its private execution workspace'),
            ('missing-global-data', lambda r: r['components'].pop('tts_data_1'), None)]:
            output = folder / (name + '.wav'); value = request(0, CASES[0][2], output); mutate(value); result = invoke(name, value)
            errors = [event for event in result['events'] if event.get('event') == 'error']
            result['passed'] = result['returncode'] == 1 and not output.exists() and not result['protocol_errors'] and not result['timed_out'] and len(errors) == 1 and (error is None or errors[0]['message'] == error)
            controls.append(result); persist(result)
            if not result['passed']: failures.append(name)

        cases = CASES + [('frame-limit', 0, CASES[0][2]), ('cancel-after-frame', 0, CASES[0][2]), ('recovery-a', 0, CASES[0][2])]
        for name, speaker, prompt in cases:
            output = folder / (name + '.wav'); value = request(speaker, prompt, output)
            if name == 'frame-limit': value['parameters']['maxFrames'] = 1
            result = invoke(name, value, cancel_step=5 if name == 'cancel-after-frame' else None)
            complete = [x for x in result['events'] if x.get('event') == 'complete']; execution = [x['details'] for x in result['events'] if x.get('event') == 'execution']
            result['output_exists'] = output.is_file(); result['execution'] = execution[0] if len(execution) == 1 else None
            common = not result['protocol_errors'] and not result['timed_out'] and not any(result['logs_truncated'])
            if name == 'cancel-after-frame':
                result['passed'] = common and result['forced_host_termination'] and result['returncode'] != 0 and not complete and not output.exists()
                controls.append(result)
            else:
                result['passed'] = common and result['returncode'] == 0 and len(complete) == 1 and complete[0]['output'] == alias(output) and len(execution) == 1 and output.is_file()
                if output.is_file():
                    result['audio'] = audio_stats(output); a = result['audio']
                    result['passed'] = result['passed'] and a['format'] == 'WAV' and a['channels'] == 1 and a['sample_width'] == 2 and a['sample_rate'] == 48000 and 0 < a['seconds'] <= 60 and a['rms'] > .00001 and a['nonzero_samples'] > 10
                if execution:
                    result['passed'] = result['passed'] and execution[0]['finishReason'] == ('length' if name == 'frame-limit' else 'stop')
                jobs.append(result)
            if not result['passed']:
                result['failure_reason'] = [x for x in result['events'] if x.get('event') == 'error']; failures.append(name)
            persist(result)
            if not result['passed']: break
    finally: subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    current(before)
    by_name = {x['name']: x for x in jobs}
    aba = all(name in by_name and by_name[name].get('audio') for name in ['prompt-a', 'recovery-a']) and by_name['prompt-a']['audio']['sha256'] == by_name['recovery-a']['audio']['sha256']
    if not aba: failures.append('A-B-A WAV determinism/recovery')
    for name in ['prompt-b', 'voice-change']:
        if name not in by_name or not by_name[name].get('audio') or by_name['prompt-a']['audio']['sha256'] == by_name[name]['audio']['sha256']: failures.append('distinct ' + name)
    if len(jobs) != 7 or len(controls) != 7: failures.append('incomplete trained test matrix')
    files = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(folder.iterdir()) if p.is_file()}
    report = dict(schema='lma.moss-nano-trained-host/1', compilation=compilation, acquisition=acquisition,
                  acquisition_receipt_sha256=sha(acquisition_path), info=info, jobs=jobs, controls=controls,
                  files=files, capture_directory=folder.relative_to(ROOT).as_posix(), failures=failures,
                  host_execution_checks_passed=not failures, aba_bitwise_identical=bool(aba),
                  trained_production_worker_executed=bool(jobs), production_worker_source_unmodified=True,
                  backend='cpu', fixture=False, asset_download_attempted=False,
                  hardlinked_user_style_workspace=True, physical_android=False, app_executed=False,
                  android_cooperative_cancellation_tested=False, speech_quality_accepted=False,
                  android_background_accepted=False, device_resource_fit_accepted=False,
                  complete_target09_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    for path in [folder / 'results.json', folder.parent / 'results.json']: path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(failures=failures, capture_directory=report['capture_directory'], aba_bitwise_identical=bool(aba))), flush=True)
    if failures: raise SystemExit(1)


if __name__ == '__main__': main()
