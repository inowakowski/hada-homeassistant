"""HADA: computers running the Home Assistant Desktop App, as devices with their own entities.

The computers connect to Home Assistant's WebSocket API and describe themselves there; see
PROTOCOL.md at the root of the repository.
"""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .device import HadaConfigEntry, HadaData
from .websocket_api import async_register_commands

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Add the commands computers connect with; they live as long as Home Assistant runs."""
    async_register_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HadaConfigEntry) -> bool:
    """Read the computers seen before, and set their entities up as unavailable until they connect."""
    integration = await async_get_integration(hass, DOMAIN)
    data = HadaData(hass, entry, str(integration.version or "0.0.0"))
    await data.async_load()
    entry.runtime_data = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HadaConfigEntry) -> bool:
    """Unload the entities. Computers that are connected find the integration gone and connect anew later."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # What is waiting to be saved would be lost with this object otherwise.
        await entry.runtime_data.async_save()
        for device in entry.runtime_data.devices.values():
            device.entities.clear()
            device.async_disconnected()
    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: HadaConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Let a computer be deleted while it is away; one that is connected would only come back."""
    data = entry.runtime_data
    for domain, device_id in device_entry.identifiers:
        if domain != DOMAIN:
            continue
        if (device := data.devices.get(device_id)) is not None and device.connected:
            return False
        data.async_forget_device(device_id)
    return True
