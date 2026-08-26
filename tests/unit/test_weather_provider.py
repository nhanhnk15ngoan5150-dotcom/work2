import asyncio
from datetime import date

import httpx
import pytest

from app.domains.weather.exceptions import (
    WeatherInvalidResponseError,
    WeatherLocationNotFoundError,
    WeatherProviderError,
)
from app.infrastructure.weather.open_meteo import OpenMeteoWeatherProvider


def _geocoding_payload() -> dict:
    return {
        "results": [
            {
                "name": "成都",
                "latitude": 30.67,
                "longitude": 104.07,
                "timezone": "Asia/Shanghai",
            }
        ]
    }


def test_open_meteo_owned_client_does_not_inherit_environment_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    class FakeAsyncClient:
        async def aclose(self) -> None:
            return None

    def create_client(**kwargs):
        captured.update(kwargs)
        return FakeAsyncClient()

    monkeypatch.setattr(httpx, "AsyncClient", create_client)

    provider = OpenMeteoWeatherProvider()
    asyncio.run(provider.close())

    assert captured["trust_env"] is False


async def _get_current(
    handler,
    *,
    max_retries: int = 2,
):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await OpenMeteoWeatherProvider(
            client,
            max_retries=max_retries,
        ).current("成都")


async def _get_forecast(handler, days: int = 2):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await OpenMeteoWeatherProvider(client).forecast("成都", days)


def test_open_meteo_current_normalizes_vendor_payload() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if "geocoding-api" in request.url.host:
            return httpx.Response(200, json=_geocoding_payload())
        return httpx.Response(
            200,
            json={
                "current": {
                    "time": "2026-08-26T10:15",
                    "temperature_2m": 28.5,
                    "relative_humidity_2m": 72,
                    "precipitation": 0.2,
                    "weather_code": 61,
                    "wind_speed_10m": 8.4,
                }
            },
        )

    snapshot = asyncio.run(_get_current(handler))

    assert snapshot.location.name == "成都"
    assert snapshot.date == date(2026, 8, 26)
    assert snapshot.weather_type == "slight_rain"
    assert snapshot.temperature == 28.5
    assert snapshot.humidity == 72.0
    assert snapshot.source == "open-meteo"


def test_open_meteo_forecast_preserves_missing_fields_as_none() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if "geocoding-api" in request.url.host:
            return httpx.Response(200, json=_geocoding_payload())
        assert request.url.params["forecast_days"] == "2"
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-08-26", "2026-08-27"],
                    "weather_code": [2, 63],
                    "temperature_2m_min": [22.0, 23.0],
                    "temperature_2m_max": [31.0, 30.0],
                    "precipitation_sum": [0.0, 4.2],
                    "wind_speed_10m_max": [10.0, 12.0],
                }
            },
        )

    forecasts = asyncio.run(_get_forecast(handler))

    assert len(forecasts) == 2
    assert forecasts[1].weather_type == "moderate_rain"
    assert forecasts[1].temperature_min == 23.0
    assert forecasts[1].precipitation == 4.2
    assert forecasts[1].humidity is None
    assert forecasts[1].observed_at is None


def test_open_meteo_reports_location_not_found() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    with pytest.raises(WeatherLocationNotFoundError):
        asyncio.run(_get_current(handler))


def test_open_meteo_retries_timeout_then_succeeds() -> None:
    forecast_attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal forecast_attempts
        if "geocoding-api" in request.url.host:
            return httpx.Response(200, json=_geocoding_payload())
        forecast_attempts += 1
        if forecast_attempts == 1:
            raise httpx.ConnectTimeout("timed out", request=request)
        return httpx.Response(
            200,
            json={"current": {"time": "2026-08-26T10:15"}},
        )

    snapshot = asyncio.run(_get_current(handler, max_retries=1))

    assert snapshot.date == date(2026, 8, 26)
    assert forecast_attempts == 2


def test_open_meteo_stops_after_finite_http_retries() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, request=request)

    with pytest.raises(WeatherProviderError, match="HTTP 503"):
        asyncio.run(_get_current(handler, max_retries=2))

    assert attempts == 3


def test_open_meteo_rejects_invalid_current_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if "geocoding-api" in request.url.host:
            return httpx.Response(200, json=_geocoding_payload())
        return httpx.Response(200, json={"current": {"time": "invalid"}})

    with pytest.raises(WeatherInvalidResponseError):
        asyncio.run(_get_current(handler))
