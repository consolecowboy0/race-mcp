"""Asynchronous HTTP callback dispatcher for ElevenLabs agent integrations."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx


LOGGER = logging.getLogger(__name__)


class CallbackDispatcher:
    """Background worker that ships telemetry events to an HTTP endpoint."""

    def __init__(
        self,
        callback_url: Optional[str] = None,
        *,
        agent_id: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.elevenlabs.io/v1",
        timeout: float = 10.0,
        max_queue_size: int = 256,
    ) -> None:
        self.callback_url = callback_url
        self.agent_id = agent_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue(max_queue_size)
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def enabled(self) -> bool:
        return bool(self.callback_url or (self.agent_id and self.api_key))

    async def start(self) -> None:
        """Start the background worker if callbacks are enabled."""

        if not self.enabled or self._task:
            return

        self._running = True
        self._task = asyncio.create_task(self._worker(), name="callback-dispatcher")

    async def stop(self) -> None:
        """Stop the worker and close the HTTP client."""

        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
            self._task = None
        if self._client:
            await self._client.aclose()
            self._client = None

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Queue an event for delivery to the ElevenLabs agent."""

        if not self.enabled:
            return

        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        }

        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            LOGGER.warning("Callback queue full, dropping event: %s", event_type)

    async def _worker(self) -> None:
        timeout = httpx.Timeout(self.timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            self._client = client
            while self._running:
                event = await self.queue.get()
                try:
                    await self._send_event(event)
                except Exception as exc:  # noqa: BLE001
                    LOGGER.error("Failed to deliver callback: %s", exc)

    async def _send_event(self, event: Dict[str, Any]) -> None:
        if not self._client:
            return
        url = self._build_callback_url()
        if not url:
            LOGGER.debug("Callback URL unavailable, skipping event")
            return

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["xi-api-key"] = self.api_key

        response = await self._client.post(url, json=event, headers=headers)
        response.raise_for_status()

    def _build_callback_url(self) -> Optional[str]:
        if self.callback_url:
            return self.callback_url
        if self.agent_id:
            return f"{self.base_url}/agents/{self.agent_id}/callbacks"
        return None


def build_callback_dispatcher_from_env() -> Optional[CallbackDispatcher]:
    """Create a dispatcher based on ELEVENLABS_* environment settings."""

    enabled = os.getenv("ENABLE_ELEVENLABS_CALLBACKS", "false").lower() == "true"
    if not enabled:
        return None

    callback_url = os.getenv("ELEVENLABS_CALLBACK_URL")
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    base_url = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1")
    timeout = float(os.getenv("ELEVENLABS_CALLBACK_TIMEOUT", "10"))
    queue_size = int(os.getenv("ELEVENLABS_CALLBACK_QUEUE_SIZE", "256"))

    if not callback_url and not (agent_id and api_key):
        LOGGER.warning("ElevenLabs callbacks enabled but misconfigured; skipping setup")
        return None

    return CallbackDispatcher(
        callback_url=callback_url,
        agent_id=agent_id,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_queue_size=queue_size,
    )
