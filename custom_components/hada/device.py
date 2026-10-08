"""The computers that registered with the integration, and what is known about each."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    KIND_BINARY_SENSOR,
    KIND_SENSOR,
    MANUFACTURER,
    SAVE_DELAY,
    STORAGE_KEY,
    STORAGE_VERSION,
)

if TYPE_CHECKING:
    from .entity import HadaEntity

type HadaConfigEntry = ConfigEntry[HadaData]

# The kinds of entity this version makes, by the platform that makes them.
KINDS: tuple[str, ...] = (KIND_SENSOR, KIND_BINARY_SENSOR)

# What of a descriptor is kept between runs: what the entity is, not what it last reported.
DESCRIPTOR_KEYS = (
    "id",
    "kind",
    "name",
    "icon",
    "device_class",
    "unit",
    "state_class",
    "min",
    "max",
    "step",
    "enabled_by_default",
)


@dataclass
class EntityState:
    """What an entity last reported."""

    state: Any = None
    attributes: dict[str, Any] = field(default_factory=dict)
    available: bool = True


class HadaDevice:
    """One computer: its entities, their states, and whether it is connected."""

    def __init__(
        self,
        device_id: str,
        name: str,
        owner_user_id: str | None,
        info: dict[str, Any] | None = None,
    ) -> None:
        """Set up a device nothing is known about yet but who it is."""
        self.id = device_id
        self.name = name
        self.owner_user_id = owner_user_id
        self.info: dict[str, Any] = info or {}
        self.descriptors: dict[str, dict[str, Any]] = {}
        self.states: dict[str, EntityState] = {}
        self.entities: dict[str, HadaEntity] = {}

        # Identifies the connection the computer is connected through; None while it is away.
        self.connection: object | None = None

        # The id of the hada/connect command that connection was made with.
        self.subscription: int | None = None

    @property
    def connected(self) -> bool:
        """Whether the computer is connected right now."""
        return self.connection is not None

    @callback
    def refresh_entities(self) -> None:
        """Write the state of every entity, e.g. after the computer came or went."""
        for entity in self.entities.values():
            entity.refresh()


class HadaData:
    """Everything the config entry holds while it is loaded."""

    def __init__(
        self, hass: HomeAssistant, entry: HadaConfigEntry, integration_version: str
    ) -> None:
        """Set up empty; the devices are read by async_load."""
        self.hass = hass
        self.entry = entry
        self.integration_version = integration_version
        self.devices: dict[str, HadaDevice] = {}

        # Each platform leaves the way to add its entities here once it is set up.
        self.adders: dict[str, AddEntitiesCallback] = {}
        self.factories: dict[str, Callable[[HadaDevice, dict[str, Any]], HadaEntity]] = {}
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(self) -> None:
        """Read the devices seen before, so their entities exist while they are away."""
        stored = await self._store.async_load() or {}
        for device_id, saved in stored.get("devices", {}).items():
            device = HadaDevice(
                device_id, saved["name"], saved.get("owner"), saved.get("info")
            )
            device.descriptors = {
                descriptor["id"]: descriptor for descriptor in saved.get("entities", [])
            }
            self.devices[device_id] = device

    @callback
    def async_schedule_save(self) -> None:
        """Save the devices soon; several changes in a row are saved once."""
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    async def async_save(self) -> None:
        """Save the devices now, e.g. before the entry is unloaded and this object let go."""
        await self._store.async_save(self._data_to_save())

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "devices": {
                device.id: {
                    "name": device.name,
                    "owner": device.owner_user_id,
                    "info": device.info,
                    "entities": list(device.descriptors.values()),
                }
                for device in self.devices.values()
            }
        }

    @callback
    def async_register_platform(
        self,
        kind: str,
        add_entities: AddEntitiesCallback,
        factory: Callable[[HadaDevice, dict[str, Any]], HadaEntity],
    ) -> None:
        """Called by a platform: remember how to add its entities, and add those already known."""
        self.adders[kind] = add_entities
        self.factories[kind] = factory
        entities = []
        for device in self.devices.values():
            for descriptor in device.descriptors.values():
                if descriptor["kind"] == kind and descriptor["id"] not in device.entities:
                    entities.append(self._make_entity(device, descriptor))
        if entities:
            add_entities(entities)

    def _make_entity(self, device: HadaDevice, descriptor: dict[str, Any]) -> HadaEntity:
        entity = self.factories[descriptor["kind"]](device, descriptor)
        device.entities[descriptor["id"]] = entity
        return entity

    @callback
    def async_update_device_registry(self, device: HadaDevice) -> None:
        """Make the device known to Home Assistant, or bring what it shows of it up to date."""
        dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, device.id)},
            manufacturer=MANUFACTURER,
            name=device.name,
            model=device.info.get("model") or device.info.get("os"),
            sw_version=device.info.get("app_version"),
        )

    @callback
    def async_set_entities(
        self, device: HadaDevice, entities: list[dict[str, Any]]
    ) -> list[str]:
        """Make the device's entities those of the list, which is complete.

        Returns the ids of the entities left out for being of a kind this version does not know.
        """
        ignored: list[str] = []
        wanted: dict[str, dict[str, Any]] = {}
        for item in entities:
            if item["kind"] not in KINDS:
                ignored.append(item["id"])
                continue
            wanted[item["id"]] = item

        registry = er.async_get(self.hass)

        # Gone, or of another kind now: the entity is removed from Home Assistant.
        for entity_id in list(device.descriptors):
            descriptor = device.descriptors[entity_id]
            if entity_id in wanted and wanted[entity_id]["kind"] == descriptor["kind"]:
                continue
            del device.descriptors[entity_id]
            device.states.pop(entity_id, None)
            entity = device.entities.pop(entity_id, None)
            if entity is not None and entity.registry_entry is not None:
                registry.async_remove(entity.entity_id)
            elif registered := registry.async_get_entity_id(
                descriptor["kind"], DOMAIN, unique_id(device.id, entity_id)
            ):
                registry.async_remove(registered)

        added: dict[str, list[HadaEntity]] = {}
        for entity_id, item in wanted.items():
            descriptor = {key: item[key] for key in DESCRIPTOR_KEYS if key in item}
            device.descriptors[entity_id] = descriptor
            device.states[entity_id] = EntityState(
                item.get("state"), item.get("attributes") or {}, item.get("available", True)
            )
            if (entity := device.entities.get(entity_id)) is not None:
                entity.set_descriptor(descriptor)
            elif descriptor["kind"] in self.adders:
                added.setdefault(descriptor["kind"], []).append(
                    self._make_entity(device, descriptor)
                )

        for kind, new_entities in added.items():
            self.adders[kind](new_entities)

        device.refresh_entities()
        self.async_schedule_save()
        return ignored

    @callback
    def async_forget_device(self, device_id: str) -> None:
        """Called when the device was deleted in Home Assistant, which removed its entities."""
        if self.devices.pop(device_id, None) is not None:
            self.async_schedule_save()


def unique_id(device_id: str, entity_id: str) -> str:
    """The unique id of an entity: unique among all devices.

    Neither id has a dot in it, so no two pairs of ids make the same one.
    """
    return f"{device_id}.{entity_id}"
