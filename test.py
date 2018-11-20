#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 19 22:03:51 2018

@author: apple
"""
import time
import asyncio
import orm
from models import User, Blog, Comment

async def test_save(loop):
    await orm.create_pool(user='root', password='password', db='awesome', loop=loop)
    u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank')
    await u.save()

async def test_findAll(loop):
    await orm.create_pool(user='root', password='password', db='awesome', loop=loop)
    rs = await User.findAll()  # rs是一个元素为dict的list
    for i in range(len(rs)):
        print(rs[i])
        
async def test_findNumber(loop):
    await orm.create_pool(user='root', password='password', db='awesome', loop=loop)
    count = await User.findNumber('email')
    print(count)
    
async def test_findById(loop):
    await orm.create_pool(user='root', password='password', db='awesome', loop=loop)
    rs = await User.findById('0015427212937869a3c9fd29601435db7f685df3f32192f000')
    print(rs)
    
async def test_remove(loop):
    await orm.create_pool(user='root', password='password', db='awesome', loop=loop)
    u = User(id='0015427212937869a3c9fd29601435db7f685df3f32192f000')
    await u.remove()

async def test_update(loop):
    await orm.create_pool(user='root', password='password', db='awesome', loop=loop)
    # 必须按照列的顺序来初始化：'update `users` set `created_at`=?, `passwd`=?, `image`=?,
    # id必须和数据库一致，其他属性可以设置成新的值,属性要全
    u = User(id='0015427212937869a3c9fd29601435db7f685df3f32192f000', created_at=time.time(), passwd='test',
             image='about:blank', admin=True, name='test', email='hello1@example.com')
    await u.update()
    
loop = asyncio.get_event_loop()
loop.run_until_complete(test_findAll(loop))
loop.close()