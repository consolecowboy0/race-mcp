import pytest

from race_mcp_server.event_handler import MCPEventHandler
from race_mcp_server.openai_client import OpenAIClient


class DummyDispatcher:
    def __init__(self):
        self.started = 0
        self.stopped = 0
        self.events = []

    async def start(self) -> None:  # pragma: no cover - trivial
        self.started += 1

    async def stop(self) -> None:  # pragma: no cover - trivial
        self.stopped += 1

    async def publish(self, event_type, payload) -> None:
        self.events.append((event_type, payload))


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


@pytest.mark.asyncio
async def test_event_handler_reports_position_gain():
    dispatcher = DummyDispatcher()
    handler = MCPEventHandler(OpenAIClient(api_key=None), dispatcher)
    await handler._evaluate_telemetry(  # type: ignore[attr-defined]
        {
            "flag_state": "Green",
            "is_on_track": True,
            "lap": 5,
            "position": 8,
        }
    )
    await handler._evaluate_telemetry(  # type: ignore[attr-defined]
        {
            "flag_state": "Green",
            "is_on_track": True,
            "lap": 5,
            "position": 7,
        }
    )

    event_types = [event[0] for event in dispatcher.events]
    assert "position_gain" in event_types


@pytest.mark.asyncio
async def test_event_handler_starts_and_stops_dispatcher():
    dispatcher = DummyDispatcher()
    handler = MCPEventHandler(OpenAIClient(api_key=None), dispatcher)
    await handler.start()
    await handler.stop()

    assert dispatcher.started == 1
    assert dispatcher.stopped == 1
