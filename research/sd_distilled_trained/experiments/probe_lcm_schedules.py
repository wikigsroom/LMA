"""Compare actual extracted scheduler implementations; version differences are not release gates."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from types import SimpleNamespace
from typing import Optional, Union
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import numpy as np
import torch
torch.set_num_threads(1)

directory = Path(__file__).resolve().parent
root = directory.parents[1]
lock = json.loads((directory / 'diffusers-scheduler-reference.json').read_text())
raw = (directory / lock['local_file']).read_bytes()
assert hashlib.sha256(raw).hexdigest() == lock['sha256']
definition = next(n for n in ast.parse(raw.decode('utf-8')).body if isinstance(n, ast.ClassDef) and n.name == 'LCMScheduler')
method = next(n for n in definition.body if isinstance(n, ast.FunctionDef) and n.name == 'set_timesteps')
scope = dict(np=np, torch=torch, Optional=Optional, Union=Union)
exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), 'official-lcm-set-timesteps', 'exec'), scope)
reference = {}
for count in range(1, 9):
    scheduler = SimpleNamespace(config=SimpleNamespace(num_train_timesteps=1000, original_inference_steps=50))
    scope['set_timesteps'](scheduler, count)
    reference[count] = scheduler.timesteps.tolist()

native_path = root / 'build/native-src/sd-cpp/src/runtime/denoiser.hpp'
native_raw = native_path.read_bytes()
block = re.search(rb'struct LCMScheduler : SigmaScheduler \{.*?\r?\n\};', native_raw, re.S).group()
assert b'original_steps = 50' in block and b'(i * original_steps) / n' in block
capture = directory / ('lcm-schedule-native-' + str(time.time_ns()))
capture.mkdir(exist_ok=False)
source = capture / 'scheduler.cpp'
source.write_bytes(b'#include <vector>\n#include <functional>\n#include <cstdint>\n#include <iostream>\n'
    b'constexpr int TIMESTEPS=1000;\nusing t_to_sigma_t=std::function<float(float)>;\n'
    b'struct SigmaScheduler { virtual std::vector<float> get_sigmas(uint32_t,float,float,t_to_sigma_t)=0; };\n'
    + block + b'\nint main(){ std::cout << "["; for(int n=1;n<=8;n++){ if(n>1)std::cout << ","; '
    b'LCMScheduler s; auto v=s.get_sigmas(n,0,0,[](float t){return t;}); std::cout<<"["; '
    b'for(int i=0;i<n;i++){if(i)std::cout<<","; std::cout<<static_cast<int>(v[i]);} std::cout<<"]";} std::cout<<"]"; }\n')
binary = capture / 'scheduler.exe'
drive = next(c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists())
subprocess.run(['subst', drive, str(root)], capture_output=True, check=True)
try:
    def alias(path): return drive + '/' + path.relative_to(root).as_posix()
    setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
    command = ['cl', '/nologo', '/std:c++17', '/EHsc', '/O2', alias(source), '/Fe:' + alias(binary),
               '/Fo:' + alias(capture / 'scheduler.obj')]
    script = capture / 'compile.cmd'
    script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n'
                      + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
    compiled = subprocess.run(['cmd', '/d', '/c', alias(script)], cwd=capture, capture_output=True, timeout=180)
    (capture / 'compile.stdout').write_bytes(compiled.stdout)
    (capture / 'compile.stderr').write_bytes(compiled.stderr)
    assert compiled.returncode == 0, 'Retained schedule compile logs'
    executed = subprocess.run([alias(binary)], cwd=capture, capture_output=True, timeout=15)
    (capture / 'native.stdout').write_bytes(executed.stdout)
    (capture / 'native.stderr').write_bytes(executed.stderr)
    assert executed.returncode == 0 and not executed.stderr
    measured = json.loads(executed.stdout)
    assert len(measured) == 8
finally:
    subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
assert native_path.read_bytes() == native_raw
rows = [dict(steps=n, reference_diffusers_0_22=reference[n], native_sd_cpp=measured[n - 1],
             equal=reference[n] == measured[n - 1]) for n in range(1, 9)]
record = dict(schema='lma.private-lcm-schedule-version-comparison/1', reference=lock,
              native_revision='be486498eadc29dc3cd234d944c2180ed42b1415',
              native_header_sha256=hashlib.sha256(native_raw).hexdigest(), extracted_block_sha256=hashlib.sha256(block).hexdigest(),
              extracted_block_compiled_and_executed=True, official_python_method_executed=True,
              cases=rows, all_equal=all(row['equal'] for row in rows),
              comparison_only=True, difference_is_not_a_model_acceptance_gate=True,
              model_weights_executed=False, physical_android=False, image_quality_accepted=False,
              complete_release_accepted=False, capture_directory=capture.relative_to(root).as_posix(),
              experiment_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(directory / 'lcm-schedule-version-comparison.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(cases=rows, all_equal=record['all_equal'])), flush=True)
