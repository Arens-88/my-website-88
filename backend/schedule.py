"""简易的定时任务调度模块 - 内置实现"""
import time
import datetime
from threading import Thread
from collections import namedtuple

# 任务定义
Job = namedtuple('Job', ['job_func', 'next_run', 'interval'])  

# 任务列表
_jobs = []

class Scheduler:
    """简单的调度器实现"""
    
    def __init__(self):
        self.jobs = []
    
    def every(self):
        """返回间隔对象"""
        return Interval(self)
    
    def run_pending(self):
        """运行所有待执行的任务"""
        now = datetime.datetime.now()
        
        for job in self.jobs:
            if job.next_run and job.next_run <= now:
                # 执行任务
                try:
                    job.job_func()
                except Exception as e:
                    print(f"任务执行错误: {e}")
                
                # 重新计算下一次执行时间
                if hasattr(job, 'interval') and job.interval:
                    if job.interval.unit == 'day':
                        job = job._replace(next_run=now + datetime.timedelta(days=1))
    
    def clear(self):
        """清除所有任务"""
        self.jobs.clear()

class Interval:
    """时间间隔对象"""
    
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.unit = None
    
    def day(self):
        """设置为每天执行"""
        self.unit = 'day'
        return self
    
    def at(self, time_str):
        """设置具体的执行时间"""
        # 解析时间字符串 HH:MM
        try:
            hour, minute = map(int, time_str.split(':'))
            now = datetime.datetime.now()
            # 计算下一次执行时间
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # 如果时间已过，设置为明天
            if next_run <= now:
                next_run += datetime.timedelta(days=1)
            
            # 返回Action对象以绑定函数
            return Action(self.scheduler, next_run, self)
        except Exception:
            raise ValueError(f"无效的时间格式: {time_str}，应为 HH:MM 格式")

class Action:
    """动作对象，用于绑定任务函数"""
    
    def __init__(self, scheduler, next_run, interval):
        self.scheduler = scheduler
        self.next_run = next_run
        self.interval = interval
    
    def do(self, job_func):
        """绑定任务函数并添加到调度器"""
        job = Job(job_func=job_func, next_run=self.next_run, interval=self.interval)
        # 为了兼容性，添加一些常用属性
        job.id = job_func.__name__
        job.job_func = job_func
        
        self.scheduler.jobs.append(job)
        return job

# 创建全局调度器实例
scheduler = Scheduler()

# 暴露主要接口
every = scheduler.every
time = time
run_pending = scheduler.run_pending
clear = scheduler.clear

# 为了兼容性，添加jobs属性
jobs = scheduler.jobs