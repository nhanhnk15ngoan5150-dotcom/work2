import asyncio
from datetime import date, datetime
from unittest.mock import AsyncMock

from app.contracts.evidence import EvidenceDomain, EvidenceType
from app.contracts.state import AgentState
from app.contracts.weather import WeatherForecast, WeatherLocation, WeatherSnapshot
from app.domains.weather.exceptions import (
    WeatherLocationNotFoundError,
    WeatherProviderError,
)
from app.domains.weather.service import WeatherService
from app.workflows.external_factor import ExternalFactorWorkflow


def _state(question: str) -> AgentState:
    return {
        "request_id": "weather-test",
        "tenant_id": "dev_tenant",
        "session_id": None,
        "question": question,
        "normalized_question": question,
        "selected_domains": [EvidenceDomain.EXTERNAL_FACTOR],
        "evidence": [],
        "errors": [],
        "warnings": [],
        "final_answer": None,
        "trace_metadata": {},
    }


def _location() -> WeatherLocation:
    return WeatherLocation(
        name="成都",
        latitude=30.67,
        longitude=104.07,
        timezone="Asia/Shanghai",
    )


def test_external_factor_current_weather_returns_fact_evidence() -> None:
    service = AsyncMock(spec=WeatherService)
    service.get_current.return_value = WeatherSnapshot(
        location=_location(),
        date=date(2026, 8, 26),
        weather_type="partly_cloudy",
        temperature=28.5,
        precipitation=0.0,
        source="open-meteo",
        observed_at=datetime(2026, 8, 26, 10, 15),
    )

    result = asyncio.run(
        ExternalFactorWorkflow(service).execute(_state("成都现在天气怎么样？"))
    )

    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["evidence"][0].domain is EvidenceDomain.EXTERNAL_FACTOR
    assert result["evidence"][0].evidence_type is EvidenceType.FACT
    assert result["evidence"][0].confidence is None
    assert result["evidence"][0].value["temperature"] == 28.5
    assert result["final_answer"] == "成都当前天气：多云，28.5℃，降水量 0.0 毫米。"


def test_external_factor_tomorrow_returns_prediction_evidence() -> None:
    service = AsyncMock(spec=WeatherService)
    service.get_forecast.return_value = [
        WeatherForecast(
            location=_location(),
            date=date(2026, 8, 26),
            source="open-meteo",
        ),
        WeatherForecast(
            location=_location(),
            date=date(2026, 8, 27),
            weather_type="moderate_rain",
            temperature_min=23.0,
            temperature_max=30.0,
            precipitation=4.2,
            source="open-meteo",
        ),
    ]

    result = asyncio.run(
        ExternalFactorWorkflow(service).execute(_state("成都明天天气怎么样？"))
    )

    evidence = result["evidence"][0]
    assert evidence.evidence_type is EvidenceType.PREDICTION
    assert evidence.confidence is None
    assert evidence.value["date"] == "2026-08-27"
    assert result["final_answer"] == (
        "成都2026-08-27天气预报：中雨，23.0～30.0℃，降水量 4.2 毫米。"
    )
    service.get_forecast.assert_awaited_once_with("成都", days=2)


def test_external_factor_extracts_location_after_temporal_prefix() -> None:
    service = AsyncMock(spec=WeatherService)
    service.get_forecast.return_value = [
        WeatherForecast(
            location=_location(),
            date=date(2026, 8, 26),
            source="open-meteo",
        ),
        WeatherForecast(
            location=_location(),
            date=date(2026, 8, 27),
            weather_type="moderate_rain",
            source="open-meteo",
        ),
    ]

    result = asyncio.run(
        ExternalFactorWorkflow(service).execute(
            _state("明天成都下雨，结合最近营业额应该注意什么？")
        )
    )

    assert result["warnings"] == []
    assert result["evidence"][0].evidence_type is EvidenceType.PREDICTION
    service.get_forecast.assert_awaited_once_with("成都", days=2)


def test_external_factor_handles_location_not_found() -> None:
    service = AsyncMock(spec=WeatherService)
    service.get_current.side_effect = WeatherLocationNotFoundError("not found")

    result = asyncio.run(
        ExternalFactorWorkflow(service).execute(_state("未知城现在天气怎么样？"))
    )

    assert result["evidence"] == []
    assert result["warnings"] == ["未找到天气地点：未知城"]


def test_external_factor_handles_provider_failure() -> None:
    service = AsyncMock(spec=WeatherService)
    service.get_current.side_effect = WeatherProviderError("unavailable")

    result = asyncio.run(
        ExternalFactorWorkflow(service).execute(_state("成都现在天气怎么样？"))
    )

    assert result["evidence"] == []
    assert result["errors"] == ["天气服务暂时不可用"]
    assert result["final_answer"] == "天气服务暂时不可用"
