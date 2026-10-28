"""Compile the unregistered SoulX DSP static library for Android ARM64/API28.

This is NOT an inference worker, APK payload, or full-model support receipt.
"""
import hashlib, json, subprocess
from pathlib import Path
from evidence import fingerprint, current
from fetch_soulx_dsp import validate_sources, LOCK
ROOT = Path(__file__).resolve().parents[1]


def main():
    lock = json.loads(LOCK.read_text(encoding='utf-8')); validate_sources(lock)
    inputs = fingerprint('research/soulx', 'tools/build_soulx_dsp.py', 'tools/fetch_soulx_dsp.py', 'third_party/soulx-dsp-source-lock.json')
    out = ROOT / 'build/soulx-dsp-arm64'; out.mkdir(exist_ok=True); (out/'receipt.json').unlink(missing_ok=True)
    drive = next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()), None)
    if not drive: raise RuntimeError('No free temporary ASCII build alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        alias = drive+'/'; toolchain = alias+'build/toolchain/'; ndk = toolchain+'android-ndk-r30'
        cmake = toolchain+'cmake-3.31.6/bin/cmake.exe'; output = alias+'build/soulx-dsp-arm64'
        commands = [[cmake,'-S',alias+'research/soulx','-B',output,'-G','Ninja',
            '-DCMAKE_MAKE_PROGRAM='+toolchain+'cmake-3.31.6/bin/ninja.exe',
            '-DCMAKE_TOOLCHAIN_FILE='+ndk+'/build/cmake/android.toolchain.cmake',
            '-DANDROID_ABI=arm64-v8a','-DANDROID_PLATFORM=android-28','-DANDROID_STL=c++_static',
            '-DCMAKE_BUILD_TYPE=Release','-DLMA_KISSFFT_SOURCE='+alias+'build/native-src/kissfft'],
            [cmake,'--build',output,'--target','lma_soulx_dsp','-j','4']]
        for i, command in enumerate(commands):
            result = subprocess.run(command,capture_output=True,timeout=180)
            (out/('build-'+str(i)+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode: raise RuntimeError('Inspect build/soulx-dsp-arm64/build-'+str(i)+'.log')
        binary = out/'liblma_soulx_dsp.a'; llvm = ndk+'/toolchains/llvm/prebuilt/windows-x86_64/bin/'
        header = subprocess.check_output([llvm+'llvm-readobj.exe','--file-headers',output+'/liblma_soulx_dsp.a'],text=True,encoding='utf-8')
        if header.count('Arch: aarch64') != 3: raise RuntimeError('Expected three Android ARM64 object files')
        undefined = subprocess.check_output([llvm+'llvm-nm.exe','--undefined-only',output+'/liblma_soulx_dsp.a'],text=True,encoding='utf-8')
        for forbidden in [' connect',' socket',' execve',' system',' popen',' dlopen']:
            if forbidden in undefined: raise RuntimeError('Unexpected external execution/network import')
        (out/'object-headers.txt').write_text(header,encoding='utf-8'); (out/'undefined-symbols.txt').write_text(undefined,encoding='utf-8')
    finally: subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    current(inputs)
    receipt = dict(android_arm64_compiled=True,android_platform=28,archive_bytes=binary.stat().st_size,
        archive_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),objects=3,engine_registered=False,
        packaged_in_apk=False,model_inference=False,physical_android=False,input_fingerprint=inputs)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='input_fingerprint'}))

if __name__=='__main__': main()
