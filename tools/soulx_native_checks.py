"""Shared native Windows ORT/CPU compilation for SoulX research checks."""
import hashlib,importlib.metadata,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def compile_host(lock,out,source):
    if source not in ['soulx_acoustic','soulx_reference']:raise RuntimeError('Unknown research source')
    host=out/'host';host.mkdir(exist_ok=True)
    if hashlib.sha256((ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp').read_bytes()).hexdigest()!=lock['json_header_sha256']:raise RuntimeError('Pinned JSON header changed')
    distribution=importlib.metadata.distribution('onnxruntime');dll=Path(distribution.locate_file('onnxruntime/capi/onnxruntime.dll'))
    if distribution.version!=lock['host_runtime']['version'] or hashlib.sha256(dll.read_bytes()).hexdigest()!=lock['host_runtime']['sha256']:raise RuntimeError('Host test runtime changed')
    shutil.copyfile(dll,host/'onnxruntime.dll');(host/'ort.def').write_text('LIBRARY onnxruntime.dll\nEXPORTS\nOrtGetApiBase\n',encoding='ascii')
    setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
    if not setup.is_file():raise RuntimeError('Native MSVC compiler required')
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        cpp='acoustic' if source=='soulx_acoustic' else 'reference'
        script=host/'compile.cmd';script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'
            'lib /nologo /def:ort.def /machine:x64 /out:onnxruntime.lib\nif errorlevel 1 exit /b %errorlevel%\n'
            'cl /nologo /O2 /W4 /fp:precise /EHsc /std:c++17 /DNDEBUG /I../../../build/native-src/kissfft '
            '/I../../../build/native-src/onnxruntime-headers/include/onnxruntime/core/session /I../../../build/native-src/sd-cpp/thirdparty '
            '../../../research/'+source+'/'+cpp+'.cpp ../../../research/'+source+'/driver.cpp ../../../research/soulx/dsp.cpp '
            '../../../build/native-src/kissfft/kiss_fft.c ../../../build/native-src/kissfft/kiss_fftr.c onnxruntime.lib /Fe:soulx-test.exe\n',encoding='utf-8')
        result=subprocess.run(['cmd','/d','/c','compile.cmd'],cwd=drive+'/'+host.relative_to(ROOT).as_posix(),capture_output=True,timeout=180)
        (host/'compile.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Inspect '+str((host/'compile.log').relative_to(ROOT)))
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    return host/'soulx-test.exe'
