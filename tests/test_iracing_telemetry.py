import math
from race_mcp_server.iracing_telemetry import IRacingTelemetry


def make_stream(track_length: float = 1000.0, player_idx: int = 0) -> IRacingTelemetry:
    stream = IRacingTelemetry()
    stream.track_length = track_length
    stream.player_car_idx = player_idx
    return stream


def test_normalisation_basic():
    stream = make_stream()
    data = {
        "CarIdxLap": [1, 1, 1],
        "CarIdxLapDistPct": [0.50, 0.55, 0.45],
        "CarIdxSpeed": [30.0, 31.0, 29.0],
        "Speed": 30.0,
        "DriverInfo": {"Drivers": [
            {"CarIdx": 0, "UserName": "Player"},
            {"CarIdx": 1, "UserName": "Alice"},
            {"CarIdx": 2, "UserName": "Bob"},
        ]},
    }

    cars = stream._normalise_car_positions(data)
    assert len(cars) == 2

    ahead = next(c for c in cars if c.car_idx == 1)
    behind = next(c for c in cars if c.car_idx == 2)

    assert math.isclose(ahead.distance, 50.0, abs_tol=1e-6)
    assert ahead.location == "ahead"
    assert math.isclose(behind.distance, -50.0, abs_tol=1e-6)
    assert behind.location == "behind"


def test_wrap_around_distance():
    stream = make_stream()
    data = {
        "CarIdxLap": [1, 1],
        "CarIdxLapDistPct": [0.99, 0.01],  # car 1 is just ahead across start/finish
        "CarIdxSpeed": [30.0, 30.0],
        "Speed": 30.0,
        "DriverInfo": {"Drivers": [
            {"CarIdx": 0, "UserName": "Player"},
            {"CarIdx": 1, "UserName": "Rival"},
        ]},
    }

    cars = stream._normalise_car_positions(data)
    assert len(cars) == 1
    rival = cars[0]
    # Relative distance should be about +20m (ahead) rather than -980m
    assert rival.distance > 0
    assert math.isclose(rival.distance, 20.0, abs_tol=1e-6)
    assert rival.location == "ahead"
