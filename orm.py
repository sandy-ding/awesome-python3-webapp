#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 15 19:29:25 2018

@author: apple
"""

import asyncio, logging

import aiomysql

#定义log函数，传入的应该是数据库语句
#这个函数在每个具体的数据库操作函数的开头调用，用来打印当前执行的sql语句
def log(sql, args = ()):
    logging.info('SQL: %s' %sql)

#创建一个全局的连接池，每个HTTP请求都可以从连接池中直接获取数据库连接。使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
#**kw指的接收不限个数个关键字参数，以dict形式存储参数，这里连接池创建函数传入的是host,port,user等连接的数据库信息
async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global _pool
    #连接池由全局变量__pool存储，缺省情况下将编码设置为utf8，自动提交事务
    #调用aiomysql.create_pool函数即可以连接到指定数据库上
    #get()查找dict,找不到用默认值
    _pool = await aiomysql.create_pool(
            host = kw.get('host', 'localhost'),
            port = kw.get('port', 3306),
            user = kw['user'],
            password = kw['password'],
            db = kw['sdb'],
            charset = kw.get('charset', 'utf8'),
            autocommit = kw.get('autocommit', True),
            maxsize = kw.get('maxsize',10),
            minsize = kw.get('minsize', 1),
            loop = loop
    )

#用select函数执行SELECT语句，需要传入SQL语句和SQL参数：
async def select(sql, args, size = None):
    log(sql, args)
    global _pool
    #获取数据库连接
    async with _pool.get() as conn:
        #获取游标,默认游标返回的结果为元组（每一项是另一个元组）,这里可以通过aiomysql.DictCursor指定元组的元素为字典
        async with conn.cursor(aiomysql.DictCursor) as cur:
            #调用游标的execute()方法来执行sql语句,execute()接收两个参数,
            #第一个为sql语句（可以包含占位符）,第二个为占位符对应的值（也就是参数列表中传入的args）,
            #使用该形式可以避免直接使用字符串拼接出来的sql的注入攻击
            #sql语句的占位符为?,mysql里为%s,做替换
            await cur.execute(sql.replace('?', '%s'), args or ())
            #size有值就获取对应数量的数据
            if size:
                rs = await cur.fetchmany(size)
            else:
                #获取所有数据库中的所有数据,此处返回的是一个数组,数组元素为字典
                rs = await cur.fetchall()
        logging.info('rows returned: %s' %len(rs))
        return rs

#要执行INSERT、UPDATE、DELETE语句，可以定义一个通用的execute()函数，因为这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数
#execute()函数和select()函数所不同的是，cursor对象不返回结果集，而是通过rowcount返回结果数。
async def execute(sql, args, autocommit=True):
    log(sql)
    async with _pool.get() as conn:
        #如果不是自动提交事务,需要手动启动,但是我发现这个是可以省略的
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                #获取增删改影响的行数
                affected = cur.rowcount
                #没有自动提交则手动执行commit()命令
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                #回滚,在执行commit()之前如果出现错误,就回滚到执行事务前的状态,以免影响数据库的完整性
                await conn.rollback()
            raise
        return affected

#创建拥有几个占位符的字符串（？？？）用在比如后面的insert中的(值1, 值2,....)
#这个部分就要根据传入的参数替换，最多有总列数的参数，所以需要提前用有总列数num个占位符'？'的字符串放在(值1, 值2,....)相应的位置。
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

#Field 类:为了保存数据库列名和类型的基类(所有表中field的类型的基类）
#基类先设置每个列都需要的属性，比如是否主键，默认值；
#其他继承的不同Field再根据自己的类型重写初始化参数。
#每个表的列名实例后，每个表的实例化就相当于在表中添加具体的每一行。
class Field(object):
    
    def __init__(self, name, column_type, primary_key, default):
        self.name = name  #列名
        self.column_type = column_type  #数据类型
        self.primary_key = primary_key  #是否为主键
        self.default = default  #默认值
    
    #<表名，列类型：列名>
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

#具体的列名的数据类型，映射varchar的StringField。ddl指的表中这一列的数据的类型设置（字符型varchar）
class StringField(Field):
    
    def __init__(self, name = None, ddl='varchar(100)', primary_key = False, default = None):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):
    
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)
        
class IntegerField(Field):
    
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)
        
class FloatField(Field):
    
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)
        
class TextField(Field):
    
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

#表的属性
class ModelMetaclass(type):
    
    def __new__(cls, name, bases, attrs):
        #排除Model类本身：
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        #获取table名称：
        #tableName就是保存表名，通过get获取dict对象attr中的__table__属性，如果为真则输出结果，否则把类名name作为表名
        #or的短路逻辑
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table:%s)' % (name, tableName))
        #获取所有的Field和主键名：
        #保存列类型的对象
        mappings = dict()
        #保存列名的数组，也就是这个表中所有的列（除主键外）
        fields = []
        #存放主键的属性，初始值为None
        primaryKey = None
        # 因为attrs中传入的是类的方法属性的集合，在属性中有id=IntergerField这样的属性
        # 其中id就是k,IntergerField就是v，下面的判断是判断传入参数
        # 将field类型的属性（也就是列名（列名都是基于field类）和值）保存下来
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                #因为在field中需要传入是不是主键的参数属性primary_key，所以可以利用这个判断
                if v.primary_key:
                    # 找到主键，进入到这里就表示当前为主键，判断在此之前primaryKey是否为真，为真则表示主键不唯一错误。
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field:%s' % k)
                    primaryKey = k
                else:
                    #保存非主键的列名
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        #如果找到一个Field属性，就把它保存到一个__mappings__的dict中，同时从类属性中删除该Field属性，
        #否则，容易造成运行时错误（实例的属性会遮盖类的同名属性）
        for k in mappings.keys():  #循环所有的键
            attrs.pop(k)  #删除所有键，也就是列名
        #lambda 参数:一个表达式，传入参数
        #escaped_fields = ['`列名`','`列名`','`列名`','`列名`']
        escaped_fields = list(map(lambda f:'`%s`' % f, fields))
        attrs['__mappings__'] = mappings  #保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey  #主键属性名
        attrs['__fields__'] = fields  #除主键外的属性名
        #构造默认的select, insert, update和delete语句：
        #保存对象的属性到内置的属性名称中
        #反引号的作用是为了避免与sql关键字冲突
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        #create_args_string(num) 这个语句是调用的前面创建占位符的函数，创建有num个占位符的字符串，num也就是总列数
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields)+1))
        attrs['__update__'] = 'update `%s` set %s where `%s` = ?' % (tableName, ', '.join(map(lambda f:'%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)
    
    
class Model(dict, metaclass = ModelMetaclass):
    
    def __init__(self, **kw):
        super(Model,self).__init__(**kw)
        
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)
    
    def __setattr__(self, key, value):
        self[key] = value
        
    def getValue(self, key):
        return getattr(self, key, None)
    
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value
    
    #classmethod 修饰符对应的函数不需要实例化，不需要 self 参数，
    #但第一个参数需要是表示自身类的 cls 参数，可以来调用类的属性，类的方法，实例化对象等
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. ' 
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            #截取前limit条记录
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            #截取[m,n]的记录
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql),args)
        #返回一个列表。每个元素都是一个dict，相当于一行记录
        #??? [cls(**r)]
        return [cls(**r) for r in rs]
    
    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where '
        # _num_是SQL的一个字段别名用法，AS关键字可以省略
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        #根据别名key取值
        #??? ['_num_']
        return rs[0]['_num_']
        
    @classmethod
    async def findById(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    #实例方法
    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)
            
    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key : affected rows: %s' % rows)            

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key : affected rows: %s' % rows)

    
    
    


    
