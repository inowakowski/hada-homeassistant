"""What all entities of a computer have in common."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .device import EntityState, HadaDevice, unique_id

_LOGGER = logging.getLogger(__name__)


def enum_or_none[T](enum: type[T], value: str | None) -> T | None:
    """The member of that name; None for none, and for a name Home Assistant does not know.

    A class Home Assistant does not know costs the class, not the entity.
    """
    if not value:
        return None
    try:
        return enum(value.lower())  # type: ignore[call-arg]
    except ValueError:
        return None


class HadaEntity(Entity):
    """An entity a computer described, showing what the computer last reported for it."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: HadaDevice, descriptor: dict[str, Any]) -> None:
        """Set up from the descriptor the computer sent, or the one kept from last time."""
        self._device = device
        self._entity_id: str = descriptor["id"]
        self._attr_unique_id = unique_id(device.id, descriptor["id"])
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device.id)})
        self._attr_entity_registry_enabled_default = descriptor.get(
            "enabled_by_default", True
        )
        self._apply(descriptor)

    @property
    def reported(self) -> EntityState:
        """What the computer last reported for this entity; nothing, before it did."""
        return self._device.states.get(self._entity_id) or EntityState()

    @property
    def available(self) -> bool:
        """Whether the computer is connected and the source of this entity is there."""
        return self._device.connected and self.reported.available

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """The attributes the computer reported, if any."""
        return self.reported.attributes or None

    @callback
    def set_descriptor(self, descriptor: dict[str, Any]) -> None:
        """Take over a descriptor that may differ from the one the entity was made with."""
        self._apply(descriptor)

    def _apply(self, descriptor: dict[str, Any]) -> None:
        """Set the attributes that come from the descriptor. Platforms add their own."""
        self._attr_name = descriptor["name"]
        self._attr_icon = descriptor.get("icon")

    @callback
    def refresh(self) -> None:
        """Write the state, if the entity is part of Home Assistant by now."""
        if self.hass is None or not self.enabled:
            return
        try:
            self.async_write_ha_state()
        except ValueError as err:
            # E.g. a text reported by a sensor that says it measures something. One entity's
            # mistake must not cost the others their update.
            _LOGGER.warning(
                "%s of %s reported a state Home Assistant does not accept: %s",
                self._entity_id,
                self._device.name,
                err,
            )
