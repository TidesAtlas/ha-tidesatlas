"""Fetch tides and derive the current tide state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TidesAtlasClient, TidesAtlasError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class Extreme:
    """One high or low tide."""

    time: datetime
    kind: str  # "high" or "low"
    height: float
    coefficient: int | None


def parse_extremes(raw: list[dict[str, Any]]) -> list[Extreme]:
    """Feed rows to sorted Extreme objects."""
    out = [
        Extreme(
            time=datetime.fromtimestamp(int(row["timestamp"]), tz=timezone.utc),
            kind="high" if row.get("type") == "high" else "low",
            height=float(row["height_m"]),
            coefficient=int(row["coefficient"]) if row.get("coefficient") is not None else None,
        )
        for row in raw
    ]
    out.sort(key=lambda e: e.time)
    return out


def tide_state(extremes: list[Extreme], now: datetime) -> dict[str, Any]:
    """Next high/low tide, trend and estimated height at `now`.

    The height between two extremes follows the usual cosine curve, which is
    the standard way to estimate the water level between a high and a low tide.
    """
    nxt = next((e for e in extremes if e.time > now), None)
    prev = next((e for e in reversed(extremes) if e.time <= now), None)
    next_high = next((e for e in extremes if e.time > now and e.kind == "high"), None)
    next_low = next((e for e in extremes if e.time > now and e.kind == "low"), None)
    height = None
    trend = None
    if prev and nxt:
        span = (nxt.time - prev.time).total_seconds()
        frac = (now - prev.time).total_seconds() / span if span > 0 else 0.0
        height = round(nxt.height + (prev.height - nxt.height) * (1 + math.cos(math.pi * frac)) / 2, 2)
        trend = "rising" if nxt.kind == "high" else "falling"
    elif nxt:
        trend = "rising" if nxt.kind == "high" else "falling"
    return {
        "next": nxt,
        "previous": prev,
        "next_high": next_high,
        "next_low": next_low,
        "height": height,
        "trend": trend,
    }


class TidesAtlasCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the feed for one place."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: TidesAtlasClient, port_id: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{port_id}",
            update_interval=UPDATE_INTERVAL,
        )
        self._client = client
        self.port_id = port_id

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self._client.tides(self.port_id)
        except TidesAtlasError as err:
            raise UpdateFailed(f"TidesAtlas: {err}") from err
        return {"port": data.get("port", {}), "extremes": parse_extremes(data.get("extremes", []))}
