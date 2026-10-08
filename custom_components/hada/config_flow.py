"""Config flow of the HADA integration: there is nothing to enter, only to confirm."""

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class HadaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Adds the one entry that computers running HADA then register with."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to confirm, and make the entry."""
        if user_input is not None:
            return self.async_create_entry(title="HADA", data={})

        return self.async_show_form(step_id="user")
