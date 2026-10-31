"""Read pinned upstream source metadata only; never install or execute upstream code."""
import concurrent.futures
import base64
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
GH = ROOT / 'build/github-cli/gh.exe'
TARGETS = [
    ('D04', 'yiboz2001/UltraTex', ['setup.py', 'requirements.txt'],
     ['mesh input and G-buffer rasterizer', 'BTD/BSA sparse-attention kernels', 'matched diffusion/VAE weights and PBR baking']),
    ('D05', 'xibushu/UniForge3D', ['setup.sh', 'requirements.txt'],
     ['VGGT pose estimation', 'anchor-guided multiview fusion', 'sparse geometry decoder and matching weights']),
    ('D06', 'PKU-YuanGroup/UltraShape-1.0', ['requirements.txt', 'setup.py'],
     ['coarse-mesh input', 'voxel-query/RoPE refinement model', 'surface extraction and matched exported weights']),
    ('D07', 'Tencent-Hunyuan/Hunyuan3D-2.1', ['requirements.txt', 'setup.py'],
     ['shape flow/VAE and surface extraction', 'separate Paint path and rasterizer if requested', 'architecture-specific tensor/operator validation']),
    ('D08', 'facebookresearch/sam-3d-objects', ['requirements.txt', 'pyproject.toml', 'doc/setup.md'],
     ['masked-image/depth conditioning', 'sparse generation and layout operators', 'matched geometry/appearance decoding']),
    ('D09', 'devinli123/MV-SAM3D', ['requirements.txt', 'environment.yml'],
     ['SAM 3D Objects native port', 'Depth Anything 3 native port', 'mask/pose alignment and scene fusion']),
    ('D10', 'Supra-3D/SUPRA-Tex', ['requirements.txt', 'setup.sh'],
     ['local geometry and material predictor', 'interleaved completion model and sparse/raster kernels', 'local-only replacement for any optional external back-image stage']),
    ('D11', 'VAST-AI-Research/TripoSG', ['requirements.txt', 'setup.py'],
     ['rectified-flow transformer', 'SDF VAE and surface extraction', 'matching native export and tensor layout']),
    ('D12', 'wgsxm/PartCrafter', ['requirements.txt', 'setup.py'],
     ['compositional part transformer', 'part-aware VAE/meshing', 'multiple-part artifact/scene output contract']),
]


def audit(target):
    number, repo, extra, work = target
    commit = json.loads(subprocess.check_output([str(GH), 'api', 'repos/' + repo + '/commits?per_page=1'], cwd=ROOT))[0]['sha']
    assert len(commit) == 40
    directory = ROOT / 'build/portability-audit' / repo.replace('/', '-')
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    for name in ['README.md', *extra]:
        url = 'https://raw.githubusercontent.com/' + repo + '/' + commit + '/' + name
        response = subprocess.run([str(GH), 'api', 'repos/' + repo + '/contents/' + name + '?ref=' + commit],
                                  cwd=ROOT, capture_output=True, timeout=40)
        if response.returncode:
            if b'404' in response.stderr:
                continue
            raise RuntimeError('Source metadata unavailable: ' + repo + '/' + name)
        value = json.loads(response.stdout)
        assert value['type'] == 'file' and value['size'] <= 200000 and value['encoding'] == 'base64'
        data = base64.b64decode(value['content'])
        assert len(data) <= 200000
        (directory / name.replace('/', '__')).write_bytes(data)
        files.append(dict(path=name, url=url, git_blob=value['sha'], bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    assert files and files[0]['path'] == 'README.md'
    return dict(id=number, repository=repo, revision=commit, files=files,
                program_integrated=False, integration_status='native_architecture_port_required',
                remaining_implementation=work, phone_feasibility='not_established',
                source_review_is_full_operator_audit=False)


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        targets = list(pool.map(audit, TARGETS))
    previous = json.loads((ROOT / 'research/expansion/benchmark-audit.json').read_text(encoding='utf-8'))
    cases = []
    for original in previous['cases']:
        row = {k: original[k] for k in ('number', 'case_id', 'model', 'case_url')}
        row['program_integrated'] = original['number'] in [1, 2, 3, 13, 14]
        row['current_scope'] = ('four_posed_rgba_views_1024_cpu_import_only' if original['number'] == 3 else
                                'single_image_subset' if row['program_integrated'] else 'native_architecture_port_required')
        row['exact_benchmark_workflow_reproduced'] = False
        cases.append(row)
    output = dict(schema='lma.portability-audit/1', app_version='0.3.3', checked_date='2026-10-31',
                  benchmark=previous['collection_url'], prior_audit='research/expansion/benchmark-audit.json',
                  integrated_architectures=['trellis2', 'pixal3d', 'pixal3d_mv'],
                  all_benchmark_architectures_integrated=False, unported_configurations=targets, cases=cases,
                  trained_model_downloads=0, trained_model_runs=0, physical_android_tests=0,
                  virtualization_used=False, upstream_code_executed=False,
                  conclusion='Desktop Python/CUDA sources are research inputs, not Android executables. Native ports remain implementation work; no remote fallback.')
    path = ROOT / 'research/portability/audit-v0.3.3.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(configurations=len(targets), cases=len(cases), all_integrated=False, model_downloads=0)))


if __name__ == '__main__':
    main()
