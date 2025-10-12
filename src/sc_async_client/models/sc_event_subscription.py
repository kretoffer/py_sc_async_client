from dataclasses import dataclass
from enum import Enum
from typing import Callable, Awaitable, Optional

from sc_async_client.constants.common import ScEventType
from sc_async_client.models.sc_addr import ScAddr

ScEventCallbackFunc = Callable[[ScAddr, ScAddr, ScAddr], Awaitable[Enum]]


@dataclass
class ScEventSubscriptionParams:
    addr: ScAddr
    event_type: ScEventType
    callback: ScEventCallbackFunc


@dataclass
class ScEventSubscription:
    id: int = 0
    event_type: Optional[ScEventType] = None
    callback: Optional[ScEventCallbackFunc] = None
