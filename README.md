# TidesAtlas Tides for Home Assistant

High and low tide times for **13,000+ ports, beaches and coastal towns in 180 countries**, in Home Assistant.

Free, no API key, no account.

## Sensors

For each place you add:

| Sensor | Example |
|---|---|
| Next high tide | `2026-11-03T14:03:00+00:00` (timestamp), with its height |
| Next low tide | `2026-11-03T21:01:00+00:00` (timestamp), with its height |
| Tide | `rising` / `falling`, with the next 6 high and low tides as attributes |
| Tide height | `6.8 m`, estimated between high and low tide (cosine curve) |
| Tide coefficient | `95` (French ports only) |

Data is refreshed every 2 hours; the state is recomputed every 5 minutes.

## Installation

### HACS

1. HACS > three dots > **Custom repositories** > add `https://github.com/TidesAtlas/ha-tidesatlas`, category **Integration**.
2. Install **TidesAtlas Tides** and restart Home Assistant.

### Manual

Copy `custom_components/tidesatlas` into your `config/custom_components/` folder and restart.

## Setup

**Settings > Devices & services > Add integration > TidesAtlas Tides.**

Type the name of a place, or leave the field empty to list the places closest to your home. Add the integration again for more places.

## Automation example

Turn on the garden lights 30 minutes before high tide:

```yaml
automation:
  - alias: "Before high tide"
    triggers:
      - trigger: template
        value_template: >
          {{ now() >= as_datetime(states('sensor.saint_malo_next_high_tide')) - timedelta(minutes=30) }}
    actions:
      - action: light.turn_on
        target:
          entity_id: light.garden
```

## Data

Tide predictions come from the free TidesAtlas widget feed (`https://tidesatlas.com/api/widget/v1/`): next 3 days, one place at a time. Only the place ID and your Home Assistant language are sent. For 14-day forecasts, weather, waves, sea temperature or any coordinates, see the [TidesAtlas API](https://tidesatlas.com/en/api/docs).

Tide times are predictions. **Not for navigation.**

## License

MIT
