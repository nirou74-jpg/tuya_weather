"""Number platform: brouillons d'offset (non envoyés tant que pas 'Enregistrer')."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TuyaWeatherCoordinator
from .const import (
    CALIB_HUM_CODE,
    CALIB_TEMP_CODE,
    DOMAIN,
    HUM_OFFSET_MAX,
    HUM_OFFSET_MIN,
    TEMP_DIVIDER,
    TEMP_OFFSET_MAX,
    TEMP_OFFSET_MIN,
    parse_calibration,
)
from .helpers import active_subdevices, device_info_for


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TuyaWeatherCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}

    entities = []
    for sub in active_subdevices(data):
        entities.append(TuyaTempOffsetNumber(coordinator, sub))
        entities.append(TuyaHumOffsetNumber(coordinator, sub))
    async_add_entities(entities)


class _OffsetNumber(CoordinatorEntity, NumberEntity):
    """Brouillon d'offset. La valeur n'est PAS envoyée à l'appareil ;
    elle est mémorisée dans le coordinator jusqu'à appui sur 'Enregistrer'."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _draft_key = ""        # "temp" ou "hum"
    _calib_code = ""
    _divider = 1

    def __init__(self, coordinator: TuyaWeatherCoordinator, sub: dict) -> None:
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._sub = sub
        self._slot = sub["slot"]
        self._device_id = coordinator.device_id
        self._attr_device_info = device_info_for(self._device_id, sub)

    def _applied_value(self) -> int:
        vals = parse_calibration((self.coordinator.data or {}).get(self._calib_code))
        return vals[self._slot]

    @property
    def native_value(self) -> float:
        # Si un brouillon existe, on l'affiche ; sinon la valeur appliquée.
        draft = self.coordinator.draft.get(self._slot, {})
        if draft.get(self._draft_key) is not None:
            return round(draft[self._draft_key] / self._divider, 1)
        return round(self._applied_value() / self._divider, 1)

    async def async_set_native_value(self, value: float) -> None:
        # On mémorise seulement le brouillon (en unités entières appareil).
        raw = int(round(value * self._divider))
        self.coordinator.draft.setdefault(self._slot, {})[self._draft_key] = raw
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class TuyaTempOffsetNumber(_OffsetNumber):
    _draft_key = "temp"
    _calib_code = CALIB_TEMP_CODE
    _divider = TEMP_DIVIDER
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = TEMP_OFFSET_MIN / TEMP_DIVIDER  # -10.0
    _attr_native_max_value = TEMP_OFFSET_MAX / TEMP_DIVIDER  # +10.0
    _attr_native_step = 0.1
    _attr_icon = "mdi:thermometer-plus"

    def __init__(self, coordinator, sub) -> None:
        super().__init__(coordinator, sub)
        key = sub["key"] or "main"
        self._attr_unique_id = f"{self._device_id}_{key}_temp_offset_set"
        self._attr_name = "Réglage offset température"


class TuyaHumOffsetNumber(_OffsetNumber):
    _draft_key = "hum"
    _calib_code = CALIB_HUM_CODE
    _divider = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = HUM_OFFSET_MIN  # -20
    _attr_native_max_value = HUM_OFFSET_MAX  # +20
    _attr_native_step = 1
    _attr_icon = "mdi:water-plus"

    def __init__(self, coordinator, sub) -> None:
        super().__init__(coordinator, sub)
        key = sub["key"] or "main"
        self._attr_unique_id = f"{self._device_id}_{key}_hum_offset_set"
        self._attr_name = "Réglage offset humidité"
