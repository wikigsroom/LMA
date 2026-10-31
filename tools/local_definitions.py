"""Load immutable local neural definitions without executing package startup.

Only whitelisted imports, definitions and literal policies execute. Model/Hub
loaders and arbitrary module-level calls are excluded; assets stay user-owned.
"""
import ast
import collections
import dataclasses
import functools
import importlib
import importlib.util
import logging
import math
import numbers
import sys
import types
import typing
import warnings
from pathlib import Path
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F
from spatial_portable import Source


class AttrDict(dict):
    __getattr__=dict.__getitem__
    __setattr__=dict.__setitem__
    __delattr__=dict.__delitem__


def unavailable(*args,**kwargs):raise ValueError('This definition is outside the local tensor export profile')


class LocalDefinitions:
    def __init__(self,target,package,prefix=None,injections=None,definitions=None):
        self.source=Source(target);self.package=package;self.prefix=prefix or package.replace('.','/')
        self.modules={};self.injections=dict(injections or {});self.definitions=definitions
        self.injections.update(PyTorchModelHubMixin=type('LocalModelMixin',(),{}),hf_hub_download=unavailable,
            create_object=unavailable,get_extrinsic_from_camray=unavailable)

    def path(self,qualified):
        assert qualified==self.package or qualified.startswith(self.package+'.'),qualified
        relative=self.prefix+qualified[len(self.package):].replace('.','/')
        if relative+'.py' in self.source.files:return relative+'.py'
        if relative+'/__init__.py' in self.source.files:return relative+'/__init__.py'
        return None

    def dependency(self,qualified,name):
        path=self.path(qualified)
        if path:
            module=self.module(qualified)
            if name=='*' or hasattr(module,name):return module
        child=self.path(qualified+'.'+name)
        if child:return types.SimpleNamespace(**{name:self.module(qualified+'.'+name)})
        raise ValueError('Missing locked local definition: '+qualified+'.'+name)

    def module(self,qualified):
        if qualified in self.modules:return self.modules[qualified]
        relative=self.path(qualified);assert relative,qualified
        path,text=self.source.read(relative);tree=ast.parse(text,str(path))
        selected=self.definitions.get(qualified) if self.definitions else None
        if selected is not None:
            keep=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in selected]
            assert {n.name for n in keep}==set(selected)
            used={n.id for node in keep for n in ast.walk(node) if isinstance(n,ast.Name)}
            tree.body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]+keep
        else:used=None
        module=types.ModuleType('lma_definitions_'+self.source.target+'_'+qualified)
        self.modules[qualified]=module;sys.modules[module.__name__]=module
        env=module.__dict__
        env.update({k:v for k,v in vars(typing).items() if not k.startswith('_')})
        env.update(torch=torch,nn=nn,F=F,np=np,math=math,warnings=warnings,logging=logging,
            logger=logging.getLogger('lma.depth'),partial=functools.partial,lru_cache=functools.lru_cache,
            functools=functools,dataclass=dataclasses.dataclass,Number=numbers.Number,Path=Path,
            Dict=AttrDict,DictConfig=dict,OmegaConf=types.SimpleNamespace(create=lambda x:x),
            trunc_normal_=nn.init.trunc_normal_,XFORMERS_AVAILABLE=False,XFORMERS_ENABLED=False,
            __package__=qualified.rsplit('.',1)[0])
        env.update(self.injections)
        # Resolve package-local aliases, including __init__ reexports, without
        # importing the original package or invoking an installed Hub helper.
        parent=qualified if relative.endswith('/__init__.py') else qualified.rsplit('.',1)[0]
        for node in tree.body:
            if isinstance(node,ast.ImportFrom):
                if node.module=='__future__':continue
                name=importlib.util.resolve_name('.'*node.level+(node.module or ''),parent) if node.level else node.module
                for alias in node.names:
                    key=alias.asname or alias.name
                    if used is not None and key not in used:continue
                    if key in self.injections:continue
                    if name==self.package or name.startswith(self.package+'.'):
                        dep=self.dependency(name,alias.name)
                        if alias.name=='*':env.update({k:v for k,v in vars(dep).items() if not k.startswith('_')})
                        else:env[key]=getattr(dep,alias.name)
                    elif name in ('typing','functools','collections','collections.abc','dataclasses','numbers','torch','torch.nn','torch.nn.init','torch.nn.functional','einops','enum'):
                        dep=importlib.import_module(name)
                        if alias.name=='*':env.update({k:v for k,v in vars(dep).items() if not k.startswith('_')})
                        else:env[key]=getattr(dep,alias.name)
                    elif name=='addict':env[key]=AttrDict
            elif isinstance(node,ast.Import):
                for alias in node.names:
                    key=alias.asname or alias.name.split('.')[0]
                    if used is not None and key not in used:continue
                    if key in self.injections:continue
                    if alias.name in ('math','typing','functools','collections','warnings','logging','numpy','torch','torch.nn','torch.nn.functional','torch.utils.checkpoint','itertools','copy'):
                        dep=importlib.import_module(alias.name)
                        env[key]=dep if alias.asname else importlib.import_module(alias.name.split('.')[0])
        body=[]
        for node in tree.body:
            if isinstance(node,ast.Try):
                # The pinned DINO sources provide a mathematical CPU fallback
                # for optional xFormers. Select its literal alias assignments.
                for handler in node.handlers:
                    if isinstance(handler.type,ast.Name) and handler.type.id=='ImportError':
                        for item in handler.body:
                            if isinstance(item,ast.Assign) and isinstance(item.value,(ast.Name,ast.Constant)):
                                body.append(item)
                continue
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
                # Compile/script decorators affect execution machinery only.
                # Preserve no_grad, class/static methods and pure memoization.
                for item in ast.walk(node):
                    if isinstance(item,(ast.FunctionDef,ast.ClassDef)):
                        item.decorator_list=[d for d in item.decorator_list if ast.unparse(d).split('(')[0] in ('staticmethod','classmethod','torch.no_grad','torch.inference_mode','lru_cache','functools.lru_cache','dataclass')]
                body.append(node)
            elif isinstance(node,(ast.Assign,ast.AnnAssign)) and node.value is not None:
                allowed=(ast.Constant,ast.List,ast.Tuple,ast.Dict,ast.Set,ast.Name,ast.Load,ast.Store,ast.Attribute,ast.UnaryOp,ast.USub,ast.UAdd,ast.Subscript,ast.BinOp,ast.Mult,ast.Div,ast.Add,ast.Sub,ast.Pow,ast.BitOr)
                if all(isinstance(n,allowed) for n in ast.walk(node.value)):body.append(node)
        code=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+body,type_ignores=[])
        exec(compile(ast.fix_missing_locations(code),str(path),'exec'),env)
        return module
