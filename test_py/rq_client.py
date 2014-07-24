from rq_server import conn
from rq import Queue
from rq import get_current_job
from time import time, sleep


low_queue = Queue('low', connection=conn)
default_queue = Queue('default', connection=conn)
high_queue = Queue('high', connection=conn)


_alive_jobs = {}


def mem_job(job):
    if job in _alive_jobs:
        if job.is_finished:
            del _alive_jobs[job]
        return
    _alive_jobs[job] = job


def get_result(job, timeout=5):
    if job.is_finished:
        return job.result
    sleep(timeout)
    return job.result if job.result else 'Job timeout'
