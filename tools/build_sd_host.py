"""Compile the unchanged production diffusion worker for native Windows tests."""
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from build_native import SD_REVISION, GGML_REVISION, git
from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('native/sd_worker.cpp', 'native/sd_backend.hpp', 'native/sd_policy.hpp', 'native/lcm_condition.hpp', 'native/vocab_external.cpp', 'native/tokenizer_data.hpp', 'native/qwen_prompt.hpp',
                       'research/sd_host', 'tools/build_sd_host.py', 'tools/build_native.py',
                       'tools/fetch_sd15_trained.py', 'third_party/notices/sd-sources.json')


def build(jobs=2, resume_cache=None):
    if os.name != 'nt' or not 1 <= jobs <= 4: raise RuntimeError('Use native Windows MSVC and one to four compiler jobs')
    before = inputs()
    if git('rev-parse', 'HEAD') != SD_REVISION or git('-C', 'ggml', 'rev-parse', 'HEAD') != GGML_REVISION:
        raise ValueError('Different pinned source revisions')
    if git('status', '--porcelain', '--untracked-files=no') or git('-C', 'ggml', 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Modified upstream source')
    key = hashlib.sha256(json.dumps(before, sort_keys=True).encode('utf-8')).hexdigest()[:16]
    directory = ROOT / 'build/sd-worker-host' / key
    receipt = directory / 'receipt.json'; executable = directory / 'bin/lma_sd_host.exe'
    tokenizer = directory / 'bin/lma_sd_tokenizer_host.exe'
    if receipt.exists():
        record = json.loads(receipt.read_text(encoding='utf-8')); current(record['input_fingerprint'])
        if record['input_fingerprint'] != before or record['sha256'] != sha(executable) or record['tokenizer_sha256'] != sha(tokenizer): raise ValueError('Changed immutable host build')
        return executable, record
    directory.mkdir(parents=True, exist_ok=True)
    workspace=directory/'bin'; drive=None
    if resume_cache:
        workspace=(ROOT/resume_cache).resolve()
        relative=workspace.relative_to((ROOT/'build/sd-worker-host').resolve())
        if len(relative.parts)!=2 or not re.fullmatch('[a-f0-9]{16}',relative.parts[0]) or relative.parts[1]!='bin':
            raise ValueError('Only an owned unaccepted host build cache may be resumed')
        if (workspace.parent/'receipt.json').exists():
            raise ValueError('An accepted immutable build cannot be used as a mutable cache')
        lines=(workspace/'CMakeCache.txt').read_text(encoding='utf-8').splitlines()
        homes=[re.fullmatch(r'CMAKE_HOME_DIRECTORY:INTERNAL=([T-Z]):[/\\]research[/\\]sd_host',line) for line in lines]
        drive=next((m[1]+':' for m in homes if m),None)
        if not drive or Path(drive+'/').exists():raise RuntimeError('Cached owned source alias is invalid or occupied')
    drive = drive or next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + '/'; relative = workspace.relative_to(ROOT).as_posix()
        cmake = alias + 'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        commands = [[cmake, '-S', alias + 'research/sd_host', '-B', alias + relative, '-G', 'Ninja',
                     '-DCMAKE_BUILD_TYPE=Release', '-DROOT=' + alias, '-DLMA_SD_REVISION=' + SD_REVISION,
                     '-DCMAKE_MAKE_PROGRAM=' + alias + 'build/toolchain/cmake-3.31.6/bin/ninja.exe'],
                    [cmake, '--build', alias + relative, '--target', 'lma_sd_host', 'lma_sd_tokenizer_host', '-j', str(jobs)]]
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index, command in enumerate(commands):
            script = directory / ('build-' + str(index) + '.cmd')
            script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
            print('Compile production SD worker on Windows', index, flush=True)
            result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=1800)
            (directory / ('build-' + str(index) + '.log')).write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError('Inspect native SD host build log')
    finally:
        subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    current(before)
    if workspace != directory/'bin':
        executable.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(workspace/'lma_sd_host.exe',executable)
        shutil.copy2(workspace/'lma_sd_tokenizer_host.exe',tokenizer)
    record = dict(schema='lma.sd-host-build/1', executable=executable.relative_to(ROOT).as_posix(),
                  sha256=sha(executable), bytes=executable.stat().st_size,
                  tokenizer_executable=tokenizer.relative_to(ROOT).as_posix(), tokenizer_sha256=sha(tokenizer), tokenizer_bytes=tokenizer.stat().st_size,
                  source_revision=SD_REVISION, ggml_revision=GGML_REVISION, backend='cpu',
                  production_worker_source_unmodified=True, production_vocabulary_source_unmodified=True,
                  windows_parent_guard=True, external_vocabulary=True, bundled_model_data=False,
                  android_compiled=False, physical_android=False, packaged_in_apk=False,
                  model_executed=False, reused_unaccepted_build_cache=bool(resume_cache),
                  compile_workspace=workspace.relative_to(ROOT).as_posix(), input_fingerprint=before)
    receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return executable, record


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--jobs',type=int,choices=range(1,5),default=2)
    parser.add_argument('--resume-cache',help='Reuse only an owned failed/unaccepted CMake cache; publish new immutable executables')
    args=parser.parse_args();path, record = build(args.jobs,args.resume_cache); print(json.dumps({k: record[k] for k in ['executable', 'bytes', 'sha256', 'backend']}))
