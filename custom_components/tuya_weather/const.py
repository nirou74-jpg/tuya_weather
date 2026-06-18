"""Constants for the Tuya Weather integration."""

DOMAIN = "tuya_weather"

CONF_CLIENT_ID = "client_id"
CONF_SECRET_KEY = "secret_key"
CONF_DEVICE_ID = "device_id"
CONF_REGION = "region"

REGIONS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}
DEFAULT_REGION = "eu"

SCAN_INTERVAL_SECONDS = 60

# Valeur renvoyée par un emplacement de capteur vide / non appairé
EMPTY_SENSOR_VALUE = -500

# Les températures sont renvoyées multipliées par 10 (251 => 25.1 °C)
TEMP_DIVIDER = 10

# Définition des "sous-appareils".
# key   : suffixe dans les codes du status ("" = station principale)
# name  : nom par défaut affiché (personnalisable par l'utilisateur ensuite)
# Chaque sous-appareil expose : température, humidité et (sauf station) batterie.
# slot : position dans les chaînes all_temp_calibration / all_hum_calibration
# (0 = station, 1 = sub1, ... 9 = sub9). Les chaînes ont 10 valeurs.
SUBDEVICES = [
    {"key": "", "name": "Station météo", "has_battery": False, "battery_index": None, "slot": 0},
    {"key": "sub1", "name": "Station météo – Capteur 1", "has_battery": True, "battery_index": 1, "slot": 1},
    {"key": "sub2", "name": "Station météo – Capteur 2", "has_battery": True, "battery_index": 2, "slot": 2},
    {"key": "sub3", "name": "Station météo – Capteur 3", "has_battery": True, "battery_index": 3, "slot": 3},
    {"key": "sub4", "name": "Station météo – Capteur 4", "has_battery": True, "battery_index": 4, "slot": 4},
    {"key": "sub5", "name": "Station météo – Capteur 5", "has_battery": True, "battery_index": 5, "slot": 5},
    {"key": "sub6", "name": "Station météo – Capteur 6", "has_battery": True, "battery_index": 6, "slot": 6},
    {"key": "sub7", "name": "Station météo – Capteur 7", "has_battery": True, "battery_index": 7, "slot": 7},
    {"key": "sub8", "name": "Station météo – Capteur 8", "has_battery": True, "battery_index": 8, "slot": 8},
    {"key": "sub9", "name": "Station météo – Capteur 9", "has_battery": True, "battery_index": 9, "slot": 9},
]

# Codes des chaînes de calibration (10 valeurs séparées par des virgules).
CALIB_TEMP_CODE = "all_temp_calibration"
CALIB_HUM_CODE = "all_hum_calibration"
CALIB_SLOTS = 10

# Bornes des offsets (valeurs entières envoyées à l'appareil).
# Température : 1 unité = 0,1 °C  → -100..+100 = -10..+10 °C
TEMP_OFFSET_MIN = -100
TEMP_OFFSET_MAX = 100
# Humidité : 1 unité = 1 %  → -20..+20 %
HUM_OFFSET_MIN = -20
HUM_OFFSET_MAX = 20


def parse_calibration(raw: str | None) -> list[int]:
    """Transforme '-3,7,0,...' en liste de 10 entiers (complète/tronque à 10)."""
    vals = [0] * CALIB_SLOTS
    if not raw:
        return vals
    parts = str(raw).split(",")
    for i in range(CALIB_SLOTS):
        if i < len(parts):
            try:
                vals[i] = int(float(parts[i]))
            except (ValueError, TypeError):
                vals[i] = 0
    return vals


def build_calibration(values: list[int]) -> str:
    """Transforme une liste d'entiers en chaîne '-3,7,0,...' de 10 valeurs."""
    v = list(values)[:CALIB_SLOTS]
    v += [0] * (CALIB_SLOTS - len(v))
    return ",".join(str(int(x)) for x in v)


def temp_code(key: str) -> str:
    """Code du status pour la température d'un sous-appareil."""
    return "temp_current" if key == "" else f"temp_current_{key}"


def hum_code(key: str) -> str:
    """Code du status pour l'humidité d'un sous-appareil."""
    return "humidity_value" if key == "" else f"humidity_value_{key}"


def battery_code(index: int) -> str:
    """Code du status pour la batterie (battery_percentage1..9)."""
    return f"battery_percentage{index}"
