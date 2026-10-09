"""Notifications shown on a computer."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.http.auth import async_sign_path
from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_NOTIFY, KIND_NOTIFY, SERVICE_NOTIFY, SIGNED_PATH_SECONDS
from .device import HadaConfigEntry
from .entity import HadaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HadaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the notify entities known so far, say how more are added, and add the action that takes all of a notification."""
    entry.runtime_data.async_register_platform(KIND_NOTIFY, async_add_entities, HadaNotify)

    # notify.send_message takes a text and a title. This one takes what a phone's notification does.
    entity_platform.async_get_current_platform().async_register_entity_service(
        SERVICE_NOTIFY,
        {
            vol.Required("message"): cv.string,
            vol.Optional("title"): cv.string,
            vol.Optional("data"): dict,
        },
        "async_notify",
    )


class HadaNotify(HadaEntity, NotifyEntity):
    """Shows notifications on the computer."""

    _attr_supported_features = NotifyEntityFeature.TITLE

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Show a text, with a title if there is one: what notify.send_message can say."""
        await self.async_notify(message, title)

    async def async_notify(
        self, message: str, title: str | None = None, data: dict[str, Any] | None = None
    ) -> None:
        """Show a notification with all it may carry; see PROTOCOL.md for what the computer makes of it."""
        fields: dict[str, Any] = {"message": message}
        if title:
            fields["title"] = title
        if data:
            fields["data"] = self._with_signed_picture(data)
        await self._device.async_send_command(COMMAND_NOTIFY, self._entity_id, **fields)

    def _with_signed_picture(self, data: dict[str, Any]) -> dict[str, Any]:
        """Sign the address of a picture that is a path here, so the computer gets it without a token.

        A camera's picture, say, is only given to who is signed in; the computer fetches the picture
        as nobody. Signed, the address is good for a minute. What is public anyway is left alone.
        """
        image = data.get("image")
        if (
            not isinstance(image, str)
            or not image.startswith("/")
            or image.startswith(("//", "/local/"))
        ):
            return data

        try:
            signed = async_sign_path(
                self.hass, image, timedelta(seconds=SIGNED_PATH_SECONDS)
            )
        except KeyError:
            # No user to sign as, which happens while Home Assistant is still being set up for the first time.
            return data
        return {**data, "image": signed}
