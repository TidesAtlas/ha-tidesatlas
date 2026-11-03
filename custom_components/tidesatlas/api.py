"""Small client for the free TidesAtlas widget feed (no API key)."""

from __future__ import annotations

from typing import Any

import aiohttp

from .const import API_BASE, LANGS


class TidesAtlasError(Exception):
    """Feed unreachable or answered with an error."""


class TidesAtlasClient:
    """Read places and tides from tidesatlas.com."""

    def __init__(self, session: aiohttp.ClientSession, language: str | None = None) -> None:
        self._session = session
        lang = (language or "en")[:2].lower()
        self._lang = lang if lang in LANGS else "en"

    async def _get(self, route: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "lang": self._lang}
        try:
            async with self._session.get(
                API_BASE + route,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": "HomeAssistant-TidesAtlas/1.0"},
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise TidesAtlasError(str(err)) from err
        if resp.status != 200 or not isinstance(data, dict):
            message = data.get("message") if isinstance(data, dict) else None
            raise TidesAtlasError(message or f"HTTP {resp.status}")
        return data

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Places whose name matches the text."""
        return (await self._get("ports", {"q": query}))["ports"]

    async def nearest(self, lat: float, lon: float) -> list[dict[str, Any]]:
        """Up to 5 places closest to a position."""
        return (await self._get("ports", {"lat": round(lat, 3), "lon": round(lon, 3)}))["ports"]

    async def tides(self, port_id: int) -> dict[str, Any]:
        """High and low tides of the next 3 days for one place."""
        return await self._get("tides", {"id": int(port_id)})
