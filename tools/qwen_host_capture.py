"""Capture real native Qwen children; cancellation follows actual generated frame 16."""
import ctypes
import json
from pathlib import Path
import queue
import subprocess
import threading
import time
ROOT = Path(__file__).resolve().parents[1]


def execute(command, cancel=False, timeout=1200):
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
                if (cancel and cancel_at is None and value.get('event') == 'execution'
                    and 16 <= value.get('details', {}).get('generatedAudioFrames', 0) < value.get('details', {}).get('audioFrameLimit', 0) and child.poll() is None):
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

