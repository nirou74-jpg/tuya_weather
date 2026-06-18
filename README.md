# Tuya Weather — Home Assistant

Intégration pour une station météo Tuya et ses capteurs déportés (température / humidité / batterie), via l'API Cloud Tuya OpenAPI. **Un appareil par capteur**, pour un affichage unifié par pièce.

## Fonctionnalités

Lecture (`/v1.0/devices/{device_id}/status`) :
- Température (valeur ×10 → divisée par 10 → °C)
- Humidité (%)
- Batterie (qualitatif : high / medium / low) — sauf la station
- Offset de calibration appliqué (température et humidité), en lecture, pour affichage

Écriture (calibration) : chaque appareil possède un **réglage d'offset** température et humidité (brouillon), et un **bouton « Enregistrer »**. À l'appui, l'intégration relit la chaîne `all_temp_calibration` / `all_hum_calibration`, remplace **uniquement la position du capteur concerné**, et renvoie la chaîne complète — les autres capteurs sont préservés.

Important : la mesure renvoyée par l'appareil **inclut déjà** l'offset ; l'intégration n'ajoute jamais l'offset à la mesure. L'offset n'est exposé que pour information / réglage.

Les emplacements vides (valeur `-500`) sont ignorés automatiquement.

## Bornes de calibration
- Température : −10 à +10 °C (pas 0,1)
- Humidité : −20 à +20 %

## Prérequis
Compte Tuya IoT Platform, station liée au projet, et **Access ID** (`client_id`), **Access Secret** (`secret_key`), **Device ID**.

## Installation
Via HACS (dépôt personnalisé, type Integration) puis redémarrage. Configuration via Paramètres → Appareils et services → Ajouter → Tuya Weather.

## Licence
MIT
