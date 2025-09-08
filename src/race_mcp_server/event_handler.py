"""Event handling for telemetry and driver interactions."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Dict, Optional

from .openai_client import OpenAIClient


class MCPEventHandler:
    """Process telemetry events and driver messages, calling OpenAI when needed."""

    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
        self.telemetry_queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        self.last_flag_state = "Green"
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False

    async def start(self) -> None:
        if not self._task:
            self._running = True
            self._task = asyncio.create_task(self._process_telemetry())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
            self._task = None

    async def on_telemetry(self, telemetry: Dict[str, Any]) -> None:
        await self.telemetry_queue.put(telemetry)

    async def handle_user_message(self, message: str) -> str:
        messages = [
            {"role": "system", "content": "You are a helpful racing coach."},
            {"role": "user", "content": message},
        ]
        response = await self.openai_client.chat(messages)
        return response.get("content", "")

    async def _process_telemetry(self) -> None:
        while self._running:
            telemetry = await self.telemetry_queue.get()
            try:
                await self._evaluate_telemetry(telemetry)
            except Exception as exc:  # noqa: BLE001
                logging.error("Telemetry processing error: %s", exc)

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
