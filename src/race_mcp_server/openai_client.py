"""OpenAI API wrapper with graceful fallback."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from io import BytesIO

try:  # pragma: no cover - import error handling
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except Exception:  # noqa: BLE001
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None  # type: ignore[assignment]
    logging.warning("OpenAI package not available; using stub responses")


class OpenAIClient:
    """Simple async wrapper around the OpenAI chat API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client: Optional[AsyncOpenAI] = None
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = AsyncOpenAI(api_key=self.api_key)
            except Exception as exc:  # noqa: BLE001
                logging.error("Failed to init OpenAI client: %s", exc)
                self.client = None

    async def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send chat messages to the OpenAI API.

        Returns a dictionary with ``role`` and ``content`` keys. If the OpenAI
        client is unavailable, a stub response is returned.
        """

        if not self.client:
            return {"role": "assistant", "content": "OpenAI not configured."}
        try:
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages
            )
            message = response.choices[0].message
            return {"role": message.role, "content": message.content or ""}
        except Exception as exc:  # noqa: BLE001
            logging.error("OpenAI request failed: %s", exc)
            return {"role": "assistant", "content": "Error contacting OpenAI."}

    async def transcribe_audio(
        self, audio: bytes, model: str = "gpt-4o-mini-transcribe"
    ) -> str:
        """Transcribe audio bytes to text using OpenAI's transcription API.

        Returns the transcribed text. If the OpenAI client is unavailable or the
        request fails, an empty string is returned instead.
        """

        if not self.client:
            return ""
        try:
            audio_file = BytesIO(audio)
            response = await self.client.audio.transcriptions.create(
                model=model, file=audio_file
            )
            return getattr(response, "text", "")
        except Exception as exc:  # noqa: BLE001
            logging.error("OpenAI transcription failed: %s", exc)
            return ""

    async def text_to_speech(
        self,
        text: str,
        voice: str = "alloy",
        model: str = "gpt-4o-mini-tts",
        format: str = "mp3",
    ) -> bytes:
        """Convert text to speech and return audio bytes.

        If the OpenAI client is unavailable or the request fails, an empty byte
        string is returned.
        """

        if not self.client:
            return b""
        try:
            response = await self.client.audio.speech.create(
                model=model, voice=voice, input=text, format=format
            )
            # HttpxBinaryResponseContent provides an async read method
            if hasattr(response, "aread"):
                return await response.aread()
            if hasattr(response, "read"):
                return response.read()
            return b""
        except Exception as exc:  # noqa: BLE001
            logging.error("OpenAI text-to-speech failed: %s", exc)
            return b""
