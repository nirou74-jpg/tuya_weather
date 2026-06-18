"""Client minimal pour l'API Tuya OpenAPI (token + status + commands)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

EMPTY_BODY_SHA256 = hashlib.sha256(b"").hexdigest()


class TuyaApiError(Exception):
    """Erreur renvoyée par l'API Tuya."""


class TuyaAuthError(TuyaApiError):
    """Erreur d'authentification (client_id / secret_key invalides)."""


class TuyaClient:
    """Petit client Tuya gérant la signature et le cache de token."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        client_id: str,
        secret_key: str,
    ) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._client_id = client_id
        self._secret = secret_key
        self._access_token: str | None = None
        self._token_expire_at: float = 0.0

    # ------------------------------------------------------------------ #
    # Signature
    # ------------------------------------------------------------------ #
    def _sign(self, message: str) -> str:
        return (
            hmac.new(
                self._secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

    def _build_headers(
        self,
        method: str,
        path: str,
        body: str = "",
        with_token: bool = True,
    ) -> dict[str, str]:
        """Construit les en-têtes signés pour une requête.

        stringToSign = method + "\n" + sha256(body) + "\n" + "" + "\n" + path
        sign = HMAC-SHA256( client_id [+ access_token] + t [+ nonce] + stringToSign )
        """
        t = str(int(time.time() * 1000))
        content_sha = hashlib.sha256(body.encode("utf-8")).hexdigest() if body else EMPTY_BODY_SHA256
        string_to_sign = f"{method}\n{content_sha}\n\n{path}"

        if with_token and self._access_token:
            sign_str = self._client_id + self._access_token + t + string_to_sign
        else:
            sign_str = self._client_id + t + string_to_sign

        headers = {
            "client_id": self._client_id,
            "sign": self._sign(sign_str),
            "t": t,
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json",
        }
        if with_token and self._access_token:
            headers["access_token"] = self._access_token
        return headers

    # ------------------------------------------------------------------ #
    # Token
    # ------------------------------------------------------------------ #
    async def _ensure_token(self) -> None:
        if self._access_token and time.time() < self._token_expire_at - 60:
            return
        await self._fetch_token()

    async def _fetch_token(self) -> None:
        path = "/v1.0/token?grant_type=1"
        headers = self._build_headers("GET", path, with_token=False)
        url = self._base + path
        async with self._session.get(url, headers=headers) as resp:
            data = await resp.json()
        if not data.get("success"):
            code = data.get("code")
            msg = data.get("msg", "unknown")
            if code in (1004, 1010, 1013, 1106):
                raise TuyaAuthError(f"Tuya auth failed: {msg} (code {code})")
            raise TuyaApiError(f"Token error: {msg} (code {code})")
        result = data["result"]
        self._access_token = result["access_token"]
        # expire_time est en secondes
        self._token_expire_at = time.time() + int(result.get("expire_time", 7200))

    # ------------------------------------------------------------------ #
    # Requête générique authentifiée
    # ------------------------------------------------------------------ #
    async def _request(
        self, method: str, path: str, body: str = ""
    ) -> dict[str, Any]:
        await self._ensure_token()
        headers = self._build_headers(method, path, body=body, with_token=True)
        url = self._base + path
        async with self._session.request(
            method, url, headers=headers, data=body or None
        ) as resp:
            data = await resp.json()

        if not data.get("success"):
            code = data.get("code")
            # token expiré / invalide -> on retente une fois
            if code in (1010, 1011, 1004):
                await self._fetch_token()
                headers = self._build_headers(method, path, body=body, with_token=True)
                async with self._session.request(
                    method, url, headers=headers, data=body or None
                ) as resp2:
                    data = await resp2.json()
                if data.get("success"):
                    return data
            raise TuyaApiError(
                f"API error on {path}: {data.get('msg')} (code {data.get('code')})"
            )
        return data

    # ------------------------------------------------------------------ #
    # API publique
    # ------------------------------------------------------------------ #
    async def get_status(self, device_id: str) -> dict[str, Any]:
        """Retourne le status sous forme {code: value}."""
        path = f"/v1.0/devices/{device_id}/status"
        data = await self._request("GET", path)
        return {item["code"]: item["value"] for item in data.get("result", [])}

    async def send_commands(
        self, device_id: str, commands: list[dict[str, Any]]
    ) -> None:
        """Envoie une liste de commandes [{'code':..,'value':..}, ...]."""
        import json

        path = f"/v1.0/devices/{device_id}/commands"
        body = json.dumps({"commands": commands}, separators=(",", ":"))
        await self._request("POST", path, body=body)

    async def async_validate(self, device_id: str) -> None:
        """Valide les identifiants et l'accès au device (utilisé par le config flow)."""
        await self._fetch_token()
        await self.get_status(device_id)
