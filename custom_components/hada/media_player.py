"""The media player of a computer: what is playing and how loud, and the controls for it."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_MEDIA, KIND_MEDIA_PLAYER
from .device import HadaConfigEntry
from .entity import HadaEntity

# What the computer says it can be told, and the control Home Assistant then offers.
FEATURES: dict[str, MediaPlayerEntityFeature] = {
    "play": MediaPlayerEntityFeature.PLAY,
    "pause": MediaPlayerEntityFeature.PAUSE,
    "next": MediaPlayerEntityFeature.NEXT_TRACK,
    "previous": MediaPlayerEntityFeature.PREVIOUS_TRACK,
    "stop": MediaPlayerEntityFeature.STOP,
    "volume_set": MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP,
    "volume_mute": MediaPlayerEntityFeature.VOLUME_MUTE,
}

# The computer says "stopped" for an app that has something loaded and is not playing it, and "idle"
# when no app offers media controls; Home Assistant has one word for both.
STATES: dict[str, MediaPlayerState] = {
    "playing": MediaPlayerState.PLAYING,
    "paused": MediaPlayerState.PAUSED,
    "stopped": MediaPlayerState.IDLE,
    "idle": MediaPlayerState.IDLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HadaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the media players known so far, and say how more are added."""
    entry.runtime_data.async_register_platform(
        KIND_MEDIA_PLAYER, async_add_entities, HadaMediaPlayer
    )


class HadaMediaPlayer(HadaEntity, MediaPlayerEntity):
    """A media player. It shows what the computer reports, never what it was just told."""

    def _apply(self, descriptor: dict[str, Any]) -> None:
        super()._apply(descriptor)
        features = MediaPlayerEntityFeature(0)
        for name in descriptor.get("features") or []:
            # A control this version does not know is left out, not refused.
            features |= FEATURES.get(name, MediaPlayerEntityFeature(0))
        self._attr_supported_features = features

    def _reported(self, key: str) -> Any:
        return self.reported.attributes.get(key)

    @property
    def state(self) -> MediaPlayerState | None:
        """Playing, paused or idle, as the computer reported it."""
        state = self.reported.state
        return STATES.get(state) if isinstance(state, str) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Nothing: what the computer reports is shown as the media player's own attributes."""
        return None

    @property
    def media_title(self) -> str | None:
        """The title of what is playing."""
        title = self._reported("title")
        return title if isinstance(title, str) else None

    @property
    def media_artist(self) -> str | None:
        """Who it is by."""
        artist = self._reported("artist")
        return artist if isinstance(artist, str) else None

    @property
    def media_album_name(self) -> str | None:
        """The album it is from."""
        album = self._reported("album")
        return album if isinstance(album, str) else None

    @property
    def app_name(self) -> str | None:
        """The app that plays it, as the computer names it."""
        app = self._reported("app")
        return app if isinstance(app, str) else None

    @property
    def volume_level(self) -> float | None:
        """The volume, which the computer reports from 0 to 100, as Home Assistant wants it: from 0 to 1."""
        volume = self._reported("volume")
        if isinstance(volume, bool) or not isinstance(volume, (int, float)):
            return None
        return min(max(volume / 100, 0.0), 1.0)

    @property
    def is_volume_muted(self) -> bool | None:
        """Whether the sound is muted."""
        muted = self._reported("muted")
        return muted if isinstance(muted, bool) else None

    async def _async_tell(self, action: str, **fields: Any) -> None:
        await self._device.async_send_command(
            COMMAND_MEDIA, self._entity_id, action=action, **fields
        )

    async def async_media_play(self) -> None:
        """Tell the computer to play."""
        await self._async_tell("play")

    async def async_media_pause(self) -> None:
        """Tell the computer to pause."""
        await self._async_tell("pause")

    async def async_media_play_pause(self) -> None:
        """Tell the computer to play if it is paused, and to pause if it is playing."""
        await self._async_tell("play_pause")

    async def async_media_next_track(self) -> None:
        """Tell the computer to go to the next track."""
        await self._async_tell("next")

    async def async_media_previous_track(self) -> None:
        """Tell the computer to go to the previous track."""
        await self._async_tell("previous")

    async def async_media_stop(self) -> None:
        """Tell the computer to stop."""
        await self._async_tell("stop")

    async def async_set_volume_level(self, volume: float) -> None:
        """Tell the computer how loud, from 0 to 100."""
        await self._async_tell("volume_set", value=round(volume * 100))

    async def async_mute_volume(self, mute: bool) -> None:
        """Tell the computer to mute, or to unmute."""
        await self._async_tell("volume_mute", value=mute)
