"""Config flow for the Avantio integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import AvantioClient, CannotConnect, InvalidAuth
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete=CONF_USERNAME)
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete=CONF_PASSWORD)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    import aiohttp

    client = AvantioClient(username=data[CONF_USERNAME], password=data[CONF_PASSWORD])
    async with aiohttp.ClientSession() as session:
        is_signed_in = await client.sign_in(session)

    if is_signed_in is False:
        raise InvalidAuth


async def async_check_credentials(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> dict[str, str]:
    """Try to sign in, returning the form errors (empty when it worked)."""
    try:
        await validate_input(hass, user_input)
    except CannotConnect:
        return {"base": "cannot_connect"}
    except InvalidAuth:
        return {"base": "invalid_auth"}
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        return {"base": "unknown"}
    return {}


class AvantioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Avantio."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            errors = await async_check_credentials(self.hass, user_input)
            if not errors:
                if self.source == "reauth":
                    entry = self._get_reauth_entry()
                    return self.async_update_reload_and_abort(
                        entry, data=user_input
                    )
                return self.async_create_entry(
                    title=user_input["username"], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AvantioOptionsFlow:
        """Set the option flow to reconfigure the integration, for the given ConfigEntry."""
        return AvantioOptionsFlow()


class AvantioOptionsFlow(OptionsFlow):
    """Change the credentials of an Avantio account."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Check the new credentials, then save them and reload the entry."""
        errors = {}
        if user_input is not None:
            errors = await async_check_credentials(self.hass, user_input)
            if not errors:
                # The integration reads its credentials from the entry data,
                # so store them there rather than in the options.
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=user_input[CONF_USERNAME],
                    data={**self.config_entry.data, **user_input},
                )
                self.hass.config_entries.async_schedule_reload(
                    self.config_entry.entry_id
                )
                return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA,
                user_input
                or {CONF_USERNAME: self.config_entry.data.get(CONF_USERNAME, "")},
            ),
            errors=errors,
        )
