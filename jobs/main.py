import logging
import queue
import threading
import time

import schedule

from jobs.jobs.trim import trim_job


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
    logging.getLogger("schedule").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)


def worker_main() -> None:
    while 1:
        job_func = jobqueue.get()
        job_func()
        jobqueue.task_done()


jobqueue: queue.Queue = queue.Queue()

schedule.every(5).seconds.do(jobqueue.put, trim_job)


worker_thread = threading.Thread(target=worker_main)
worker_thread.start()

if __name__ == "__main__":
    init_log()
    logging.info("starting asynchronous jobs...")
    while 1:
        schedule.run_pending()
        time.sleep(1)
