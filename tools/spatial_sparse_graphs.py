"""Version-1 CPU sparse export operators for lma.spatial, not model recipes.

No dynamic libraries or user code are loaded by Android. These operators are
compiled into the signed Spatial worker. A complete model still needs an
explicit architecture exporter, orchestration, input and decoder adapter.
"""
import torch
from torch import nn


class Conv(torch.autograd.Function):
    @staticmethod
    def forward(ctx, features, coords, weights, bias, dilation):
        rows = {tuple(c): i for i, c in enumerate(coords.tolist())}
        out = bias[None].expand(len(coords), -1).clone()
        sizes = weights.shape[1:4]
        for i, c in enumerate(coords.tolist()):
            for x in range(sizes[0]):
                for y in range(sizes[1]):
                    for z in range(sizes[2]):
                        p = tuple([c[0]] + [c[j+1] + (offset-sizes[j]//2)*int(dilation[j]) for j, offset in enumerate((x, y, z))])
                        if p in rows:
                            out[i] += weights[:, x, y, z] @ features[rows[p]]
        return out

    @staticmethod
    def symbolic(g, features, coords, weights, bias, dilation):
        out = g.op('lma.spatial::SubmanifoldConv3D', features, coords, weights, bias, dilation)
        shape = features.type().varyingSizes()
        weight_shape = weights.type().varyingSizes()
        if shape is not None and weight_shape is not None:
            out.setType(features.type().with_sizes([shape[0], weight_shape[0]]))
        return out


class Pool(torch.autograd.Function):
    @staticmethod
    def forward(ctx, features, coords, policy):
        c = coords.clone()
        c[:, 1:] = torch.div(c[:, 1:], policy[:3], rounding_mode='floor')
        unique, inverse = torch.unique(c, dim=0, sorted=True, return_inverse=True)
        mode = int(policy[3])
        out = torch.zeros((len(unique), features.shape[1]), dtype=features.dtype)
        if mode == 2:
            out.scatter_reduce_(0, inverse[:, None].expand_as(features), features, reduce='amax', include_self=False)
        else:
            out.scatter_add_(0, inverse[:, None].expand_as(features), features)
            count = torch.bincount(inverse, minlength=len(unique)) + (1 if mode == 1 else 0)
            out = out / count[:, None]
        return out, unique, inverse

    @staticmethod
    def symbolic(g, features, coords, policy):
        a, b, c = g.op('lma.spatial::Pool3D', features, coords, policy, outputs=3)
        a.setType(features.type().with_sizes([None, features.type().varyingSizes()[1]]))
        b.setType(coords.type().with_sizes([None, 4]))
        c.setType(coords.type().with_sizes([None]))
        return a, b, c


class Subdivide(torch.autograd.Function):
    @staticmethod
    def forward(ctx, features, coords, mask, order):
        parent, child = torch.nonzero(mask, as_tuple=True)
        c = coords[parent].clone()
        c[:, 1:] *= 2
        for j in range(3):
            c[:, j+1] += (child >> (2-j if int(order[0]) == 0 else j)) & 1
        return features[parent], c, parent, child

    @staticmethod
    def symbolic(g, features, coords, mask, order):
        a, b, c, d = g.op('lma.spatial::Subdivide3D', features, coords, mask, order, outputs=4)
        a.setType(features.type().with_sizes([None, features.type().varyingSizes()[1]]))
        b.setType(coords.type().with_sizes([None, 4]))
        c.setType(coords.type().with_sizes([None]))
        d.setType(coords.type().with_sizes([None]))
        return a, b, c, d


class SpatialToChannel(torch.autograd.Function):
    @staticmethod
    def forward(ctx, features, coords, factor):
        n = int(factor[0])
        _, c, inverse = Pool.apply(features, coords, torch.tensor([n, n, n, 0]))
        child = sum((coords[:, j+1] % n) * n**j for j in range(3))
        out = torch.zeros((len(c)*n**3, features.shape[1]), dtype=features.dtype)
        out[inverse*n**3+child] = features
        return out.reshape(len(c), n**3*features.shape[1]), c, inverse, child

    @staticmethod
    def symbolic(g, features, coords, factor):
        a, b, c, d = g.op('lma.spatial::SpatialToChannel3D', features, coords, factor, outputs=4)
        a.setType(features.type().with_sizes([None, None]))
        b.setType(coords.type().with_sizes([None, 4]))
        c.setType(coords.type().with_sizes([None]))
        d.setType(coords.type().with_sizes([None]))
        return a, b, c, d


class PackedAttention(torch.autograd.Function):
    @staticmethod
    def forward(ctx, q, k, v, q_lengths, k_lengths):
        results = []
        qs, ks = 0, 0
        for qn, kn in zip(q_lengths.tolist(), k_lengths.tolist()):
            result = nn.functional.scaled_dot_product_attention(q[qs:qs+qn].transpose(0, 1), k[ks:ks+kn].transpose(0, 1), v[ks:ks+kn].transpose(0, 1))
            results.append(result.transpose(0, 1))
            qs, ks = qs+qn, ks+kn
        return torch.cat(results)

    @staticmethod
    def symbolic(g, q, k, v, q_lengths, k_lengths):
        out = g.op('lma.spatial::PackedAttention', q, k, v, q_lengths, k_lengths)
        out.setType(q.type().with_sizes([q.type().varyingSizes()[0], q.type().varyingSizes()[1], v.type().varyingSizes()[2]]))
        return out


# Keep the dispatcher library alive. Opaque dispatcher calls avoid tracing a
# particular coordinate map into the ONNX graph before symbolic replacement.
_library = torch.library.Library('lma_sparse_export', 'DEF')
_signatures = {
    'conv': ('(Tensor features, Tensor coords, Tensor weights, Tensor bias, Tensor dilation) -> Tensor', Conv),
    'pool': ('(Tensor features, Tensor coords, Tensor policy) -> (Tensor, Tensor, Tensor)', Pool),
    'subdivide': ('(Tensor features, Tensor coords, Tensor mask, Tensor order) -> (Tensor, Tensor, Tensor, Tensor)', Subdivide),
    'spatial_to_channel': ('(Tensor features, Tensor coords, Tensor factor) -> (Tensor, Tensor, Tensor, Tensor)', SpatialToChannel),
    'attention': ('(Tensor q, Tensor k, Tensor v, Tensor q_lengths, Tensor k_lengths) -> Tensor', PackedAttention),
}
for _name, (_signature, _operation) in _signatures.items():
    _library.define(_name + _signature)
    _library.impl(_name, lambda *args, op=_operation: op.forward(None, *args), 'CPU')
    torch.onnx.register_custom_op_symbolic('lma_sparse_export::'+_name, _operation.symbolic, 17)


def operation(name):
    """Return the fixed exporter operator; names are a closed allowlist."""
    if name not in _signatures:
        raise ValueError('Unknown Spatial CPU export operator')
    return getattr(torch.ops.lma_sparse_export, name)
