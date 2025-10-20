from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypedDict, Union, Optional, List, Dict

from sc_async_client.constants import ScType, common
from sc_async_client.constants.exceptions import InvalidTypeError, LinkContentOversizeError
from sc_async_client.constants.numeric import LINK_CONTENT_MAX_SIZE
from sc_async_client.models.sc_addr import ScAddr


class ScConstruction:
    def __init__(self) -> None:
        self.aliases: Dict[str, int] = {}
        self.commands: List[ScConstructionCommand] = []

    def generate_node(self, sc_type: ScType, alias: Optional[str] = None) -> None:
        if not sc_type.is_node():
            raise InvalidTypeError("You should pass the node type here")
        cmd = ScConstructionCommand(sc_type, None)
        if alias:
            self.aliases[alias] = len(self.commands)
        self.commands.append(cmd)

    def generate_connector(
        self,
        sc_type: ScType,
        source: str | ScAddr,
        target: str | ScAddr,
        alias: Optional[str] = None,
    ) -> None:
        if not sc_type.is_connector():
            raise InvalidTypeError("You should pass the connector type here")
        cmd = ScConstructionCommand(sc_type, {common.SOURCE: source, common.TARGET: target})
        if alias:
            self.aliases[alias] = len(self.commands)
        self.commands.append(cmd)

    def generate_link(self, sc_type: ScType, content: ScLinkContent, alias: Optional[str] = None) -> None:
        if not sc_type.is_link():
            raise InvalidTypeError("You should pass the link type here")
        cmd = ScConstructionCommand(sc_type, {common.CONTENT: content.data, common.TYPE: content.content_type.value})
        if alias:
            self.aliases[alias] = len(self.commands)
        self.commands.append(cmd)

    def get_index(self, alias: str) -> int:
        return self.aliases[alias]


@dataclass
class ScConstructionCommand:
    el_type: ScType
    data: Any


class ScIdtfResolveParams(TypedDict):
    idtf: str
    type: ScType | None


class ScLinkContentType(Enum):
    INT = 0
    FLOAT = 1
    STRING = 2


ScLinkContentData = Union[str, int, float]


@dataclass
class ScLinkContent:
    data: ScLinkContentData
    content_type: ScLinkContentType
    addr: Optional[ScAddr] = None

    def __post_init__(self):
        if len(str(self.data)) > LINK_CONTENT_MAX_SIZE:
            raise LinkContentOversizeError
        self.content_type = ScLinkContentType(self.content_type)

    def type_to_str(self) -> str:
        return self.content_type.name.lower()


class Response(TypedDict):
    id: int
    status: bool
    event: bool
    payload: Any
