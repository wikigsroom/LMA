"""Actual pinned camera/projection and worker guards; no trained weights or emulator."""
import copy,json,os,struct,subprocess
from pathlib import Path
from evidence import current,fingerprint
from fetch_multiview_sources import verify
ROOT=Path(__file__).resolve().parents[1]

def main():
    verify()
    inputs=fingerprint('native/multiview','native/worker_common.hpp','native/runtime_metrics.hpp','tools/build_multiview.py','tools/fetch_multiview_sources.py',
        'tools/test_multiview.py','tests/expansion-native/multiview.cpp','third_party/multiview-source-lock.json','research/multiview','tools/multiview_catalogue.py','catalogue/multiview-bundles.json')
    out=ROOT/'build/multiview-tests';out.mkdir(exist_ok=True)
    alias=None
    for letter in 'UVWXYZT':
        if not Path(letter+':/').exists() and subprocess.run(['subst',letter+':',str(ROOT)],capture_output=True).returncode==0:alias=letter+':';break
    assert alias
    try:
        a=alias+'/';source=a+'build/native-src/pixal3d-mv-cpp/';target=a+'build/multiview-tests/'
        setup=r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
        command=['cl','/nologo','/std:c++17','/utf-8','/EHsc','/O2','/D_USE_MATH_DEFINES','/I',source+'include','/Fe:'+target+'projection.exe','/Fo:'+target,
            a+'tests/expansion-native/multiview.cpp',source+'src/proj_grid.cpp',source+'src/transforms_json.cpp']
        script=out/'compile.cmd';script.write_text('@echo off\ncall "'+setup+'" >nul\n'+subprocess.list2cmdline(command)+'\n',encoding='utf-8')
        result=subprocess.run(['cmd','/d','/c',str(script)],capture_output=True);(out/'compile.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,'Inspect multiview-tests/compile.log'
        projection=json.loads(subprocess.check_output([target+'projection.exe',target],text=True,encoding='utf-8'))
        worker=a+'build/multiview-host/lma-multiview.exe';info=json.loads(subprocess.check_output([worker,'--info'],text=True));assert info['views']==4 and not info['modelInferenceTested']
        work=out/'work';work.mkdir(exist_ok=True);(work/'models').mkdir(exist_ok=True);(work/'views').mkdir(exist_ok=True)
        header=b'\x89PNG\r\n\x1a\n'+struct.pack('>I4sIIBBBBB',13,b'IHDR',16,16,8,6,0,0,0)
        names=['00_front.png','01_right.png','02_back.png','03_left.png']
        request=dict(schema='lma.engine-request/1',type='mesh.generate',pipeline='pixal3d_mv',parameters={},
            workspace=target+'work/models',viewsDirectory=target+'work/views',output=target+'work/output.glb')
        case_names=['missing_weights','rgb_input','oversized_pixels','truncated_input','missing_view','camera_count','camera_url','camera_fov','camera_scale','camera_reflection','camera_origin','wrong_task']
        results=[]
        for name in case_names:
            for file in names:(work/'views'/file).write_bytes(header)
            value=copy.deepcopy(request)
            camera=dict(frames=[dict(camera_angle_x=.34906585,transform_matrix=[[1,0,0,0],[0,1,0,0],[0,0,1,3],[0,0,0,1]]) for _ in range(4)])
            if name=='rgb_input':(work/'views'/names[0]).write_bytes(header[:25]+b'\x02'+header[26:])
            if name=='oversized_pixels':(work/'views'/names[0]).write_bytes(header[:16]+struct.pack('>II',8192,8192)+header[24:])
            if name=='truncated_input':(work/'views'/names[0]).write_bytes(b'png')
            if name=='missing_view':(work/'views'/names[0]).unlink()
            if name=='camera_count':camera['frames'].pop()
            if name=='camera_url':camera['frames'][0]['file_path']='https://example.invalid'
            if name=='camera_fov':camera['frames'][0]['camera_angle_x']=4
            if name=='camera_scale':camera['frames'][0]['transform_matrix'][0][0]=2
            if name=='camera_reflection':camera['frames'][0]['transform_matrix'][0][0]=-1
            if name=='camera_origin':camera['frames'][0]['transform_matrix'][2][3]=0
            if name=='wrong_task':value['type']='image.generate'
            if name.startswith('camera_'):value['parameters']['cameraPoses']=json.dumps(camera)
            file=out/'request.json';file.write_text(json.dumps(value),encoding='utf-8')
            result=subprocess.run([worker,target+'request.json'],capture_output=True,text=True,encoding='utf-8',timeout=15)
            events=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            assert result.returncode!=0 and any(e['event']=='error' for e in events) and not any(e['event']=='complete' for e in events),name
            measurements=next(e['details']['runtimeMeasurements'] for e in events if e['event']=='execution' and 'runtimeMeasurements' in e['details'])
            assert measurements['elapsedMs']>=0 and not measurements['qualityAssessed'] and measurements['memoryScope']=='worker_process_peak_rss_not_model_peak_or_whole_app',name
            results.append(dict(case=name,exit=result.returncode,expected_rejection=True,observations=measurements))
        report=dict(passed=projection['passed']+len(results)*2+1,projection=projection,cases=results,actual_native_worker_processes=len(results),
            trained_model=False,complete_model_downloads=0,physical_android=False,virtualization_used=False,input_fingerprint=inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    current(inputs);(out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ('input_fingerprint','cases')}))

if __name__=='__main__':main()
