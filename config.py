#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 22 17:17:50 2018

@author: apple
"""

'''
Configuration
'''

import config_default

class Dict(dict):
    '''
    simple dict but support access as x.y style.
    '''
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k,v in zip(names, values):
            self[k] = v
            
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)
            
    def __setattr__(self, key, value):
        self[key] = value
        
        
def merge(defaults, override):
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v,dict):
                #递归
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r
            
def toDict(d):
    D = Dict()
    for k, v in d.items():
        #递归，dict转换成Dict后可以这么读取配置：configs.db.host就能读到host的值
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)