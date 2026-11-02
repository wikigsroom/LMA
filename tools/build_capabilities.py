"""Package reviewed capability declarations without changing frozen model selections."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    plan=json.loads((ROOT/'docs/proposals/update-direction-20261102.json').read_text(encoding='utf-8'))
    result={'schema':'lma.capabilities/1','reviewedAt':'2026-11-02','models':{},'sources':plan['sources']}
    for record in plan['languageModels']:
        result['models'][record['modelId']]={
            'native':record['capabilities'],'artifact':record['selectedArtifact'],
            'lma':{'operations':['text.generate'],'visionBridge':'component_pair_required' if record['modelId'] in ['m03','m09','m15','m16'] else 'not_declared',
                   'toolParser':'implemented','modelToolReliability':'unknown','phoneVerified':False},
            'composed':['tool:media-generation'],'evidence':{'declared':True,'pinnedExportPair':False,'programBridge':True,'phoneOutput':False,'quality':False}}
    (ROOT/'app/src/main/assets/capabilities.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('14 exact language-model capability declarations packaged; no assets downloaded')

if __name__=='__main__': main()
