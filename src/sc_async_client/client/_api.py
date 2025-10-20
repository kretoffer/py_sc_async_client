"""
This source file is part of an OSTIS project. For the latest info, see https://github.com/ostis-ai
Distributed under the MIT License
(See an accompanying file LICENSE or a copy at http://opensource.org/licenses/MIT)
"""
# pyright: reportReturnType=false

from __future__ import annotations

from sc_async_client import session
from sc_async_client.constants import common, exceptions
from sc_async_client.constants.numeric import SERVER_RECONNECT_RETRIES, SERVER_RECONNECT_RETRY_DELAY
from sc_async_client.constants.sc_types import ScType
from sc_async_client.models import (
    ScAddr,
    ScConstruction,
    ScEventSubscription,
    ScEventSubscriptionParams,
    ScIdtfResolveParams,
    ScLinkContent,
    SCsText,
    ScTemplate,
    ScTemplateIdtf,
    ScTemplateParams,
    ScTemplateResult,
)
from sc_async_client.models.sc_construction import ScLinkContentData


async def connect(url: str) -> None:
    await session.set_connection(url)


def is_connected() -> bool:
    return session.is_connected()


async def disconnect() -> None:
    await session.close_connection()


def set_error_handler(callback) -> None:
    session.set_error_handler(callback)


def set_reconnect_handler(**reconnect_kwargs) -> None:
    session.set_reconnect_handler(
        reconnect_kwargs.get("reconnect_handler", session.default_reconnect_handler),
        reconnect_kwargs.get("post_reconnect_handler"),
        reconnect_kwargs.get("reconnect_retries", SERVER_RECONNECT_RETRIES),
        reconnect_kwargs.get("reconnect_retry_delay", SERVER_RECONNECT_RETRY_DELAY),
    )


async def get_elements_types(*addrs: ScAddr) -> list[ScType]:
    return await session.execute(common.ClientCommand.GET_ELEMENTS_TYPES, *addrs)


async def generate_elements(constr: ScConstruction) -> list[ScAddr]:
    return await session.execute(common.ClientCommand.GENERATE_ELEMENTS, constr)


async def generate_elements_by_scs(text: SCsText) -> list[bool]:
    return await session.execute(common.ClientCommand.GENERATE_ELEMENTS_BY_SCS, text)


async def erase_elements(*addrs: ScAddr) -> bool:
    return await session.execute(common.ClientCommand.ERASE_ELEMENTS, *addrs)


async def set_link_contents(*contents: ScLinkContent) -> bool:
    return await session.execute(common.ClientCommand.SET_LINK_CONTENTS, *contents)


async def get_link_content(*addr: ScAddr) -> list[ScLinkContent]:
    return await session.execute(common.ClientCommand.GET_LINK_CONTENT, *addr)


async def search_links_by_contents(*contents: ScLinkContent | ScLinkContentData) -> list[list[ScAddr]]:
    return await session.execute(common.ClientCommand.SEARCH_LINKS_BY_CONTENT, *contents)


async def search_links_by_contents_substrings(*contents: ScLinkContent | ScLinkContentData) -> list[list[ScAddr]]:
    return await session.execute(common.ClientCommand.SEARCH_LINKS_BY_CONTENT_SUBSTRING, *contents)


async def search_link_contents_by_content_substrings(*contents: ScLinkContent | ScLinkContentData) -> list[list[ScAddr]]:
    return await session.execute(common.ClientCommand.SEARCH_LINKS_CONTENTS_BY_CONTENT_SUBSTRING, *contents)


async def resolve_keynodes(*params: ScIdtfResolveParams) -> list[ScAddr]:
    return await session.execute(common.ClientCommand.SEARCH_KEYNODES, *params)


async def search_by_template(
    template: ScTemplate | str | ScTemplateIdtf | ScAddr, params: ScTemplateParams | None = None
) -> list[ScTemplateResult]:
    return await session.execute(common.ClientCommand.SEARCH_BY_TEMPLATE, template, params)


async def generate_by_template(
    template: ScTemplate | str | ScTemplateIdtf | ScAddr, params: ScTemplateParams | None = None
) -> ScTemplateResult:
    return await session.execute(common.ClientCommand.GENERATE_BY_TEMPLATE, template, params)


async def create_elementary_event_subscriptions(*params: ScEventSubscriptionParams) -> list[ScEventSubscription]:
    return await session.execute(common.ClientCommand.CREATE_EVENT_SUBSCRIPTIONS, *params)


async def destroy_elementary_event_subscriptions(*event_subscriptions: ScEventSubscription) -> bool:
    return await session.execute(common.ClientCommand.DESTROY_EVENT_SUBSCRIPTIONS, *event_subscriptions)


async def is_event_subscription_valid(event_subscription: ScEventSubscription) -> bool:
    if not isinstance(event_subscription, ScEventSubscription):
        raise exceptions.InvalidTypeError("expected object types: ScEventSubscription")
    return bool(session.get_event_subscription(event_subscription.id))
