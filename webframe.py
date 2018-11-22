#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 19 22:36:00 2018

@author: apple
"""

import asyncio, os, inspect, logging, functools

from urllib import parse
from aiohttp import web
from apis import APIError


def get(path):
    '''
    Define decorator @get('/path')
    '''
    ' @get装饰器，给处理函数绑定URL和HTTP method-GET的属性 '
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    '''
    define decorator @post('/path')
    '''
    ' @post装饰器，给处理函数绑定URL和HTTP method-POST的属性 '
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

# inspect.Parameter.kind 类型：
# POSITIONAL_ONLY          位置参数
# KEYWORD_ONLY             命名关键词参数
# VAR_POSITIONAL           可选参数 *args
# VAR_KEYWORD              关键词参数 **kw
# POSITIONAL_OR_KEYWORD    位置或必选参数
def has_request_arg(fn):
    ' 检查函数是否有request参数，返回布尔值。若有request参数，检查该参数是否为该函数的最后一个参数，否则抛出异常 '
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        #如果找到‘request’参数后，还出现位置参数，就会抛出异常
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

def has_named_kw_args(fn):
    ' 检查函数是否有命名关键字参数，返回布尔值 '
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True
        
def has_var_kw_arg(fn):
    ' 检查函数是否有关键字参数集，返回布尔值 '
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def get_named_kw_args(fn):
    ' 将函数所有的 命名关键字参数名 作为一个tuple返回 '
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def get_required_kw_args(fn):
    ' 将函数所有 没默认值的 命名关键字参数名 作为一个tuple返回 '
    args = []
    params = inspect.signature(fn).parameters     # 含有 参数名，参数 的信息
    for name, param in params.items():
        #类型为关键词参数 and 无默认值
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            # param.kind : describes how argument values are bound to the parameter.
		   # KEYWORD_ONLY : value must be supplied as keyword argument, which appear after a * or *args
		   # param.default : the default value for the parameter,if has no default value,this is set to Parameter.empty
		   # Parameter.empty : a special class-level marker to specify absence of default values and annotations
            args.append(name)
    return tuple(args)

#RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数，
#然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求
class RequestHandler(object):
    ' 请求处理器，用来封装处理函数 '
    def __init__(self, app, fn):
        # app : an application instance for registering the fn
        # fn : a request handler with a particular HTTP method and path
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)
        
    async def __call__(self, request):
        ' 分析请求，request handler,must be a coroutine that accepts a request instance as its only argument and returns a streamresponse derived instance '
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                # POST请求预处理
                if not request.content_type:
                    # 无正文类型信息时返回
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    # 处理JSON类型的数据，传入参数字典中
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    # 处理表单类型的数据，传入参数字典中
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            # GET请求预处理
            if request.method == 'GET':
                # 获取URL中的请求参数，如 name=Justone, id=007
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k,v in parse.parse_qs(qs, True).items():
                        # parse a query string, data are returned as a dict. 
                        #the dict keys are the unique query variable names and the values are lists of values for each name
					 # a True value indicates that blanks should be retained as blank strings
                        kw[k] = v[0]
        # 请求无请求参数时
        # request.match_info返回dict对象。可变路由中的可变字段{variable}为参数名，传入request请求的path为值
        # 若存在可变路由：/a/{name}/c，可匹配path为：/a/jack/c的request
        # 则reqwuest.match_info返回{name = jack}
        if kw is None:
            kw = dict(**request.match_info)
            # match_info: Read-only property with AbstractMatchInfo instance for result of route resolving
        else:
            # 参数字典收集请求参数
            # 若视图函数没有关键词参数 只有命名关键词参数
            if not self._has_var_kw_arg and self._named_kw_args:
                # 只保留命名关键词参数
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            #check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    # 检查kw中的参数是否和match_info中的重复
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        # check无默认值的关键字参数
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    # 若未传入必须参数值，报错。
                    # 例如 一般的账号注册时，没填入密码就提交注册申请时，提示密码未输入
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        # 至此，kw为视图函数fn真正能调用的参数
        # request请求中的参数，终于传递给了视图函数
        try:
            # 最后调用处理函数，并传入请求参数，进行请求处理
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)
        
def add_static(app):
    ' 添加静态资源路径 '
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static') #获得包含'static'的绝对路径
    app.router.add_static('/static/', path) # 添加静态资源路径
    logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):
    ' 将处理函数注册到web服务程序的路由当中 '
    method = getattr(fn, '__method__', None)
    path = getattr(fn,'__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' %str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        # 当处理函数不是协程时，封装为协程函数
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    # 在app中注册经RequestHandler类封装的视图函数
    app.router.add_route(method, path, RequestHandler(app, fn))
    
def add_routes(app, module_name):
    ' 自动把handler模块符合条件的函数注册 '
    n = module_name.rfind('.')  # 从右侧检索，返回索引。若无，返回-1。
    # 没有匹配项时
    if n == (-1):
        #__import__() 函数用于动态加载类和函数。,如果一个模块经常变化就可以使用 __import__() 来动态载入
        # __import__ 作用同import语句，但__import__是一个函数，并且只接收字符串作为参数
        # __import__(name[, globals[, locals[, fromlist[, level]]]])
        # __import__('os',globals(),locals(),['path','pip'], 0) ,等价于from os import path, pip
        mod = __import__(module_name, globals(), locals())
    else:
        # 添加模块属性 name，并赋值给mod
        name = module_name[n+1:]
        # 只获取最终导入的模块，为后续调用dir()
        mod = getattr(__import__(module_name[:n], globals(), locals(),[name]), name)
    for attr in dir(mod):
        # dir()函数不带参数时，返回当前作用域中的名称列表；带参数时，返回给定对象的一个已排序的属性名称列表
        if attr.startswith('_'):
            # 略过所有私有属性
            continue
        # 获取属性的值，可以是一个method
        fn = getattr(mod, attr)
        # 确保是函数
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                # 对已经修饰过的URL处理函数注册到web服务的路由中
                add_route(app, fn)
        
