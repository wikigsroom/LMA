"""Prepare the fixed publisher CPU FDG kernel without PyTorch/CUDA bindings.

No upstream installer, model, or network access is used. Fetch the explicit
Eigen source pin and Git blob beforehand. Build-time changes are recorded.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from evidence import ROOT

REVISION='75fbf0183001ed9876c8dbb35de6b68552ee08bd'
BLOB='ad89edc01d1efb9d2644f251560c60de243cb1dd'
EIGEN='3147391d946bb4b6c68edd901f2add6ac1f31f8c'


def prepare():
    src=ROOT/'build/spatial-source-review/blobs'/BLOB;data=src.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==BLOB
    eigen=ROOT/'build/native-src/eigen-fdg'
    assert subprocess.check_output(['git','-C',str(eigen),'rev-parse','HEAD'],text=True).strip()==EIGEN
    assert not subprocess.check_output(['git','-C',str(eigen),'status','--porcelain','--untracked-files=no'],text=True).strip()
    text=data.decode('utf-8')
    prefix=text[:text.index('/**\n * Extract flexible dual grid')]
    # Types/functions live in a private namespace; the std hash specialization
    # remains at global scope with its fully qualified argument type.
    prefix=prefix.replace('#include "api.h"','namespace lma_fdg_source {')
    prefix=prefix.replace('namespace std {','}\nnamespace std {',1)
    prefix=prefix.replace('hash<VoxelCoord>','hash<lma_fdg_source::VoxelCoord>',1)
    prefix=prefix.replace('operator()(const VoxelCoord& v)','operator()(const lma_fdg_source::VoxelCoord& v)',1)
    pos=prefix.index('void intersect_qef(');prefix=prefix[:pos]+'namespace lma_fdg_source {\n'+prefix[pos:]
    prefix=prefix.replace('voxels.push_back({coord.x, coord.y, coord.z});',
        'lma_worker::require(voxels.size()<lma_sparse::point_limit,"FDG surface exceeds the phone coordinate budget");\n                                        voxels.push_back({coord.x, coord.y, coord.z});')
    # Work guards fail rather than truncate an otherwise identical scan.
    for function,next_function in (('intersect_qef','face_qef'),('face_qef','boundry_qef')):
        begin=prefix.index('void '+function+'(');end=prefix.index('void '+next_function+'(')
        body=prefix[begin:end];body=body.replace('const size_t N_tri = triangles.size() / 3;',
            'size_t work=0; const size_t N_tri = triangles.size() / 3;',1)
        if function=='intersect_qef':needle='for (int x_idx = line_start; x_idx < line_end; ++x_idx) {'
        else:needle='for (int x = bb_min.x(); x < bb_max.x(); ++x) {'
        assert body.count(needle)==1
        body=body.replace(needle,needle+'\n                        lma_worker::require(++work<=50000000,"FDG scan exceeds the phone work budget");')
        prefix=prefix[:begin]+body+prefix[end:]
    begin=text.index('    clock_t start, end;',text.index('mesh_to_flexible_dual_grid_cpu('))
    end=text.index('    return std::make_tuple(',begin)
    body=text[begin:end]
    signature='''struct Grid {std::vector<int3> coords;std::vector<float3> vertices;std::vector<bool3> intersected;};
inline Grid convert(const float* v_ptr,const int* f_ptr,int F,const float* voxel_size_ptr,const int* grid_range_ptr,
 float face_weight,float boundary_weight,float regularization_weight,bool timing=false) {
'''
    generated=prefix+signature+body+'    return {std::move(voxels),std::move(dual_vertices),std::move(intersected)};\n}\n}\n'
    # MSVC/NDK do not accept the publisher's nonstandard double-literal suffix.
    generated=re.sub(r'(?<![A-Za-z0-9_])((?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?)d\b',r'\1',generated)
    # All neighbor indices address the guarded coordinate vector (< point_limit).
    # Clang requires explicit size_t -> int conversion in aggregate initializers.
    matches=re.findall(r'int4 quad_indices\{[^}]+\};',generated)
    assert len(matches)==3
    for block in matches:
        converted=re.sub(r'neigh_indices\[(\d)\]',r'static_cast<int>(neigh_indices[\1])',block)
        assert converted.count('static_cast<int>')==3
        generated=generated.replace(block,converted)
    generated='#pragma once\n// Derived from microsoft/TRELLIS.2 '+REVISION+'\n// o-voxel/src/convert/flexible_dual_grid.cpp, MIT. See third_party notices.\n#include <map>\n#include <array>\n#include <limits>\n#include <algorithm>\n#include <iostream>\n'+generated
    directory=ROOT/'build/fdg-cpu-source';directory.mkdir(exist_ok=True)
    output=directory/'lma_fdg_source.hpp';output.write_text(generated,'utf-8')
    record=dict(schema='lma.fixed-cpu-source/1',repository='microsoft/TRELLIS.2',revision=REVISION,git_blob=BLOB,
        source_sha256=hashlib.sha256(data).hexdigest(),generated_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        eigen_repository='eigen-mirror/eigen',eigen_revision=EIGEN,
        eigen_files={p.relative_to(eigen).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((eigen/'Eigen').rglob('*')) if p.is_file()},
        changes=['C++ vector input/output instead of torch Tensor bindings','private namespace','bounded fail-only coordinate/work guards','standard double literal spelling','explicit bounded neighbor-index conversion for Clang'],
        numerical_kernel='publisher CPU scan/QEF/boundary and constrained QR solve',trained_assets=False)
    (directory/'receipt.json').write_text(json.dumps(record,indent=2)+'\n','utf-8')
    return record


if __name__=='__main__':
    record=prepare();print(json.dumps(dict(git_blob=record['git_blob'],eigen_revision=EIGEN,generated_sha256=record['generated_sha256'])))
