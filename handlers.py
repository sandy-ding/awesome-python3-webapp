#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 22 17:58:20 2018

@author: apple
"""

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from webframe import get, post

from models import User, Comment, Blog, next_id

@get('/')
async def index(request):
    users = await User.findAll()
    return {
            '__template__':'test.html',
            'users':users
            }