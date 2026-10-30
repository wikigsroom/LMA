"""Build an isolated native Windows denoised-latent diagnostic; no product patch."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_sd_vulkan import build, inputs as production_inputs
from build_native import SD_REVISION
from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**production_inputs(), **fingerprint('tools/build_wan_latent_probe.py', 'research/wan_latent_probe')}


def build_probe():
    if os.name != 'nt': raise RuntimeError('Native Windows research only')
    before = inputs(); _, production = build()
    original = ROOT/'build/native-src/sd-cpp/src/pipeline/video.cpp'
    text = original.read_text(encoding='utf-8')
    marker = '        sd::Tensor<float> vid = sd->decode_first_stage(video_latent, true);'
    if text.count(marker) != 1: raise ValueError('Review the pinned Wan decode seam')
    capture = '''        // LMA diagnostic only: save real denoised latents; do not decode a video.
        if (const char* file = std::getenv("LMA_WAN_PROBE_LATENTS")) {
            if (!sd_version_is_wan(sd->version) || (video_latent.dim() != 4 && video_latent.dim() != 5) || video_latent.shape()[3] != 16) return nullptr;
            std::ofstream stream(std::filesystem::u8path(file), std::ios::binary);
            stream.write("LMAWZ1\\0\\0", 8);
            const uint32_t rank = static_cast<uint32_t>(video_latent.dim());
            stream.write(reinterpret_cast<const char*>(&rank), sizeof(rank));
            for (int64_t dim : video_latent.shape()) stream.write(reinterpret_cast<const char*>(&dim), sizeof(dim));
            const int64_t count = video_latent.numel();
            stream.write(reinterpret_cast<const char*>(&count), sizeof(count));
            stream.write(reinterpret_cast<const char*>(video_latent.data()), count * sizeof(float));
            stream.close();
            return nullptr;
        }
'''
    modified = '#include <filesystem>\n#include <fstream>\n'+text.replace(marker, capture+marker)
    directory = ROOT/'build/wan-latent-probe'; directory.mkdir(exist_ok=True)
    (directory/'video_probe.cpp').write_text(modified, encoding='utf-8')
    drive = next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()), None)
    cache = directory/'CMakeCache.txt'
    if cache.exists():
        import re
        match = re.search(r'CMAKE_HOME_DIRECTORY:INTERNAL=([T-Z]):[/\\]', cache.read_text(encoding='utf-8'))
        if not match: raise ValueError('Preserve unexpected diagnostic cache')
        drive = match[1]+':'
        if Path(drive+'/').exists(): raise RuntimeError('Diagnostic build alias occupied')
    if not drive: raise RuntimeError('No free task-owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        prefix = drive+'/'; cmake = prefix+'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        setup = r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
        commands = [
            [cmake, '-S', prefix+'research/wan_latent_probe', '-B', prefix+'build/wan-latent-probe', '-G', 'Ninja',
             '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_MAKE_PROGRAM='+prefix+'build/toolchain/cmake-3.31.6/bin/ninja.exe', '-DLMA_SD_REVISION='+SD_REVISION],
            [cmake, '--build', prefix+'build/wan-latent-probe', '--target', 'lma_wan_latent_probe', '-j', '2']]
        for index, command in enumerate(commands):
            script = directory/('build-'+str(index)+'.cmd')
            script.write_text('@echo off\ncall "'+setup+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n', encoding='utf-8')
            with (directory/('build-'+str(index)+'.log')).open('wb') as log:
                result = subprocess.run(['cmd', '/d', '/c', str(script)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            if result.returncode: raise RuntimeError('Inspect isolated diagnostic build log '+str(index))
    finally:
        subprocess.run(['subst', drive, '/d'], capture_output=True, check=True)
    current(before)
    binary = directory/'lma_wan_latent_probe.exe'
    record = dict(schema='lma.wan-latent-probe-build/1', source_revision=SD_REVISION,
                  production_compilation=production, modified_seams=1,
                  original_video_cpp_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                  diagnostic_video_cpp_sha256=hashlib.sha256((directory/'video_probe.cpp').read_bytes()).hexdigest(),
                  sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), bytes=binary.stat().st_size,
                  packaged_in_apk=False, generation_completed=False, physical_android=False, input_fingerprint=before)
    (directory/'receipt.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return binary, record


if __name__ == '__main__':
    binary, record = build_probe()
    print(json.dumps(dict(file=binary.relative_to(ROOT).as_posix(), sha256=record['sha256'])))
