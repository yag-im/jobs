import logging
import queue
import threading
import time
from typing import Callable

import schedule

# from jobs.jobs.scale_cluster import scale_cluster_job
from jobs.jobs.trim_sessions import trim_sessions_job


def init_log() -> None:
    # TODO: use app.config["DEBUG"] flag for log_level
    log_level = logging.DEBUG

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))

    root_log = logging.getLogger()
    root_log.handlers.clear()
    root_log.addHandler(handler)
    root_log.setLevel(log_level)
    root_log.propagate = False

    # talkative modules:
    for module in ["schedule", "urllib3", "httpx", "httpcore"]:
        logging.getLogger(module).setLevel(logging.INFO)


def worker_main(jobqueue: queue.Queue) -> None:
    while 1:
        job_func = jobqueue.get()
        job_func()
        jobqueue.task_done()


def enqueue_if_empty(jobqueue: queue.Queue, job_func: Callable) -> None:
    if jobqueue.empty():
        jobqueue.put(job_func)


trim_sessions_queue: queue.Queue = queue.Queue()
scale_cluster_queue: queue.Queue = queue.Queue()

schedule.every(5).seconds.do(enqueue_if_empty, trim_sessions_queue, trim_sessions_job)
# schedule.every(1).minutes.do(enqueue_if_empty, scale_cluster_queue, scale_cluster_job)


worker_thread = threading.Thread(target=worker_main, args=(trim_sessions_queue,))
worker_thread.start()

scale_worker_thread = threading.Thread(target=worker_main, args=(scale_cluster_queue,))
scale_worker_thread.start()

if __name__ == "__main__":
    init_log()
    logging.info("starting asynchronous jobs...")
    while 1:
        schedule.run_pending()
        time.sleep(1)
