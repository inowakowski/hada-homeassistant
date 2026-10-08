"""Sensors of a computer."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .const import KIND_SENSOR
from .device import HadaConfigEntry
from .entity import HadaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HadaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the sensors known so far, and say how more are added."""
    entry.runtime_data.async_register_platform(
        KIND_SENSOR, async_add_entities, HadaSensor
    )


class HadaSensor(HadaEntity, SensorEntity):
    """A sensor: a number, a text or a time."""

    def _apply(self, descriptor: dict[str, Any]) -> None:
        super()._apply(descriptor)
        self._attr_device_class = _enum_or_none(
            SensorDeviceClass, descriptor.get("device_class")
        )
        self._attr_state_class = _enum_or_none(
            SensorStateClass, descriptor.get("state_class")
        )
        self._attr_native_unit_of_measurement = descriptor.get("unit")

    @property
    def native_value(self) -> StateType | date | datetime:
        """What the computer reported; a time is sent as text and read here."""
        state = self.reported.state
        if isinstance(state, bool):
            # A sensor has no truth values; this one should have been a binary sensor.
            return str(state).lower()

        if (
            self.device_class in (SensorDeviceClass.TIMESTAMP, SensorDeviceClass.DATE)
            and isinstance(state, str)
        ):
            if (timestamp := dt_util.parse_datetime(state)) is None:
                return None
            if self.device_class == SensorDeviceClass.DATE:
                return timestamp.date()
            return timestamp if timestamp.tzinfo else dt_util.as_utc(timestamp)

        return state


def _enum_or_none[T](enum: type[T], value: str | None) -> T | None:
    """The member of that name; None for none, and for a name Home Assistant does not know."""
    if not value:
        return None
    try:
        return enum(value.lower())  # type: ignore[call-arg]
    except ValueError:
        return None
