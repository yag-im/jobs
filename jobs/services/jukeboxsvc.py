import os
from http import HTTPStatus

import httpx

from jobs.jobs.misc import JobException
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client import Client
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.api.default import get_cluster_state as _get_cluster_state
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.api.default import scale_cluster as _scale_cluster
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.api.default import stop_container as _stop_container
from jobs.services.clients.jukeboxsvc.jukeboxsvc_client.models import ClusterStateResponseDTO

JUKEBOXSVC_URL = os.environ["JUKEBOXSVC_URL"]
_TIMEOUT = httpx.Timeout(connect=3, read=120, write=30, pool=10)


def _client() -> Client:
    return Client(base_url=JUKEBOXSVC_URL, timeout=_TIMEOUT)  # type: ignore[call-arg]


def get_cluster_state() -> ClusterStateResponseDTO:
    resp = _get_cluster_state.sync_detailed(client=_client())
    if resp.status_code != HTTPStatus.OK:
        raise JobException(message=resp.content.decode())
    if resp.parsed is None:
        raise JobException(message="empty response from cluster/state")
    return resp.parsed


def stop_container(node_id: str, container_id: str) -> None:
    resp = _stop_container.sync_detailed(node_id=node_id, container_id=container_id, client=_client())
    if resp.status_code != HTTPStatus.OK:
        raise JobException(message=resp.content.decode())


def scale_cluster() -> None:
    resp = _scale_cluster.sync_detailed(client=_client())
    if resp.status_code != HTTPStatus.OK:
        raise JobException(message=resp.content.decode())
