"""
This source file is part of an OSTIS project. For the latest info, see https://github.com/ostis-ai
Distributed under the MIT License
(See an accompanying file LICENSE or a copy at http://opensource.org/licenses/MIT)
"""

import logging
import asyncio
import websockets
from typing import Callable, Awaitable, Dict, Any, cast, Optional, Union
import json

from sc_async_client.constants.numeric import (
    SERVER_ESTABLISH_CONNECTION_TIME,
    SERVER_RECONNECT_RETRIES,
    SERVER_RECONNECT_RETRY_DELAY,
    LOGGING_MAX_SIZE,
    MAX_PAYLOAD_SIZE,
    SERVER_RESPONSE_TIMEOUT,
)
from sc_async_client.models import ScEventSubscription, Response, ScAddr
from sc_async_client.constants.common import ClientCommand
from sc_async_client.constants import common
from sc_async_client.constants.exceptions import PayloadMaxSizeError
from sc_async_client.client._executor import Executor


logger = logging.getLogger(__name__)


async def default_reconnect_handler(retry: int = 0) -> None:
    if _ScClientSession.url is not None:
        await establish_connection(_ScClientSession.url)


async def default_error_handler(error: Exception) -> None:
    raise error


async def noop_async(*args) -> None:
    pass


class _ScClientSession:
    url = None
    lock_instance = asyncio.Lock()
    is_open: bool = False
    command_id: int = 0
    executor: Executor = Executor()
    connection: Optional[websockets.ClientConnection] = None
    post_reconnect_callback: Callable[..., Awaitable[None]] = noop_async
    error_handler: Callable[[Exception], Awaitable[None]] = default_error_handler
    reconnect_callback: Callable[[int], Awaitable[None]] = default_reconnect_handler
    reconnect_retries: int = SERVER_RECONNECT_RETRIES
    reconnect_retry_delay: float = SERVER_RECONNECT_RETRY_DELAY
    responses_dict: Dict[int, dict] = {}
    event_subscriptions_dict: Dict[int, ScEventSubscription] = {}
    pending_futures: Dict[int, asyncio.Future] = {}

    @classmethod
    def clear(cls):
        cls.is_open = False
        cls.responses_dict = {}
        cls.event_subscriptions_dict = {}
        cls.command_id = 0
        cls.connection = None
        cls.error_handler = default_error_handler
        cls.reconnect_callback = default_reconnect_handler
        cls.post_reconnect_callback = noop_async
        cls.reconnect_retries = SERVER_RECONNECT_RETRIES
        cls.reconnect_retry_delay = SERVER_RECONNECT_RETRY_DELAY


async def _on_message(response_input: Union[str, bytes]) -> None:
    logger.debug(f"Receive: {str(response_input)[:LOGGING_MAX_SIZE]}")
    response = cast(Response, json.loads(response_input))
    command_id = response.get(common.ID)

    if response.get(common.EVENT):
        asyncio.create_task(_emit_callback(command_id, response.get(common.PAYLOAD)))
    else:
        future: Optional[asyncio.Future] = _ScClientSession.pending_futures.pop(
            command_id, None
        )
        if future and not future.done():
            future.set_result(response)


async def _emit_callback(event_id: int, elems: list[int]) -> None:
    event = _ScClientSession.event_subscriptions_dict.get(event_id)
    if event and event.callback:
        await event.callback(*[ScAddr(addr) for addr in elems])


async def set_connection(url: str) -> None:
    await establish_connection(url)


def is_connected() -> bool:
    return _ScClientSession.is_open


async def _on_open() -> None:
    logger.info("Connection opened")
    _ScClientSession.is_open = True


async def _on_error(error: Exception) -> None:
    await _ScClientSession.error_handler(error)


async def _on_close() -> None:
    logger.info("Connection closed")
    _ScClientSession.is_open = False


def set_error_handler(callback) -> None:
    _ScClientSession.error_handler = callback


def set_reconnect_handler(
    reconnect_callback,
    post_reconnect_callback,
    reconnect_retries: int,
    reconnect_retry_delay: float,
) -> None:
    _ScClientSession.reconnect_callback = reconnect_callback
    _ScClientSession.post_reconnect_callback = post_reconnect_callback
    _ScClientSession.reconnect_retries = reconnect_retries
    _ScClientSession.reconnect_retry_delay = reconnect_retry_delay


async def establish_connection(url) -> None:
    _ScClientSession.url = url

    async def connect():
        try:
            async with websockets.connect(url) as conn:
                _ScClientSession.connection = conn
                logger.info(f"Sc-server socket: {url}")

                await _on_open()

                async for message in conn:
                    await _on_message(message)

        except websockets.WebSocketException as e:
            await _on_error(e)
        finally:
            await _on_close()

    asyncio.create_task(connect())
    await asyncio.sleep(SERVER_ESTABLISH_CONNECTION_TIME)
    if _ScClientSession.is_open:
        await _ScClientSession.post_reconnect_callback()


async def close_connection() -> None:
    try:
        if _ScClientSession.connection:
            await _ScClientSession.connection.close()
            _ScClientSession.is_open = False
    except AttributeError as e:
        await _on_error(e)


async def _send_message(data: str, retries: int, retry: int = 0) -> None:
    try:
        logger.debug(f"Send: {data[:LOGGING_MAX_SIZE]}")
        if not _ScClientSession.connection:
            raise Exception("ScServer connection wasn't open")
        await _ScClientSession.connection.send(data)
    except websockets.ConnectionClosed:
        if _ScClientSession.reconnect_callback and retry < retries:
            logger.warning(
                f"Connection to sc-server has failed. "
                f"Trying to reconnect to sc-server socket in {_ScClientSession.reconnect_retry_delay} seconds"
            )
            if retry > 0:
                await asyncio.sleep(_ScClientSession.reconnect_retry_delay)
            await _ScClientSession.reconnect_callback(retry)
            await _send_message(data, retries, retry + 1)
        else:
            await _on_error(
                ConnectionAbortedError("Sc-server takes a long time to respond")
            )


async def send_message(
    request_type: common.RequestType, payload: Any
) -> Optional[Response]:
    async with _ScClientSession.lock_instance:
        _ScClientSession.command_id += 1
        command_id = _ScClientSession.command_id

    data = json.dumps(
        {
            common.ID: command_id,
            common.TYPE: request_type.value,
            common.PAYLOAD: payload,
        }
    )

    len_data = len(data.encode("utf-8"))
    if len_data > MAX_PAYLOAD_SIZE:
        await _on_error(
            PayloadMaxSizeError(
                f"Data is too large: {len_data} > {MAX_PAYLOAD_SIZE} bytes"
            )
        )
        return None

    loop = asyncio.get_running_loop()
    future = loop.create_future()
    _ScClientSession.pending_futures[command_id] = future

    await _send_message(data, _ScClientSession.reconnect_retries)

    try:
        response: Optional[Response] = await asyncio.wait_for(
            future, timeout=SERVER_RESPONSE_TIMEOUT
        )
    except asyncio.TimeoutError:
        await _on_error(
            ConnectionAbortedError("Sc-server takes a long time to respond")
        )
        response = None

    return response


def get_event_subscription(event_subscription_id: int) -> Optional[ScEventSubscription]:
    return _ScClientSession.event_subscriptions_dict.get(event_subscription_id)


def drop_event_subscription(event_subscription_id: int):
    del _ScClientSession.event_subscriptions_dict[event_subscription_id]


def set_event_subscription(event_subscription: ScEventSubscription) -> None:
    _ScClientSession.event_subscriptions_dict[event_subscription.id] = (
        event_subscription
    )


async def execute(request_type: ClientCommand, *args):
    return await _ScClientSession.executor.run(request_type, *args)
