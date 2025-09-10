#!/usr/bin/env python3
"""iRacing telemetry streaming module.

This module connects to the iRacing shared memory via ``pyirsdk`` and
provides normalised car position data in real time.  The goal is to offer a
simple interface for other parts of the system to subscribe to telemetry
updates without having to interact with ``pyirsdk`` directly.

The streamer polls the SDK at a configurable rate, computes relative
positions for all cars in the session and notifies all registered listeners
with the processed data.

The implementation is intentionally light‑weight and does not attempt to
model every bit of available telemetry.  Only the information required for
car spotting (relative location, distance and speed) is extracted and
normalised.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

# ``pyirsdk`` is optional during development and unit testing.  The module
# should still be importable when the package is not installed.
try:  # pragma: no cover - import guard
    import pyirsdk

    PYIRSDK_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    pyirsdk = None  # type: ignore
    PYIRSDK_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class NormalisedCar:
    """Normalised representation of a car in the session."""

    car_idx: int
    driver_name: str
    distance: float  # metres relative to player's car (positive = ahead)
    speed: float  # metres/second
    relative_speed: float  # metres/second (positive = faster than player)
    location: str  # ``ahead`` or ``behind``


class IRacingTelemetry:
    """Stream iRacing telemetry and publish normalised car positions."""

    def __init__(self, poll_rate: float = 10.0):
        """Create the telemetry streamer.

        Parameters
        ----------
        poll_rate:
            Number of telemetry polls per second.  Values above ~60 provide
            little benefit and consume more CPU.
        """

        self.poll_rate = poll_rate
        self.ir = pyirsdk.IRSDK() if PYIRSDK_AVAILABLE else None
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._running = False
        self.track_length: Optional[float] = None
        self.player_car_idx: Optional[int] = None

    # ------------------------------------------------------------------
    # Subscription handling
    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for telemetry updates."""

        self._listeners.append(callback)

    # ------------------------------------------------------------------
    async def start(self) -> None:
        """Start polling telemetry and notifying listeners.

        This coroutine runs until :meth:`stop` is called or the connection to
        iRacing is lost.
        """

        if not PYIRSDK_AVAILABLE:
            raise RuntimeError("pyirsdk is required for real telemetry")

        assert self.ir is not None
        if not self.ir.startup():  # pragma: no cover - requires iRacing
            raise RuntimeError("Unable to connect to iRacing")

        self.track_length = float(self.ir["TrackLength"] or 0)
        driver_info = self.ir["DriverInfo"] or {}
        self.player_car_idx = driver_info.get("DriverCarIdx", 0)

        logger.info("iRacing telemetry started")
        self._running = True
        try:
            while self._running and self.ir.is_connected:
                # Wait for fresh telemetry
                self.ir.wait_for_data(timeout=1)
                data = self.ir.get_data()
                if not data:
                    await asyncio.sleep(1.0 / self.poll_rate)
                    continue

                cars = self._normalise_car_positions(data)
                snapshot = {"timestamp": time.time(), "cars": cars}
                for cb in list(self._listeners):
                    try:
                        cb(snapshot)
                    except Exception:  # pragma: no cover - defensive
                        logger.exception("Telemetry listener error")

                await asyncio.sleep(1.0 / self.poll_rate)
        finally:  # pragma: no cover - shutdown path
            self.ir.shutdown()
            self._running = False
            logger.info("iRacing telemetry stopped")

    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Request the telemetry loop to terminate."""

        self._running = False

    # ------------------------------------------------------------------
    def _normalise_car_positions(self, data: Dict[str, Any]) -> List[NormalisedCar]:
        """Convert raw ``pyirsdk`` data into :class:`NormalisedCar` entries.

        The method relies only on a subset of iRacing variables so it can be
        unit tested with synthetic data.  ``self.track_length`` and
        ``self.player_car_idx`` must be populated beforehand.
        """

        if self.track_length is None or self.player_car_idx is None:
            return []

        track_len = self.track_length
        player_idx = self.player_car_idx

        # Player car state
        player_lap = data.get("CarIdxLap", [0])[player_idx]
        player_pct = data.get("CarIdxLapDistPct", [0])[player_idx]
        player_dist = (player_lap + player_pct) * track_len
        player_speed = data.get("Speed", 0.0)

        # Build lookup of driver names
        drivers: Dict[int, str] = {}
        info = data.get("DriverInfo") or {}
        for drv in info.get("Drivers", []):
            drivers[drv.get("CarIdx")] = drv.get("UserName", f"Car {drv.get('CarIdx')}")

        cars: List[NormalisedCar] = []
        laps: Iterable[int] = data.get("CarIdxLap", [])
        pcts: Iterable[float] = data.get("CarIdxLapDistPct", [])
        speeds: Iterable[float] = data.get("CarIdxSpeed", [])

        total_cars = max(len(laps), len(pcts), len(speeds))
        for idx in range(total_cars):
            if idx == player_idx:
                continue

            lap = laps[idx] if idx < len(laps) else 0
            pct = pcts[idx] if idx < len(pcts) else 0.0
            speed = speeds[idx] if idx < len(speeds) else 0.0

            car_dist = (lap + pct) * track_len
            rel_dist = car_dist - player_dist

            # Account for track wrap‑around: choose shortest signed distance
            if rel_dist > track_len / 2:
                rel_dist -= track_len
            elif rel_dist < -track_len / 2:
                rel_dist += track_len

            rel_speed = speed - player_speed
            location = "ahead" if rel_dist > 0 else "behind"

            cars.append(
                NormalisedCar(
                    car_idx=idx,
                    driver_name=drivers.get(idx, f"Car {idx}"),
                    distance=rel_dist,
                    speed=speed,
                    relative_speed=rel_speed,
                    location=location,
                )
            )

        return cars


__all__ = ["IRacingTelemetry", "NormalisedCar"]
