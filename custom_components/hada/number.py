"""Numbers of a computer: values that can be set, such as the volume."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_SET, KIND_NUMBER
from .device import HadaConfigEntry
from .entity import HadaEntity, enum_or_none


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HadaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the numbers known so far, and say how more are added."""
    entry.runtime_data.async_register_platform(KIND_NUMBER, async_add_entities, HadaNumber)


class HadaNumber(HadaEntity, NumberEntity):
    """A number. It shows what the computer reports, never what it was just told."""

    def _apply(self, descriptor: dict[str, Any]) -> None:
        super()._apply(descriptor)
        self._attr_device_class = enum_or_none(NumberDeviceClass, descriptor.get("device_class"))
        self._attr_native_unit_of_measurement = descriptor.get("unit")

        # What the computer does not say is left to Home Assistant, which has its own defaults.
        for attribute, key in (
            ("_attr_native_min_value", "min"),
            ("_attr_native_max_value", "max"),
            ("_attr_native_step", "step"),
        ):
            if (value := descriptor.get(key)) is not None:
                setattr(self, attribute, value)

    @property
    def native_value(self) -> float | None:
        """What the computer reported, if it is a number."""
        state = self.reported.state
        if isinstance(state, bool) or not isinstance(state, (int, float)):
            return None
        return state

    async def async_set_native_value(self, value: float) -> None:
        """Tell the computer the wanted value."""
        await self._device.async_send_command(COMMAND_SET, self._entity_id, value=value)
