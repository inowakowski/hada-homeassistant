"""Buttons of a computer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_PRESS, KIND_BUTTON
from .device import HadaConfigEntry
from .entity import HadaEntity, enum_or_none


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HadaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the buttons known so far, and say how more are added."""
    entry.runtime_data.async_register_platform(KIND_BUTTON, async_add_entities, HadaButton)


class HadaButton(HadaEntity, ButtonEntity):
    """A button: pressing it has the computer do something."""

    def _apply(self, descriptor: dict[str, Any]) -> None:
        super()._apply(descriptor)
        self._attr_device_class = enum_or_none(ButtonDeviceClass, descriptor.get("device_class"))

    async def async_press(self) -> None:
        """Tell the computer, and fail if it does not confirm."""
        await self._device.async_send_command(COMMAND_PRESS, self._entity_id)
