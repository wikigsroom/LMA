"""Reviewed BasicSR architecture definitions only; never its package entrypoint."""
import ast,hashlib,json,math,types,warnings
from spatial_reference import ROOT


def verify():
    lock=json.loads((ROOT/'third_party/paint-source-lock.json').read_text('utf-8'))
    for item in lock['files']:
        data=(ROOT/lock['directory']/item['path']).read_bytes()
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
    return lock


def rrdb():
    import torch
    from torch import nn
    lock=verify();folder=ROOT/lock['directory'];namespace=dict(torch=torch,nn=nn,F=torch.nn.functional,init=nn.init,math=math,warnings=warnings)
    for path,names in [('basicsr/archs/arch_util.py',{'default_init_weights','make_layer','pixel_unshuffle'}),
                       ('basicsr/archs/rrdbnet_arch.py',{'ResidualDenseBlock','RRDB','RRDBNet'})]:
        tree=ast.parse((folder/path).read_text('utf-8'))
        body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
        assert len(body)==len(names)
        for node in body:
            if node.name=='RRDBNet':
                assert [ast.unparse(d) for d in node.decorator_list]==['ARCH_REGISTRY.register()']
                node.decorator_list=[]
        exec(compile(ast.Module(body=body,type_ignores=[]),str(folder/path),'exec'),namespace)
    return namespace['RRDBNet']
