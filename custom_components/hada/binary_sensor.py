"""Binary sensors of a computer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import KIND_BINARY_SENSOR
from .device import HadaConfigEntry
from .entity import HadaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HadaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the binary sensors known so far, and say how more are added."""
    entry.runtime_data.async_register_platform(
        KIND_BINARY_SENSOR, async_add_entities, HadaBinarySensor
    )


class HadaBinarySensor(HadaEntity, BinarySensorEntity):
    """A binary sensor: on, off, or not known."""

    def _apply(self, descriptor: dict[str, Any]) -> None:
        super()._apply(descriptor)
        device_class = descriptor.get("device_class")
        try:
            self._attr_device_class = (
                BinarySensorDeviceClass(device_class.lower()) if device_class else None
            )
        except ValueError:
            # A class Home Assistant does not know costs the class, not the entity.
            self._attr_device_class = None

    @property
    def is_on(self) -> bool | None:
        """What the computer reported, if it is a truth value."""
        state = self.reported.state
        return state if isinstance(state, bool) else None
