import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.place import ExchangeRateResult, RouteResult, WeatherResult

logger = get_logger(__name__)

_cache: dict[str, tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(hours=1)


def _cache_key(prefix: str, **kwargs: Any) -> str:
    raw = json.dumps(kwargs, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"


def _get_cached(key: str) -> Any | None:
    if key in _cache:
        value, expires = _cache[key]
        if datetime.now(UTC) < expires:
            return value
        del _cache[key]
    return None


def _set_cache(key: str, value: Any) -> None:
    _cache[key] = (value, datetime.now(UTC) + CACHE_TTL)


class WeatherAdapter:
    async def get_weather(self, latitude: float, longitude: float, target_date: date) -> WeatherResult:
        key = _cache_key("weather", lat=latitude, lon=longitude, date=str(target_date))
        cached = _get_cached(key)
        if cached:
            return WeatherResult(**cached, cache_hit=True)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
                        "timezone": "auto",
                        "start_date": str(target_date),
                        "end_date": str(target_date),
                    },
                )
                data = response.json()
                daily = data.get("daily", {})
                condition = "clear"
                codes = daily.get("weathercode", [0])
                if codes and codes[0] >= 61:
                    condition = "rainy"
                elif codes and codes[0] >= 3:
                    condition = "cloudy"
                result = WeatherResult(
                    date=target_date,
                    condition=condition,
                    temperature_high=daily.get("temperature_2m_max", [20])[0],
                    temperature_low=daily.get("temperature_2m_min", [10])[0],
                    precipitation_chance=daily.get("precipitation_probability_max", [0])[0],
                    fetched_at=datetime.now(UTC),
                    cache_hit=False,
                )
                _set_cache(key, result.model_dump())
                return result
        except Exception as exc:
            logger.warning("Weather fetch failed: %s", exc)
            return WeatherResult(
                date=target_date,
                condition="unknown",
                temperature_high=20.0,
                temperature_low=10.0,
                precipitation_chance=0.0,
                fetched_at=datetime.now(UTC),
            )


class CurrencyAdapter:
    async def get_exchange_rate(
        self, from_currency: str, to_currency: str, reference_date: date
    ) -> ExchangeRateResult:
        key = _cache_key("fx", from_=from_currency, to=to_currency, date=str(reference_date))
        cached = _get_cached(key)
        if cached:
            return ExchangeRateResult(**cached, cache_hit=True)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://open.er-api.com/v6/latest/{from_currency.upper()}"
                )
                data = response.json()
                rates = data.get("rates", {})
                rate = rates.get(to_currency.upper(), 1.0)
                result = ExchangeRateResult(
                    from_currency=from_currency.upper(),
                    to_currency=to_currency.upper(),
                    rate=rate,
                    reference_date=reference_date,
                    fetched_at=datetime.now(UTC),
                )
                _set_cache(key, result.model_dump())
                return result
        except Exception as exc:
            logger.warning("Currency fetch failed: %s", exc)
            return ExchangeRateResult(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=1.0,
                reference_date=reference_date,
                fetched_at=datetime.now(UTC),
            )


class PlacesAdapter:
    async def search_places(
        self, query: str, latitude: float | None, longitude: float | None, category: str | None
    ) -> list[dict]:
        key = _cache_key("places", q=query, lat=latitude, lon=longitude, cat=category)
        cached = _get_cached(key)
        if cached:
            return cached
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params: dict[str, Any] = {"q": query, "format": "json", "limit": 5}
                if latitude and longitude:
                    params["lat"] = latitude
                    params["lon"] = longitude
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params=params,
                    headers={"User-Agent": "travel-planner-api/0.1"},
                )
                results = [
                    {
                        "name": item.get("display_name", query),
                        "latitude": float(item.get("lat", 0)),
                        "longitude": float(item.get("lon", 0)),
                        "address": item.get("display_name"),
                        "category": category or item.get("type", "place"),
                    }
                    for item in response.json()
                ]
                _set_cache(key, results)
                return results
        except Exception as exc:
            logger.warning("Places search failed: %s", exc)
            return []


class RoutingAdapter:
    async def get_route(
        self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float, mode: str
    ) -> RouteResult:
        key = _cache_key("route", o=(origin_lat, origin_lon), d=(dest_lat, dest_lon), m=mode)
        cached = _get_cached(key)
        if cached:
            return RouteResult(**cached, cache_hit=True)
        try:
            profile = "driving" if mode == "driving" else "foot"
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"https://router.project-osrm.org/route/v1/{profile}/{origin_lon},{origin_lat};{dest_lon},{dest_lat}",
                    params={"overview": "false"},
                )
                data = response.json()
                route = data.get("routes", [{}])[0]
                result = RouteResult(
                    origin=f"{origin_lat},{origin_lon}",
                    destination=f"{dest_lat},{dest_lon}",
                    mode=mode,
                    distance_km=route.get("distance", 0) / 1000,
                    duration_minutes=int(route.get("duration", 0) / 60),
                    fetched_at=datetime.now(UTC),
                )
                _set_cache(key, result.model_dump())
                return result
        except Exception as exc:
            logger.warning("Routing failed: %s", exc)
            return RouteResult(
                origin=f"{origin_lat},{origin_lon}",
                destination=f"{dest_lat},{dest_lon}",
                mode=mode,
                distance_km=0.0,
                duration_minutes=30,
                fetched_at=datetime.now(UTC),
            )
