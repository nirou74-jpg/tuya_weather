"""Utilitaires partagés : découverte des sous-capteurs actifs."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, EMPTY_SENSOR_VALUE, SUBDEVICES, temp_code


def active_subdevices(status: dict) -> list[dict]:
    """Retourne la liste des sous-appareils réellement présents.

    Un emplacement est actif si sa température n'est pas la valeur vide (-500).
    """
    result = []
    for sub in SUBDEVICES:
        raw = status.get(temp_code(sub["key"]))
        if raw is None:
            continue
        try:
            if int(raw) == EMPTY_SENSOR_VALUE:
                continue
        except (ValueError, TypeError):
            continue
        result.append(sub)
    return result


def device_info_for(device_id: str, sub: dict) -> DeviceInfo:
    """DeviceInfo commun à toutes les entités d'un même sous-capteur."""
    key = sub["key"] or "main"
    return DeviceInfo(
        identifiers={(DOMAIN, f"{device_id}_{key}")},
        name=sub["name"],
        manufacturer="Tuya",
        model="Weather sensor",
    )
