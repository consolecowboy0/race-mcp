import pytest

from race_mcp_server.event_handler import MCPEventHandler
from race_mcp_server.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_handle_user_message_returns_string():
    client = OpenAIClient(api_key=None)
    handler = MCPEventHandler(client)
    response = await handler.handle_user_message("Hello coach")
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_handle_voice_input_uses_transcription(monkeypatch):
    client = OpenAIClient(api_key=None)
    handler = MCPEventHandler(client)

    async def fake_transcribe(audio: bytes, model: str = "gpt-4o-mini-transcribe") -> str:
        return "Voice message"

    async def fake_chat(messages):
        return {"role": "assistant", "content": "ack"}

    monkeypatch.setattr(client, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(client, "chat", fake_chat)

    result = await handler.handle_voice_input(b"audio")
    assert result == "ack"
