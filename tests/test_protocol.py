"""What a computer running HADA can do over the WebSocket API, as PROTOCOL.md describes it."""

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.hada import async_remove_config_entry_device
from custom_components.hada.const import DOMAIN

from .conftest import CPU, DISPLAY, connect_message, find_device


async def test_connecting_makes_the_device_and_its_entities(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """A computer that connects shows up as a device, with its entities and their states."""
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(connect_message(CPU, DISPLAY, model="Windows computer"))
    answer = await client.receive_json()
    await hass.async_block_till_done()

    assert answer["success"], answer
    assert answer["result"]["protocol"] == 1
    assert answer["result"]["ignored"] == []
    assert answer["result"]["integration_version"]

    device = find_device(hass, entry, "laptop")
    assert device is not None
    assert device.name == "Laptop"
    assert device.manufacturer == "HADA"
    assert device.model == "Windows computer"
    assert device.sw_version == "1.4.0"

    cpu = hass.states.get("sensor.laptop_cpu_load")
    assert cpu is not None
    assert cpu.state == "12.5"
    assert cpu.attributes["unit_of_measurement"] == "%"
    assert cpu.attributes["state_class"] == "measurement"
    assert cpu.attributes["icon"] == "mdi:cpu-64-bit"
    assert cpu.attributes["cores"] == 8
    assert hass.states.get("binary_sensor.laptop_display").state == STATE_ON

    registry = er.async_get(hass)
    assert registry.async_get("sensor.laptop_cpu_load").unique_id == "laptop.cpu_load"
    assert registry.async_get("sensor.laptop_cpu_load").device_id == device.id


async def test_updates_change_what_they_name_and_leave_the_rest(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """An update carries what changed; attributes and availability stay unless given."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(connect_message(CPU, DISPLAY))
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    await client.send_json_auto_id(
        {
            "type": "hada/update",
            "device_id": "laptop",
            "states": [
                {"id": "cpu_load", "state": 14},
                {"id": "display_on", "state": False},
                {"id": "no_such_entity", "state": 1},
            ],
        }
    )
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert hass.states.get("sensor.laptop_cpu_load").state == "14"
    assert hass.states.get("sensor.laptop_cpu_load").attributes["cores"] == 8
    assert hass.states.get("binary_sensor.laptop_display").state == STATE_OFF

    await client.send_json_auto_id(
        {
            "type": "hada/update",
            "device_id": "laptop",
            "states": [
                {"id": "cpu_load", "available": False},
                {"id": "display_on", "state": None, "attributes": {"mode": "dimmed"}},
            ],
        }
    )
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert hass.states.get("sensor.laptop_cpu_load").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.laptop_display").state == STATE_UNKNOWN
    assert hass.states.get("binary_sensor.laptop_display").attributes["mode"] == "dimmed"


async def test_a_computer_that_leaves_is_unavailable_at_once(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """However the connection ends, the entities do not keep looking current."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(connect_message(CPU, DISPLAY))
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    await client.close()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.laptop_cpu_load").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.laptop_display").state == STATE_UNAVAILABLE

    # And back when it returns, through a new connection.
    again = await hass_ws_client(hass)
    await again.send_json_auto_id(connect_message(CPU, DISPLAY))
    assert (await again.receive_json())["success"]
    await hass.async_block_till_done()

    assert hass.states.get("sensor.laptop_cpu_load").state == "12.5"


async def test_unsubscribing_is_leaving_too(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """A computer can say it leaves without closing the connection."""
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, **connect_message(CPU)})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    await client.send_json({"id": 2, "type": "unsubscribe_events", "subscription": 1})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert hass.states.get("sensor.laptop_cpu_load").state == STATE_UNAVAILABLE

    await client.send_json(
        {"id": 3, "type": "hada/update", "device_id": "laptop", "states": [{"id": "cpu_load", "state": 1}]}
    )
    assert (await client.receive_json())["error"]["code"] == "not_found"


async def test_the_list_of_entities_is_complete(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """An entity that is no longer listed is removed, a new one added, an unknown kind left out."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(connect_message(CPU, DISPLAY))
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    await client.send_json_auto_id(
        {
            "type": "hada/entities",
            "device_id": "laptop",
            "entities": [
                {**CPU, "name": "Processor load", "unit": "percent"},
                {"id": "memory_usage", "kind": "sensor", "name": "Memory", "state": 40},
                {"id": "from_the_future", "kind": "hologram", "name": "Hologram"},
            ],
        }
    )
    answer = await client.receive_json()
    await hass.async_block_till_done()

    assert answer["result"]["ignored"] == ["from_the_future"]
    registry = er.async_get(hass)
    assert registry.async_get("binary_sensor.laptop_display") is None
    assert hass.states.get("binary_sensor.laptop_display") is None
    assert hass.states.get("sensor.laptop_memory").state == "40"

    # The entity keeps its id in Home Assistant; what describes it follows the computer.
    cpu = hass.states.get("sensor.laptop_cpu_load")
    assert cpu.attributes["friendly_name"] == "Laptop Processor load"
    assert cpu.attributes["unit_of_measurement"] == "percent"


async def test_entities_are_kept_while_the_computer_is_away_and_home_assistant_restarts(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """After a restart the entities are there, unavailable, until the computer connects."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(connect_message(CPU, DISPLAY))
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.laptop_cpu_load").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.laptop_display").state == STATE_UNAVAILABLE

    again = await hass_ws_client(hass)
    await again.send_json_auto_id(connect_message(CPU, DISPLAY))
    assert (await again.receive_json())["success"]
    await hass.async_block_till_done()

    assert hass.states.get("sensor.laptop_cpu_load").state == "12.5"
    assert len(er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)) == 2


async def test_what_home_assistant_does_not_know_costs_the_detail_not_the_entity(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Unknown classes are dropped; a time is read from its text; unknown fields are ignored."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        connect_message(
            {"id": "odd", "kind": "sensor", "name": "Odd", "device_class": "no_such_class", "state": "x"},
            {"id": "plugged", "kind": "binary_sensor", "name": "Plugged", "device_class": "PLUG", "state": True},
            {
                "id": "last_boot",
                "kind": "sensor",
                "name": "Last boot",
                "device_class": "timestamp",
                "state": "2026-10-03T08:00:00+02:00",
                "added_in_a_later_version": {"anything": 1},
            },
        )
    )
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert hass.states.get("sensor.laptop_odd").state == "x"
    assert "device_class" not in hass.states.get("sensor.laptop_odd").attributes
    assert hass.states.get("binary_sensor.laptop_plugged").attributes["device_class"] == "plug"
    assert hass.states.get("sensor.laptop_last_boot").state == "2026-10-03T06:00:00+00:00"


async def test_a_device_belongs_to_the_user_who_connected_it_first(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """Another user cannot connect under the id of someone's computer; an administrator can."""
    other = await hass_ws_client(hass, hass_read_only_access_token)
    await other.send_json_auto_id(connect_message(CPU, id="tablet", name="Tablet"))
    assert (await other.receive_json())["success"]
    await hass.async_block_till_done()

    owner = await hass_ws_client(hass)
    await owner.send_json_auto_id(connect_message(CPU))
    assert (await owner.receive_json())["success"]
    await hass.async_block_till_done()

    await other.send_json_auto_id(connect_message(CPU))
    answer = await other.receive_json()
    assert not answer["success"]
    assert answer["error"]["code"] == "unauthorized"
    assert hass.states.get("sensor.laptop_cpu_load").state == "12.5"

    # The administrator may take over the tablet, and is then the one it is connected through.
    await owner.send_json_auto_id(connect_message({**CPU, "state": 99}, id="tablet", name="Tablet"))
    assert (await owner.receive_json())["success"]
    await hass.async_block_till_done()
    await other.close()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.tablet_cpu_load").state == "99"


async def test_malformed_messages_are_refused(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Ids are ids, and no entity is named twice."""
    client = await hass_ws_client(hass)

    for message in (
        connect_message(CPU, id="Not An Id"),
        connect_message(CPU, CPU),
        connect_message({**CPU, "id": "Has Space"}),
        {**connect_message(CPU), "protocol": 0},
    ):
        await client.send_json_auto_id(message)
        answer = await client.receive_json()
        assert not answer["success"], message
        assert answer["error"]["code"] == "invalid_format"

    assert find_device(hass, entry, "laptop") is None


async def test_without_an_entry_the_commands_say_so(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Installed but not set up: the computer is told, rather than left guessing."""
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(connect_message(CPU))
    answer = await client.receive_json()

    assert not answer["success"]
    assert answer["error"]["code"] == "not_found"


async def test_a_device_can_be_deleted_while_it_is_away(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Deleting gives the device id up; a connected computer would only come back."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(connect_message(CPU))
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    device = find_device(hass, entry, "laptop")

    assert not await async_remove_config_entry_device(hass, entry, device)

    await client.close()
    await hass.async_block_till_done()

    assert await async_remove_config_entry_device(hass, entry, device)
    assert "laptop" not in entry.runtime_data.devices
