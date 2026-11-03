"""Config flow and sensors, with the feed mocked from real responses."""

from datetime import datetime, timezone

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.tidesatlas.const import API_BASE, DOMAIN
from custom_components.tidesatlas.coordinator import parse_extremes, tide_state

from .conftest import load

TIDES = load("tides.json")


async def test_flow_search(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(API_BASE + "ports", json=load("search.json"))
    aioclient_mock.get(API_BASE + "tides", json=TIDES)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search": "saint malo"})
    assert result["step_id"] == "pick"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"port_id": "653"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"port_id": 653, "port_name": "Saint Malo"}


async def test_flow_near_home(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(API_BASE + "ports", json=load("nearest.json"))
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search": ""})
    assert result["step_id"] == "pick"
    assert "lat" in str(aioclient_mock.mock_calls[-1][1])


async def test_flow_no_results(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(API_BASE + "ports", json={"ports": []})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search": "zzzz"})
    assert result["errors"] == {"base": "no_results"}


async def test_flow_cannot_connect(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(API_BASE + "ports", status=500, json={"error": True})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search": "brest"})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_sensors(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory) -> None:
    ext = TIDES["extremes"]
    # Halfway between the first and second extremes.
    mid = (ext[0]["timestamp"] + ext[1]["timestamp"]) // 2
    freezer.move_to(datetime.fromtimestamp(mid, tz=timezone.utc))
    aioclient_mock.get(API_BASE + "tides", json=TIDES)
    entry = MockConfigEntry(domain=DOMAIN, unique_id="653", data={"port_id": 653, "port_name": "Saint Malo"}, title="Saint Malo")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = {s.entity_id: s for s in hass.states.async_all("sensor")}
    trend = states["sensor.saint_malo_tide"]
    height = next(s for e, s in states.items() if e.endswith("tide_height"))
    expected_trend = "rising" if ext[1]["type"] == "high" else "falling"
    assert trend.state == expected_trend
    assert abs(float(height.state) - (ext[0]["height_m"] + ext[1]["height_m"]) / 2) < 0.02
    nh = next(s for e, s in states.items() if e.endswith("next_high_tide"))
    first_high = next(x for x in ext if x["type"] == "high" and x["timestamp"] > mid)
    assert datetime.fromisoformat(nh.state).timestamp() == first_high["timestamp"]
    assert nh.attributes["height_m"] == first_high["height_m"]
    # French port: coefficient sensor exists
    assert any(e.endswith("tide_coefficient") for e in states)
    assert trend.attributes["attribution"].startswith("Tide data by TidesAtlas")


def test_tide_state_edges() -> None:
    ext = parse_extremes(TIDES["extremes"])
    before = tide_state(ext, ext[0].time.replace(year=2000))
    assert before["height"] is None and before["next"] == ext[0]
    after = tide_state(ext, ext[-1].time.replace(year=2100))
    assert after["next"] is None and after["trend"] is None
