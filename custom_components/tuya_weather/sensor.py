"""Sensor platform for Tuya Weather (read-only)."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
    EMPTY_SENSOR_VALUE,
    TEMP_DIVIDER,
    battery_code,
    hum_code,
    parse_calibration,
    temp_code,
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

    entities: list[SensorEntity] = []
    for sub in active_subdevices(data):
        entities.append(TuyaTempSensor(coordinator, sub))
        entities.append(TuyaHumSensor(coordinator, sub))
        if sub["has_battery"] and battery_code(sub["battery_index"]) in data:
            entities.append(TuyaBatterySensor(coordinator, sub))
        entities.append(TuyaAppliedTempOffset(coordinator, sub))
        entities.append(TuyaAppliedHumOffset(coordinator, sub))

    async_add_entities(entities)


class _Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TuyaWeatherCoordinator, sub: dict) -> None:
        super().__init__(coordinator)
        self._sub = sub
        self._device_id = coordinator.device_id
        self._attr_device_info = device_info_for(self._device_id, sub)

    @property
    def _status(self) -> dict:
        return self.coordinator.data or {}

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class TuyaTempSensor(_Base):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sub) -> None:
        super().__init__(coordinator, sub)
        key = sub["key"] or "main"
        self._attr_unique_id = f"{self._device_id}_{key}_temp"
        self._attr_name = "Température"

    @property
    def native_value(self) -> float | None:
        raw = self._status.get(temp_code(self._sub["key"]))
        try:
            val = int(raw)
        except (ValueError, TypeError):
            return None
        if val == EMPTY_SENSOR_VALUE:
            return None
        return round(val / TEMP_DIVIDER, 1)


class TuyaHumSensor(_Base):
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, sub) -> None:
        super().__init__(coordinator, sub)
        key = sub["key"] or "main"
        self._attr_unique_id = f"{self._device_id}_{key}_hum"
        self._attr_name = "Humidité"

    @property
    def native_value(self) -> int | None:
        raw = self._status.get(hum_code(self._sub["key"]))
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None


class TuyaBatterySensor(_Base):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["high", "medium", "low"]

    def __init__(self, coordinator, sub) -> None:
        super().__init__(coordinator, sub)
        key = sub["key"] or "main"
        self._attr_unique_id = f"{self._device_id}_{key}_battery"
        self._attr_name = "Batterie"
        self._index = sub["battery_index"]

    @property
    def native_value(self) -> str | None:
        raw = self._status.get(battery_code(self._index))
        if raw is None:
            return None
        val = str(raw).lower()
        return val if val in ("high", "medium", "low") else None

    @property
    def icon(self) -> str:
        return {
            "high": "mdi:battery",
            "medium": "mdi:battery-50",
            "low": "mdi:battery-20",
        }.get(self.native_value, "mdi:battery-unknown")


class _AppliedOffset(_Base):
    """Offset actuellement appliqué (lecture seule), pour affichage coloré."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _calib_code = ""
    _divider = 1

    def __init__(self, coordinator, sub) -> None:
        super().__init__(coordinator, sub)
        self._slot = sub["slot"]

    @property
    def native_value(self) -> float | None:
        vals = parse_calibration(self._status.get(self._calib_code))
        return round(vals[self._slot] / self._divider, 1)


class TuyaAppliedTempOffset(_AppliedOffset):
    _calib_code = CALIB_TEMP_CODE
    _divider = TEMP_DIVIDER
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-alert"

    def __init__(self, coordinator, sub) -> None:
        super().__init__(coordinator, sub)
        key = sub["key"] or "main"
        self._attr_unique_id = f"{self._device_id}_{key}_applied_temp_offset"
        self._attr_name = "Offset température appliqué"


class TuyaAppliedHumOffset(_AppliedOffset):
    _calib_code = CALIB_HUM_CODE
    _divider = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:water-alert"

    def __init__(self, coordinator, sub) -> None:
        super().__init__(coordinator, sub)
        key = sub["key"] or "main"
        self._attr_unique_id = f"{self._device_id}_{key}_applied_hum_offset"
        self._attr_name = "Offset humidité appliqué"
