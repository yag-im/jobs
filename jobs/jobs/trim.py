import datetime
import logging

from jobs.jobs.misc import catch_exceptions
from jobs.services.dto.jukeboxsvc import ClusterStateResponseDTO
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
LONG_PENDING_PERIOD = 10
ORPHANED_PERIOD = 10


def log_sessions_report(sessions: list[SessionDC]) -> None:
    logging.debug(
        "\tsessions - pending: %d, active: %d, paused: %d, total: %d",
        sum(s.status == "pending" for s in sessions),
        sum(s.status == "active" for s in sessions),
        sum(s.status == "paused" for s in sessions),
        len(sessions),
    )


def trim_long_paused(sessions: list[SessionDC]) -> None:
    logging.debug("trimming long paused sessions/containers")
    log_sessions_report(sessions)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    for s in sessions:
        if (s.status == SessionStatus.PAUSED) and (now - s.updated).total_seconds() > LONG_PAUSE_PERIOD:
            logging.info("\tclosing long paused session: %s", s.id)
            close_session(s.id)


def trim_long_pending(sessions: list[SessionDC]) -> None:
    logging.debug("trimming long pending sessions/containers")
    log_sessions_report(sessions)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    for s in sessions:
        if (s.status == SessionStatus.PENDING) and (now - s.updated).total_seconds() > LONG_PENDING_PERIOD:
            logging.info("\tclosing long pending session: %s", s.id)
            close_session(s.id)


def trim_orphans(sessions: list[SessionDC], nodes: list[ClusterStateResponseDTO.Node]) -> None:
    logging.debug("trimming orphaned sessions/containers")

    def sess_map_key(app_release_uuid: str, user_id: int) -> str:
        return f"{app_release_uuid}|{str(user_id)}"

    sess_dct: dict[str, SessionDC] = {sess_map_key(s.app_release_uuid, s.user_id): s for s in sessions}
    log_sessions_report(sessions)

    containers_dct: dict[str, tuple[ClusterStateResponseDTO.Node.Container, str]] = {}
    for n in nodes:
        for c in n.containers.values():
            containers_dct[sess_map_key(c.specs.labels.app_release_uuid, int(c.specs.labels.user_id))] = (c, n.id)
    logging.debug(
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
        logging.info(f"\torphaned sessions: {orphaned_sessions}")  # pylint: disable=logging-fstring-interpolation
        for s in orphaned_sessions:
            logging.info("\tclosing orphaned session: %s", s.id)
            close_session(s.id)

    orphaned_containers: list[tuple[ClusterStateResponseDTO.Node.Container, str]] = [
        v
        for k, v in containers_dct.items()
        if k not in sess_dct and (now - v[0].created).total_seconds() > ORPHANED_PERIOD
    ]
    if orphaned_containers:
        logging.info(f"\torphaned containers: {orphaned_containers}")  # pylint: disable=logging-fstring-interpolation
        for oc in orphaned_containers:
            logging.info("\tstopping orphaned container: %s", oc[0].id)
            stop_container(oc[1], oc[0].id)


def run() -> None:
    sessions = get_sessions()
    cluster_state = get_cluster_state()
    trim_orphans(sessions=sessions.sessions, nodes=list(cluster_state.nodes.values()))
    trim_long_paused(sessions=sessions.sessions)
    trim_long_pending(sessions=sessions.sessions)


@catch_exceptions(cancel_on_failure=True)
def trim_job() -> None:
    run()
