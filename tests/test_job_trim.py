import datetime
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from jobs.jobs.trim import (
    LONG_PAUSE_CONTAINER_PERIOD,
    LONG_PAUSE_PERIOD,
    LONG_PENDING_PERIOD,
    ORPHANED_PERIOD,
    run,
    trim_long_paused,
    trim_long_pending,
    trim_orphans,
)
from jobs.services.dto.sessionsvc import (
    SessionDC,
    SessionStatus,
)

_NOW = datetime.datetime(2026, 3, 5, 12, 0, 0, tzinfo=datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Helpers to build lightweight stub objects
# ---------------------------------------------------------------------------


def _make_session(
    *,
    sid: str = "s1",
    status: SessionStatus = SessionStatus.ACTIVE,
    age_seconds: int = 0,
    app_release_uuid: str = "app-uuid-1",
    user_id: int = 1,
) -> SessionDC:
    """Return a minimal SessionDC-like stub."""
    s = MagicMock(spec=SessionDC)
    s.id = sid
    s.status = status
    s.updated = _NOW - datetime.timedelta(seconds=age_seconds)
    s.app_release_uuid = app_release_uuid
    s.user_id = user_id
    return s


def _make_container(
    *,
    cid: str = "c1",
    status: str = "running",
    age_seconds: int = 0,
    app_release_uuid: str = "app-uuid-1",
    user_id: str = "1",
    app_slug: str = "some-app",
):
    """Return a minimal Container-like stub (mirrors ClusterStateResponseDTO.Node.Container)."""
    c = MagicMock()
    c.id = cid
    c.status = status
    c.created = _NOW - datetime.timedelta(seconds=age_seconds)
    c.specs.labels.app_release_uuid = app_release_uuid
    c.specs.labels.user_id = user_id
    c.specs.labels.app_slug = app_slug
    return c


def _make_node(*, node_id: str = "n1", containers: list | None = None):
    """Return a minimal Node-like stub (mirrors ClusterStateResponseDTO.Node)."""
    n = MagicMock()
    n.id = node_id
    n.containers = {c.id: c for c in (containers or [])}
    return n


# ---------------------------------------------------------------------------
# trim_long_paused – sessions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrimLongPausedSessions:
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_closes_paused_session_older_than_threshold(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", status=SessionStatus.PAUSED, age_seconds=LONG_PAUSE_PERIOD + 1)
        trim_long_paused([session], nodes=[])
        mock_close.assert_called_once_with("s1")
        mock_stop.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_does_not_close_recently_paused_session(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", status=SessionStatus.PAUSED, age_seconds=LONG_PAUSE_PERIOD - 1)
        trim_long_paused([session], nodes=[])
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_does_not_close_active_session(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", status=SessionStatus.ACTIVE, age_seconds=LONG_PAUSE_PERIOD + 100)
        trim_long_paused([session], nodes=[])
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_closes_multiple_paused_sessions(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        sessions = [
            _make_session(sid="s1", status=SessionStatus.PAUSED, age_seconds=LONG_PAUSE_PERIOD + 10),
            _make_session(sid="s2", status=SessionStatus.PAUSED, age_seconds=LONG_PAUSE_PERIOD + 20),
            _make_session(sid="s3", status=SessionStatus.ACTIVE, age_seconds=LONG_PAUSE_PERIOD + 30),
        ]
        trim_long_paused(sessions, nodes=[])
        assert mock_close.call_count == 2
        mock_close.assert_any_call("s1")
        mock_close.assert_any_call("s2")


# ---------------------------------------------------------------------------
# trim_long_paused – containers (irrespective of session state)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrimLongPausedContainers:
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_stops_container_paused_longer_than_threshold(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        container = _make_container(cid="c1", status="paused", age_seconds=LONG_PAUSE_CONTAINER_PERIOD + 1)
        node = _make_node(node_id="n1", containers=[container])
        trim_long_paused([], nodes=[node])
        mock_stop.assert_called_once_with("n1", "c1")
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_does_not_stop_recently_paused_container(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        container = _make_container(cid="c1", status="paused", age_seconds=LONG_PAUSE_CONTAINER_PERIOD - 1)
        node = _make_node(node_id="n1", containers=[container])
        trim_long_paused([], nodes=[node])
        mock_stop.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_does_not_stop_running_container(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        container = _make_container(cid="c1", status="running", age_seconds=LONG_PAUSE_CONTAINER_PERIOD + 100)
        node = _make_node(node_id="n1", containers=[container])
        trim_long_paused([], nodes=[node])
        mock_stop.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_stops_containers_across_multiple_nodes(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        c1 = _make_container(cid="c1", status="paused", age_seconds=LONG_PAUSE_CONTAINER_PERIOD + 10)
        c2 = _make_container(cid="c2", status="paused", age_seconds=LONG_PAUSE_CONTAINER_PERIOD + 20)
        nodes = [
            _make_node(node_id="n1", containers=[c1]),
            _make_node(node_id="n2", containers=[c2]),
        ]
        trim_long_paused([], nodes=nodes)
        assert mock_stop.call_count == 2
        mock_stop.assert_any_call("n1", "c1")
        mock_stop.assert_any_call("n2", "c2")

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.datetime")
    def test_handles_sessions_and_containers_together(self, mock_dt, mock_stop, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", status=SessionStatus.PAUSED, age_seconds=LONG_PAUSE_PERIOD + 1)
        container = _make_container(cid="c1", status="paused", age_seconds=LONG_PAUSE_CONTAINER_PERIOD + 1)
        node = _make_node(node_id="n1", containers=[container])
        trim_long_paused([session], nodes=[node])
        mock_close.assert_called_once_with("s1")
        mock_stop.assert_called_once_with("n1", "c1")


# ---------------------------------------------------------------------------
# trim_long_pending
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrimLongPending:
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_closes_pending_session_older_than_threshold(self, mock_dt, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", status=SessionStatus.PENDING, age_seconds=LONG_PENDING_PERIOD + 1)
        trim_long_pending([session])
        mock_close.assert_called_once_with("s1")

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_does_not_close_recently_pending_session(self, mock_dt, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", status=SessionStatus.PENDING, age_seconds=LONG_PENDING_PERIOD - 1)
        trim_long_pending([session])
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_ignores_active_sessions(self, mock_dt, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", status=SessionStatus.ACTIVE, age_seconds=LONG_PENDING_PERIOD + 100)
        trim_long_pending([session])
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_ignores_paused_sessions(self, mock_dt, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", status=SessionStatus.PAUSED, age_seconds=LONG_PENDING_PERIOD + 100)
        trim_long_pending([session])
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_closes_multiple_pending_sessions(self, mock_dt, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        sessions = [
            _make_session(sid="s1", status=SessionStatus.PENDING, age_seconds=LONG_PENDING_PERIOD + 5),
            _make_session(sid="s2", status=SessionStatus.PENDING, age_seconds=LONG_PENDING_PERIOD + 10),
            _make_session(sid="s3", status=SessionStatus.ACTIVE, age_seconds=9999),
        ]
        trim_long_pending(sessions)
        assert mock_close.call_count == 2
        mock_close.assert_any_call("s1")
        mock_close.assert_any_call("s2")

    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_no_sessions_does_nothing(self, mock_dt, mock_close):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        trim_long_pending([])
        mock_close.assert_not_called()


# ---------------------------------------------------------------------------
# trim_orphans
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrimOrphans:
    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_closes_orphaned_session_without_matching_container(self, mock_dt, mock_close, mock_stop):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", app_release_uuid="app-1", user_id=10, age_seconds=ORPHANED_PERIOD + 1)
        node = _make_node(node_id="n1", containers=[])
        trim_orphans([session], [node])
        mock_close.assert_called_once_with("s1")
        mock_stop.assert_not_called()

    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_does_not_close_session_with_matching_container(self, mock_dt, mock_close, mock_stop):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", app_release_uuid="app-1", user_id=10, age_seconds=ORPHANED_PERIOD + 1)
        container = _make_container(cid="c1", app_release_uuid="app-1", user_id="10", age_seconds=0)
        node = _make_node(node_id="n1", containers=[container])
        trim_orphans([session], [node])
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_stops_orphaned_container_without_matching_session(self, mock_dt, mock_close, mock_stop):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        container = _make_container(cid="c1", app_release_uuid="app-1", user_id="10", age_seconds=ORPHANED_PERIOD + 1)
        node = _make_node(node_id="n1", containers=[container])
        trim_orphans([], [node])
        mock_stop.assert_called_once_with("n1", "c1")
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_does_not_stop_young_orphaned_container(self, mock_dt, mock_close, mock_stop):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        container = _make_container(cid="c1", app_release_uuid="app-1", user_id="10", age_seconds=ORPHANED_PERIOD - 1)
        node = _make_node(node_id="n1", containers=[container])
        trim_orphans([], [node])
        mock_stop.assert_not_called()

    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_does_not_close_young_orphaned_session(self, mock_dt, mock_close, mock_stop):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", app_release_uuid="app-1", user_id=10, age_seconds=ORPHANED_PERIOD - 1)
        trim_orphans([session], [])
        mock_close.assert_not_called()

    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_matched_session_and_container_are_not_orphaned(self, mock_dt, mock_close, mock_stop):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        session = _make_session(sid="s1", app_release_uuid="app-1", user_id=10, age_seconds=ORPHANED_PERIOD + 100)
        container = _make_container(cid="c1", app_release_uuid="app-1", user_id="10", age_seconds=ORPHANED_PERIOD + 100)
        node = _make_node(node_id="n1", containers=[container])
        trim_orphans([session], [node])
        mock_close.assert_not_called()
        mock_stop.assert_not_called()

    @patch("jobs.jobs.trim.stop_container")
    @patch("jobs.jobs.trim.close_session")
    @patch("jobs.jobs.trim.datetime")
    def test_multiple_orphans_in_both_directions(self, mock_dt, mock_close, mock_stop):
        mock_dt.datetime.now.return_value = _NOW
        mock_dt.timezone = datetime.timezone
        # sessions without containers
        s1 = _make_session(sid="s1", app_release_uuid="app-1", user_id=1, age_seconds=ORPHANED_PERIOD + 1)
        s2 = _make_session(sid="s2", app_release_uuid="app-2", user_id=2, age_seconds=ORPHANED_PERIOD + 1)
        # containers without sessions
        c1 = _make_container(cid="c1", app_release_uuid="app-3", user_id="3", age_seconds=ORPHANED_PERIOD + 1)
        c2 = _make_container(cid="c2", app_release_uuid="app-4", user_id="4", age_seconds=ORPHANED_PERIOD + 1)
        node = _make_node(node_id="n1", containers=[c1, c2])
        trim_orphans([s1, s2], [node])
        assert mock_close.call_count == 2
        assert mock_stop.call_count == 2


# ---------------------------------------------------------------------------
# run (integration of all trimmers)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRun:
    @patch("jobs.jobs.trim.trim_long_pending")
    @patch("jobs.jobs.trim.trim_long_paused")
    @patch("jobs.jobs.trim.trim_orphans")
    @patch("jobs.jobs.trim.get_cluster_state")
    @patch("jobs.jobs.trim.get_sessions")
    def test_run_calls_all_trimmers(self, mock_get_sessions, mock_get_cluster, mock_orphans, mock_paused, mock_pending):
        session = _make_session(sid="s1")
        mock_get_sessions.return_value.sessions = [session]

        node = _make_node(node_id="n1")
        mock_get_cluster.return_value.nodes = {"n1": node}

        run()

        mock_get_sessions.assert_called_once()
        mock_get_cluster.assert_called_once()
        mock_orphans.assert_called_once_with(sessions=[session], nodes=[node])
        mock_paused.assert_called_once_with(sessions=[session], nodes=[node])
        mock_pending.assert_called_once_with(sessions=[session])
