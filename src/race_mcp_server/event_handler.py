"""Event handling for telemetry and driver interactions."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Dict, Optional, Protocol

from .openai_client import OpenAIClient


class CallbackPublisher(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None: ...


class MCPEventHandler:
    """Process telemetry events and driver messages, calling OpenAI when needed."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        callback_dispatcher: Optional[CallbackPublisher] = None,
    ):
        self.openai_client = openai_client
        self.telemetry_queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        self.voice_queue: "asyncio.Queue[bytes]" = asyncio.Queue()
        self.last_flag_state = "Green"
        self._telemetry_task: Optional[asyncio.Task[None]] = None
        self._voice_task: Optional[asyncio.Task[None]] = None
        self._running = False
        self.callback_dispatcher = callback_dispatcher
        self.last_position: Optional[int] = None
        self.last_lap: Optional[int] = None

    async def start(self) -> None:
        if not self._telemetry_task:
            self._running = True
            self._telemetry_task = asyncio.create_task(self._process_telemetry())
        if not self._voice_task:
            self._voice_task = asyncio.create_task(self._process_voice())
        if self.callback_dispatcher:
            await self.callback_dispatcher.start()

    async def stop(self) -> None:
        self._running = False
        for task_name in ("_telemetry_task", "_voice_task"):
            task = getattr(self, task_name)
            if task:
                task.cancel()
                with contextlib.suppress(BaseException):
                    await task
                setattr(self, task_name, None)
        if self.callback_dispatcher:
            await self.callback_dispatcher.stop()

    async def on_telemetry(self, telemetry: Dict[str, Any]) -> None:
        await self.telemetry_queue.put(telemetry)

    async def on_voice_input(self, audio: bytes) -> None:
        """Queue raw audio bytes for processing."""
        await self.voice_queue.put(audio)

    async def handle_user_message(self, message: str) -> str:
        messages = [
            {"role": "system", "content": "You are a helpful racing coach."},
            {"role": "user", "content": message},
        ]
        response = await self.openai_client.chat(messages)
        return response.get("content", "")

    async def handle_voice_input(self, audio: bytes) -> str:
        """Transcribe audio and handle it as a user message."""
        transcript = await self.openai_client.transcribe_audio(audio)
        if not transcript:
            return ""
        return await self.handle_user_message(transcript)

    async def _process_telemetry(self) -> None:
        while self._running:
            telemetry = await self.telemetry_queue.get()
            try:
                await self._evaluate_telemetry(telemetry)
            except Exception as exc:  # noqa: BLE001
                logging.error("Telemetry processing error: %s", exc)

    async def _process_voice(self) -> None:
        while self._running:
            audio = await self.voice_queue.get()
            try:
                response = await self.handle_voice_input(audio)
                if response:
                    logging.info("Voice response: %s", response)
            except Exception as exc:  # noqa: BLE001
                logging.error("Voice processing error: %s", exc)

    async def _evaluate_telemetry(self, telemetry: Dict[str, Any]) -> None:
        flag_state = telemetry.get("flag_state", "Green")
        if flag_state != self.last_flag_state:
            self.last_flag_state = flag_state
            messages = [
                {"role": "system", "content": "You are a professional racing spotter."},
                {
                    "role": "user",
                    "content": f"Flag changed to {flag_state}. Offer concise advice.",
                },
            ]
            response = await self.openai_client.chat(messages)
            logging.info("Flag change advice: %s", response.get("content", ""))

        if not telemetry.get("is_on_track", True):
            messages = [
                {"role": "system", "content": "You are a racing coach."},
                {
                    "role": "user",
                    "content": "Driver off track, give recovery tips.",
                },
            ]
            response = await self.openai_client.chat(messages)
            logging.info("Off-track advice: %s", response.get("content", ""))

        await self._dispatch_callback("telemetry_snapshot", {"telemetry": telemetry})
        await self._detect_position_change(telemetry)
        await self._detect_lap_change(telemetry)

    async def _dispatch_callback(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self.callback_dispatcher:
            await self.callback_dispatcher.publish(event_type, payload)

    async def _detect_position_change(self, telemetry: Dict[str, Any]) -> None:
        position = telemetry.get("position")
        if position is None:
            return
        if self.last_position is not None:
            if position < self.last_position:
                await self._dispatch_callback(
                    "position_gain",
                    {
                        "message": f"Driver gained a spot: P{self.last_position} -> P{position}",
                        "position": position,
                        "previous_position": self.last_position,
                        "lap": telemetry.get("lap"),
                    },
                )
            elif position > self.last_position:
                await self._dispatch_callback(
                    "position_loss",
                    {
                        "message": f"Driver lost a spot: P{self.last_position} -> P{position}",
                        "position": position,
                        "previous_position": self.last_position,
                        "lap": telemetry.get("lap"),
                    },
                )
        self.last_position = position

    async def _detect_lap_change(self, telemetry: Dict[str, Any]) -> None:
        lap = telemetry.get("lap")
        if lap is None:
            return
        if self.last_lap is not None and lap > self.last_lap:
            await self._dispatch_callback(
                "lap_complete",
                {
                    "message": f"Completed lap {self.last_lap}",
                    "lap": self.last_lap,
                    "next_lap": lap,
                    "lap_time": telemetry.get("lap_time"),
                },
            )
        self.last_lap = lap
