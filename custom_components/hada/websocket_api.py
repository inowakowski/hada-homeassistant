"""The commands computers running HADA send over Home Assistant's WebSocket API.

See PROTOCOL.md at the root of the repository.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    ERR_UNSUPPORTED_PROTOCOL,
    EVENT_HADA,
    EVENT_NAME_QUICK_ACTION,
    MAX_ENTITIES,
    MIN_PROTOCOL_VERSION,
    PROTOCOL_VERSION,
)
from .device import HadaData, HadaDevice

ID = vol.All(str, vol.Match(r"^[a-z0-9_]{1,64}$"))
NAME = vol.All(str, vol.Length(min=1, max=255))
TEXT = vol.All(str, vol.Length(max=255))
OPTIONAL_TEXT = vol.Any(None, TEXT)
OPTIONAL_NUMBER = vol.Any(None, vol.Coerce(float))
STATE = vol.Any(None, bool, int, float, TEXT)

# Fields this version does not know are dropped rather than refused, so that newer computers may send more.
ENTITY_SCHEMA = vol.Schema(
    {
        vol.Required("id"): ID,
        vol.Required("kind"): TEXT,
        vol.Required("name"): NAME,
        vol.Optional("icon"): OPTIONAL_TEXT,
        vol.Optional("device_class"): OPTIONAL_TEXT,
        vol.Optional("unit"): OPTIONAL_TEXT,
        vol.Optional("state_class"): OPTIONAL_TEXT,
        vol.Optional("min"): OPTIONAL_NUMBER,
        vol.Optional("max"): OPTIONAL_NUMBER,
        vol.Optional("step"): OPTIONAL_NUMBER,
        vol.Optional("enabled_by_default", default=True): bool,
        vol.Optional("state"): STATE,
        vol.Optional("attributes"): vol.Any(None, dict),
        vol.Optional("available", default=True): bool,
    },
    extra=vol.REMOVE_EXTRA,
)


def _no_id_twice(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Refuse a list that names an entity twice: which of the two is meant cannot be told."""
    ids = [entity["id"] for entity in entities]
    if len(set(ids)) != len(ids):
        raise vol.Invalid("two entities have the same id")
    return entities


ENTITIES_SCHEMA = vol.All(
    [ENTITY_SCHEMA], vol.Length(max=MAX_ENTITIES), _no_id_twice
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("id"): ID,
        vol.Required("name"): NAME,
        vol.Optional("app_version"): OPTIONAL_TEXT,
        vol.Optional("os"): OPTIONAL_TEXT,
        vol.Optional("os_version"): OPTIONAL_TEXT,
        vol.Optional("model"): OPTIONAL_TEXT,
    },
    extra=vol.REMOVE_EXTRA,
)

STATE_UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required("id"): ID,
        vol.Optional("state"): STATE,
        vol.Optional("attributes"): vol.Any(None, dict),
        vol.Optional("available"): bool,
    },
    extra=vol.REMOVE_EXTRA,
)


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    """Add the commands. They answer "not found" while the integration has no entry."""
    websocket_api.async_register_command(hass, handle_connect)
    websocket_api.async_register_command(hass, handle_entities)
    websocket_api.async_register_command(hass, handle_update)
    websocket_api.async_register_command(hass, handle_command_result)
    websocket_api.async_register_command(hass, handle_event)


def _data(hass: HomeAssistant) -> HadaData | None:
    """What the loaded entry holds; None while there is no entry, or it is not loaded."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    return None


def _connected_device(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> tuple[HadaData, HadaDevice] | None:
    """The device the message is about, if this connection is the one it is connected through.

    Answers the message with an error, and returns None, otherwise.
    """
    data = _data(hass)
    device = data.devices.get(msg["device_id"]) if data else None
    if data is None or device is None or device.connection is not connection:
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            "This connection is not connected as that device",
        )
        return None
    return data, device


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hada/connect",
        vol.Required("protocol"): vol.All(int, vol.Range(min=1)),
        vol.Required("device"): DEVICE_SCHEMA,
        vol.Required("entities"): ENTITIES_SCHEMA,
    }
)
@callback
def handle_connect(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """A computer connects: take over its entities, and show them as available until it leaves."""
    if (data := _data(hass)) is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "The HADA integration is not set up"
        )
        return

    if msg["protocol"] < MIN_PROTOCOL_VERSION:
        connection.send_error(
            msg["id"],
            ERR_UNSUPPORTED_PROTOCOL,
            f"Protocol {msg['protocol']} is no longer spoken; the oldest is {MIN_PROTOCOL_VERSION}",
        )
        return

    info: dict[str, Any] = msg["device"]
    device_id: str = info["id"]
    device = data.devices.get(device_id)
    if (
        device is not None
        and device.owner_user_id is not None
        and device.owner_user_id != connection.user.id
        and not connection.user.is_admin
    ):
        connection.send_error(
            msg["id"],
            websocket_api.ERR_UNAUTHORIZED,
            "This device belongs to another user",
        )
        return

    if device is None:
        device = data.devices[device_id] = HadaDevice(
            device_id, info["name"], connection.user.id
        )

    device.name = info["name"]
    device.info = {key: value for key, value in info.items() if key not in ("id", "name")}
    data.async_update_device_registry(device)

    # Connected before anything is written, so that the states written are those of a device that is there.
    device.async_connected(connection, msg["id"])
    ignored = data.async_set_entities(device, msg["entities"])

    @callback
    def disconnect() -> None:
        """The connection closed, or the computer unsubscribed."""
        # Unless the computer has connected anew since, through this or another connection.
        if device.connection is connection and device.subscription == msg["id"]:
            device.async_disconnected()

    connection.subscriptions[msg["id"]] = disconnect
    connection.send_result(
        msg["id"],
        {
            "protocol": min(msg["protocol"], PROTOCOL_VERSION),
            "integration_version": data.integration_version,
            "ignored": ignored,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hada/entities",
        vol.Required("device_id"): ID,
        vol.Required("entities"): ENTITIES_SCHEMA,
    }
)
@callback
def handle_entities(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """The entities of a connected computer changed; the list is complete, as when connecting."""
    if (found := _connected_device(hass, connection, msg)) is None:
        return

    data, device = found
    connection.send_result(
        msg["id"], {"ignored": data.async_set_entities(device, msg["entities"])}
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hada/update",
        vol.Required("device_id"): ID,
        vol.Required("states"): vol.All(
            [STATE_UPDATE_SCHEMA], vol.Length(max=MAX_ENTITIES)
        ),
    }
)
@callback
def handle_update(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Entities of a connected computer report: what is named changes, the rest stays."""
    if (found := _connected_device(hass, connection, msg)) is None:
        return

    _, device = found
    for update in msg["states"]:
        if (state := device.states.get(update["id"])) is None:
            continue
        if "state" in update:
            state.state = update["state"]
        if "attributes" in update:
            state.attributes = update["attributes"] or {}
        if "available" in update:
            state.available = update["available"]
        if (entity := device.entities.get(update["id"])) is not None:
            entity.refresh()

    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hada/command_result",
        vol.Required("device_id"): ID,
        vol.Required("command_id"): TEXT,
        vol.Required("success"): bool,
        vol.Optional("error"): OPTIONAL_TEXT,
    }
)
@callback
def handle_command_result(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """A connected computer says how a command it was sent went."""
    if (found := _connected_device(hass, connection, msg)) is None:
        return

    # An answer nobody waits for any more, as after the 10 seconds, is not an error of the computer's.
    found[1].async_command_answered(msg["command_id"], msg["success"], msg.get("error"))
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hada/event",
        vol.Required("device_id"): ID,
        vol.Required("name"): ID,
        vol.Required("value"): vol.All(str, vol.Match(r"^[A-Za-z0-9_.-]{1,64}$")),
    }
)
@callback
def handle_event(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Something happened on a connected computer: a quick action was chosen, a button of a notification pressed."""
    if (found := _connected_device(hass, connection, msg)) is None:
        return

    _, device = found
    if msg["name"] == EVENT_NAME_QUICK_ACTION and (entity := device.entities.get(msg["value"])):
        entity.async_happened()

    # For automations: the event HADA fires itself when it is connected without the integration.
    hass.bus.async_fire(
        EVENT_HADA,
        {"device_id": device.id, "name": msg["name"], "value": msg["value"]},
        context=connection.context(msg),
    )
    connection.send_result(msg["id"])
