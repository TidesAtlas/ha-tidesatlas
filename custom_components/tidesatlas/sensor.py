"""Tide sensors: next high tide, next low tide, tide height, trend, coefficient."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import TidesAtlasConfigEntry
from .const import ATTRIBUTION, DOMAIN
from .coordinator import TidesAtlasCoordinator, tide_state


@dataclass(frozen=True, kw_only=True)
class TideSensorDescription(SensorEntityDescription):
    """A tide sensor and how to read it from the tide state."""

    value: Callable[[dict[str, Any]], Any]
    attrs: Callable[[dict[str, Any]], dict[str, Any]] = lambda s: {}


SENSORS: tuple[TideSensorDescription, ...] = (
    TideSensorDescription(
        key="next_high_tide",
        translation_key="next_high_tide",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda s: s["next_high"].time if s["next_high"] else None,
        attrs=lambda s: {"height_m": s["next_high"].height, "coefficient": s["next_high"].coefficient} if s["next_high"] else {},
    ),
    TideSensorDescription(
        key="next_low_tide",
        translation_key="next_low_tide",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda s: s["next_low"].time if s["next_low"] else None,
        attrs=lambda s: {"height_m": s["next_low"].height} if s["next_low"] else {},
    ),
    TideSensorDescription(
        key="tide_height",
        translation_key="tide_height",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_display_precision=2,
        value=lambda s: s["height"],
    ),
    TideSensorDescription(
        key="tide_trend",
        translation_key="tide_trend",
        device_class=SensorDeviceClass.ENUM,
        options=["rising", "falling"],
        value=lambda s: s["trend"],
        attrs=lambda s: {
            "upcoming": [
                {"time": e.time.isoformat(), "type": e.kind, "height_m": e.height, **({"coefficient": e.coefficient} if e.coefficient else {})}
                for e in s["upcoming"]
            ]
        },
    ),
)

COEFFICIENT = TideSensorDescription(
    key="tide_coefficient",
    translation_key="tide_coefficient",
    state_class=SensorStateClass.MEASUREMENT,
    value=lambda s: s["next_high"].coefficient if s["next_high"] else None,
)


async def async_setup_entry(hass: HomeAssistant, entry: TidesAtlasConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Create the sensors of one place."""
    coordinator = entry.runtime_data
    descriptions = list(SENSORS)
    # The French tidal coefficient only exists for French ports.
    if any(e.coefficient is not None for e in coordinator.data["extremes"]):
        descriptions.append(COEFFICIENT)
    async_add_entities(TideSensor(coordinator, d) for d in descriptions)


class TideSensor(CoordinatorEntity[TidesAtlasCoordinator], SensorEntity):
    """One tide value, recomputed every 5 minutes between feed updates."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: TideSensorDescription

    def __init__(self, coordinator: TidesAtlasCoordinator, description: TideSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        port = coordinator.data["port"]
        self._attr_unique_id = f"{coordinator.port_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(coordinator.port_id))},
            name=port.get("name") or coordinator.config_entry.title,
            manufacturer="TidesAtlas",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=port.get("url"),
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_track_time_interval(self.hass, self._tick, timedelta(minutes=5)))

    @callback
    def _tick(self, _now: Any) -> None:
        self.async_write_ha_state()

    def _state(self) -> dict[str, Any]:
        now = dt_util.utcnow()
        extremes = self.coordinator.data["extremes"]
        state = tide_state(extremes, now)
        state["upcoming"] = [e for e in extremes if e.time > now][:6]
        return state

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self._state())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attrs(self._state())
