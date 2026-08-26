from datetime import date

import pytest
from pydantic import ValidationError

from app.contracts.weather import WeatherForecast, WeatherLocation, WeatherSnapshot


def test_weather_contracts_allow_missing_vendor_fields() -> None:
    location = WeatherLocation(
        name="成都",
        latitude=30.67,
        longitude=104.07,
        timezone="Asia/Shanghai",
    )

    snapshot = WeatherSnapshot(
        location=location,
        date=date(2026, 8, 26),
        temperature=28.5,
        source="test-weather",
    )
    forecast = WeatherForecast(
        location=location,
        date=date(2026, 8, 27),
        temperature_min=23.0,
        temperature_max=31.0,
        source="test-weather",
    )

    assert snapshot.weather_type is None
    assert snapshot.precipitation is None
    assert forecast.precipitation is None
    assert forecast.observed_at is None


def test_weather_contracts_reject_invalid_measurement_ranges() -> None:
    location = WeatherLocation(name="上海", latitude=31.23, longitude=121.47)

    with pytest.raises(ValidationError):
        WeatherSnapshot(
            location=location,
            date=date(2026, 8, 26),
            humidity=101.0,
            source="test-weather",
        )
