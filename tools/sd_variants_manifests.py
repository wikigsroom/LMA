"""Metadata-only optional import manifests, reusing the shipped diffusion recipes."""
import argparse
import copy
import json
from pathlib import Path

from evidence import fingerprint
from fetch_sd15_trained import bundle as sd15_bundle
from fetch_sd_variants_trained import selected

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'research/sd_variants_trained/manifests'
IDS = dict(sdxl_base_q4_0='sdxl_genai_q4_0_ra02cea3', sd15_style_pixelart='sd15_pixelart_redmond_reb7c3bf',
           sdxl_style_pixelart='sdxl_pixelart_nerijs_r8bf4a4d', sd15_lcm_lora='sd15_lcm_lora_rcf2fced',
           sdxl_lcm_lora='sdxl_lcm_lora_ra18548d')


def inputs():
    return fingerprint('tools/sd_variants_manifests.py', 'research/sd_variants_trained/assets.json',
                       'app/src/main/assets/recipe-templates.json', 'app/src/main/assets/model-bundles.json')


def manifests():
    templates = {t['id']: t for t in json.loads((ROOT / 'app/src/main/assets/recipe-templates.json').read_text(encoding='utf-8'))['templates']}
    result = {}; base = sd15_bundle(); merges = next(c for c in base['components'] if c['role'] == 'clip_merges')
    for item in selected()['assets']:
        adapter = item['role'] == 'lora'; arch = item['architecture']
        template_id = arch + ('_lcm_lora_cpu_v1' if item['sampling'] == 'lcm' else '_lora_cpu_v1' if adapter else '_checkpoint_cpu_v1')
        value = copy.deepcopy(templates[template_id]['definition'])
        value.update(schema='lma.model-bundle/1', id=IDS[item['id']], modelId=IDS[item['id']], recipeId=template_id,
                     name={'sdxl_base_q4_0': 'SDXL Base 1.0 Q4_0 (genai-archive)',
                           'sd15_style_pixelart': 'PixelArtRedmond SD 1.5', 'sdxl_style_pixelart': 'Pixel Art XL (nerijs)',
                           'sd15_lcm_lora': 'LCM-LoRA SD 1.5', 'sdxl_lcm_lora': 'LCM-LoRA SDXL'}[item['id']])
        value['components'] = [{key: item[key] for key in ['role', 'format', 'repository', 'revision', 'path', 'bytes', 'sha256', 'url']}]
        if not adapter: value['components'].append(copy.deepcopy(merges))
        else:
            value['adapter']['baseModelIds'] = [base['modelId'] if arch == 'sd15' else IDS['sdxl_base_q4_0']]
        # No trusted-catalogue or phone-validation flags: these are independent user imports.
        result[item['id']] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--write', action='store_true'); args = parser.parse_args()
    values = manifests()
    if args.write:
        DIRECTORY.mkdir(parents=True, exist_ok=True)
        for key, value in values.items():
            path = DIRECTORY / (key + '.json'); data = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
            if path.exists() and path.read_bytes() != data.encode('utf-8'): raise FileExistsError('Preserve existing import manifest')
            if not path.exists(): path.write_text(data, encoding='utf-8')
    for key, value in values.items():
        if json.loads((DIRECTORY / (key + '.json')).read_text(encoding='utf-8')) != value: raise ValueError('Changed optional import manifest')
    print('Five optional data-only manifests verified; no model is installed or downloaded.')


if __name__ == '__main__': main()
