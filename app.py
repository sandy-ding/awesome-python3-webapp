#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 13 21:05:44 2018

@author: apple
"""

'''
async web application
'''


import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

import orm
from webframe import add_routes, add_static

def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    # class Environment(**options)
    # 配置options参数
    options = dict(
        # 自动转义xml/html的特殊字符
        autoescape = kw.get('autoescape', True),
        block_start_string = kw.get('block_start_string', '{%'),
        block_end_string = kw.get('block_end_string', '%}'),
        variable_start_string = kw.get('variable_start_string', '{{'),
        variable_end_string = kw.get('variable_end_string', '}}'),
        # 自动加载修改后的模板文件
        auto_reload = kw.get('auto_reload', True)        
    )
    # 获取模板文件夹路径
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    	# Environment类是jinja2的核心类，用来保存配置、全局对象以及模板文件的路径
	# FileSystemLoader类加载path路径中的模板文件
    env = Environment(loader=FileSystemLoader(path), **options)
    # 过滤器集合
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            # filters是Environment类的属性：过滤器字典
            env.filters[name] = f
    	# 所有的一切是为了给app添加__templating__字段
	# 前面将jinja2的环境配置都赋值给env了，这里再把env存入app的dict中，这样app就知道要到哪儿去找模板，怎么解析模板
    app['__templating__'] = env

# 编写用于输出日志的middleware
# handler是视图函数
async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        # await asyncio.sleep(0.3)
        return (await handler(request))
    return logger


async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data

# 处理视图函数返回值，制作response的middleware
# 请求对象request的处理工序：
# logger_factory => response_factory => RequestHandler().__call__ => handler
# 响应对象response的处理工序：
# 1、由视图函数处理request后返回数据
# 2、@get@post装饰器在返回对象上附加'__method__'和'__route__'属性，使其附带URL信息
# 3、response_factory对处理后的对象，经过一系列类型判断，构造出真正的web.Response对象
async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        # StreamResponse是所有Response对象的父类
        if isinstance(r, web.StreamResponse):
            # 无需构造，直接返回
            return r
        if isinstance(r, bytes):
            # 继承自StreamResponse，接受body参数，构造HTTP响应内容
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
             # 若返回重定向字符串
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])  # 重定向至目标URL
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            # 在后续构造视图函数返回值时，会加入__template__值，用以选择渲染的模板
            template = r.get('__template__')
            # 不带模板信息，返回json对象
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o:o.__dict__).encode('utf-8'))
                #json.dumps()函数是将一个Python数据类型列表进行json格式的编码，即将字典转化为字符串
                # ensure_ascii：默认True，仅能输出ascii格式数据。故设置为False
                # default：r对象会先被传入default中的函数进行处理，然后才被序列化为json对象
                # __dict__：以dict形式返回对象属性和值的映射
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            # 带模板信息，渲染模板
            else:
                #app['__templating__']获取已初始化的Environment对象，调用get_template()方法返回Template对象
                # 调用Template对象的render()方法，传入r渲染模板，返回unicode格式字符串，将其用utf-8编码
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        # 返回响应码
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        # 返回了一组响应代码和原因，如：(200, 'OK'), (404, 'Not Found')
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >=100 and t <600:
                return web.Response(t, str(m))
        # 均以上条件不满足，默认返回utf-8纯文本
        resp = web.Response(body=str(r).encode('utf-8')) 
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta//60)
    if delta < 86400:
        return u'%s小时前' % (delta //3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

async def init(loop):
    await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password='password', db='awesome')
    app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    init_jinja2(app,filters=dict(datetime=datetime_filter))
    add_routes(app, 'handers')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()