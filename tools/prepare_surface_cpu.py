"""Prepare pinned original mesher math for a bounded, inference-only CPU build.

No model data. DISO retains CC BY-NC 4.0 attribution; Lewiner retains its
public-domain/MIT/BSD notices. CUDA memory management/launches and mesh file
readers are excluded. Actual forward kernels, ambiguity tables and geometry
interpolation remain source code, not a different tetrahedra algorithm.
"""
import hashlib,json,re
from pathlib import Path
from fetch_surface_sources import ROOT,verify
OUT=ROOT/'build/surface-cpu'


def function(source,name):
    match=re.search(r'(?:template\s*<[^>]+>\s*)?(?:inline\s+)?(?:__device__\s+|__global__\s+|__host__\s+)*(?:[\w:<>,]+\s+)+\b'+name+r'\s*\(',source)
    assert match,name
    begin=source.index('{',match.end());depth=1;end=begin+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[match.start():end]


def prepare():
    lock=verify();OUT.mkdir(exist_ok=True)
    directory=ROOT/'build/surface-source-review/LEWINER/tools/precompute/mc_meta'
    source=(directory/'MarchingCubes.cpp').read_text('utf-8')
    # Pure geometry ends before all original PLY/IV/ISO disk writers.
    source=source[:source.index('void MarchingCubes::writeISO')]
    source=source.replace('#include "ply.h"','').replace('#include "MarchingCubes.h"','#include "lewiner.h"').replace('#include "LookUpTable.h"','#include "lewiner_tables.h"')
    source=re.sub(r'#if !defined\(WIN32\).*?#endif // WIN32','',source,flags=re.S)
    source=source.replace('printf(', 'lma_mc_quiet(')
    source='#include <cstdio>\n#include <stdexcept>\nstatic int lma_mc_quiet(const char*,...){return 0;}\n'+source
    # Fail during growth, before an imported field can exhaust arbitrary RAM.
    source=source.replace('_triangles = new Triangle[ 2*_Ntrigs ] ;','if(_Ntrigs>=2000000)throw std::runtime_error("Lewiner triangle allocation budget");\n        _triangles = new Triangle[ 2*_Ntrigs ] ;')
    source=source.replace('_vertices = new Vertex[ _Nverts*2 ] ;','if(_Nverts>=2000000)throw std::runtime_error("Lewiner vertex allocation budget");\n    _vertices = new Vertex[ _Nverts*2 ] ;')
    header=(ROOT/'build/surface-source-review/LEWINER_CPP/cpp/marchingcubes.h').read_text('utf-8')
    header=re.sub(r'^//- Ajay -.*\n','',header,flags=re.M)
    header=header.replace('set_ext_data  ( uchar *data )','set_ext_data  ( real *data )').replace('set_data  ( const uchar val','set_data  ( const real val').replace('uchar     *_data','real      *_data')
    header=re.sub(r'#if !defined\(WIN32\).*?#endif // WIN32','',header,flags=re.S)
    for name,data in [('lewiner.cpp',source),('lewiner.h',header),('lewiner_tables.h',(directory/'LookUpTable.h').read_text('utf-8'))]:
        (OUT/name).write_text(data,'utf-8')
    raw=(ROOT/'build/surface-source-review/DISO/src/cudualmc.cu').read_text('utf-8')
    arrays=re.findall(r'__constant__\s+.*?\}\s*;',raw,re.S)
    assert len(arrays)>=7,len(arrays)
    functions=['count_used_cells_kernel','index_used_cells_kernel','count_cell_mc_verts_kernel','computeMcVert',
               'index_cell_mc_verts_kernel','getCellCode','getGoodCellCode','count_cell_patches_kernel','create_dmc_verts_kernel','get_quad_index','create_quads_kernel']
    pieces=[]
    for name in functions:
        data=function(raw,name)
        data=re.sub(r'__device__|__global__|__host__|__restrict__','',data)
        data=data.replace('blockIdx.x * blockDim.x + threadIdx.x','thread_index')
        pieces.append(data)
    head=(ROOT/'build/surface-source-review/DISO/src/cudualmc.h').read_text('utf-8')
    types=head[head.index('  template <typename T>'):head.index('    inline __host__ void resize')]
    types=re.sub(r'__device__|__host__|__restrict__','',types)+'\n};\n'
    data='// Inference CPU adaptation of DISO, Xinyue Wei, CC BY-NC 4.0.\n#pragma once\n#include <cstdint>\n#include <algorithm>\nnamespace lma_dmc_cpu {\ninline int thread_index=0;\ntemplate<typename T> inline T clamp(T v,T lo,T hi){return std::clamp(v,lo,hi);}\n'+types+'\n'
    data+='\n'.join(a.replace('__constant__','inline constexpr') for a in arrays)+'\n'+'\n'.join(pieces)+'\n}\n'
    (OUT/'diso_cpu.hpp').write_text(data,'utf-8')
    record=dict(schema='lma.surface-cpu-preparation/1',sources=lock['sources'],modelAssets=False,
                changes=['CPU scalar forward-kernel dispatch and exclusive scans','no CUDA allocation or autograd','Lewiner real-valued header restored; no file readers/writers','bounded mesh allocation'],
                files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='receipt.json'})
    (OUT/'receipt.json').write_text(json.dumps(record,indent=2)+'\n','utf-8');return record


if __name__=='__main__':print(json.dumps(dict(files=len(prepare()['files']),modelAssets=False)))
