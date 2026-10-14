import json
import logging
import os
from http import HTTPStatus

import httpx

from jobs.jobs.misc import JobException
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client import Client
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.api.default import get_cluster_state as _get_cluster_state
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.api.default import scale_cluster as _scale_cluster
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.api.default import stop_container as _stop_container
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.api.default import sync_cluster_state as _sync_cluster_state
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.models import ClusterStateResponseDTO

JUKEBOXSVC_URL = os.environ["JUKEBOXSVC_URL"]
_TIMEOUT = httpx.Timeout(connect=3, read=120, write=30, pool=10)
ERR_CODE_NODE_NOT_FOUND = 1404

log = logging.getLogger("jobs.jukeboxsvc")


def _client() -> Client:
    return Client(base_url=JUKEBOXSVC_URL, timeout=_TIMEOUT)


def get_cluster_state() -> ClusterStateResponseDTO:
    resp = _get_cluster_state.sync_detailed(client=_client())
    if resp.status_code != HTTPStatus.OK:
        raise JobException(message=resp.content.decode())
    if resp.parsed is None:
        raise JobException(message="empty response from cluster/state")
    return resp.parsed


def _error_code(content: bytes) -> int | None:
    try:
        body = json.loads(content)
    except ValueError:
        return None
    if isinstance(body, dict) and isinstance(body.get("detail"), dict):
        body = body["detail"]
    return body.get("code") if isinstance(body, dict) else None


def stop_container(node_id: str, container_id: str) -> None:
    resp = _stop_container.sync_detailed(node_id=node_id, container_id=container_id, client=_client())
    if resp.status_code == HTTPStatus.OK:
        return
    code = _error_code(resp.content)
    if code == ERR_CODE_NODE_NOT_FOUND:
        # node is gone (e.g. decommissioned) and so are its containers
        log.warning("node %s not found, treating container %s as stopped", node_id, container_id)
        return
    raise JobException(code=code, message=resp.content.decode())


def scale_cluster() -> None:
    resp = _scale_cluster.sync_detailed(client=_client())
    if resp.status_code != HTTPStatus.OK:
        raise JobException(message=resp.content.decode())


def sync_cluster() -> None:
    resp = _sync_cluster_state.sync_detailed(client=_client())
    if resp.status_code != HTTPStatus.OK:
        raise JobException(message=resp.content.decode())
