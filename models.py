#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 19 20:41:01 2018

@author: apple
"""

import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

    # 使用时间与伪随机数生成返回值
def next_id():
    #%015d：由时间生成15位的整数，不足在前用0补全
    #uuid4()可以获得一个唯一的ID, hex：指定32个字符以创建UUID对象
    #共50位的id
    return '%015d%s000' % (int(time.time()*1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'
    
    id = StringField(primary_key=True, default=next_id,ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)
    
class Blog(Model):
    __table__ = 'blogs'
    
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)
    
class Comment(Model):
    __table__ = 'comments'
    
    id = StringField(primary_key=True, default=next_id,ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)
    