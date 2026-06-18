"""The Tuya Weather integration (read-only)."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CLIENT_ID,
    CONF_DEVICE_ID,
    CONF_REGION,
    CONF_SECRET_KEY,
    DEFAULT_REGION,
    DOMAIN,
    REGIONS,
    SCAN_INTERVAL_SECONDS,
)
from .tuya_api import TuyaApiError, TuyaClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.BUTTON]


class TuyaWeatherCoordinator(DataUpdateCoordinator):
    """Poll le status du device météo + gère les brouillons de calibration."""

    def __init__(self, hass: HomeAssistant, client: TuyaClient, device_id: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.device_id = device_id
        # Brouillons d'offset par slot : {slot: {"temp": int, "hum": int}}
        # Non envoyés tant que le bouton "Enregistrer" n'est pas pressé.
        self.draft: dict[int, dict[str, int | None]] = {}

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.get_status(self.device_id)
        except TuyaApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_send_commands(self, commands: list[dict]) -> None:
        await self.client.send_commands(self.device_id, commands)
        # L'API Cloud Tuya ne reflète pas la commande instantanément dans le
        # status : on laisse un court délai de propagation avant de relire,
        # sinon le refresh renvoie l'ancienne valeur.
        await asyncio.sleep(2)
        await self.async_request_refresh()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tuya Weather from a config entry."""
    region = entry.data.get(CONF_REGION, DEFAULT_REGION)
    base_url = REGIONS.get(region, REGIONS[DEFAULT_REGION])

    session = async_get_clientsession(hass)
    client = TuyaClient(
        session=session,
        base_url=base_url,
        client_id=entry.data[CONF_CLIENT_ID],
        secret_key=entry.data[CONF_SECRET_KEY],
    )

    coordinator = TuyaWeatherCoordinator(hass, client, entry.data[CONF_DEVICE_ID])
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
