"""Review data-only HF identities/headers and build optional community model bundles.

Network access requires --refresh. Never fetch images, previews, prompts or complete
weights. A range response must be exact before a safetensors header is accepted.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'catalogue/community-sources.json'
EVIDENCE = ROOT / 'research/community/metadata.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def get(url, limit, byte_range=None):
    headers = {'User-Agent': 'curl/8.0'}
    if byte_range:
        headers['Range'] = 'bytes=%d-%d' % byte_range
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
        if byte_range:
            expected = 'bytes %d-%d/' % byte_range
            assert response.status == 206 and response.headers.get('Content-Range', '').startswith(expected), 'Server must honor the exact header range'
        body = response.read(limit + 1)
        assert len(body) <= limit, 'Metadata response too large'
        if byte_range:
            assert len(body) == byte_range[1] - byte_range[0] + 1
        return body


def review_header(url, architecture):
    size = struct.unpack('<Q', get(url, 8, (0, 7)))[0]
    assert 16 <= size <= 4 * 1024 * 1024, 'Unbounded safetensors header'
    raw = get(url, size, (8, size + 7))
    header = json.loads(raw)
    tensors = {k: v for k, v in header.items() if k != '__metadata__'}
    assert tensors and all(isinstance(v, dict) and 'shape' in v for v in tensors.values())
    names = list(tensors)
    checkpoint = any(k.startswith('model.diffusion_model.') for k in names)
    clip = any(k.startswith(('cond_stage_model.', 'conditioner.embedders.')) for k in names)
    vae = any(k.startswith('first_stage_model.') for k in names)
    if architecture == 'sd15':
        assert checkpoint and clip, 'Need a full SD 1.5 checkpoint, not UNet-only data'
        cross = [v['shape'] for k, v in tensors.items() if k.endswith('attn2.to_k.weight')]
        assert cross and all(s[-1] == 768 for s in cross), 'Not SD 1.5 cross attention'
    elif architecture == 'sdxl':
        assert checkpoint and clip, 'Need a full SDXL checkpoint'
        cross = [v['shape'] for k, v in tensors.items() if k.endswith('attn2.to_k.weight')]
        assert cross and all(s[-1] == 2048 for s in cross), 'Not SDXL cross attention'
    elif architecture == 'wan21':
        shapes = {k: v['shape'] for k, v in tensors.items()}
        assert shapes.get('patch_embedding.weight') == [1536, 16, 1, 2, 2], 'Only Wan 2.1 T2V 1.3B is integrated'
        assert 'blocks.29.self_attn.q.weight' in shapes and not any(k.startswith('blocks.30.') for k in shapes), 'Wrong Wan layer count'
    elif architecture == 'sd15_vae':
        assert 'encoder.conv_in.weight' in tensors and 'decoder.conv_out.weight' in tensors
    else:
        raise AssertionError('Unreviewed architecture')
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=size, tensorCount=len(tensors),
                architecture=architecture, checkpoint=checkpoint, textEncoderPresent=clip, vaePresent=vae,
                trainedWeightBytesFetched=0, inferenceTested=False)


def refresh(origin):
    assert origin in ('https://huggingface.co', 'https://hf-mirror.com')
    spec = read(SOURCE)
    repositories = {}
    for source in spec['repositories']:
        repo = source['repository']
        raw = get(origin + '/api/models/' + repo + '?blobs=true', 8 * 1024 * 1024)
        data = json.loads(raw)
        assert data['id'].lower() == repo.lower() and re.fullmatch('[a-f0-9]{40}', data['sha'])
        revision = data['sha']
        card = get(origin + '/' + repo + '/resolve/' + revision + '/README.md', 512 * 1024)
        for marker in source.get('cardMarkers', []):
            assert marker.casefold() in card.decode('utf-8').casefold(), 'Publisher marker changed: ' + repo
        files = {f['rfilename']: f for f in data['siblings']}
        selected = {}
        for variant in source['variants']:
            path = variant['file']
            file = files[path]
            lfs = file['lfs']
            assert re.fullmatch('[a-f0-9]{64}', lfs['sha256']) and lfs['size'] == file['size']
            url = origin + '/' + repo + '/resolve/' + revision + '/' + urllib.parse.quote(path, safe='/')
            header = review_header(url, source['architecture'])
            selected[path] = dict(bytes=file['size'], sha256=lfs['sha256'], header=header)
            print('Header checked:', repo, path, flush=True)
        repositories[repo] = dict(repository=repo, revision=revision, accessedVia=origin,
            apiSha256=hashlib.sha256(raw).hexdigest(), cardSha256=hashlib.sha256(card).hexdigest(),
            cardBytes=len(card), cardMarkers=source.get('cardMarkers', []),
            licenseMetadata=data.get('cardData', {}).get('license', ''),
            contentTags=[t for t in data.get('tags', []) if t in ('nsfw', 'not-for-all-audiences')], files=selected)
    write(EVIDENCE, dict(schema='lma.community-source-evidence/1', checkedAt='2026-10-31',
        metadataOnly=True, modelWeightsDownloaded=False, modelInferenceTested=False, physicalDeviceTests=0,
        sourceSpecSha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), repositories=repositories))


def build():
    spec, evidence = read(SOURCE), read(EVIDENCE)
    assert evidence['sourceSpecSha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert evidence['metadataOnly'] and not evidence['modelWeightsDownloaded'] and not evidence['modelInferenceTested']
    base = read(ROOT / 'catalogue/model-bundles.json')['bundles']
    templates = {t['id']: t for t in read(ROOT / 'app/src/main/assets/recipe-templates.json')['templates']}
    sd = next(b for b in base if b['pipeline'] == 'sd15')
    wan = next(b for b in base if b['engine'] == 'wan_sd_cpp')
    bundles, proofs = [], []
    for source in spec['repositories']:
        repo = source['repository']; checked = evidence['repositories'][repo]
        if source.get('dependencyOnly'): continue
        revision = checked['revision']; arch = source['architecture']
        for variant in source['variants']:
            file = variant['file']; item = checked['files'][file]
            assert item['header']['architecture'] == arch and item['header']['trainedWeightBytesFetched'] == 0
            template = templates['wan21_13b_split_vulkan_v1' if arch == 'wan21' else arch + '_checkpoint_cpu_v1']
            bundle = copy.deepcopy(template['definition'])
            key = variant['id'] + '_r' + revision[:7]
            content = copy.deepcopy(source['content'])
            content.update(checkedAt=evidence['checkedAt'], sourceRevision=revision,
                sourceUrl='https://huggingface.co/' + repo + '/blob/' + revision + '/README.md', modelQualityTested=False)
            if content['basis'] == 'publisher_filename':
                assert 'nsfw' in file.lower(); content['sourceUrl'] = 'https://huggingface.co/' + repo + '/blob/' + revision + '/' + file
            if content['basis'] == 'hf_sensitive_tag':
                assert 'not-for-all-audiences' in checked['contentTags']
            primary = dict(role='diffusion' if arch == 'wan21' else 'model', repository=repo, revision=revision,
                path=file, bytes=item['bytes'], sha256=item['sha256'], format='safetensors',
                url='https://huggingface.co/' + repo + '/resolve/' + revision + '/' + file)
            dependencies = copy.deepcopy([c for c in wan['components'] if c['role'] != 'diffusion'] if arch == 'wan21' else [c for c in sd['components'] if c['role'] == 'clip_merges'])
            dependencies += copy.deepcopy(source.get('extraComponents', []))
            for dep in source.get('extraDependencies', []):
                origin = evidence['repositories'][dep['repository']]; asset = origin['files'][dep['file']]
                dependencies.append(dict(role=dep['role'], repository=dep['repository'], revision=origin['revision'],
                    path=dep['file'], bytes=asset['bytes'], sha256=asset['sha256'], format='safetensors',
                    url='https://huggingface.co/' + dep['repository'] + '/resolve/' + origin['revision'] + '/' + dep['file']))
            if arch != 'wan21':
                assert item['header']['vaePresent'] or any(c['role'] == 'vae' for c in dependencies), 'Missing VAE'
            bundle.update(schema='lma.model-bundle/1', id=key, modelId=variant['id'], recipeId=template['id'],
                name=variant['name'], catalogue=True, content=content,
                community=dict(family=source['family'], variant=variant['name'], sourceRole=source.get('sourceRole', 'publisher'),
                    publisherUrl=source.get('publisherUrl', 'https://huggingface.co/' + repo), repository=repo),
                description=source['description'], license=dict(name=source['licenseName'], url=source.get('licenseUrl', content['sourceUrl'])),
                evidence=dict(status='header_checked_program_route_not_model_tested', physicalDeviceTests=0,
                    sourceUrl=content['sourceUrl'], header=item['header'], compatibilityNote=source['compatibilityNote']),
                resources=dict(estimatedPeakRamBytes=0, estimateKnown=False), components=[primary] + dependencies)
            immutable = hashlib.sha256(json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()[:10]
            key += '_c' + immutable; bundle['id'] = key
            bundles.append(bundle)
            # Existing shared assets keep their original provenance, not a fabricated fresh check.
            original = read(ROOT / 'catalogue/bundle-evidence.json')['bundles']
            dependency_proofs = {}
            for p in original:
                for c in p['components']:
                    dependency_proofs[(c.get('repository'), c.get('revision'), c.get('path'))] = c
            components = [dict(primary, kind='hf_lfs', live_hf_metadata_checked_this_update=True)]
            for c in dependencies:
                prior = dependency_proofs.get((c.get('repository'), c.get('revision'), c.get('path')))
                if prior is not None: components.append(copy.deepcopy(prior))
                else:
                    checked_dependency = evidence['repositories'][c['repository']]
                    asset = checked_dependency['files'][c['path']]
                    assert checked_dependency['revision'] == c['revision'] and asset['sha256'] == c['sha256'] and asset['bytes'] == c['bytes']
                    components.append(dict(c, kind='hf_lfs', live_hf_metadata_checked_this_update=True))
            proofs.append(dict(bundleId=key, components=components))
    assert len({b['id'] for b in bundles}) == len(bundles)
    write(ROOT / 'catalogue/community-bundles.json', dict(schema='lma.bundle-catalogue/1', bundles=bundles))
    write(ROOT / 'catalogue/community-bundle-evidence.json', dict(schema='lma.bundle-metadata-evidence/2',
        model_inference_tested=False, physical_device_tests=0, model_weights_downloaded=False, bundles=proofs))
    print('Community bundles:', len(bundles), 'families:', len({b['community']['family'] for b in bundles}),
          'NSFW labels:', sum(b['content']['classification'] == 'nsfw' for b in bundles))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--origin', default='https://huggingface.co')
    args = parser.parse_args()
    if args.refresh: refresh(args.origin)
    build()
