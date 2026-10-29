"""Build an isolated F32 sampler with the publisher's modulation order."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from build_ltx098_compute_precision import build as compute_build, inputs as compute_inputs
from evidence import current, fingerprint
from fetch_ltx098_text import sha

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**compute_inputs(), **fingerprint('research/ltx098_modulation', 'tools/build_ltx098_modulation.py')}


def build():
    if os.name != 'nt': raise RuntimeError('Use native Windows MSVC; no virtualization')
    before = inputs(); _, base_record = compute_build(False)
    base = ROOT / base_record['executable']; base = base.parent.parent
    key = hashlib.sha256(json.dumps(before, sort_keys=True).encode('utf-8')).hexdigest()[:16]
    output = ROOT / 'build/ltx098-modulation-host' / key
    receipt = output / 'receipt.json'; executable = output / 'bin/lma_ltx098_sample.exe'
    libraries = {name: sha(ROOT / 'build/ltx098-host-vulkan' / name) for name in base_record['linked_archives']}
    if receipt.exists():
        record = json.loads(receipt.read_text(encoding='utf-8')); current(record['input_fingerprint'])
        if record['input_fingerprint'] != before or record['linked_archives'] != libraries or record['executable_sha256'] != sha(executable):
            raise ValueError('Changed immutable modulation build')
        for name, identity in record['generated_sources'].items():
            if sha(output / 'src' / name) != identity: raise ValueError('Changed generated source')
        return executable, record
    source = output / 'src'; source.mkdir(parents=True, exist_ok=False)
    for item in (base / 'src').iterdir():
        if item.is_file(): shutil.copyfile(item, source / item.name)
    path = source / 'transformer.cpp'; text = path.read_text(encoding='utf-8')
    anchor = '''    ggml_tensor* modulate(ggml_context* ctx,ggml_tensor* x,ggml_tensor* shift,ggml_tensor* scale) {
        return ggml_add(ctx,ggml_add(ctx,x,ggml_mul(ctx,x,scale)),shift);
    }'''
    if text.count(anchor) != 1: raise ValueError('Changed original modulation anchor')
    text = text.replace(anchor, (ROOT / 'research/ltx098_modulation/modulation.inc').read_text(encoding='utf-8').rstrip())
    for old, new in [
        ('m.chunk(c,mods,0),m.chunk(c,mods,1))', 'm.chunk(c,mods,0),m.chunk(c,mods,1),one)'),
        ('m.chunk(c,mods,3),m.chunk(c,mods,4))', 'm.chunk(c,mods,3),m.chunk(c,mods,4),one)'),
        ('m.modulate(c,ggml_norm(c,x,1e-6f),shift,scale)', 'm.modulate(c,ggml_norm(c,x,1e-6f),shift,scale,one)')]:
        if text.count(old) != 1: raise ValueError('Changed modulation call coverage')
        text = text.replace(old, new)
    path.write_text(text, encoding='utf-8')
    path = source / 'sampling_driver.cpp'; text = path.read_text(encoding='utf-8')
    anchor = 'record["precision_policy"]="explicit_f32_matmul_f32";record["explicit_f32_matmul_operands"]=true;'
    if text.count(anchor) != 1: raise ValueError('Changed candidate identity')
    text = text.replace(anchor, 'record["precision_policy"]="explicit_f32_matmul_publisher_modulation";record["explicit_f32_matmul_operands"]=true;record["publisher_modulation_order"]=true;')
    path.write_text(text, encoding='utf-8')
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + '/'; relative = output.relative_to(ROOT).as_posix()
        cmake = alias + 'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        commands = [[cmake, '-S', alias + relative + '/src', '-B', alias + relative + '/bin', '-G', 'Ninja',
                     '-DCMAKE_BUILD_TYPE=Release', '-DROOT=' + alias, '-DCMAKE_MAKE_PROGRAM=' + alias + 'build/toolchain/cmake-3.31.6/bin/ninja.exe'],
                    [cmake, '--build', alias + relative + '/bin', '-j', '4']]
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index, command in enumerate(commands):
            script = output / ('build-' + str(index) + '.cmd')
            script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
            process = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=300)
            (output / ('build-' + str(index) + '.log')).write_bytes(process.stdout + process.stderr)
            if process.returncode: raise RuntimeError('Inspect isolated modulation build log')
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    current(before)
    record = dict(schema='lma.ltx098-modulation-build/1', mode='publisher_modulation',
                  executable=executable.relative_to(ROOT).as_posix(), executable_sha256=sha(executable),
                  linked_archives=libraries, base_build=base_record,
                  generated_sources={p.name: sha(p) for p in source.iterdir() if p.is_file()},
                  publisher_modulation_order=True, android_compiled=False, packaged_in_apk=False,
                  engine_registered=False, input_fingerprint=before)
    receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return executable, record
