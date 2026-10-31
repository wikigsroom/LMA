"""Pinned publisher manifests, optional import-only assets; never fetch weights."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from expansion_catalogue import field

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='raven38/pixal3d.cpp'
REVISION='d1b4926452f9e09702b891db5f05acc845e153ed'
SOURCE=ROOT/'research/multiview/model-manifests.json'
ROLE={'shape_flow_512':'shape_flow','shape_flow_1024':'shape_flow_hr','texture_flow_1024':'texture_flow_hr'}

def capture():
    records=[]
    for quant in ('f16','q8_0'):
        path=f'models/pixal3d-{quant}-v1/pixal3d-models.json'
        data=subprocess.check_output(['git','show',REVISION+':'+path],cwd=ROOT/'build/native-src/pixal3d-mv-cpp')
        value=json.loads(data)
        assert len(value['files'])==9
        records.append(dict(quantization=quant,path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            gitBlob=subprocess.check_output(['git','rev-parse',REVISION+':'+path],cwd=ROOT/'build/native-src/pixal3d-mv-cpp',text=True).strip(),
            manifest=value,source_url='https://github.com/'+REPOSITORY+'/blob/'+REVISION+'/'+path))
    SOURCE.parent.mkdir(exist_ok=True)
    SOURCE.write_text(json.dumps(dict(schema='lma.multiview-model-metadata/1',repository=REPOSITORY,revision=REVISION,
        availability='import_only_no_verified_weight_download_endpoint',weight_hashes='publisher_declared_not_download_measured',
        model_weights_downloaded=False,model_inference_tested=False,physical_device_tests=0,manifests=records),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def parameters(texture=False):
    return dict(version=1,fields=dict(threads=field('integer','CPU 线程',2,1,16,presets=[1,2,4,8]),
        resolution=field('integer','3D 生成分辨率',1024,1024,1024),steps=field('integer','每阶段采样步数',12,1,50,presets=[4,8,12,20]),
        seed=field('integer','随机种子',1234,1,2147483647),faces=field('integer','输出网格面数目标',30000,1000,150000,presets=[10000,30000,60000]),
        atlas=field('integer','贴图图集尺寸',1024,256,2048,multipleOf=256,presets=[512,1024,2048]),guidance=field('number','引导强度',7.5,0,15),
        maxTokens=field('integer','稀疏 token 保护上限',8192,1024,49152,presets=[4096,8192,16384]),
        meshScale=field('number','相机对应的网格尺度',1,.1,10),texture=field('boolean','生成贴图',texture),
        cameraPoses=field('string','四视图相机参数（留空使用标准转台）','',maxLength=16000)))

def build():
    source=json.loads(SOURCE.read_text(encoding='utf-8'));assert source['revision']==REVISION
    bundles=[];proofs=[]
    for record in source['manifests']:
        for texture in (False,True):
            components=[]
            for item in record['manifest']['files']:
                role=ROLE.get(item['role'],item['role'])
                if not texture and role in ('texture_flow_hr','texture_decoder'):continue
                components.append(dict(role=role,format='gguf',path=item['name'],bytes=item['size_bytes'],sha256=item['sha256'],
                    repository=REPOSITORY,revision=REVISION,url=''))
            ident='pixal3d_mv_'+record['quantization']+('_pbr' if texture else '_geometry')+'_v1'
            bundles.append(dict(schema='lma.model-bundle/2',id=ident,modelId=ident,recipeId='pixal3d_mv_gguf_cpu_v1',
                name='Pixal3D MV · '+record['quantization'].upper()+' · '+('PBR' if texture else 'Geometry'),
                description='四张已标定、已去背景的 RGBA PNG → GLB；匹配 MV 全套权重，不接受单图 flow。仅校验导入：尚无已核实的公开权重下载地址。也可用自选配方从 HF 选择匹配组件。CPU / 1024 分辨率，未证明 Z20 内存足够；标准转台与自定义相机均需真实对应输入。',
                catalogue=True,engine='pixal_multiview',architecture='pixal3d_mv',pipeline='pixal3d_mv',backend='cpu',
                tasks=['3d'],capabilities=['multi_view_to_3d','posed_rgba_inputs']+(['pbr_materials'] if texture else []),
                parameters=parameters(texture),components=components,resources=dict(source='unmeasured',estimatedPeakRamBytes=0),
                content=dict(classification='unclassified',basis='none',summary='未获得明确内容声明；不推定为 NSFW 或无审查。'),
                license=dict(name='Model/component terms apply; source runtime MIT',url='https://github.com/'+REPOSITORY,status='component_terms_apply'),
                evidence=dict(status='compiled_program_only_not_model_or_device_tested',physicalDeviceTests=0,modelInferenceTested=False,
                    sourceUrl=record['source_url'],acquisition='import_only',hashBasis='publisher_manifest_not_measured_weights')))
            proofs.append(dict(bundleId=ident,components=[dict(c,kind='pinned_source_manifest',source='research/multiview/model-manifests.json',
                manifestSha256=record['sha256'],quantization=record['quantization']) for c in components]))
    return bundles,proofs

def recipes():
    b=copy.deepcopy(build()[0][-1]);definition={k:b[k] for k in ('engine','architecture','pipeline','backend','tasks','capabilities','parameters')}
    definition['parameters']=parameters(False)
    return [dict(id='pixal3d_mv_gguf_cpu_v1',name='Pixal3D MV · 四视图自选配套组件',primaryRole='image_encoder',definition=definition,
        requirements=[dict(role=c['role'],label=c['role']+' · '+c['path'],formats=['gguf'],required=c['role'] not in ('texture_flow_hr','texture_decoder'),matchFiles=[c['path']]) for c in b['components']],
        fixedComponents=[],help='从 HF 选择同一 MV 导出族配套组件，声明后自行确认下载或导入。四张 RGBA PNG 必须与相机参数一致；默认标准转台 20° 水平视角、零仰角、距离 3.119204998。允许填写四个 camera-to-world 矩阵与弧度制视角；不自动从任意照片恢复相机。1024、CPU，手机内存与效果未测。')]

def main():
    if not SOURCE.exists():capture()
    bundles,proofs=build()
    for filename,value in [('multiview-bundles.json',dict(schema='lma.bundle-catalogue/1',bundles=bundles)),
        ('multiview-bundle-evidence.json',dict(schema='lma.bundle-metadata-evidence/2',model_inference_tested=False,model_weights_downloaded=False,physical_device_tests=0,bundles=proofs))]:
        (ROOT/'catalogue'/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(bundles=len(bundles),recipes=len(recipes()),acquisition='import_only',model_weights_downloaded=False)))

if __name__=='__main__':main()
