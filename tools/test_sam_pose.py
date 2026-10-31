"""Source pose conventions, independent rotation oracle and strict shared-weight loading."""
import ast,copy,json,subprocess,sys,types
from pathlib import Path
from evidence import ROOT,current,fingerprint


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import torch,numpy as np
    from scipy.spatial.transform import Rotation
    from safetensors.torch import save_file
    from spatial_portable import Source,strict_weights
    torch.set_num_threads(2);torch.manual_seed(8301);source=Source('D08')
    inputs=fingerprint('native/spatial/sam_pose.hpp','tools/spatial_portable.py','tools/test_sam_pose.py','third_party/portable-sparse-source-lock.json')
    path,text=source.read('sam3d_objects/data/dataset/tdfy/pose_target.py');tree=ast.parse(text)
    def method(name):
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name);f=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='to_instance_pose'));f.decorator_list=[];f.returns=None
        for arg in f.args.args:arg.annotation=None
        scope=dict(torch=torch,InstancePose=lambda **kwargs:types.SimpleNamespace(**kwargs));exec(compile(ast.fix_missing_locations(ast.Module([f],type_ignores=[])),str(path),'exec'),scope);return scope[f.name]
    disparity,apparent=method('DisparitySpace'),method('InvariantPoseTarget')
    _,text=source.read('sam3d_objects/pipeline/inference_utils.py');nodes=[n for n in ast.parse(text).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['ROTATION_6D_MEAN','ROTATION_6D_STD'] for t in n.targets)]
    scope=dict(torch=torch);exec(compile(ast.fix_missing_locations(ast.Module(nodes,type_ignores=[])),'pinned_rotation_constants','exec'),scope)
    out=ROOT/'build/sam-pose-tests';out.mkdir(exist_ok=True);checks=[];drive=next(c+':' for c in 'RTUVWXYZ' if not Path(c+':/').exists());subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    def native(value,success=True):
        file=out/'request.json';file.write_text(json.dumps(value),'utf-8');alias=lambda p:drive+'/'+p.relative_to(ROOT).as_posix();r=subprocess.run([alias(ROOT/'build/spatial-worker-host/bin/lma_cascade_contract.exe'),alias(file)],capture_output=True,text=True,encoding='utf-8',timeout=20)
        assert (r.returncode==0)==success,r.stderr;return json.loads(r.stdout) if success else None
    try:
        for convention in ['ScaleShiftInvariant','ZeroPredictionScaleShiftInvariant','ApparentSize','DisparitySpace']:
            for rot_type in ['quaternion','6drotation','6drotation_normalized']:
                for factor in [1,2]:
                    t=torch.randn(1,1,3);s=torch.randn(1,1,3)*.3;ts=torch.randn(1,1,1)*.2;scene=.73;shift=[.12,-.31,.29];rotation=torch.randn(4 if rot_type=='quaternion' else 6)
                    if rot_type=='quaternion':rotation=rotation/rotation.norm();quaternion=rotation.numpy()
                    else:
                        raw=rotation if rot_type=='6drotation' else rotation*scope['ROTATION_6D_STD'].reshape(-1)+scope['ROTATION_6D_MEAN'].reshape(-1)
                        a,b=raw[:3],raw[3:];a=a/a.norm();b=b-a.dot(b)*a;b=b/b.norm();matrix=torch.stack([a,b,torch.cross(a,b,dim=-1)],dim=-1).numpy();q=Rotation.from_matrix(matrix).as_quat();quaternion=np.r_[q[-1],q[:3]];quaternion*=1 if quaternion[0]>=0 else -1
                    parts=dict(shape=[0.]*8,translation=t.reshape(-1).tolist(),scale=s.reshape(-1).tolist(),translation_scale=ts.reshape(-1).tolist());parts[rot_type]=rotation.tolist();heads=[dict(name=k,rows=1,channels=len(v),strength=0,pointStrength=0,interval=None) for k,v in parts.items()];values=sum(parts.values(),[])
                    c=dict(operation='sam_pose',values=values,heads=heads,scale=scene,shift=shift,convention=convention,factor=factor);actual=native(c)
                    if convention=='DisparitySpace':
                        p=types.SimpleNamespace(x_instance_translation=t,x_instance_scale=s.exp(),x_translation_scale=ts.exp(),x_instance_rotation=torch.tensor(quaternion).reshape(1,1,4),x_scene_scale=torch.tensor([[scene]]),x_scene_center=torch.tensor([shift]));expected=disparity(None,p);translation=expected.instance_position_l2c.reshape(-1).numpy();scale=float(expected.instance_scale_l2c.mean())*factor
                    elif convention=='ApparentSize':
                        p=types.SimpleNamespace(t_unit=t,s_tilde=s.exp(),t_rel_norm=ts.exp(),q=None,s_scene=torch.tensor([[scene]]),t_scene_center=torch.tensor([shift]));expected=apparent(p);translation=expected.instance_position_l2c.reshape(-1).numpy();scale=float(expected.instance_scale_l2c.mean())*factor
                    else:
                        if convention.startswith('Zero'):t=torch.zeros_like(t);s=torch.full_like(s,1.337)
                        translation=t.numpy().reshape(-1)*scene+np.array(shift);scale=float(s.exp().mean())*scene*factor
                    np.testing.assert_allclose(actual['translation'],translation,atol=3e-6,rtol=3e-6);np.testing.assert_allclose(actual['scale'],[scale]*3,atol=3e-6,rtol=3e-6);np.testing.assert_allclose(actual['rotationWXYZ'],quaternion,atol=3e-6,rtol=3e-6);checks.append(convention+'_'+rot_type+'_'+str(factor))
        bad=copy.deepcopy(c);bad['factor']=3;native(bad,False);checks.append('invalid_pose_factor_rejects')
        bad=copy.deepcopy(c);bad['values']=[0.]*len(values);bad['heads'][-1]['name']='6drotation';native(bad,False);checks.append('degenerate_rotation_rejects')
        # Source models can share head parameters under multiple state paths.
        class Shared(torch.nn.Module):
            def __init__(self):super().__init__();self.first=torch.nn.Linear(3,4);self.second=self.first;self.other=torch.nn.Linear(4,2)
        model=Shared();original=model.state_dict();file=out/'weights.safetensors';weights={k:v.clone() for k,v in original.items() if not k.startswith('second.')};save_file(weights,str(file));actual=strict_weights(Shared(),file);assert torch.equal(actual.first.weight,original['first.weight']) and actual.first.weight is actual.second.weight;checks.append('proven_shared_alias_reconstructed')
        for case in ['missing_nonalias','conflicting_alias','wrong_shape','nonfinite','unknown_key']:
            values={k:v.clone() for k,v in weights.items()}
            if case=='missing_nonalias':values.pop('other.weight')
            if case=='conflicting_alias':values['second.weight']=values['first.weight']+1
            if case=='wrong_shape':values['other.weight']=torch.zeros(1)
            if case=='nonfinite':values['first.weight'].fill_(float('nan'))
            if case=='unknown_key':values['unknown']=torch.zeros(1)
            save_file(values,str(file))
            try:strict_weights(Shared(),file);raise RuntimeError('Invalid checkpoint accepted')
            except AssertionError:checks.append('strict_weights_'+case+'_rejects')
        current(inputs);report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsRun=0,phoneTests=0,sourcePoseMethods=['DisparitySpace','InvariantPoseTarget'],rotationOracle='scipy_rotation_matrix',ssiOracle='uniform_scale_translation_contract')
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)


if __name__=='__main__':main()
