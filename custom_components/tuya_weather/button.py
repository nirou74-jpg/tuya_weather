"""Button platform: applique le brouillon d'offset (temp + hum) du capteur."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TuyaWeatherCoordinator
from .const import (
    CALIB_HUM_CODE,
    CALIB_TEMP_CODE,
    DOMAIN,
    build_calibration,
    parse_calibration,
)
from .helpers import active_subdevices, device_info_for

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TuyaWeatherCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}

    entities = []
    for sub in active_subdevices(data):
        entities.append(TuyaSaveCalibrationButton(coordinator, sub))
    async_add_entities(entities)


class TuyaSaveCalibrationButton(CoordinatorEntity, ButtonEntity):
    """Reconstruit les chaînes de calibration avec le brouillon de CE capteur
    et envoie l'appareil. Les autres positions sont préservées."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:content-save-check"

    def __init__(self, coordinator: TuyaWeatherCoordinator, sub: dict) -> None:
        super().__init__(coordinator)
        self._sub = sub
        self._slot = sub["slot"]
        self._device_id = coordinator.device_id
        self._attr_device_info = device_info_for(self._device_id, sub)
        key = sub["key"] or "main"
        self._attr_unique_id = f"{self._device_id}_{key}_save_calibration"
        self._attr_name = "Enregistrer la calibration"

    async def async_press(self) -> None:
        status = self.coordinator.data or {}
        draft = self.coordinator.draft.get(self._slot, {})

        commands = []

        # Température : on relit la chaîne actuelle, on remplace notre slot.
        temp_vals = parse_calibration(status.get(CALIB_TEMP_CODE))
        if draft.get("temp") is not None:
            temp_vals[self._slot] = draft["temp"]
            commands.append(
                {"code": CALIB_TEMP_CODE, "value": build_calibration(temp_vals)}
            )

        # Humidité : idem.
        hum_vals = parse_calibration(status.get(CALIB_HUM_CODE))
        if draft.get("hum") is not None:
            hum_vals[self._slot] = draft["hum"]
            commands.append(
                {"code": CALIB_HUM_CODE, "value": build_calibration(hum_vals)}
            )

        if commands:
            await self.coordinator.async_send_commands(commands)
            # Brouillon consommé : on le vide pour ce capteur.
            self.coordinator.draft.pop(self._slot, None)
