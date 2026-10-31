"""Literal pinned MoGe focal recovery / DA3 metric camera postprocessing."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from evidence import ROOT,fingerprint,current


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import torch
    import numpy as np
    from local_definitions import LocalDefinitions,AttrDict
    torch.set_num_threads(2);torch.manual_seed(83902)
    moge=LocalDefinitions('MOGE','moge').module('moge.utils.geometry_torch')
    loader=LocalDefinitions('DA3','depth_anything_3','src/depth_anything_3')
    transform=loader.module('depth_anything_3.model.utils.transform')
    definitions=loader.module('depth_anything_3.model.da3')
    geometry=loader.module('depth_anything_3.utils.geometry')
    cls=definitions.NestedDepthAnything3Net
    model=cls.__new__(cls);torch.nn.Module.__init__(model)
    out=ROOT/'build/depth-postprocess-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('native/spatial/depth.hpp','tests/expansion-native/sparse_graph.cpp','tools/test_depth_postprocess.py',
        'tools/local_definitions.py','tools/spatial_portable.py','third_party/portable-sparse-source-lock.json')
    checks=[]
    def check(name,value,**details):assert value,(name,details);checks.append(dict(case=name,**details))
    def compare(name,a,b,tol=2e-5):
        a=np.asarray(a);b=b.detach().numpy() if hasattr(b,'detach') else np.asarray(b)
        check(name,a.size==b.size and np.allclose(a.reshape(b.shape),b,atol=tol,rtol=tol),error=float(np.max(np.abs(a.reshape(b.shape)-b))) if a.size==b.size else None)
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(case,ok=True):
        (out/'request.json').write_text(json.dumps(case),'utf-8');run=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',alias+'/build/depth-postprocess-tests/request.json'],capture_output=True,text=True,encoding='utf-8',timeout=30)
        check('native_accept' if ok else 'native_reject',(run.returncode==0)==ok,reason=run.stderr[-600:]);return json.loads(run.stdout) if ok else None
    try:
        for h,w in ((19,23),(64,64),(97,73)):
            uv=moge.normalized_view_plane_uv(w,h)
            for focal in (.7,1.6,3.):
                for shift in (-.12,.34):
                    z=1+torch.rand(h,w)*2
                    xy=uv*(z+shift)[...,None]/focal
                    points=torch.cat((xy,z[...,None]),-1)+torch.randn(h,w,3)*1e-4
                    mask=torch.rand(h,w)>.2
                    expected_f,expected_s=moge.recover_focal_shift(points,mask)
                    case=dict(operation='moge_recover',height=h,width=w,points=points.flatten().tolist(),mask=mask.float().flatten().tolist())
                    actual=native(case)
                    compare('source_moge_focal',actual['focal'],expected_f,1e-3);compare('source_moge_shift',actual['shift'],expected_s,1e-3)
            case['mask']=[0]*len(case['mask']);actual=native(case);check('source_empty_mask_contract',actual['focal']==1 and actual['shift']==0)
        h,w=17,23;views=3
        pose=torch.randn(1,views,9);pose[:,:,7:]=pose[:,:,7:].abs()+.7
        c2w,K=transform.pose_encoding_to_extri_intri(pose,(h,w));E=geometry.affine_inverse(c2w)
        depth=torch.rand(1,views,h,w)*5+.1;confidence=torch.rand_like(depth)+1;metric=torch.rand_like(depth)*10+.1
        sky=(torch.rand_like(depth)>.6).float()
        expected=AttrDict(depth=depth.clone(),depth_conf=confidence.clone(),intrinsics=K.clone(),extrinsics=E.clone())
        metric_output=AttrDict(depth=metric.clone(),sky=sky.clone())
        model._apply_metric_scaling(expected,metric_output);model._apply_depth_alignment(expected,metric_output);model._handle_sky_regions(expected,metric_output)
        case=dict(operation='depth_postprocess',height=h,width=w,poses=pose[0].tolist(),depth=depth.flatten().tolist(),confidence=confidence.flatten().tolist(),metric=metric.flatten().tolist(),sky=sky.flatten().tolist())
        actual=native(case)
        compare('source_nested_depth',actual['depth'],expected.depth);compare('source_nested_confidence',actual['confidence'],expected.depth_conf)
        compare('source_nested_scale',actual['scale'],expected.scale_factor)
        for index,camera in enumerate(actual['cameras']):
            compare('source_intrinsics',camera['intrinsics'],K[0,index]);compare('source_scaled_world_to_camera',camera['extrinsics'],geometry.as_homogeneous(expected.extrinsics)[0,index])
        for name,change in (
            ('zero_quaternion',lambda p:p['poses'][0].__setitem__(slice(3,7),[0]*4)),
            ('nonfinite_depth',lambda p:p['depth'].__setitem__(0,float('nan'))),
            ('no_alignment',lambda p:p.__setitem__('sky',[1]*len(p['sky']))),
            ('shape_mismatch',lambda p:p.__setitem__('metric',[])),
        ):
            bad=copy.deepcopy(case);change(bad);native(bad,False);check(name,True)
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    (out/'results.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsRun=0,physicalDeviceTests=0,
        focalSolver='Eigen MINPACK LM, same profiled focal objective; float32 tolerance',quantileRng='native mt19937; source equations, no claim of Torch RNG bit parity'),indent=2)+'\n','utf-8')
    print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
