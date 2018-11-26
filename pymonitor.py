#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 26 14:52:56 2018

@author: apple
"""

'''
创建监视修改重启程序
'''

import os, sys, time, subprocess

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def log(s):
    print('[Monitor] % s' % s)
   
#FileSystemEventHandler事件类基类，所有具体事件类的父类
#事件处理器的基类，用于处理事件，用户需继承该类，并在子类中重写对应方法
#当一个目录或文件变化时，就会产生一个特定事件，也就是该类的子类
class MyFileSystemEventHandler(FileSystemEventHandler):
    
    def __init__(self, fn):
        super(MyFileSystemEventHandler, self).__init__()
        self.restart = fn
        
    #任何事件发生都会首先执行该方法，该方法默认为空，
    #dispatch()方法会先执行该方法，然后再把event分派给其他方法处理
    def on_any_event(self, event):
        #监视`.py`后缀文件发生改变
        if event.src_path.endswith('.py'):
            log('Python source file changed: %s' % event.src_path)
            self.restart()
            
# ???
command = ['echo', 'ok']  #重启操作文件的信息
process = None

def kill_process():
    global process
    if process:
        log('Kill process [%s]...' % process.pid)
        process.kill()
        # p.wait() 立即阻塞父进程，直到子进程结束,返回 p.returncode 属性
        process.wait()
        log('Process ended with code %s.' % process.returncode)
        process = None

def start_process():
    global process, command
    log('Start process %s...' % ' '.join(command))
    # subprocess.Popen(args, tdin=None, stdout=None, stderr=None)创建并返回一个子进程，并在这个进程中执行指定的程序
    # args：要执行的命令或可执行文件的路径，stdin, stdout, stderr分别表示程序的标准输入、输出、错误输出
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    
def restart_process():
    kill_process()
    start_process()
    
def start_watch(path, callback):
    # 该类实现了监控文件变化，触发对应的事件类，然后调用关联的事件处理类来处理事件
    #该类其实是threading.Thread的子类线程，不会阻塞主进程运行
    observer = Observer()
    # 监控指定路径path，该路径触发任何事件都会调用event_handler来处理
    # 如果path是目录，则recursive=True则会递归监控该目录的所有变化
    observer.schedule(MyFileSystemEventHandler(restart_process), path, recursive=True)
    observer.start()
    log('Watching directory %s...' % path)
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    #thread1.join() blocks the thread in which you're making the call, until thread1 is finished.
    #It's like wait_until_finished(thread1)
    observer.join()
    
if __name__ == '__main__':
    argv = sys.argv[1:]
    if not argv:
        print('Usage: ./pymonitor your-script.py')
        exit(0)
    print(argv)
    if argv[0] != 'python3':
        argv.insert(0, 'python3')
    command = argv  #操作文件的名字及程序名
    path = os.path.abspath('.')
    start_watch(path, None)