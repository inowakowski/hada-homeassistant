"""Fixtures for the tests of the HADA integration."""

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.hada.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load the integration from custom_components."""


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    """The integration, set up as after "Add integration"."""
    config_entry = MockConfigEntry(domain=DOMAIN, title="HADA", data={})
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def connect_message(*entities: dict[str, Any], **device: Any) -> dict[str, Any]:
    """A hada/connect command for the computer "Laptop" with those entities."""
    return {
        "type": "hada/connect",
        "protocol": 1,
        "device": {"id": "laptop", "name": "Laptop", "app_version": "1.4.0", **device},
        "entities": list(entities),
    }


CPU = {
    "id": "cpu_load",
    "kind": "sensor",
    "name": "CPU load",
    "unit": "%",
    "state_class": "measurement",
    "icon": "mdi:cpu-64-bit",
    "state": 12.5,
    "attributes": {"cores": 8},
}

DISPLAY = {
    "id": "display_on",
    "kind": "binary_sensor",
    "name": "Display",
    "state": True,
}
