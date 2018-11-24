#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 22 17:08:58 2018

@author: apple
"""

'''
Default configurations.
'''

configs = {
        'debug':True,
        'db':{
            'host':'127.0.0.1',
            'port':3306,
            'user':'root',
            'password':'password',
            'db':'awesome'
        },
        'session':{
                'secret':'Awesome'
        }
}