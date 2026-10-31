"""Independent ray/geometry/GLB checks of the production CPU material core."""
import hashlib,json,os,struct,subprocess,sys
from pathlib import Path
from evidence import fingerprint,current
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/material-tests'


def main():
    sys.path[:0]=[str(ROOT/'build/spatial-reference-python'),str(ROOT/'build/shape-reference-python')]
    import numpy as np
    from PIL import Image
    import io
    inputs=fingerprint('native/spatial/texture.hpp','tests/expansion-native/material.cpp','tools/test_material.py','third_party/spatial-shape-source-lock.json',
        'build/native-src/trellis-cpp/thirdparty/xatlas/xatlas.cpp','build/native-src/trellis-cpp/thirdparty/xatlas/xatlas.h')
    OUT.mkdir(exist_ok=True)
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None)
    assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    checks=[]
    def check(name,ok,**details):
        assert ok,(name,details)
        checks.append(dict(case=name,**details))
    def run(p,success=True):
        f=OUT/'request.json';f.write_text(json.dumps(p),'utf-8')
        r=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_material_contract.exe',alias+'/build/material-tests/request.json'],capture_output=True,text=True,encoding='utf-8',timeout=60)
        assert (r.returncode==0)==success,r.stderr
        return json.loads(r.stdout) if success else None
    # Asymmetric closed mesh tests transform/normal/depth, not just a triangle
    # identical to the production barycentric implementation.
    vertices=np.array([[-1,-.7,-.4],[1,-.7,-.4],[1,.8,-.4],[-1,.8,-.4],[-1,-.7,.9],[1,-.7,.9],[1,.8,.9],[-1,.8,.9]])
    indices=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,3,7,6,3,6,2,0,4,7,0,7,3,1,2,6,1,6,5]
    try:
        for elev,azim in [(0,0),(0,90),(0,180),(0,270),(90,0),(-90,180),(21,37),(-17,141)]:
            size=32;p=dict(vertices=vertices.tolist(),indices=indices,size=size,elevation=elev,azimuth=azim)
            r=run(p);v=vertices[:,[0,2,1]]*np.array([-1,1,-1]);v-=(v.min(0)+v.max(0))/2;v*=1.15/(2*np.linalg.norm(v,axis=1).max())
            check('transform_'+str((elev,azim)),np.allclose(r['vertices'],v,atol=1e-7))
            # Fixed publisher camera equations evaluated independently in NumPy.
            e,a=np.deg2rad(-elev),np.deg2rad(azim+90)
            eye=1.45*np.array([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)])
            back=eye/np.linalg.norm(eye);right=np.cross(-back,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(back,right)
            check('camera_'+str((elev,azim)),all(np.allclose(r[k],val,atol=1e-7) for k,val in [('eye',eye),('right',right),('up',up),('back',back)]))
            # Orthographic ray-plane intersection + inside-triangle cross
            # products. No screen triangle scan/barycentric code is reused.
            yy,xx=np.mgrid[0:size,0:size];origin=eye[None,None]+((xx+.5)/size-.5)[...,None]*1.2*right+(.5-(yy+.5)/size)[...,None]*1.2*up
            depth=np.full((size,size),np.inf);surface=np.full((size,size),-1);normals=np.zeros((size,size,3))
            for f,tri in enumerate(np.array(indices).reshape(-1,3)):
                t=v[tri];normal=np.cross(t[1]-t[0],t[2]-t[0]);normal/=np.linalg.norm(normal);den=np.dot(-back,normal)
                if abs(den)<1e-9:continue
                distance=np.einsum('...j,j->...',t[0]-origin,normal)/den;point=origin-distance[...,None]*back
                mask=(distance>=0)&(distance<=2)&(distance<depth-1e-7)
                for k in range(3):mask &= np.einsum('...j,j->...',np.cross(t[(k+1)%3]-t[k],point-t[k]),normal)>=-1e-8
                depth[mask]=distance[mask];surface[mask]=f;normals[mask]=normal
            got=np.array(r['depth']).reshape(size,size);mask=np.isfinite(depth)
            check('ray_visibility_'+str((elev,azim)),np.array_equal(got>=0,mask))
            error=float(np.max(np.abs(got[mask]-depth[mask])))
            check('ray_depth_'+str((elev,azim)),error<1e-6,maximumError=error)
            expected=np.ones((size,size,3));expected[mask]=np.floor(np.clip((normals[mask]+1)*.5,0,1)*255)/255
            gotn=np.array(r['normal']).reshape(size,size,3)
            check('normal_condition_'+str((elev,azim)),np.max(np.abs(expected-gotn))<1e-6)
            expected=np.ones((size,size,3));expected[mask]=np.floor(np.clip(.5-(origin[mask]-depth[mask,None]*back)/1.15,0,1)*255)/255
            check('position_condition_'+str((elev,azim)),np.max(np.abs(expected-np.array(r['position']).reshape(size,size,3)))<=1/255+1e-6)
        out=OUT/'material.glb';out.unlink(missing_ok=True)
        p.update(bake=True,output=alias+'/build/material-tests/material.glb',atlas=128)
        r=run(p);check('uv_seams_preserve_positions',all(any(np.allclose(x,y) for y in vertices) for x in r['uvVertices']))
        check('uv_triangle_count',len(r['uvIndices'])==len(indices))
        uv=np.array(r['uv']);check('uv_finite_unit',np.isfinite(uv).all() and uv.min()>=0 and uv.max()<=1)
        check('bake_has_surface',r['covered']>0 and r['unobserved']<r['covered'])
        data=out.read_bytes();magic,version,length=struct.unpack_from('<III',data);n,kind=struct.unpack_from('<II',data,12);gltf=json.loads(data[20:20+n]);bin_size,bin_kind=struct.unpack_from('<II',data,20+n);binary=data[28+n:]
        check('glb_framing',magic==0x46546c67 and version==2 and length==len(data) and kind==0x4e4f534a and bin_kind==0x004e4942 and bin_size==len(binary))
        check('pbr_material_links',gltf['materials'][0]['pbrMetallicRoughness']==dict(baseColorTexture=dict(index=0),metallicRoughnessTexture=dict(index=1),metallicFactor=1,roughnessFactor=1))
        for index in range(2):
            view=gltf['bufferViews'][gltf['images'][index]['bufferView']];png=binary[view['byteOffset']:view['byteOffset']+view['byteLength']];image=np.array(Image.open(io.BytesIO(png)))
            color=np.array([64,128,191,255] if index==0 else [0,204,51,255]);check('embedded_png_'+str(index),image.shape==(r['atlasHeight'],r['atlasWidth'],4) and np.max(np.abs(image.astype(int)-color))<=1)
        # Explicit invalid geometry/size/topology/overwrite cases.
        for name,change in [('zero_extent',dict(vertices=[[0,0,0]]*8)),('bad_index',dict(indices=[0,1,99])),('size_budget',dict(size=4096)),('uv_budget',dict(atlas=8192))]:
            run({**p,**change},False);check(name,True)
        run(p,False);check('existing_output_not_replaced',True)
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsDownloaded=0,completeModelsRun=0,physicalDeviceTests=0,virtualizationUsed=False)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModelsRun=0)))


if __name__=='__main__':main()
