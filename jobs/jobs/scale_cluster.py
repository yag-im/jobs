import logging

from jobs.jobs.misc import catch_exceptions
from jobs.services.jukeboxsvc import scale_cluster

log = logging.getLogger("jobs.job_scale_cluster")


def run() -> None:
    log.debug("scaling cluster")
    scale_cluster()
    log.debug("cluster scaled")


@catch_exceptions(cancel_on_failure=True)
def scale_cluster_job() -> None:
    run()
