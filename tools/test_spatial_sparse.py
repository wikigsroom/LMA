"""Bounded CPU sparse kernels + actual exported ONNX bridge, zero trained models."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import warnings
from evidence import fingerprint, current
from spatial_reference import ROOT, verify, definitions

OUT = ROOT/'build/spatial-sparse-tests'
CHECKS = []
ALIAS = None


class SparseFixture:
    def __init__(self, feats, coords, shape=None, layout=None):
        self.feats, self.coords = feats, coords
        self.shape = shape or (int(coords[:, 0].max())+1, feats.shape[1])
        self._shape = self.shape
        self.layout = layout if layout is not None else [slice(int((coords[:, 0]<i).sum()), int((coords[:, 0]<=i).sum())) for i in range(self.shape[0])]
        self._scale, self._spatial_cache = (1, 1, 1), {}
        self.spatial_shape = (12, 12, 12)
        self.device, self.dtype = feats.device, feats.dtype

    def get_spatial_cache(self, key):
        return self._spatial_cache.get(key)

    def register_spatial_cache(self, key, value):
        self._spatial_cache[key] = value

    def replace(self, features):
        out = copy.copy(self)
        out.feats = features
        return out


def check(label, value, **details):
    assert value, (label, details)
    CHECKS.append(dict(case=label, **details))


def compare(label, a, b):
    import numpy as np
    a = a.detach().numpy() if hasattr(a, 'detach') else np.array(a)
    b = b.detach().numpy() if hasattr(b, 'detach') else np.array(b)
    assert a.shape == b.shape, (label, a.shape, b.shape)
    error = float(np.max(np.abs(a-b))) if a.size else 0
    check(label, a.shape == b.shape and np.allclose(a, b, atol=5e-6, rtol=2e-5), maximumAbsoluteError=error)


def graph(name, args, names, outputs):
    import torch
    from spatial_sparse_graphs import Conv, Pool, Subdivide, SpatialToChannel, PackedAttention
    from spatial_sparse_graphs import operation as operator
    op = operator(name)

    class Wrapper(torch.nn.Module):
        def forward(self, *values):
            return op(*values)

    dynamic = {key: {0: key+'_rows'} for key, item in zip(names, args) if item.ndim > 1 or key in ('q_lengths', 'k_lengths')}
    dynamic.update({key: {0: key+'_rows'} for key in outputs})
    file = OUT/(name+'.onnx')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        torch.onnx.export(Wrapper(), args, file, input_names=names, output_names=outputs, dynamic_axes=dynamic,
                          opset_version=17, custom_opsets={'lma.spatial': 1}, dynamo=False, external_data=False)
    import onnx
    m = onnx.load(str(file))
    onnx.checker.check_model(m)
    check(name+'_signed_in_domain', len(m.graph.node) == 1 and m.graph.node[0].domain == 'lma.spatial')
    return file


def native(graph_file, names, args, success=True):
    request = dict(graph=ALIAS+'/'+graph_file.relative_to(ROOT).as_posix(), inputs=[dict(name=n, shape=list(t.shape),
        dtype='float32' if str(t.dtype) == 'torch.float32' else 'int64', values=t.flatten().tolist()) for n, t in zip(names, args)])
    path = OUT/'request.json'
    path.write_text(json.dumps(request), 'utf-8')
    r = subprocess.run([ALIAS+'/build/spatial-worker-host/bin/lma_sparse_graph.exe', ALIAS+'/'+path.relative_to(ROOT).as_posix()],
                       capture_output=True, text=True, encoding='utf-8', timeout=30)
    check(graph_file.stem+('_success' if success else '_rejected'), (r.returncode == 0) == success, error=r.stderr[-300:] if r.returncode else '')
    if not success:
        return []
    import numpy as np
    return [np.array(v['values']).reshape(v['shape']) for v in json.loads(r.stdout)]


def main():
    global ALIAS
    sys.path.insert(0, str(ROOT/'build/shape-reference-python'))
    import torch
    from spatial_sparse_graphs import Conv, Pool, Subdivide, SpatialToChannel, PackedAttention
    torch.manual_seed(105)
    torch.set_num_threads(2)
    verify()
    OUT.mkdir(exist_ok=True)
    inputs = fingerprint('native/spatial', 'tools/spatial_sparse_graphs.py', 'tools/test_spatial_sparse.py',
                         'tools/spatial_reference.py', 'tests/expansion-native/sparse_graph.cpp', 'third_party/spatial-shape-source-lock.json')
    ALIAS = next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()), None)
    assert ALIAS
    subprocess.run(['subst', ALIAS, str(ROOT)], check=True, capture_output=True)
    try:
        uni = definitions('D05', 'uniforge3d/modules/sparse/spatial/basic.py', {'SparseTensor': SparseFixture})
        channel = definitions('D05', 'uniforge3d/modules/sparse/spatial/spatial2channel.py', {'SparseTensor': SparseFixture})
        sam = definitions('D08', 'sam3d_objects/model/backbone/tdfy_dit/modules/sparse/spatial.py', {'SparseTensor': SparseFixture})
        for n in (11, 23, 47):
            coords = torch.unique(torch.cat((torch.randint(0, 2, (n, 1)), torch.randint(0, 10, (n, 3))), 1), dim=0).long()
            f = torch.randn(len(coords), 3)
            shape = SparseFixture(f, coords)
            if n == 11:
                pool_graph = graph('pool', (f, coords, torch.tensor([2, 2, 2, 0])), ['features', 'coords', 'policy'], ['pooled', 'pooled_coords', 'inverse'])
                split_graph = graph('subdivide', (f, coords, torch.ones(len(coords), 8, dtype=torch.int64), torch.tensor([0])), ['features', 'coords', 'mask', 'order'], ['subdivided', 'subdivided_coords', 'parent', 'child'])
                channel_graph = graph('spatial_to_channel', (f, coords, torch.tensor([2])), ['features', 'coords', 'factor'], ['features_out', 'coords_out', 'parent', 'child'])
            for policy, mode in ((0, 'mean'), (1, 'sam_mean'), (2, 'max')):
                factor = 3 if n == 47 else 2
                expected = sam.SparseDownsample(factor)(shape) if policy == 1 else uni.SparseDownsample(factor, mode)(shape)
                data = (f, coords, torch.tensor([factor, factor, factor, policy]))
                actual = native(pool_graph, ['features', 'coords', 'policy'], data)
                compare('publisher_'+mode+'_features_'+str(n), expected.feats, actual[0])
                compare('publisher_'+mode+'_coords_'+str(n), expected.coords, actual[1])
                expected_up = (sam.SparseUpsample(factor) if policy == 1 else uni.SparseUpsample(factor))(expected)
                compare('publisher_'+mode+'_paired_restore_'+str(n), expected_up.feats, torch.tensor(actual[0])[torch.tensor(actual[2])])
                compare('export_reference_'+mode+'_'+str(n), Pool.apply(*data)[0], actual[0])
            for order in (0, 1):
                mask = torch.ones(len(coords), 8, dtype=torch.int64) if order == 0 else torch.randint(0, 2, (len(coords), 8))
                expected = sam.SparseSubdivide()(shape) if order == 0 else uni.SparseUpsample(2)(SparseFixture(f, coords), SparseFixture(mask, coords))
                actual = native(split_graph, ['features', 'coords', 'mask', 'order'], (f, coords, mask, torch.tensor([order])))
                compare('publisher_subdivide_features_'+str((n, order)), expected.feats, actual[0])
                compare('publisher_subdivide_coords_'+str((n, order)), expected.coords, actual[1])
                compare('export_subdivide_'+str((n, order)), Subdivide.apply(f, coords, mask, torch.tensor([order]))[1], actual[1])
            expected = channel.SparseSpatial2Channel(2)(shape)
            actual = native(channel_graph, ['features', 'coords', 'factor'], (f, coords, torch.tensor([2])))
            compare('publisher_spatial_to_channel_'+str(n), expected.feats, actual[0])
            compare('publisher_spatial_to_channel_coords_'+str(n), expected.coords, actual[1])
            restore = torch.tensor(actual[0]).reshape(-1, 3)[torch.tensor(actual[2])*8+torch.tensor(actual[3])]
            compare('publisher_channel_restore_'+str(n), channel.SparseChannel2Spatial(2)(expected).feats, restore)
            weights, bias, dilation = torch.randn(4, 3, 1, 3, 3), torch.randn(4), torch.tensor([2, 1, 1])
            if n == 11:
                conv_graph = graph('conv', (f, coords, weights, bias, dilation), ['features', 'coords', 'weights', 'bias', 'dilation'], ['output'])
            actual = native(conv_graph, ['features', 'coords', 'weights', 'bias', 'dilation'], (f, coords, weights, bias, dilation))[0]
            dense = torch.zeros((2, 3, 12, 12, 12))
            for row, feat in zip(coords, f):
                b, x, y, z = row.tolist()
                dense[b, :, x, y, z] = feat
            reference = torch.nn.functional.conv3d(dense, weights.permute(0, 4, 1, 2, 3), bias, padding=(2, 0, 1), dilation=(2, 1, 1))
            expected = torch.stack([reference[b, :, x, y, z] for b, x, y, z in coords.tolist()])
            compare('independent_dense_conv_'+str(n), expected, actual)
            compare('export_conv_'+str(n), Conv.apply(f, coords, weights, bias, dilation), actual)
        sdpa = definitions('D08', 'sam3d_objects/model/backbone/tdfy_dit/modules/sparse/attention/masked_sdpa.py').masked_sdpa
        for ql, kl in (([2, 5], [3, 7]), ([1, 0, 9], [1, 0, 4]), ([13], [27])):
            q, k, v = torch.randn(sum(ql), 2, 5), torch.randn(sum(kl), 2, 5), torch.randn(sum(kl), 2, 3)
            args = (q, k, v, torch.tensor(ql), torch.tensor(kl))
            if len(CHECKS) and ql == [2, 5]:
                attention_graph = graph('attention', args, ['q', 'k', 'v', 'q_lengths', 'k_lengths'], ['output'])
            # Length vectors have a dynamic batch dimension, separately checked below.
            actual = native(attention_graph, ['q', 'k', 'v', 'q_lengths', 'k_lengths'], args)[0]
            compare('pytorch_packed_attention_'+str(ql), PackedAttention.apply(*args), actual)
            compare('publisher_sam_masked_sdpa_'+str(ql), sdpa(q[None], k[None], v[None], ql, kl), actual)
        # Malformed custom input is rejected locally, without crashing the process.
        bad_coords = coords.clone()
        bad_coords[0] = bad_coords[1]
        native(conv_graph, ['features', 'coords', 'weights', 'bias', 'dilation'], (f, bad_coords, weights, bias, dilation), False)
        bad_coords[0, 1] = -1
        native(conv_graph, ['features', 'coords', 'weights', 'bias', 'dilation'], (f, bad_coords, weights, bias, dilation), False)
        native(conv_graph, ['features', 'coords', 'weights', 'bias', 'dilation'], (f, coords, weights, bias, torch.tensor([0, 1, 1])), False)
        native(pool_graph, ['features', 'coords', 'policy'], (f, coords, torch.tensor([2, 2, 2, 99])), False)
        native(split_graph, ['features', 'coords', 'mask', 'order'], (f, coords, torch.full((len(coords), 8), 2), torch.tensor([0])), False)
        current(inputs)
    finally:
        subprocess.run(['subst', ALIAS, '/D'], check=True, capture_output=True)
    result = dict(passed=len(CHECKS), checks=CHECKS, input_fingerprint=inputs, completeModelsDownloaded=0,
                  completeModelsRun=0, physicalDeviceTests=0, virtualizationUsed=False, modelAdaptersCompleted=[])
    (OUT/'results.json').write_text(json.dumps(result, indent=2)+'\n', 'utf-8')
    print(json.dumps({k: result[k] for k in ('passed', 'completeModelsRun', 'modelAdaptersCompleted')}))


if __name__ == '__main__':
    main()
