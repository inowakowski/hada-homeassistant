"""Notifications sent to a computer, and what the computer says happened on it."""

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .test_commands import answer, connect

NOTIFICATION = {"id": "notification", "kind": "notify", "name": "Notification"}
TOGGLE_LAMP = {"id": "toggle_lamp", "kind": "event", "name": "Toggle lamp"}


async def send(hass: HomeAssistant, client: Any, message_id: int, service: tuple[str, str], data: dict[str, Any]) -> dict[str, Any]:
    """Call the action, answer the command it makes as the computer does, and return that command."""
    call = hass.async_create_task(
        hass.services.async_call(*service, {"entity_id": "notify.laptop_notification", **data}, blocking=True)
    )
    command = await client.receive_json()
    await answer(client, command, message_id, success=True)
    await call
    return command["event"]


async def test_send_message_shows_a_text_and_a_title(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """What Home Assistant's own action for notify entities can say."""
    client = await connect(hass, hass_ws_client, NOTIFICATION)

    command = await send(
        hass, client, 2, ("notify", "send_message"), {"message": "The washing machine is done.", "title": "Laundry"}
    )

    assert command["command"] == "notify"
    assert command["entity"] == "notification"
    assert command["message"] == "The washing machine is done."
    assert command["title"] == "Laundry"
    assert "data" not in command


async def test_hada_notify_carries_all_a_notification_may(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """The data goes to the computer as it is given, but for a picture that needs signing."""
    client = await connect(hass, hass_ws_client, NOTIFICATION)
    data = {
        "tag": "door",
        "url": "/lovelace/cameras",
        "sticky": True,
        "actions": [{"action": "open_door", "title": "Open"}],
        "image": "/api/camera_proxy/camera.front_door",
    }

    command = await send(
        hass, client, 2, ("hada", "notify"), {"message": "Someone is at the door.", "title": "Front door", "data": data}
    )

    assert command["message"] == "Someone is at the door."
    assert command["title"] == "Front door"
    assert {key: command["data"][key] for key in ("tag", "url", "sticky", "actions")} == {
        key: data[key] for key in ("tag", "url", "sticky", "actions")
    }

    # Good without an access token, for a while; still a path at this Home Assistant.
    assert command["data"]["image"].startswith("/api/camera_proxy/camera.front_door?authSig=")


@pytest.mark.parametrize("image", ["/local/door.jpg", "https://example.com/door.jpg", "//example.com/door.jpg"])
async def test_a_picture_that_is_public_or_elsewhere_is_left_as_it_is(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator, image: str
) -> None:
    """Only what needs signing in here is signed."""
    client = await connect(hass, hass_ws_client, NOTIFICATION)

    command = await send(hass, client, 2, ("hada", "notify"), {"message": "Hello", "data": {"image": image}})

    assert command["data"]["image"] == image


async def test_a_notification_the_computer_does_not_take_fails_the_action(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """As with any other command."""
    client = await connect(hass, hass_ws_client, NOTIFICATION)

    call = hass.async_create_task(
        hass.services.async_call(
            "hada", "notify", {"entity_id": "notify.laptop_notification", "message": "Hello"}, blocking=True
        )
    )
    command = await client.receive_json()
    await answer(client, command, 2, success=False, error="Nobody is signed in")

    with pytest.raises(HomeAssistantError, match="Nobody is signed in"):
        await call


async def test_a_quick_action_triggers_its_entity_and_fires_an_event(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Both ways to start an automation from it."""
    client = await connect(hass, hass_ws_client, TOGGLE_LAMP)
    events = async_capture_events(hass, "hada_event")
    assert hass.states.get("event.laptop_toggle_lamp").state == STATE_UNKNOWN

    await client.send_json(
        {"id": 2, "type": "hada/event", "device_id": "laptop", "name": "quick_action", "value": "toggle_lamp"}
    )
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    state = hass.states.get("event.laptop_toggle_lamp")
    assert state.state != STATE_UNKNOWN
    assert state.attributes["event_type"] == "pressed"
    assert [event.data for event in events] == [
        {"device_id": "laptop", "name": "quick_action", "value": "toggle_lamp"}
    ]


async def test_a_pressed_button_of_a_notification_and_what_is_not_known_fire_the_event(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """A newer HADA may report things this version has no entity for; automations still hear of them."""
    client = await connect(hass, hass_ws_client, NOTIFICATION)
    events = async_capture_events(hass, "hada_event")

    for message_id, (name, value) in enumerate(
        [("notification_action", "open_door"), ("something_new", "x.y-z"), ("quick_action", "no_such_entity")], start=2
    ):
        await client.send_json(
            {"id": message_id, "type": "hada/event", "device_id": "laptop", "name": name, "value": value}
        )
        assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert [(event.data["name"], event.data["value"]) for event in events] == [
        ("notification_action", "open_door"),
        ("something_new", "x.y-z"),
        ("quick_action", "no_such_entity"),
    ]


async def test_events_are_only_taken_from_the_computer_itself(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Another connection cannot say something happened on the computer."""
    await connect(hass, hass_ws_client, TOGGLE_LAMP)
    events = async_capture_events(hass, "hada_event")
    other = await hass_ws_client(hass)

    await other.send_json(
        {"id": 1, "type": "hada/event", "device_id": "laptop", "name": "quick_action", "value": "toggle_lamp"}
    )
    reply = await other.receive_json()
    await hass.async_block_till_done()

    assert reply["error"]["code"] == "not_found"
    assert events == []
