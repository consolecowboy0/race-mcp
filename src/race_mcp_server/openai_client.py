"""OpenAI API wrapper with graceful fallback."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

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
