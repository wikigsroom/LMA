"""Equal-peer matched spatial recipes. No automatic downloads or raw PT execution."""
from expansion_catalogue import field


def parameters(pipeline):
    ultra = pipeline == 'ultrashape_1_refine'
    result = dict(version=1, fields=dict(
        threads=field('integer', 'CPU 线程', 2, 1, 16, presets=[1, 2, 4, 8]),
        steps=field('integer', '形状采样步数', 30, 1, 100, presets=[10, 20, 30, 50]),
        seed=field('integer', '随机种子', 1234, 0, 2147483647),
        tokens=field('integer', '形状潜变量 token', 8192 if ultra else 4096, 512, 32768, multipleOf=512, presets=[512, 1024, 4096, 8192, 16384]),
        grid=field('integer', 'SDF 网格单轴格数', 64, 32, 256, multipleOf=16, presets=[32, 64, 96, 128]),
        queryChunk=field('integer', 'SDF 分块查询点数', 512, 128, 4096, presets=[256, 512, 1024, 2048]),
        guidance=field('number', '图像引导强度', 5, 0, 15),
        maxTriangles=field('integer', '三角面保护上限', 300000, 1000, 1000000, presets=[100000, 300000, 600000]),
        meshScale=field('number', '粗网格归一化半边长', .99, .1, 1),
        surfaceSamples=field('integer', '粗网格表面采样点', 65536, 1024, 409600)))
    if not ultra:
        del result['fields']['meshScale'], result['fields']['surfaceSamples']
    return result


def definition(pipeline):
    ultra = pipeline == 'ultrashape_1_refine'
    assert ultra or pipeline == 'hunyuan3d_21_shape'
    return dict(engine='spatial_ort', architecture='ultrashape_1' if ultra else 'hunyuan3d_21', pipeline=pipeline,
                backend='cpu', tasks=['3d'], capabilities=['image_conditioning', 'sdf_geometry'] +
                (['mesh_refinement', 'coarse_mesh_conditioning'] if ultra else ['image_to_3d']), parameters=parameters(pipeline))


def recipes():
    from shape_catalogue import recipes as rf_recipes
    result = []
    import copy
    for pipeline, name in [('hunyuan3d_21_shape', 'Hunyuan3D 2.1 · 形状'), ('ultrashape_1_refine', 'UltraShape 1.0 · 粗网格精修')]:
        r = copy.deepcopy(rf_recipes()[0])
        r.update(id=pipeline + '_onnx_cpu_v1', name=name + ' · 配套 FP32 ONNX', definition=definition(pipeline))
        r['requirements'][0].update(label='配套 spatial-config.json', matchFiles=['spatial-config.json'])
        r['help'] = ('选择同一批离线转换的五组配置 / ONNX 组件；原始 safetensors / PT 需先在用户明确选择的本地资产上转换。无已核实的公开配套 ONNX 整包。'
                     + ('需要参考 PNG 和含可用锐边的粗 GLB；一半面积采样、一半锐边长度采样，先归一化再经 FP16 舍入。' if pipeline.startswith('ultra') else '需要参考 PNG；当前仅形状，不含 Hunyuan3D Paint。')
                     + '全部推理在手机 CPU；MoE 保留全部专家权重并依次计算，依次驻留阶段图。不附带权重，不自动抠图，无远程服务；完整权重、质量、内存、速度及真机未测。')
        result.append(r)
    return result
