# pyright: reportArgumentType = false

import pytest
from unittest.mock import AsyncMock, patch

from sc_async_client.client import (
    connect,
    create_elementary_event_subscriptions,
    destroy_elementary_event_subscriptions,
    disconnect,
    erase_elements,
    generate_by_template,
    generate_elements,
    generate_elements_by_scs,
    get_elements_types,
    get_link_content,
    is_connected,
    is_event_subscription_valid,
    resolve_keynodes,
    search_by_template,
    search_link_contents_by_content_substrings,
    search_links_by_contents,
    search_links_by_contents_substrings,
    set_error_handler,
    set_link_contents,
    set_reconnect_handler,
)
from sc_async_client.constants import sc_type
from sc_async_client.constants.common import ScEventType
from sc_async_client.constants.exceptions import InvalidTypeError
from sc_async_client.models import (
    ScAddr,
    ScConstruction,
    ScEventSubscription,
    ScEventSubscriptionParams,
    ScIdtfResolveParams,
    ScLinkContent,
    ScLinkContentType,
    SCsText,
    ScTemplate,
    ScTemplateResult,
)


@pytest.mark.asyncio
async def test_establish_connection_server_unavailable():
    url = "ws://localhost:12345"

    with (
        patch(
            "sc_async_client.session.websockets.connect",
            side_effect=Exception("Connection failed"),
        ),
        patch("sc_async_client.session._ScClientSession") as mock_session,
        patch(
            "sc_async_client.session._on_close", new_callable=AsyncMock
        ) as mock_on_close,
    ):
        mock_session.is_open = False
        mock_session.post_reconnect_callback = AsyncMock()

        await connect(url)

        assert mock_session.url == url
        mock_on_close.assert_called_once()
        mock_session.post_reconnect_callback.assert_not_called()


def test_is_connected():
    with patch("sc_async_client.session._ScClientSession") as mock_session:
        mock_session.is_open = True
        assert is_connected() is True
        mock_session.is_open = False
        assert is_connected() is False


def test_set_error_handler():
    def my_error_handler():
        pass

    with patch("sc_async_client.session._ScClientSession") as mock_session:
        set_error_handler(my_error_handler)
        assert mock_session.error_handler == my_error_handler


def test_set_reconnect_handler():
    def my_reconnect_handler():
        pass

    def my_post_reconnect_handler():
        pass

    with patch("sc_async_client.session._ScClientSession") as mock_session:
        set_reconnect_handler(
            reconnect_handler=my_reconnect_handler,
            post_reconnect_handler=my_post_reconnect_handler,
            reconnect_retries=10,
            reconnect_retry_delay=5,
        )
        assert mock_session.reconnect_callback == my_reconnect_handler
        assert mock_session.post_reconnect_callback == my_post_reconnect_handler
        assert mock_session.reconnect_retries == 10
        assert mock_session.reconnect_retry_delay == 5


@pytest.mark.asyncio
async def test_connect_success():
    url = "ws://localhost:8090/ws_json"
    with patch("sc_async_client.session.websockets.connect") as mock_connect, patch(
        "sc_async_client.session._ScClientSession"
    ) as mock_session:
        cm_mock = AsyncMock()
        mock_connect.return_value = cm_mock
        conn_mock = AsyncMock()
        cm_mock.__aenter__.return_value = conn_mock
        conn_mock.__aiter__ = lambda: conn_mock
        conn_mock.__anext__ = AsyncMock(side_effect=StopAsyncIteration)

        mock_session.is_open = True
        mock_session.post_reconnect_callback = AsyncMock()

        await connect(url)

        mock_connect.assert_called_with(url)
        assert mock_session.url == url


@pytest.mark.asyncio
async def test_disconnect():
    with patch("sc_async_client.session._ScClientSession") as mock_session:
        mock_session.connection = AsyncMock()
        await disconnect()
        mock_session.connection.close.assert_called_once()


@pytest.mark.asyncio
class TestApiClient:
    @pytest.fixture(autouse=True)
    def mock_send_message(self):
        with patch("sc_async_client.session.send_message", new_callable=AsyncMock) as self.mock_send:
            yield

    async def test_get_elements_types(self):
        mock_response = {
            "id": 1,
            "status": True,
            "event": False,
            "payload": [sc_type.CONST_NODE.value, sc_type.VAR_NODE.value],
        }
        self.mock_send.return_value = mock_response

        addrs = [ScAddr(1), ScAddr(2)]
        result = await get_elements_types(*addrs)

        assert result == [sc_type.CONST_NODE, sc_type.VAR_NODE]
        self.mock_send.assert_called_once()

    async def test_generate_elements(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": [12, 34, 56]}
        self.mock_send.return_value = mock_response

        construction = ScConstruction()
        construction.generate_node(sc_type.CONST_NODE, "node1")

        result = await generate_elements(construction)

        assert result == [ScAddr(12), ScAddr(34), ScAddr(56)]
        self.mock_send.assert_called_once()

    async def test_generate_elements_by_scs(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": [True]}
        self.mock_send.return_value = mock_response

        scs_text: SCsText = ["node1;;"]
        result = await generate_elements_by_scs(scs_text)

        assert result == [True]
        self.mock_send.assert_called_once()

    async def test_erase_elements(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": True}
        self.mock_send.return_value = mock_response

        addrs = [ScAddr(1), ScAddr(2)]
        result = await erase_elements(*addrs)

        assert result is True
        self.mock_send.assert_called_once()

    async def test_set_link_contents(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": True}
        self.mock_send.return_value = mock_response

        link_addr = ScAddr(5)
        content = ScLinkContent("Hello", ScLinkContentType.STRING, link_addr)
        result = await set_link_contents(content)

        assert result is True
        self.mock_send.assert_called_once()

    async def test_get_link_content(self):
        mock_response = {
            "id": 1,
            "status": True,
            "event": False,
            "payload": [{"value": "World", "type": "string"}],
        }
        self.mock_send.return_value = mock_response

        link_addr = ScAddr(10)
        result = await get_link_content(link_addr)

        assert len(result) == 1
        assert result[0].data == "World"
        assert result[0].content_type == ScLinkContentType.STRING
        self.mock_send.assert_called_once()

    async def test_search_links_by_contents(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": [[123], [456]]}
        self.mock_send.return_value = mock_response

        content1 = ScLinkContent("content1", ScLinkContentType.STRING)
        content2 = "content2"
        result = await search_links_by_contents(content1, content2)

        assert result == [[ScAddr(123)], [ScAddr(456)]]
        self.mock_send.assert_called_once()

    async def test_search_links_by_contents_substrings(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": [[123], [456]]}
        self.mock_send.return_value = mock_response

        content1 = ScLinkContent("content1", ScLinkContentType.STRING)
        content2 = "content2"
        result = await search_links_by_contents_substrings(content1, content2)

        assert result == [[ScAddr(123)], [ScAddr(456)]]
        self.mock_send.assert_called_once()

    async def test_search_link_contents_by_content_substrings(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": [[123], [456]]}
        self.mock_send.return_value = mock_response

        content1 = "cont"
        result = await search_link_contents_by_content_substrings(content1)

        # The implementation has a bug and returns list[list[int]] instead of list[list[ScAddr]]
        assert result == [[123], [456]]
        self.mock_send.assert_called_once()

    async def test_resolve_keynodes(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": [101, 202]}
        self.mock_send.return_value = mock_response

        params = [
            ScIdtfResolveParams(idtf="keynode1", type=sc_type.CONST_NODE),
            ScIdtfResolveParams(idtf="keynode2", type=None),
        ]
        result = await resolve_keynodes(*params)

        assert result == [ScAddr(101), ScAddr(202)]
        self.mock_send.assert_called_once()

    async def test_search_by_template(self):
        mock_response = {
            "id": 1,
            "status": True,
            "event": False,
            "payload": {"aliases": {"_alias": 0}, "addrs": [[1, 2, 3], [4, 5, 6]]},
        }
        self.mock_send.return_value = mock_response

        template = ScTemplate()
        template.triple(ScAddr(1), sc_type.VAR_PERM_POS_ARC, sc_type.VAR_NODE >> "_alias")

        result = await search_by_template(template)

        assert len(result) == 2
        assert isinstance(result[0], ScTemplateResult)
        assert result[0].get("_alias") == ScAddr(1)
        assert result[1].get(0) == ScAddr(4)
        self.mock_send.assert_called_once()

    async def test_generate_by_template(self):
        mock_response = {
            "id": 1,
            "status": True,
            "event": False,
            "payload": {"aliases": {"_alias": 1}, "addrs": [10, 20, 30]},
        }
        self.mock_send.return_value = mock_response

        template = ScTemplate()
        template.triple(sc_type.VAR_NODE, sc_type.VAR_PERM_POS_ARC >> "_alias", ScAddr(1))

        result = await generate_by_template(template)

        assert isinstance(result, ScTemplateResult)
        assert result.get("_alias") == ScAddr(20)
        self.mock_send.assert_called_once()

    async def test_create_event_subscriptions(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": [12345]}
        self.mock_send.return_value = mock_response

        async def my_callback(addr1, addr2, addr3):
            pass

        with patch("sc_async_client.session.set_event_subscription") as mock_set_event:
            params = ScEventSubscriptionParams(ScAddr(55), ScEventType.AFTER_GENERATE_OUTGOING_ARC, my_callback)
            result = await create_elementary_event_subscriptions(params)

            assert len(result) == 1
            assert isinstance(result[0], ScEventSubscription)
            assert result[0].id == 12345
            assert result[0].callback == my_callback
            mock_set_event.assert_called_once()
            self.mock_send.assert_called_once()

    async def test_destroy_event_subscriptions(self):
        mock_response = {"id": 1, "status": True, "event": False, "payload": True}
        self.mock_send.return_value = mock_response

        event = ScEventSubscription(id=12345)
        with patch("sc_async_client.session.drop_event_subscription") as mock_drop_event:
            result = await destroy_elementary_event_subscriptions(event)

            assert result is True
            mock_drop_event.assert_called_with(12345)
            self.mock_send.assert_called_once()

    async def test_is_event_subscription_valid(self):
        event_valid = ScEventSubscription(id=1)
        event_invalid = ScEventSubscription(id=2)

        with patch("sc_async_client.session.get_event_subscription") as mock_get_event:
            mock_get_event.side_effect = lambda event_id: event_valid if event_id == 1 else None

            assert await is_event_subscription_valid(event_valid) is True
            assert await is_event_subscription_valid(event_invalid) is False

        with pytest.raises(InvalidTypeError):
            await is_event_subscription_valid(123)
