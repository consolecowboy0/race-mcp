import pytest

from race_mcp_server.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_transcribe_audio_returns_string_without_openai():
    client = OpenAIClient(api_key=None)
    result = await client.transcribe_audio(b"fake")
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_text_to_speech_returns_bytes_without_openai():
    client = OpenAIClient(api_key=None)
    audio = await client.text_to_speech("hello")
    assert isinstance(audio, bytes)
