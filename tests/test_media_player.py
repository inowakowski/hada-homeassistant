"""The media player: what the computer reports about what is playing, and what it is told to do."""

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant

from .test_commands import answer, connect

PLAYER = {
    "id": "media_player",
    "kind": "media_player",
    "name": "Media player",
    "icon": "mdi:play-box-outline",
    "features": [
        "play",
        "pause",
        "play_pause",
        "next",
        "previous",
        "stop",
        "volume_set",
        "volume_mute",
        "something_newer",
    ],
    "state": "playing",
    "attributes": {
        "title": "Song",
        "artist": "Band",
        "album": "Record",
        "app": "Spotify.exe",
        "volume": 40,
        "muted": False,
    },
}

ENTITY_ID = "media_player.laptop_media_player"


async def test_the_media_player_shows_what_the_computer_reports(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """What plays and how loud are the media player's own attributes, and its controls those it was said to have."""
    client = await connect(hass, hass_ws_client, PLAYER)

    state = hass.states.get(ENTITY_ID)
    assert state.state == "playing"
    assert state.attributes["media_title"] == "Song"
    assert state.attributes["media_artist"] == "Band"
    assert state.attributes["media_album_name"] == "Record"
    assert state.attributes["app_name"] == "Spotify.exe"
    assert state.attributes["volume_level"] == 0.4
    assert state.attributes["is_volume_muted"] is False
    assert "title" not in state.attributes

    features = MediaPlayerEntityFeature(state.attributes["supported_features"])
    for feature in (
        MediaPlayerEntityFeature.PLAY,
        MediaPlayerEntityFeature.PAUSE,
        MediaPlayerEntityFeature.NEXT_TRACK,
        MediaPlayerEntityFeature.PREVIOUS_TRACK,
        MediaPlayerEntityFeature.STOP,
        MediaPlayerEntityFeature.VOLUME_SET,
        MediaPlayerEntityFeature.VOLUME_MUTE,
    ):
        assert feature in features
    assert MediaPlayerEntityFeature.SEEK not in features

    await client.send_json(
        {
            "id": 2,
            "type": "hada/update",
            "device_id": "laptop",
            "states": [{"id": "media_player", "state": "stopped", "attributes": {"volume": 55, "muted": True}}],
        }
    )
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.state == "idle"
    assert state.attributes["volume_level"] == 0.55
    assert state.attributes["is_volume_muted"] is True
    assert "media_title" not in state.attributes


async def test_what_is_done_with_the_media_player_is_told_to_the_computer(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Each control sends its action; the volume goes out from 0 to 100, as the computer counts it."""
    client = await connect(hass, hass_ws_client, PLAYER)

    calls = [
        ("media_next_track", {}, {"action": "next"}),
        ("media_previous_track", {}, {"action": "previous"}),
        ("media_play", {}, {"action": "play"}),
        ("media_pause", {}, {"action": "pause"}),
        ("media_play_pause", {}, {"action": "play_pause"}),
        ("media_stop", {}, {"action": "stop"}),
        ("volume_set", {"volume_level": 0.3}, {"action": "volume_set", "value": 30}),
        ("volume_mute", {"is_volume_muted": True}, {"action": "volume_mute", "value": True}),
    ]
    for number, (service, data, expected) in enumerate(calls):
        call = hass.async_create_task(
            hass.services.async_call(
                "media_player", service, {"entity_id": ENTITY_ID, **data}, blocking=True
            )
        )
        command = await client.receive_json()
        assert command["event"]["command"] == "media", service
        assert command["event"]["entity"] == "media_player"
        for key, value in expected.items():
            assert command["event"][key] == value, service
        await answer(client, command, number + 2, success=True)
        await call

    # Told to play, it still shows what the computer last reported.
    assert hass.states.get(ENTITY_ID).state == "playing"
