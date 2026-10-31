"""Publisher point-VAE learned path; sampling is an explicit native CPU stage."""
import torch
from torch import nn


class PointEncoder(nn.Module):
    def __init__(self, vae):
        super().__init__()
        self.embedder, self.encoder, self.quant = vae.embedder, vae.encoder, vae.quant

    def forward(self, points, sampled_points):
        # Actual _encode: XYZ frequency embedding concatenated with normals,
        # cross attention from FPS queries to all point features, then quant.
        kv = torch.cat((self.embedder(points[..., :3]), points[..., 3:]), dim=-1)
        q = torch.cat((self.embedder(sampled_points[..., :3]), sampled_points[..., 3:]), dim=-1)
        return self.quant(self.encoder(q, kv))
