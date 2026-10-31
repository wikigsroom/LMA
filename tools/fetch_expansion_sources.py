"""Fetch pinned source code only; never fetch trained weights, demos or voice data."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'third_party/expansion-source-lock.json'


def git(folder, *args):
    return subprocess.check_output(['git', *args], cwd=folder, stderr=subprocess.STDOUT)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_audio(folder):
    """An exact, reviewable embedding patch; leave upstream model code unchanged."""
    file = folder / 'CMakeLists.txt'
    original = git(folder, 'show', 'HEAD:CMakeLists.txt').decode('utf-8')
    marker = 'file(GLOB AUDIOCPP_RECIPE_PLUGIN_SOURCES CONFIGURE_DEPENDS'
    assert original.count(marker) == 1
    patched = original.replace(marker, 'if(LMA_EMBEDDING_ONLY)\n    return()\nendif()\n\n' + marker)
    assert file.read_bytes().replace(b'\r\n', b'\n') in (original.encode(), patched.encode()), 'Unexpected upstream source edits'
    file.write_bytes(patched.encode())
    patches = [{'file': 'CMakeLists.txt', 'upstream_sha256': hashlib.sha256(original.encode()).hexdigest(), 'patched_sha256': sha(file),
                'change': 'return after runtime libraries; no CLI/server/WebUI/demo/download tools configured'}]
    name = 'src/framework/model_spec/package.cpp'; file = folder / name
    original = git(folder, 'show', 'HEAD:' + name).decode('utf-8')
    needle = '        root = engine::io::json::parse(spec->json);'
    assert original.count(needle) == 1
    replacement = '''        // LMA: a user GGUF cannot replace signed adapter resource paths/options.
        const auto builtin = builtin_model_spec(std::filesystem::path("model_specs") / (spec->family + ".json"));
        if (!builtin) throw std::runtime_error("LMA requires a signed model specification");
        root = engine::io::json::parse(*builtin);'''
    patched = original.replace(needle, replacement)
    assert file.read_bytes().replace(b'\r\n', b'\n') in (original.encode(), patched.encode()), 'Unexpected package source edits'
    file.write_bytes(patched.encode())
    patches.append({'file': name, 'upstream_sha256': hashlib.sha256(original.encode()).hexdigest(), 'patched_sha256': sha(file),
                    'change': 'use compiled signed family spec for GGUF; ignore user-supplied executable/resource configuration'})
    return patches


def fetch():
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    for item in lock['sources']:
        folder = ROOT / item['directory']
        if not (folder / '.git').exists():
            subprocess.run(['git', 'clone', '--depth', '1', '--filter=blob:none', '--no-checkout',
                            item['clone'], str(folder)], check=True)
        if git(folder, 'rev-parse', 'HEAD').decode().strip() != item['revision']:
            git(folder, 'fetch', '--depth', '1', 'origin', item['revision'])
        # Select code directly from the Git tree; no excluded weight blob is downloaded.
        tree = git(folder, 'ls-tree', '-r', '-z', item['revision'])
        keep = []
        extensions = {'.cpp', '.cc', '.c', '.h', '.hpp', '.hh', '.in', '.cmake', '.json', '.inc', '.def',
                      '.rc', '.txt', '.md', '.cu', '.cuh', '.metal', '.glsl', '.comp', '.py', '.S', '.s',
                      '.mm', '.vert', '.frag', '.cl', '.m', '.proto', '.toml', '.cfg', '.csv', '.ipp', '.cxx',
                      '.bat', '.sh', '.yml', '.yaml', '.manifest'}
        for entry in tree.split(b'\0'):
            if not entry:
                continue
            meta, name = entry.split(b'\t', 1)
            if meta.split()[1] != b'blob':
                continue
            name = name.decode('utf-8'); path = PurePosixPath(name)
            if path.parts[0] in ('assets', 'tests', 'webui') or any(p in path.parts for p in ('tests', 'test', 'data', 'testdata', 'voices', 'espeak-ng', 'resources', 'fixtures')):
                continue
            if path.suffix in extensions or path.name in ('LICENSE', 'COPYING', 'NOTICE', '.gitmodules'):
                keep.append('/' + name)
        git(folder, 'sparse-checkout', 'init', '--no-cone')
        (folder / '.git/info/sparse-checkout').write_text('\n'.join(keep) + '\n', encoding='utf-8')
        # Only the documented CMake embedding patch is permitted.
        if item['id'] == 'audio':
            cmake = folder / 'CMakeLists.txt'
            if cmake.exists():
                prepare_audio(folder)
                git(folder, 'restore', '--source=HEAD', '--', 'CMakeLists.txt', 'src/framework/model_spec/package.cpp')
        git(folder, 'checkout', '--detach', item['revision'])
        git(folder, 'sparse-checkout', 'reapply')
        if item['id'] == 'audio':
            patch = prepare_audio(folder)
            print(json.dumps({'source': item['id'], 'revision': item['revision'], 'files': len(keep), 'embedding_patch': patch}))
        else:
            print(json.dumps({'source': item['id'], 'revision': item['revision'], 'files': len(keep)}))
    verify()


def verify():
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    for item in lock['sources']:
        folder = ROOT / item['directory']
        assert git(folder, 'rev-parse', 'HEAD').decode().strip() == item['revision']
        status = git(folder, 'status', '--porcelain', '--untracked-files=no').decode().strip()
        if item['id'] == 'audio':
            prepare_audio(folder)
            modified = {line[3:] for line in git(folder, 'status', '--porcelain', '--untracked-files=no').decode().splitlines()}
            assert modified <= {'CMakeLists.txt', 'src/framework/model_spec/package.cpp'}
        else:
            assert not status, 'Unreviewed source modifications'
        for pattern in ('*.safetensors', '*.onnx', '*.gguf', '*.pt', '*.pth', '*.tflite'):
            assert not list(folder.rglob(pattern)), 'A trained asset entered the code-only source checkout'
    return lock


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    if args.fetch:
        fetch()
    else:
        verify()
        print('Pinned source code verified; no model assets downloaded.')
