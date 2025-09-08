"""Utilities for real-time voice input and output."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .openai_client import OpenAIClient

try:  # pragma: no cover - optional dependency
    import sounddevice as sd
    import numpy as np

    SOUNDDEVICE_AVAILABLE = True
except Exception:  # noqa: BLE001
    sd = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    SOUNDDEVICE_AVAILABLE = False
    logging.warning("sounddevice not available; voice features disabled")


class VoiceInterface:
    """Interface for capturing microphone input and playing voice responses."""

    def __init__(self, client: OpenAIClient, sample_rate: int = 16000):
        self.client = client
        self.sample_rate = sample_rate

    async def record(self, duration: float = 3.0) -> Optional[bytes]:
        """Record audio from the default microphone.

        Returns raw PCM bytes or ``None`` if recording is unavailable.
        """

        if not SOUNDDEVICE_AVAILABLE:
            logging.error("sounddevice is required for recording audio")
            return None
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            lambda: sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
            ),
        )
        await loop.run_in_executor(None, sd.wait)
        return audio.tobytes()

    async def play(self, audio: bytes) -> None:
        """Play raw PCM audio bytes through the default output device."""

        if not SOUNDDEVICE_AVAILABLE:
            logging.error("sounddevice is required for audio playback")
            return
        if not audio:
            return
        loop = asyncio.get_event_loop()
        samples = np.frombuffer(audio, dtype="int16")
        await loop.run_in_executor(None, lambda: sd.play(samples, self.sample_rate))
        await loop.run_in_executor(None, sd.wait)

    async def chat_once(self, duration: float = 3.0) -> str:
        """Capture voice input, send to OpenAI, speak the response, and return it."""

        audio = await self.record(duration)
        if not audio:
            return ""
        transcript = await self.client.transcribe_audio(audio)
        if not transcript:
            return ""
        response = await self.client.chat([{"role": "user", "content": transcript}])
        await self.play(await self.client.text_to_speech(response.get("content", "")))
        return response.get("content", "")
