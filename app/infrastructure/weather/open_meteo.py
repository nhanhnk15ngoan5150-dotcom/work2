from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from app.contracts.weather import WeatherForecast, WeatherLocation, WeatherSnapshot
from app.domains.weather.exceptions import (
    WeatherInvalidResponseError,
    WeatherLocationNotFoundError,
    WeatherProviderError,
)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
SOURCE_NAME = "open-meteo"

CURRENT_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
)
DAILY_VARIABLES = (
    "weather_code",
    "temperature_2m_min",
    "temperature_2m_max",
    "precipitation_sum",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
)

WMO_WEATHER_TYPES = {
    0: "clear_sky",
    1: "mainly_clear",
    2: "partly_cloudy",
    3: "overcast",
    45: "fog",
    48: "rime_fog",
    51: "light_drizzle",
    53: "moderate_drizzle",
    55: "dense_drizzle",
    56: "light_freezing_drizzle",
    57: "dense_freezing_drizzle",
    61: "slight_rain",
    63: "moderate_rain",
    65: "heavy_rain",
    66: "light_freezing_rain",
    67: "heavy_freezing_rain",
    71: "slight_snow",
    73: "moderate_snow",
    75: "heavy_snow",
    77: "snow_grains",
    80: "slight_rain_showers",
    81: "moderate_rain_showers",
    82: "violent_rain_showers",
    85: "slight_snow_showers",
    86: "heavy_snow_showers",
    95: "thunderstorm",
    96: "thunderstorm_with_slight_hail",
    99: "thunderstorm_with_heavy_hail",
}


class OpenMeteoWeatherProvider:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Weather timeout must be positive")
        if max_retries < 0:
            raise ValueError("Weather max retries cannot be negative")
        self._client = client or httpx.AsyncClient(trust_env=False)
        self._owns_client = client is None
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_retries = max_retries

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # 1. 查询并标准化当前天气
    async def current(self, location: str) -> WeatherSnapshot:
        resolved = await self._resolve_location(location)
        payload = await self._request_json(
            FORECAST_URL,
            params={
                "latitude": resolved.latitude,
                "longitude": resolved.longitude,
                "current": ",".join(CURRENT_VARIABLES),
                "timezone": resolved.timezone or "auto",
            },
        )
        current = payload.get("current")
        if not isinstance(current, Mapping):
            raise WeatherInvalidResponseError("Current weather payload is missing")

        observed_at = _parse_datetime(current.get("time"))
        if observed_at is None:
            raise WeatherInvalidResponseError("Current weather time is invalid")
        try:
            return WeatherSnapshot(
                location=resolved,
                date=observed_at.date(),
                weather_type=_weather_type(current.get("weather_code")),
                temperature=_optional_float(current.get("temperature_2m")),
                precipitation=_optional_float(current.get("precipitation")),
                humidity=_optional_float(current.get("relative_humidity_2m")),
                wind_speed=_optional_float(current.get("wind_speed_10m")),
                source=SOURCE_NAME,
                observed_at=observed_at,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise WeatherInvalidResponseError(
                "Current weather payload is invalid"
            ) from exc

    # 2. 查询并标准化逐日预报
    async def forecast(self, location: str, days: int) -> list[WeatherForecast]:
        if not 1 <= days <= 16:
            raise ValueError("Forecast days must be between 1 and 16")
        resolved = await self._resolve_location(location)
        payload = await self._request_json(
            FORECAST_URL,
            params={
                "latitude": resolved.latitude,
                "longitude": resolved.longitude,
                "daily": ",".join(DAILY_VARIABLES),
                "timezone": resolved.timezone or "auto",
                "forecast_days": days,
            },
        )
        daily = payload.get("daily")
        if not isinstance(daily, Mapping):
            raise WeatherInvalidResponseError("Daily forecast payload is missing")
        times = daily.get("time")
        if not isinstance(times, list) or not times:
            raise WeatherInvalidResponseError("Daily forecast dates are missing")

        forecasts: list[WeatherForecast] = []
        for index, raw_date in enumerate(times):
            try:
                forecasts.append(
                    WeatherForecast(
                        location=resolved,
                        date=date.fromisoformat(str(raw_date)),
                        weather_type=_weather_type(
                            _daily_value(daily, "weather_code", index)
                        ),
                        temperature_min=_optional_float(
                            _daily_value(daily, "temperature_2m_min", index)
                        ),
                        temperature_max=_optional_float(
                            _daily_value(daily, "temperature_2m_max", index)
                        ),
                        precipitation=_optional_float(
                            _daily_value(daily, "precipitation_sum", index)
                        ),
                        humidity=_optional_float(
                            _daily_value(daily, "relative_humidity_2m_mean", index)
                        ),
                        wind_speed=_optional_float(
                            _daily_value(daily, "wind_speed_10m_max", index)
                        ),
                        source=SOURCE_NAME,
                    )
                )
            except (TypeError, ValueError, ValidationError) as exc:
                raise WeatherInvalidResponseError(
                    "Daily forecast payload is invalid"
                ) from exc
        return forecasts

    # 3. 解析天气地点
    async def _resolve_location(self, location: str) -> WeatherLocation:
        payload = await self._request_json(
            GEOCODING_URL,
            params={
                "name": location,
                "count": 1,
                "language": "zh",
                "format": "json",
            },
        )
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            raise WeatherLocationNotFoundError(
                f"Weather location was not found: {location}"
            )
        first = results[0]
        if not isinstance(first, Mapping):
            raise WeatherInvalidResponseError("Geocoding result is invalid")
        try:
            return WeatherLocation(
                name=str(first["name"]),
                latitude=float(first["latitude"]),
                longitude=float(first["longitude"]),
                timezone=(
                    str(first["timezone"])
                    if first.get("timezone") is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise WeatherInvalidResponseError("Geocoding result is invalid") from exc

    # 4. 执行有限重试的 HTTP 请求
    async def _request_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(
                    url,
                    params=params,
                    timeout=self._timeout,
                )
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < self._max_retries:
                    continue
                raise WeatherProviderError("Weather provider request failed") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < self._max_retries:
                    continue
                raise WeatherProviderError(
                    f"Weather provider returned HTTP {exc.response.status_code}"
                ) from exc

            try:
                payload = response.json()
            except ValueError as exc:
                raise WeatherInvalidResponseError(
                    "Weather provider returned invalid JSON"
                ) from exc
            if not isinstance(payload, dict):
                raise WeatherInvalidResponseError(
                    "Weather provider response must be an object"
                )
            if payload.get("error") is True:
                raise WeatherProviderError(
                    str(payload.get("reason") or "Weather provider error")
                )
            return payload

        raise WeatherProviderError("Weather provider request failed")


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _weather_type(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return WMO_WEATHER_TYPES.get(int(value))
    except (TypeError, ValueError):
        raise WeatherInvalidResponseError("Weather code is invalid") from None


def _daily_value(daily: Mapping[str, Any], key: str, index: int) -> Any:
    values = daily.get(key)
    if values is None:
        return None
    if not isinstance(values, list) or index >= len(values):
        raise WeatherInvalidResponseError(f"Daily forecast field is invalid: {key}")
    return values[index]
