import os

from jobs.jobs.misc import JobException
from jobs.services.dto.jukeboxsvc import ClusterStateResponseDTO
from jobs.services.helpers import get_http_client_session

REQUESTS_TIMEOUT_CONN_READ = (3, 10)
JUKEBOXSVC_URL = os.environ["JUKEBOXSVC_URL"]


def get_cluster_state() -> ClusterStateResponseDTO:
    s = get_http_client_session()
    res = s.get(
        url=f"{JUKEBOXSVC_URL}/cluster/state",
        timeout=REQUESTS_TIMEOUT_CONN_READ,
    )
    if res.status_code != 200:
        raise JobException(message=res.text)
    return ClusterStateResponseDTO.Schema().load(data=res.json())


def stop_container(node_id: str, container_id: str) -> None:
    s = get_http_client_session()
    res = s.post(
        url=f"{JUKEBOXSVC_URL}/nodes/{node_id}/containers/{container_id}/stop",
        timeout=REQUESTS_TIMEOUT_CONN_READ,
    )
    if res.status_code != 200:
        raise JobException(message=res.text)
