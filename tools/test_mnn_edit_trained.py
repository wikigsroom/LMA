"""Execute the production fixed-style image-edit worker with all fifteen selected assets."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from PIL import Image

from build_mnn_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_mnn_edit_trained import verify, inputs as asset_inputs
from fetch_mnn_trained import sha
from test_mnn_trained import workspace, image_stats, difference
from test_sd15_trained import execute

ROOT = Path(__file__).resolve().parents[1]
PROMPT = 'Convert to a Ghibli-style illustration: soft contrast, warm tones, slight linework, keep the scene consistent.'


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint('tools/test_mnn_edit_trained.py',
        'tools/test_mnn_trained.py', 'tools/test_sd15_trained.py', 'tests/fixtures/images')}


def main():
    before = inputs(); lock = verify(); binary, compilation = build()
    folder = ROOT / 'build/mnn-edit-trained-tests' / ('run-' + str(time.time_ns())); folder.mkdir(parents=True)
    source = folder / 'source.png'; shutil.copy2(ROOT / 'tests/fixtures/images/astronaut.png', source)
    jpeg = folder / 'source-crop.jpg'
    with Image.open(source) as image:
        image.convert('RGB').crop((60, 20, 460, 320)).save(jpeg, quality=95)
    corrupt = folder / 'corrupt.png'; corrupt.write_bytes(source.read_bytes()[:24])
    oversized = folder / 'oversized.png'; data = bytearray(source.read_bytes()[:24]); data[16:24] = (4096).to_bytes(4, 'big') * 2; oversized.write_bytes(data)
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    checks = []; runs = []; outputs = {}; comparisons = {}
    def check(value, description): checks.append(dict(passed=bool(value), description=description))
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        root = workspace(folder, lock, alias)
        info, logs = execute([alias(binary), '--info'], dict(os.environ), timeout=30)
        check(info['returncode'] == 0 and len(info['events']) == 1 and info['events'][0].get('engine') == 'mnn_diffusion', 'Production native identity')

        def invoke(name, selected=source, prompt=PROMPT, parameters=None, negative='', pipeline='sana_edit_mnn_v1', broken=None, expect=True):
            p = dict(width=512, height=512, steps=10, threads=4, maxInputTokens=512, useCfg=False, cfg=4, seed=42)
            if parameters: p.update(parameters)
            output = folder / (name + '.png')
            command = dict(schema='lma.engine-request/1', type='image.generate', pipeline=pipeline,
                           input=dict(prompt=prompt, negativePrompt=negative, imagePath=alias(selected)),
                           parameters=p, workspace=alias(root), output=alias(output))
            request = folder / (name + '.json'); request.write_text(json.dumps(command, indent=2) + '\n', encoding='utf-8')
            removed = root / broken if broken else None
            if removed: os.unlink(removed)
            print('Execute real image-edit components:', name, flush=True)
            try: result, logs = execute([alias(binary), alias(request)], dict(os.environ), timeout=600)
            finally:
                if removed:
                    from fetch_mnn_trained import asset_path
                    original = next(asset_path(i) for i in lock['components'] if Path(i['path']).name == removed.name)
                    os.link(original, removed)
            stdout = folder / (name + '.stdout'); stderr = folder / (name + '.stderr')
            stdout.write_bytes(logs[0]); stderr.write_bytes(logs[1])
            complete = [e for e in result['events'] if e.get('event') == 'complete']
            check(not result['timed_out'] and not result['protocol_errors'] and not any(result['logs_truncated']) and not logs[1], name + ': bounded structured protocol')
            item = dict(name=name, request=command, process=result, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
            if expect:
                check(result['returncode'] == 0 and len(complete) == 1 and output.is_file(), name + ': actual complete image')
                if output.is_file():
                    item['image'] = image_stats(output); outputs[name] = output
                    check(item['image']['width'] == 512 and item['image']['height'] == 512 and max(item['image']['stddev']) > 1, name + ': actual 512x512 nonuniform image, not a quality gate')
                    check(complete[0]['output'] == alias(output) and complete[0]['format'] == 'png', name + ': output provenance')
                check([e['fraction'] for e in result['events'] if e.get('event') == 'progress'] == [(i+1)/p['steps'] for i in range(p['steps'])], name + ': real sampling steps')
                check([e['stage'] for e in result['events'] if e.get('event') == 'stage'] == ['encoding_text', 'loading_diffusion', 'encoding_image'], name + ': text, diffusion and source-image stages')
                check(result['resources']['observed'], name + ': native host resources observed')
            else:
                check(result['returncode'] != 0 and not complete and not output.exists(), name + ': failure publishes no artifact')
            runs.append(item)

        invoke('a')
        invoke('jpeg-crop', selected=jpeg)
        invoke('single-step', parameters={'steps': 1})
        invoke('missing-image', selected=folder/'not-selected.png', expect=False)
        invoke('oversized-image', selected=oversized, expect=False)
        invoke('corrupt-image', selected=corrupt, expect=False)
        invoke('arbitrary-prompt', prompt='a red teapot', expect=False)
        invoke('negative-conditioning', negative='blurry', expect=False)
        invoke('unsupported-cfg', parameters={'useCfg': True}, expect=False)
        invoke('unsupported-resolution', parameters={'width': 256}, expect=False)
        invoke('legacy-text-pipeline', pipeline='sana_mnn_v1', expect=False)
        invoke('missing-image-encoder', broken='models/vae_encoder.mnn', expect=False)
        invoke('token-budget', parameters={'maxInputTokens': 1}, expect=False)
        invoke('recovery-a')
        for name, left, right in [('source-effect', 'a', 'jpeg-crop'), ('step-effect', 'a', 'single-step'), ('recovery', 'a', 'recovery-a')]:
            if left in outputs and right in outputs:
                comparisons[name] = difference(outputs[left], outputs[right])
                check(comparisons[name]['maximum'] == 0 if name == 'recovery' else comparisons[name]['maximum'] > 0, name + ': observed same-host pixel relationship')
            else: check(False, name + ': missing output')
    finally: subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    verify(); current(before)
    report = dict(schema='lma.mnn-edit-trained-host/1', passed=all(i['passed'] for i in checks), checks=checks,
                  compilation=compilation, assets=lock['components'], runs=runs, comparisons=comparisons,
                  source_images=[dict(file=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=sha(p)) for p in (source,jpeg)],
                  capture_directory=folder.relative_to(ROOT).as_posix(), real_trained_host_execution=True,
                  task='image_to_image', fixed_style=True, model_data_bundled=False, network_inference=False,
                  physical_android=False, independent_reference_numerics_accepted=False, image_quality_accepted=False,
                  complete_target04_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    for path in (folder/'results.json',folder.parent/'results.json'): path.write_text(json.dumps(report, indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'], checks=len(checks), runs=len(runs), images=len(outputs), capture_directory=report['capture_directory'])),flush=True)
    if not report['passed']: raise RuntimeError('Inspect actual edit execution checks')


if __name__ == '__main__': main()
