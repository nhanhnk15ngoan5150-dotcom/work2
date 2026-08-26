import asyncio
from unittest.mock import AsyncMock

import pytest

from app.contracts.providers import WeatherProvider
from app.domains.weather.exceptions import WeatherLocationNotFoundError
from app.domains.weather.service import WeatherService


def test_weather_service_normalizes_location_before_provider_call() -> None:
    provider = AsyncMock(spec=WeatherProvider)
    provider.forecast.return_value = []

    result = asyncio.run(
        WeatherService(provider).get_forecast("  上海  ", days=2)
    )

    assert result == []
    provider.forecast.assert_awaited_once_with("上海", 2)


def test_weather_service_rejects_missing_location() -> None:
    provider = AsyncMock(spec=WeatherProvider)

    with pytest.raises(WeatherLocationNotFoundError):
        asyncio.run(WeatherService(provider).get_current("   "))

    provider.current.assert_not_awaited()
