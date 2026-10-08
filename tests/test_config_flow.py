"""Setting the integration up: one confirmation, once."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.hada.const import DOMAIN


async def test_the_user_confirms_and_the_entry_is_made(hass: HomeAssistant) -> None:
    """There is nothing to enter."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HADA"
    assert result["data"] == {}


async def test_it_is_set_up_only_once(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Computers are added to the one entry; a second makes no sense."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
