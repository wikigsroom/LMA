"""Fixed DIS source definitions, without torchvision/package import side effects."""
import ast
import torch
from torch import nn
from fetch_vision_sources import ROOT,verify


def definitions():
    verify();path=ROOT/'build/vision-source-review/DIS/IS-Net/models/isnet.py'
    source=ast.parse(path.read_text('utf-8'))
    names={'REBNCONV','RSU7','RSU6','RSU5','RSU4','RSU4F','ISNetDIS','_upsample_like'}
    body=[n for n in source.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    assert {n.name for n in body}==names
    scope=dict(torch=torch,nn=nn,F=torch.nn.functional)
    exec(compile(ast.fix_missing_locations(ast.Module(body,type_ignores=[])),str(path),'exec'),scope)
    return scope


def construct():return definitions()['ISNetDIS'](3,1)


class Foreground(nn.Module):
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,pixels):return self.model(pixels)[0][0]
