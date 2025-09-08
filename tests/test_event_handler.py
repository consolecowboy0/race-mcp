import pytest

from race_mcp_server.event_handler import MCPEventHandler
from race_mcp_server.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_handle_user_message_returns_string():
    client = OpenAIClient(api_key=None)
    handler = MCPEventHandler(client)
    response = await handler.handle_user_message("Hello coach")
    assert isinstance(response, str)
