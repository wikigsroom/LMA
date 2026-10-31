"""Data fields shared by source-matched RF image / point reconstructions."""
from expansion_catalogue import field


def fields():
    return dict(extraction=dict(type='enum',label='曲面提取',default='uniform',values=['uniform','publisher_octree','publisher_flash']),
        octreeDepth=field('integer','分层提取目标深度',6,5,8),
        denseDepth=field('integer','初始稠密网格深度（octree）',5,3,8,maximumFrom=dict(field='octreeDepth')))
