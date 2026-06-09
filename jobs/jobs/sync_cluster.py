import logging

from jobs.jobs.misc import catch_exceptions
from jobs.services.jukeboxsvc import sync_cluster

log = logging.getLogger("jobs.job_sync_cluster")


def run() -> None:
    log.debug("syncing cluster")
    sync_cluster()
    log.debug("cluster synced")


@catch_exceptions(cancel_on_failure=True)
def sync_cluster_job() -> None:
    run()
