"""Code-only Pixal3D MV checkout and exact embedding patch; no model downloads."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from fetch_expansion_sources import git, sha

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'third_party/multiview-source-lock.json'


def prepare(folder):
    original = git(folder, 'show', 'HEAD:src/trellis_cli.cpp').decode('utf-8')
    patched = 'extern int lma_mv_steps();\nextern int lma_mv_faces();\nextern void lma_mv_stage(const char*);\n' + original
    # Apply controls to the actual upstream sampling calls, not just the UI snapshot.
    needle = 'trellis::sample_flow('
    assert patched.count(needle) >= 4
    marker = 'int trellis_run_mv(const trellis::TrellisParams& cfg) {'
    assert patched.count(marker) == 1
    wrapper = '''static std::vector<float> lma_mv_sample_flow(const trellis::FlowFwdProj& f,
    const std::vector<float>& noise, const float* cond, const float* negative,
    const float* proj, const float* negproj, trellis::SamplerParams p) {
    p.steps = lma_mv_steps();
    return trellis::sample_flow(f,noise,cond,negative,proj,negproj,p);
}
'''
    # Only compile the MV entry point. Keep the shared helpers preceding it, omit
    # the SV/TRELLIS CLI bodies after it. No server, installer or downloader.
    start = patched.index(marker)
    end_marker = '// --sv-image:'
    end = patched.index(end_marker, start)
    patched = patched[:start] + patched[start:end].replace(needle, 'lma_mv_sample_flow(')
    patched = patched[:patched.index(marker)] + wrapper + patched[patched.index(marker):]
    patched = patched.replace('1000000, dv, df', 'lma_mv_faces(), dv, df')
    cap = '        if ((int)q.size() < cfg.max_tokens || hr_res == 1024) {'
    assert patched.count(cap) == 1
    patched = patched.replace(cap, '        if ((int)q.size() > cfg.max_tokens) throw std::runtime_error("Selected sparse token budget exceeded");\n' + cap)
    # Geometry-only outputs also honor the requested simplification target.
    marker = '    mv_apply_reference_frame(mesh.verts);'
    assert patched.count(marker) == 1
    patched = patched.replace(marker, '''    if (!textured && mesh.F() > lma_mv_faces()) {
        std::vector<float> v; std::vector<int32_t> f;
        trellis::decimate_qem(mesh.verts, mesh.V(), mesh.faces, mesh.F(), lma_mv_faces(), v, f);
        mesh.verts.swap(v); mesh.faces.swap(f);
    }
''' + marker)
    for prefix, stage in [('[1/6]', 'loading_views'), ('[2/6]', 'sparse_structure'),
                          ('[3/6]', 'shape_sampling'), ('[4/6]', 'shape_decoding'),
                          ('[5/6]', 'texture_sampling'), ('[6/6]', 'exporting_glb')]:
        patched = patched.replace('printf("'+prefix, 'lma_mv_stage("'+stage+'"); printf("'+prefix)
    output = ROOT / 'build/multiview-generated/trellis_cli.cpp'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(patched.encode())
    uv_original=git(folder,'show','HEAD:src/uv_bake.cpp').decode('utf-8')
    uv=uv_original.replace('auto pack = [](int64_t cx, int64_t cy, int64_t cz)', 'auto pack = [=](int64_t cx, int64_t cy, int64_t cz)').replace('auto clampc = [](int64_t c)', 'auto clampc = [=](int64_t c)')
    assert uv!=uv_original
    uv_output=output.with_name('uv_bake.cpp');uv_output.write_bytes(uv.encode())
    return dict(file='src/trellis_cli.cpp',upstream_sha256=hashlib.sha256(original.encode()).hexdigest(),
                patched_sha256=sha(output),uv_bake_upstream_sha256=hashlib.sha256(uv_original.encode()).hexdigest(),
                uv_bake_patched_sha256=sha(uv_output),changes=['MV-only embedding','actual sampler step control',
                    'bounded face target for both outputs','protocol stages','hard sparse token budget','explicit constexpr lambda captures for MSVC'])


def fetch():
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    for item in lock['sources']:
        folder = ROOT/item['directory']
        if not (folder/'.git').exists():
            subprocess.run(['git','clone','--depth','1','--filter=blob:none','--no-checkout',item['clone'],str(folder)],check=True)
        if git(folder,'rev-parse','HEAD').decode().strip()!=item['revision']:
            git(folder,'fetch','--depth','1','origin',item['revision'])
        keep=[]
        for entry in git(folder,'ls-tree','-r','-z',item['revision']).split(b'\0'):
            if not entry: continue
            meta,name=entry.split(b'\t',1)
            if meta.split()[1]!=b'blob':continue
            name=name.decode(); p=PurePosixPath(name)
            if any(part in ('tests','test','assets','models','data','resources','fixtures','web','app','install','docker') for part in p.parts):continue
            if p.suffix in ('.cpp','.c','.cc','.h','.hpp','.in','.cmake','.inc','.S','.s','.txt','.md','.cu','.cuh','.ipp','.def','.comp','.py','.m','.mm','.metal','.glsl') or p.name in ('LICENSE','NOTICE','.gitmodules'):
                keep.append('/'+name)
        git(folder,'sparse-checkout','init','--no-cone')
        (folder/'.git/info/sparse-checkout').write_text('\n'.join(keep)+'\n',encoding='utf-8')
        git(folder,'checkout','--detach',item['revision']);git(folder,'sparse-checkout','reapply')
    return verify()


def verify():
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    for item in lock['sources']:
        folder=ROOT/item['directory']
        assert git(folder,'rev-parse','HEAD').decode().strip()==item['revision']
        assert not git(folder,'status','--porcelain','--untracked-files=no').strip()
        for pattern in ('*.gguf','*.safetensors','*.onnx','*.pth','*.pt'):
            assert not list(folder.rglob(pattern)), 'Learned asset in code checkout'
    patch=prepare(ROOT/lock['sources'][0]['directory'])
    (ROOT/'build/multiview-generated/patch.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8')
    return lock


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fetch',action='store_true');args=parser.parse_args()
    fetch() if args.fetch else verify()
    print('Pinned multiview code verified; no learned model assets fetched.')
