"""Switches of a computer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_SET, KIND_SWITCH
from .device import HadaConfigEntry
from .entity import HadaEntity, enum_or_none


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HadaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the switches known so far, and say how more are added."""
    entry.runtime_data.async_register_platform(KIND_SWITCH, async_add_entities, HadaSwitch)


class HadaSwitch(HadaEntity, SwitchEntity):
    """A switch. It shows what the computer reports, never what it was just told."""

    def _apply(self, descriptor: dict[str, Any]) -> None:
        super()._apply(descriptor)
        self._attr_device_class = enum_or_none(SwitchDeviceClass, descriptor.get("device_class"))

    @property
    def is_on(self) -> bool | None:
        """What the computer reported, if it is a truth value."""
        state = self.reported.state
        return state if isinstance(state, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Tell the computer to switch it on."""
        await self._device.async_send_command(COMMAND_SET, self._entity_id, value=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Tell the computer to switch it off."""
        await self._device.async_send_command(COMMAND_SET, self._entity_id, value=False)
