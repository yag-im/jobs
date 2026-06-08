import datetime
import logging

from jobs.jobs.misc import catch_exceptions
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.models import (
    ContainerDTO,
    NodeDTO,
)
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.types import Unset
from jobs.services.dto.sessionsvc import (
    SessionDC,
    SessionStatus,
)
from jobs.services.jukeboxsvc import (
    get_cluster_state,
    stop_container,
)
from jobs.services.sessionsvc import (
    close_session,
    get_sessions,
)

LONG_PAUSE_PERIOD = 600
LONG_PAUSE_CONTAINER_PERIOD = 900
LONG_PENDING_PERIOD = 20
ORPHANED_PERIOD = 30

log = logging.getLogger("jobs.job_trim_sessions")


def log_sessions_report(sessions: list[SessionDC]) -> None:
    log.debug(
        "\tsessions - pending: %d, active: %d, paused: %d, total: %d",
        sum(s.status == "pending" for s in sessions),
        sum(s.status == "active" for s in sessions),
        sum(s.status == "paused" for s in sessions),
        len(sessions),
    )


def trim_long_paused(
    sessions: list[SessionDC],
    nodes: list[NodeDTO],
) -> None:
    log.debug("trimming long paused sessions/containers")
    log_sessions_report(sessions)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    for s in sessions:
        if (s.status == SessionStatus.PAUSED) and (now - s.updated).total_seconds() > LONG_PAUSE_PERIOD:
            log.info("\tclosing long paused session: %s", s.id)
            close_session(s.id)

    # stop containers that have been paused for too long, irrespective of session state
    for n in nodes:
        for c in n.containers:
            if (
                c.status == "paused"
                and not isinstance(c.created, Unset)
                and c.created is not None
                and (now - c.created).total_seconds() > LONG_PAUSE_CONTAINER_PERIOD
            ):
                log.info("\tstopping long paused container: %s on node %s", c.id, n.id)
                stop_container(n.id, c.id)


def trim_long_pending(sessions: list[SessionDC]) -> None:
    log.debug("trimming long pending sessions/containers")
    log_sessions_report(sessions)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    for s in sessions:
        if (s.status == SessionStatus.PENDING) and (now - s.updated).total_seconds() > LONG_PENDING_PERIOD:
            log.info("\tclosing long pending session: %s", s.id)
            close_session(s.id)


def trim_orphans(sessions: list[SessionDC], nodes: list[NodeDTO]) -> None:
    log.debug("trimming orphaned sessions/containers")

    def sess_map_key(app_release_uuid: str, user_id: int) -> str:
        return f"{app_release_uuid}|{str(user_id)}"

    sess_dct: dict[str, SessionDC] = {sess_map_key(s.app_release_uuid, s.user_id): s for s in sessions}
    log_sessions_report(sessions)

    containers_dct: dict[str, tuple[ContainerDTO, str]] = {}
    for n in nodes:
        for c in n.containers:
            containers_dct[sess_map_key(c.specs.labels.app_release_uuid, int(c.specs.labels.user_id))] = (c, n.id)
    log.debug(
        "\tcontainers - running: %d, paused: %d, total: %d",
        sum(c[0].status == "running" for c in containers_dct.values()),
        sum(c[0].status == "paused" for c in containers_dct.values()),
        len(containers_dct),
    )

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    orphaned_sessions: list[SessionDC] = [
        v
        for k, v in sess_dct.items()
        if k not in containers_dct and (now - v.updated).total_seconds() > ORPHANED_PERIOD
    ]
    if orphaned_sessions:
        log.info(f"\torphaned sessions: {orphaned_sessions}")  # pylint: disable=logging-fstring-interpolation
        for s in orphaned_sessions:
            log.info("\tclosing orphaned session: %s", s.id)
            close_session(s.id)

    orphaned_containers: list[tuple[ContainerDTO, str]] = [
        v
        for k, v in containers_dct.items()
        if k not in sess_dct
        and not isinstance(v[0].created, Unset)
        and v[0].created is not None
        and (now - v[0].created).total_seconds() > ORPHANED_PERIOD
    ]
    if orphaned_containers:
        log.info(f"\torphaned containers: {orphaned_containers}")  # pylint: disable=logging-fstring-interpolation
        for oc in orphaned_containers:
            log.info("\tstopping orphaned container: %s", oc[0].id)
            stop_container(oc[1], oc[0].id)


def run() -> None:
    log.debug("getting sessions")
    sessions = get_sessions()
    log.debug("getting cluster state")
    cluster_state = get_cluster_state()
    trim_orphans(sessions=sessions.sessions, nodes=cluster_state.nodes)
    trim_long_paused(sessions=sessions.sessions, nodes=cluster_state.nodes)
    trim_long_pending(sessions=sessions.sessions)


@catch_exceptions(cancel_on_failure=True)
def trim_sessions_job() -> None:
    run()
