from app.contracts.providers import WeatherProvider
from app.contracts.weather import WeatherForecast, WeatherSnapshot
from app.domains.weather.exceptions import WeatherLocationNotFoundError


class WeatherService:
    def __init__(self, provider: WeatherProvider) -> None:
        self._provider = provider

    # 1. 查询当前天气
    async def get_current(self, location: str) -> WeatherSnapshot:
        normalized = location.strip()
        if not normalized:
            raise WeatherLocationNotFoundError("Weather location is required")
        return await self._provider.current(normalized)

    # 2. 查询天气预报
    async def get_forecast(
        self,
        location: str,
        days: int = 1,
    ) -> list[WeatherForecast]:
        normalized = location.strip()
        if not normalized:
            raise WeatherLocationNotFoundError("Weather location is required")
        if not 1 <= days <= 16:
            raise ValueError("Forecast days must be between 1 and 16")
        return await self._provider.forecast(normalized, days)
