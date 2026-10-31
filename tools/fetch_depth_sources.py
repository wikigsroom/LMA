"""Fetch immutable neural source definitions only; never model assets."""
from fetch_spatial_sources import fetch,DIRECTORY

SOURCES=[dict(id='MOGE',repository='microsoft/MoGe',revision='74fbce054ebed49800de42d0ad0e83495065719a'),
    dict(id='DA3',repository='ByteDance-Seed/Depth-Anything-3',revision='3d835ec1a5802d64a8b8b15f817a1ab54809bfe4'),
    dict(id='TIMM',repository='huggingface/pytorch-image-models',revision='78c3724f4545c0067d0b4d2f7df6337196be01ce',
        paths=['timm/models/vision_transformer.py','LICENSE'],prefixes=['timm/layers/'])]

if __name__=='__main__':
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    for source in SOURCES:fetch(source)
