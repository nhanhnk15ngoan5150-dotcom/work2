import re
from typing import cast

from app.contracts.evidence import Evidence, EvidenceDomain, EvidenceType
from app.contracts.state import AgentState
from app.contracts.weather import WeatherForecast, WeatherSnapshot
from app.domains.weather.exceptions import (
    WeatherLocationNotFoundError,
    WeatherProviderError,
)
from app.domains.weather.service import WeatherService

WEATHER_TYPE_LABELS = {
    "clear_sky": "晴",
    "mainly_clear": "晴间多云",
    "partly_cloudy": "多云",
    "overcast": "阴",
    "fog": "雾",
    "rime_fog": "冻雾",
    "light_drizzle": "小毛毛雨",
    "moderate_drizzle": "毛毛雨",
    "dense_drizzle": "强毛毛雨",
    "slight_rain": "小雨",
    "moderate_rain": "中雨",
    "heavy_rain": "大雨",
    "slight_snow": "小雪",
    "moderate_snow": "中雪",
    "heavy_snow": "大雪",
    "thunderstorm": "雷暴",
}


class ExternalFactorWorkflow:
    """Single-domain workflow for external weather factors."""

    def __init__(self, weather_service: WeatherService) -> None:
        self._weather_service = weather_service

    @property
    def domain(self) -> EvidenceDomain:
        return EvidenceDomain.EXTERNAL_FACTOR

    # 1. 识别天气意图和地点
    async def execute(self, state: AgentState) -> AgentState:
        question = state["question"].strip()
        location = self._extract_location(question)
        if location is None:
            return self._with_warning(state, "未识别天气查询地点")

        try:
            if "明天" in question or "预报" in question:
                return await self._execute_forecast(state, location)
            return await self._execute_current(state, location)
        except WeatherLocationNotFoundError:
            return self._with_warning(state, f"未找到天气地点：{location}")
        except WeatherProviderError:
            return self._with_error(state, "天气服务暂时不可用")

    # 2. 查询当前天气并转换为 FACT Evidence
    async def _execute_current(
        self,
        state: AgentState,
        location: str,
    ) -> AgentState:
        snapshot = await self._weather_service.get_current(location)
        evidence = Evidence(
            tenant_id=state["tenant_id"],
            domain=self.domain,
            evidence_type=EvidenceType.FACT,
            claim=f"{snapshot.location.name}{snapshot.date.isoformat()}当前天气",
            value=snapshot.model_dump(mode="json"),
            source_type="weather_api",
            source_id=self._source_id("current", snapshot),
        )
        return self._with_evidence(
            state,
            evidence,
            self._format_current(snapshot),
            location,
            "current",
        )

    # 3. 查询明日天气并转换为 PREDICTION Evidence
    async def _execute_forecast(
        self,
        state: AgentState,
        location: str,
    ) -> AgentState:
        forecasts = await self._weather_service.get_forecast(location, days=2)
        if len(forecasts) < 2:
            return self._with_warning(state, "天气预报数据不足")
        forecast = forecasts[1]
        evidence = Evidence(
            tenant_id=state["tenant_id"],
            domain=self.domain,
            evidence_type=EvidenceType.PREDICTION,
            claim=f"{forecast.location.name}{forecast.date.isoformat()}天气预报",
            value=forecast.model_dump(mode="json"),
            source_type="weather_api",
            source_id=self._source_id("forecast", forecast),
        )
        return self._with_evidence(
            state,
            evidence,
            self._format_forecast(forecast),
            location,
            "forecast",
        )

    @staticmethod
    def _extract_location(question: str) -> str | None:
        prefix = re.split(
            r"明天|今天|现在|当前|天气|气温|温度|预报",
            question,
            maxsplit=1,
        )[0]
        location = re.sub(r"^(请问|请查询|查询|查一下)", "", prefix).strip(" ，,。？?")
        return location or None

    @staticmethod
    def _source_id(
        kind: str,
        weather: WeatherSnapshot | WeatherForecast,
    ) -> str:
        location = weather.location
        return (
            f"{weather.source}:{kind}:"
            f"{location.latitude}:{location.longitude}:{weather.date.isoformat()}"
        )

    @staticmethod
    def _with_evidence(
        state: AgentState,
        evidence: Evidence,
        answer: str,
        location: str,
        weather_intent: str,
    ) -> AgentState:
        result = dict(state)
        result["normalized_question"] = state["question"].replace(" ", "")
        result["evidence"] = [evidence]
        result["final_answer"] = answer
        result["trace_metadata"] = {
            "weather_intent": weather_intent,
            "weather_location": location,
        }
        return cast(AgentState, result)

    @staticmethod
    def _with_warning(state: AgentState, warning: str) -> AgentState:
        result = dict(state)
        result["warnings"] = [warning]
        result["final_answer"] = warning
        return cast(AgentState, result)

    @staticmethod
    def _with_error(state: AgentState, error: str) -> AgentState:
        result = dict(state)
        result["errors"] = [error]
        result["final_answer"] = error
        return cast(AgentState, result)

    @staticmethod
    def _format_current(snapshot: WeatherSnapshot) -> str:
        details = _weather_details(
            snapshot.weather_type,
            snapshot.temperature,
            None,
            snapshot.precipitation,
        )
        return f"{snapshot.location.name}当前天气：{'，'.join(details)}。"

    @staticmethod
    def _format_forecast(forecast: WeatherForecast) -> str:
        details = _weather_details(
            forecast.weather_type,
            forecast.temperature_min,
            forecast.temperature_max,
            forecast.precipitation,
        )
        return (
            f"{forecast.location.name}{forecast.date.isoformat()}天气预报："
            f"{'，'.join(details)}。"
        )


def _weather_details(
    weather_type: str | None,
    temperature_min: float | None,
    temperature_max: float | None,
    precipitation: float | None,
) -> list[str]:
    details: list[str] = []
    if weather_type is not None:
        details.append(WEATHER_TYPE_LABELS.get(weather_type, weather_type))
    if temperature_min is not None and temperature_max is not None:
        details.append(f"{temperature_min:.1f}～{temperature_max:.1f}℃")
    elif temperature_min is not None:
        details.append(f"{temperature_min:.1f}℃")
    if precipitation is not None:
        details.append(f"降水量 {precipitation:.1f} 毫米")
    return details or ["暂无可展示的天气指标"]
