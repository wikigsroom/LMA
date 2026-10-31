"""Preserve earlier audit identities; describe actual spatial subsets and gaps."""
import copy
import json
from evidence import fingerprint, current, version
from spatial_reference import ROOT, verify


def main():
    assert version() == '0.3.5'
    lock = verify()
    data = json.loads((ROOT/'research/portability/audit-v0.3.4.json').read_text('utf-8'))
    data.update(app_version=version(), prior_audit='research/portability/audit-v0.3.4.json',
                integrated_architectures=['trellis2', 'pixal3d', 'pixal3d_mv', 'triposg', 'partcrafter', 'ultrashape_1_refine', 'hunyuan3d_21_shape'])
    for item in data['unported_configurations']:
        if item['id'] not in ('D06', 'D07'):
            if item['id'] in ('D05', 'D08', 'D09', 'D10'):
                item['shared_cpu_building_blocks'] = ['submanifold convolution', 'explicit pooling policy', 'explicit subdivision order', 'spatial/channel rearrangement', 'packed attention']
                item['building_blocks_are_complete_model_adapter'] = False
            continue
        source = next(x for x in lock['sources'] if x['id'] == item['id'])
        item.update(program_integrated=True, integration_status='matched_onnx_cpu_geometry_subset',
                    source_files=source['files'], full_trained_export_tested=False, phone_inference_tested=False,
                    quality_accepted=False, acquisition='explicit user-selected local export/import; no verified public matched complete download package')
        if item['id'] == 'D06':
            item.update(program_scope='reference RGBA PNG + static coarse GLB -> half-area/half-sharp-edge sampling -> float16 positions -> occupied voxel RoPE -> masked Dino -> RefineDiT/MoE -> cached VAE/SDF -> bounded mesh -> GLB',
                        remaining_implementation=[], exclusions=['Flash/octree extraction', 'automatic background removal', 'automatic coarse-shape generation', 'texture'])
        else:
            item.update(program_scope='reference PNG -> Dino -> HunYuanDiTPlain with source MoE routing -> cached shape VAE -> SDF query -> bounded surface -> GLB',
                        remaining_implementation=['separate Hunyuan3D Paint export, rasterizer, multiview diffusion and texture baking'],
                        exclusions=['Hunyuan3D Paint', 'Flash/octree extraction', 'automatic background removal'], partial_port=True)
    completed = [x for x in data['unported_configurations'] if x['id'] == 'D06']
    # Keep D07 visible as incomplete: its separate Paint architecture is absent.
    data['unported_configurations'] = [x for x in data['unported_configurations'] if x['id'] != 'D06']
    data['ported_configurations'].extend(completed)
    data['partial_configurations'] = [copy.deepcopy(x) for x in data['unported_configurations'] if x.get('partial_port')]
    for row in data['cases']:
        if row['number'] == 6:
            row.update(program_integrated=True, current_scope='matched UltraShape refinement subset; area and sharp-edge length weighted coarse mesh sampling; no complete benchmark reproduction')
        if row['number'] == 7:
            row.update(program_integrated=True, current_scope='matched Hunyuan3D shape subset only; separate Paint remains missing')
    data.update(all_benchmark_architectures_integrated=False, full_benchmark_workflows_reproduced=False,
                shared_cpu_operators_integrated=True, shared_cpu_operator_only_targets=['D05', 'D08', 'D09', 'D10'],
                evidence=['verification/program/spatial.json', 'verification/program/spatial-graphs.json', 'verification/program/spatial-sparse.json',
                          'verification/program/spatial-android.json', 'verification/program/expansion.json', 'verification/program/ui.json'],
                conclusion='UltraShape refinement and Hunyuan3D shape have matched CPU export/import program paths. Six configurations retain implementation gaps, including Hunyuan Paint. Shared sparse operations do not complete SAM, UniForge or SUPRA. No full trained exports or phone quality/performance tests.',
                input_fingerprint=fingerprint('research/portability/audit-v0.3.4.json', 'tools/audit_spatial.py',
                    'third_party/spatial-shape-source-lock.json', 'native/spatial', 'tools/spatial_shape_graphs.py', 'tools/spatial_sparse_graphs.py',
                    'tools/spatial_reference.py', 'tools/export_spatial.py', 'tools/test_spatial.py', 'tools/test_spatial_sparse.py',
                    'tools/test_spatial_shape_graphs.py', 'app/src/main/java/com/lma/app/core/SpatialSpec.java'))
    current(data['input_fingerprint'])
    (ROOT/'research/portability/audit-v0.3.5.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', 'utf-8')
    print(json.dumps(dict(geometry_subsets_added=2, incomplete_configurations=len(data['unported_configurations']), all_adaptations_complete=False)))


if __name__ == '__main__':
    main()
