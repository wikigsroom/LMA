"""Run production HF inventory/review/apply with explicit metadata fixtures."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import current, fingerprint

ROOT=Path(__file__).resolve().parents[1]


def main():
    backend=json.loads((ROOT/'build/backend-tests/results.json').read_text(encoding='utf-8'))
    current(backend['input_fingerprint'])
    inputs=fingerprint('app/src/main/java','app/src/main/assets/recipe-templates.json','tests/host','tools/recipe_file_hints.py','tools/build_recipe_templates.py','tools/test_recipe_suggestions.py')
    previous=ROOT/'build/recipe-suggestion-tests/dev33-templates.json';previous.parent.mkdir(parents=True,exist_ok=True)
    old=subprocess.check_output(['git','show','bb10c11714ab715258e20a904dd11a049e685701:app/src/main/assets/recipe-templates.json'],cwd=ROOT);previous.write_bytes(old)
    result=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-cp',str(ROOT/'build/backend-tests/classes')+os.pathsep+str(ROOT/'build/test-deps/json-20250517.jar'),'com.lma.app.RecipeSuggestionsTest',str(ROOT),str(previous)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=90)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    file=ROOT/'build/recipe-suggestion-tests/results.json';report=json.loads(file.read_text(encoding='utf-8'));current(inputs)
    report.update(historical_identity_source_commit='bb10c11714ab715258e20a904dd11a049e685701',scope='Production Java HF client/controller/persistent store; exact-revision pagination, file-name-only suggestions, explicit application, stale/cancel cases. Metadata/byte fixtures, no model downloads or inference, no Android acceptance.',input_fingerprint=inputs)
    file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['passed','checks','asset_downloads','model_inference','physical_android']}))


if __name__=='__main__':main()
