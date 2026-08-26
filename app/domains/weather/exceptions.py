class WeatherProviderError(RuntimeError):
    """Base error for expected weather provider failures."""


class WeatherLocationNotFoundError(WeatherProviderError):
    """The provider could not resolve the requested location."""


class WeatherInvalidResponseError(WeatherProviderError):
    """The provider returned a response that cannot satisfy the contract."""
