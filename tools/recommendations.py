"""Validate the model-free recommendation registry against the actual bundled catalogue."""
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def check():
    policy = json.loads((ROOT/'app/src/main/assets/recommendations.json').read_text(encoding='utf-8'))
    assert policy['schema']=='lma.recommendations/1'
    assert policy['preservedTextIds']==['m08','m06','m01']
    assert not policy['automaticDownloads'] and not policy['phoneInferenceValidated']
    catalogue = {}
    for name in ('model-bundles','community-bundles','expansion-bundles','multiview-bundles'):
        for bundle in json.loads((ROOT/'catalogue'/(name+'.json')).read_text(encoding='utf-8'))['bundles']:
            assert bundle['id'] not in catalogue
            catalogue[bundle['id']]=bundle
    counts = {task:0 for task in ('image','video','audio','3d')}
    seen = set()
    for entry in policy['entries']:
        assert entry['bundleId'] not in seen
        seen.add(entry['bundleId'])
        bundle=catalogue[entry['bundleId']]
        assert entry['task'] in bundle['tasks'] and entry['task'] in counts
        counts[entry['task']]+=1
        assert bundle['catalogue'] and bundle['engine']!='asset_source'
        assert entry['bytes']==sum(item['bytes'] for item in bundle['components'])
        assert all(urlparse(item.get('url','')).scheme=='https' for item in bundle['components'])
        assert all(isinstance(entry[key],str) and 1<=len(entry[key])<=160 for key in ('reason','hint'))
        assert entry['sourceUrl']=='https://huggingface.co/'+bundle['components'][0]['repository']
    assert counts=={'image':3,'video':2,'audio':3,'3d':3},counts
    return dict(passed=True,text=3,**counts,total=3+len(seen),model_downloads=0)


if __name__=='__main__':
    print(json.dumps(check()))
