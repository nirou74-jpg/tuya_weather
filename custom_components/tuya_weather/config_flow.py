"""Config flow for Tuya Weather."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CLIENT_ID,
    CONF_DEVICE_ID,
    CONF_REGION,
    CONF_SECRET_KEY,
    DEFAULT_REGION,
    DOMAIN,
    REGIONS,
)
from .tuya_api import TuyaApiError, TuyaAuthError, TuyaClient


class TuyaWeatherConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya Weather."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            region = user_input.get(CONF_REGION, DEFAULT_REGION)
            session = async_get_clientsession(self.hass)
            client = TuyaClient(
                session=session,
                base_url=REGIONS[region],
                client_id=user_input[CONF_CLIENT_ID].strip(),
                secret_key=user_input[CONF_SECRET_KEY].strip(),
            )
            try:
                await client.async_validate(device_id)
            except TuyaAuthError:
                errors["base"] = "invalid_auth"
            except TuyaApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Station météo ({device_id[:8]}…)",
                    data={
                        CONF_CLIENT_ID: user_input[CONF_CLIENT_ID].strip(),
                        CONF_SECRET_KEY: user_input[CONF_SECRET_KEY].strip(),
                        CONF_DEVICE_ID: device_id,
                        CONF_REGION: region,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_SECRET_KEY): str,
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_REGION, default=DEFAULT_REGION): vol.In(
                    list(REGIONS.keys())
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
