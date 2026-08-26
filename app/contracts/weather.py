from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class WeatherLocation(BaseModel):
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    timezone: str | None = None


class WeatherSnapshot(BaseModel):
    location: WeatherLocation
    date: date
    weather_type: str | None = None
    temperature: float | None = None
    precipitation: float | None = Field(default=None, ge=0.0)
    humidity: float | None = Field(default=None, ge=0.0, le=100.0)
    wind_speed: float | None = Field(default=None, ge=0.0)
    source: str = Field(min_length=1)
    observed_at: datetime | None = None


class WeatherForecast(BaseModel):
    location: WeatherLocation
    date: date
    weather_type: str | None = None
    temperature_min: float | None = None
    temperature_max: float | None = None
    precipitation: float | None = Field(default=None, ge=0.0)
    humidity: float | None = Field(default=None, ge=0.0, le=100.0)
    wind_speed: float | None = Field(default=None, ge=0.0)
    source: str = Field(min_length=1)
    observed_at: datetime | None = None
