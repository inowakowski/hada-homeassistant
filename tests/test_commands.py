"""Buttons, switches and numbers: what Home Assistant tells the computer, and what it does with the answer."""

from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import CPU, connect_message

LOCK = {"id": "lock_screen", "kind": "button", "name": "Lock screen", "icon": "mdi:lock"}
MUTE = {"id": "audio_mute", "kind": "switch", "name": "Mute", "state": False}
VOLUME = {
    "id": "volume_level",
    "kind": "number",
    "name": "Volume",
    "unit": "%",
    "min": 0,
    "max": 100,
    "step": 1,
    "state": 40,
}


async def connect(hass: HomeAssistant, hass_ws_client: WebSocketGenerator, *entities: dict[str, Any]) -> Any:
    """Connect the computer "Laptop" with those entities; returns the client, whose connect command has the id 1."""
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, **connect_message(*entities)})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    return client


async def answer(client: Any, command: dict[str, Any], message_id: int, **result: Any) -> None:
    """Answer a command as the computer does."""
    await client.send_json(
        {
            "id": message_id,
            "type": "hada/command_result",
            "device_id": "laptop",
            "command_id": command["event"]["command_id"],
            **result,
        }
    )
    assert (await client.receive_json())["success"]


async def test_pressing_a_button_tells_the_computer_and_waits_for_it(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """The command goes out on the connect subscription; the action is done when it is answered."""
    client = await connect(hass, hass_ws_client, LOCK)
    assert hass.states.get("button.laptop_lock_screen").state == STATE_UNKNOWN

    press = hass.async_create_task(
        hass.services.async_call("button", "press", {"entity_id": "button.laptop_lock_screen"}, blocking=True)
    )
    command = await client.receive_json()

    assert command["id"] == 1
    assert command["type"] == "event"
    assert command["event"]["command"] == "press"
    assert command["event"]["entity"] == "lock_screen"
    assert not press.done()

    await answer(client, command, 2, success=True)
    await press


async def test_a_switch_and_a_number_show_what_the_computer_reports_not_what_it_was_told(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Setting sends the wanted value; the state follows only the computer's own report."""
    client = await connect(hass, hass_ws_client, MUTE, VOLUME)
    volume = hass.states.get("number.laptop_volume")
    assert volume.state == "40"
    assert (volume.attributes["min"], volume.attributes["max"], volume.attributes["step"]) == (0, 100, 1)
    assert volume.attributes["unit_of_measurement"] == "%"
    assert hass.states.get("switch.laptop_mute").state == STATE_OFF

    turn_on = hass.async_create_task(
        hass.services.async_call("switch", "turn_on", {"entity_id": "switch.laptop_mute"}, blocking=True)
    )
    command = await client.receive_json()
    assert (command["event"]["command"], command["event"]["entity"], command["event"]["value"]) == (
        "set",
        "audio_mute",
        True,
    )
    await answer(client, command, 2, success=True)
    await turn_on
    assert hass.states.get("switch.laptop_mute").state == STATE_OFF

    set_value = hass.async_create_task(
        hass.services.async_call(
            "number", "set_value", {"entity_id": "number.laptop_volume", "value": 30}, blocking=True
        )
    )
    command = await client.receive_json()
    assert (command["event"]["command"], command["event"]["entity"], command["event"]["value"]) == (
        "set",
        "volume_level",
        30,
    )
    await answer(client, command, 3, success=True)
    await set_value
    assert hass.states.get("number.laptop_volume").state == "40"

    await client.send_json(
        {
            "id": 4,
            "type": "hada/update",
            "device_id": "laptop",
            "states": [{"id": "audio_mute", "state": True}, {"id": "volume_level", "state": 30}],
        }
    )
    assert (await client.receive_json())["success"]

    assert hass.states.get("switch.laptop_mute").state == STATE_ON
    assert hass.states.get("number.laptop_volume").state == "30"


async def test_a_command_the_computer_refuses_fails_the_action_with_its_reason(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """What the computer says went wrong is what the user is told."""
    client = await connect(hass, hass_ws_client, LOCK)

    press = hass.async_create_task(
        hass.services.async_call("button", "press", {"entity_id": "button.laptop_lock_screen"}, blocking=True)
    )
    command = await client.receive_json()
    await answer(client, command, 2, success=False, error="This entity is switched off")

    with pytest.raises(HomeAssistantError, match="This entity is switched off"):
        await press


async def test_a_computer_that_does_not_answer_fails_the_action(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Rather than leaving the action waiting for ever, or calling it done."""
    client = await connect(hass, hass_ws_client, LOCK)

    with (
        patch("custom_components.hada.const.COMMAND_TIMEOUT", 0.05),
        pytest.raises(HomeAssistantError, match="did not answer"),
    ):
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.laptop_lock_screen"}, blocking=True
        )

    # An answer that comes too late is taken without complaint.
    command = await client.receive_json()
    await answer(client, command, 2, success=True)


async def test_a_computer_that_leaves_before_answering_fails_the_action(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """The action does not wait out the 10 seconds for a computer that is gone."""
    client = await connect(hass, hass_ws_client, LOCK)

    press = hass.async_create_task(
        hass.services.async_call("button", "press", {"entity_id": "button.laptop_lock_screen"}, blocking=True)
    )
    await client.receive_json()
    await client.close()

    with pytest.raises(HomeAssistantError, match="went away"):
        await press


async def test_an_entity_that_changes_its_kind_is_made_anew(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """As when a computer that listed its switch as a binary sensor is updated."""
    client = await connect(
        hass, hass_ws_client, CPU, {"id": "audio_mute", "kind": "binary_sensor", "name": "Mute", "state": True}
    )
    assert hass.states.get("binary_sensor.laptop_mute").state == STATE_ON

    await client.send_json({"id": 2, **connect_message(CPU, {**MUTE, "state": True})})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert er.async_get(hass).async_get("binary_sensor.laptop_mute") is None
    assert hass.states.get("switch.laptop_mute").state == STATE_ON
