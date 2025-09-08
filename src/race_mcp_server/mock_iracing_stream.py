import asyncio
import json
import math
import random
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class MockTelemetry:
    """Simplified telemetry snapshot matching iRacing fields."""

    SessionTime: float
    Lap: int
    LapCurrentLapTime: float
    LapDist: float
    Speed: float
    RPM: float
    Gear: int
    Throttle: float
    Brake: float
    SteeringWheelAngle: float
    TrackTemp: float
    AirTemp: float
    FuelLevel: float
    IsOnTrack: bool
    SessionState: str
    SessionFlags: str


class MockIRacingDataGenerator:
    """Generate somewhat realistic iRacing-like telemetry data."""

    def __init__(self, track_length_m: float = 5000.0, tick_rate: float = 10.0):
        self.track_length = track_length_m
        self.tick_rate = tick_rate
        self.start_time = time.time()
        self.lap_start_time = self.start_time
        self.lap = 1
        self.lap_dist = 0.0
        self.speed = 0.0
        self.rpm = 0.0
        self.gear = 1
        self.throttle = 0.0
        self.brake = 0.0
        self.fuel_level = 18.0
        self.track_temp = 85.0
        self.air_temp = 72.0
        self.steering = 0.0

    def _update_state(self, dt: float) -> None:
        # Randomly adjust throttle and brake for variability
        if random.random() < 0.1:
            self.throttle = max(0.0, min(1.0, self.throttle + random.uniform(-0.3, 0.3)))
        if random.random() < 0.05:
            self.brake = max(0.0, min(1.0, random.uniform(0.0, 1.0)))
        else:
            self.brake = max(0.0, self.brake - 0.1)

        # Update speed based on throttle and brake
        accel = (self.throttle - self.brake) * 5.0  # m/s^2
        self.speed = max(0.0, self.speed + accel * dt)
        self.speed = min(self.speed, 80.0)  # cap around 180 mph (~80 m/s)

        # Convert speed to mph for telemetry
        speed_mph = self.speed * 2.23694

        # Simple gear estimation based on speed
        self.gear = min(6, max(1, int(speed_mph // 30) + 1))

        # RPM tied to speed and gear with some noise
        gear_ratio = [0, 3.2, 2.1, 1.5, 1.2, 1.0, 0.85][self.gear]
        self.rpm = min(9000.0, speed_mph * gear_ratio * 50 + random.uniform(-50, 50))

        # Steering oscillates slightly with noise
        self.steering = math.sin(time.time() * 0.5) * 0.2 + random.uniform(-0.02, 0.02)

        # Update lap distance
        self.lap_dist += self.speed * dt
        if self.lap_dist >= self.track_length:
            self.lap += 1
            self.lap_dist -= self.track_length
            self.lap_start_time = time.time()

        # Fuel consumption
        self.fuel_level = max(0.0, self.fuel_level - self.speed * dt * 0.0005)

    def generate(self) -> Dict[str, Any]:
        now = time.time()
        dt = now - self.start_time - self.session_time if hasattr(self, 'session_time') else 1.0 / self.tick_rate
        self.session_time = now - self.start_time
        self._update_state(dt)

        # Simulate occasional flag changes and off-track events for AI testing
        elapsed = self.session_time
        
        # Simulate flag changes every 30-60 seconds
        flag_cycle = elapsed % 60
        if flag_cycle < 5:
            session_flags = "Yellow"  # Caution
        elif flag_cycle < 8:
            session_flags = "Red"     # Red flag
        elif flag_cycle < 55:
            session_flags = "Green"   # Normal racing
        else:
            session_flags = "Checkered"  # End of session
            
        # Simulate going off track occasionally (every 45 seconds for 3 seconds)
        off_track_cycle = elapsed % 45
        is_on_track = not (42 <= off_track_cycle <= 45)

        lap_time = now - self.lap_start_time
        telemetry = MockTelemetry(
            SessionTime=self.session_time,
            Lap=self.lap,
            LapCurrentLapTime=lap_time,
            LapDist=self.lap_dist,
            Speed=self.speed * 2.23694,  # mph
            RPM=self.rpm,
            Gear=self.gear,
            Throttle=self.throttle,
            Brake=self.brake,
            SteeringWheelAngle=self.steering,
            TrackTemp=self.track_temp,
            AirTemp=self.air_temp,
            FuelLevel=self.fuel_level,
            IsOnTrack=is_on_track,
            SessionState="Racing",
            SessionFlags=session_flags,
        )
        return asdict(telemetry)


class MockIRacingStreamServer:
    """TCP server emitting JSON telemetry frames to connected clients."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9000, tick_rate: float = 10.0):
        self.generator = MockIRacingDataGenerator(tick_rate=tick_rate)
        self.host = host
        self.port = port
        self.tick_rate = tick_rate

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                data = json.dumps(self.generator.generate()).encode() + b"\n"
                writer.write(data)
                await writer.drain()
                await asyncio.sleep(1.0 / self.tick_rate)
        except asyncio.CancelledError:  # pragma: no cover - server shutdown
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self) -> None:
        server = await asyncio.start_server(self._handle_client, self.host, self.port)
        async with server:
            await server.serve_forever()


def main() -> None:
    """Entry point for running the mock telemetry stream."""
    import argparse

    parser = argparse.ArgumentParser(description="Mock iRacing telemetry stream")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind server")
    parser.add_argument("--port", type=int, default=9000, help="Port to bind server")
    parser.add_argument("--rate", type=float, default=10.0, help="Telemetry frames per second")
    args = parser.parse_args()

    server = MockIRacingStreamServer(host=args.host, port=args.port, tick_rate=args.rate)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:  # pragma: no cover - manual stop
        pass


if __name__ == "__main__":
    main()
