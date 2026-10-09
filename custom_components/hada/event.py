"""Events of a computer: things the user does there that automations can start from, such as quick actions."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import EVENT_TYPE_PRESSED, KIND_EVENT
from .device import HadaConfigEntry
from .entity import HadaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HadaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the events known so far, and say how more are added."""
    entry.runtime_data.async_register_platform(KIND_EVENT, async_add_entities, HadaEvent)


class HadaEvent(HadaEntity, EventEntity):
    """A quick action: its state is when it was last chosen."""

    _attr_event_types = [EVENT_TYPE_PRESSED]

    @callback
    def async_happened(self) -> None:
        """The quick action was chosen on the computer."""
        if self.hass is None or not self.enabled:
            return
        self._trigger_event(EVENT_TYPE_PRESSED)
        self.async_write_ha_state()
