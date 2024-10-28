# sync with jukeboxsvc (jukeboxsvc/dto/container.py)

import datetime
import typing as t
from dataclasses import field
from enum import StrEnum

from marshmallow import Schema
from marshmallow_dataclass import dataclass


class DcRegion(StrEnum):
    EU_CENTRAL_1 = "eu-central-1"
    US_EAST_1 = "us-east-1"
    US_WEST_1 = "us-west-1"


class WindowSystem(StrEnum):
    X11 = "x11"
    WAYLAND = "wayland"


class VideoEnc(StrEnum):
    CPU = "cpu"
    GPU_INTEL = "gpu-intel"
    GPU_NVIDIA = "gpu-nvidia"


@dataclass
class WsConnDC:
    """Websocket connection (sigsvc) parameters."""

    consumer_id: str  # peer_id of the party awaiting for a stream
    id: str  # unique ws connection id (used as a sticky session cookie value)


@dataclass
class RunContainerRequestDTO:
    @dataclass
    class AppDescr:
        # slug and release_uuid are also parts of an app path in appstor
        slug: str  # igdb slug, e.g. the-pink-panther-hokus-pokus-pink
        release_uuid: str  # unique release id, e.g.: 653cc955-8e32-4fb6-b44c-5d43897e0219

    @dataclass
    class Requirements:
        @dataclass
        class AppRequirements:
            color_bits: int
            midi: bool
            screen_height: int
            screen_width: int

        @dataclass
        class ContainerSpecs:
            @dataclass
            class Runner:
                name: str
                ver: str
                window_system: WindowSystem = field(metadata={"by_value": True})

            image_rev: str
            runner: Runner
            video_enc: VideoEnc = field(metadata={"by_value": True})  # streamd requirement

            def image_tag(self) -> str:
                res = "{}_{}_{}_{}_{}".format(  # pylint: disable=consider-using-f-string
                    self.runner.window_system,
                    self.video_enc,
                    self.runner.name,
                    self.runner.ver,
                    self.image_rev,
                )
                return res

        # TODO: dup of jukebox.core.node.NodeRequirements
        @dataclass
        class HardwareRequirements:
            dgpu: bool  # could be for either app (3D game) or streamd (powerfull codec / highres)
            igpu: bool  # mostly for streamd, but can also be used by some games
            memory: int  # memory required by apps running inside a container (game, runner and streamd)
            memory_shared: t.Optional[int]  # shared memory required by apps (in bytes)
            nanocpus: int  # nanocpus required by apps running inside a container (game, runner and streamd)

        app: AppRequirements
        container: ContainerSpecs
        hw: HardwareRequirements

    app_descr: AppDescr
    # TODO: add DcRegion enum into "preferred_dcs" and validation:
    # https://github.com/lovasoa/marshmallow_dataclass/issues/255
    preferred_dcs: list[str]
    reqs: Requirements
    user_id: int
    ws_conn: WsConnDC
    Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name


@dataclass
class NodeAttrs:
    """Node attributes (from client.info())."""

    igpu: bool  # is integrated GPU present
    dgpu: bool  # is dedicated GPU present
    cpus: int  # number of logical cores
    total_memory: int  # total memory in bytes


@dataclass
class ContainerRunSpecs:
    @dataclass
    class Attrs:
        cpuset_cpus: list[int]
        image_tag: str
        memory_limit: int  # memory required by app (in bytes, includes runners' reqs)
        memory_shared: t.Optional[int]  # shared memory required (if any)
        name: str
        nanocpus_limit: int  # nanocpus required by app (includes runners' reqs)

    @dataclass
    class EnvVars:
        # pylint: disable=invalid-name
        COLOR_BITS: int
        FPS: int
        MAX_INACTIVITY_PERIOD: int
        RUN_MIDI_SYNTH: str
        SIGNALER_AUTH_TOKEN: str
        SIGNALER_HOST: str
        SIGNALER_URI: str
        SCREEN_HEIGHT: int
        SCREEN_WIDTH: int
        STUN_URI: str
        WS_CONN_ID: str
        WS_CONSUMER_ID: str
        # optional vars
        GST_DEBUG: t.Optional[str] = None
        # x11-specific vars
        DISPLAY: t.Optional[str] = None
        SHOW_POINTER: t.Optional[bool] = None

    @dataclass
    class Labels:
        app_release_uuid: str
        app_slug: str
        user_id: str

    attrs: Attrs
    env_vars: EnvVars
    labels: Labels


@dataclass
class ContainerStats:
    cpu_throttling_data: dict[str, int]
    cpu_usage_perc: float
    memory_usage_perc: float


@dataclass
class ClusterStateResponseDTO:
    @dataclass
    class Node:
        @dataclass
        class Container:
            created: datetime.datetime
            id: str
            specs: ContainerRunSpecs
            stats: t.Optional[ContainerStats]  # e.g. not avail for a paused container
            status: str

        attrs: NodeAttrs
        api_uri: str
        containers: dict[str, Container]
        id: str
        region: str

    nodes: dict[str, Node]
    Schema: t.ClassVar[t.Type[Schema]] = Schema  # pylint: disable=invalid-name
