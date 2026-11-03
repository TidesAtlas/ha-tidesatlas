"""Constants for the TidesAtlas Tides integration."""

from datetime import timedelta

DOMAIN = "tidesatlas"
API_BASE = "https://tidesatlas.com/api/widget/v1/"
ATTRIBUTION = "Tide data by TidesAtlas (tidesatlas.com)"
CONF_PORT_ID = "port_id"
CONF_PORT_NAME = "port_name"
LANGS = ("en", "fr", "es", "it", "pt")
# The feed covers the next 3 days and is cached for 30 minutes on the server.
UPDATE_INTERVAL = timedelta(hours=2)
