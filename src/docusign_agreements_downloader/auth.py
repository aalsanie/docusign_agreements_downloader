from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import jwt

from .config import Settings
from .models import DocuSignAccount, OAuthToken


class AuthError(RuntimeError):
    pass


def _now_epoch() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


def build_jwt_assertion(settings: Settings) -> str:
    """Build a JWT assertion for DocuSign JWT Grant (RS256)."""
    iat = _now_epoch()
    exp = iat + 3600  # DocuSign expects <= 1 hour
    payload: dict[str, Any] = {
        "iss": settings.integration_key,
        "sub": settings.user_id,
        "aud": str(settings.auth_server),
        "iat": iat,
        "exp": exp,
        "scope": settings.scopes,
    }
    token = jwt.encode(payload, settings.private_key_pem_bytes(), algorithm="RS256")
    return token.decode("utf-8") if isinstance(token, bytes) else token


def fetch_access_token(settings: Settings, client: httpx.Client) -> OAuthToken:
    assertion = build_jwt_assertion(settings)
    url = f"{str(settings.auth_server).rstrip('/')}/oauth/token"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }
    resp = client.post(url, data=data)
    if resp.status_code >= 400:
        raise AuthError(f"Token request failed ({resp.status_code}): {resp.text}")
    return OAuthToken.model_validate(resp.json())


def fetch_userinfo_account(settings: Settings, client: httpx.Client, token: OAuthToken) -> DocuSignAccount:
    url = f"{str(settings.auth_server).rstrip('/')}/oauth/userinfo"
    resp = client.get(url, headers={"Authorization": f"Bearer {token.access_token}"})
    if resp.status_code >= 400:
        raise AuthError(f"Userinfo request failed ({resp.status_code}): {resp.text}")
    body = resp.json()
    accounts = body.get("accounts") or []
    if not accounts:
        raise AuthError("No accounts returned from /oauth/userinfo")
    acct = next((a for a in accounts if a.get("is_default") is True), accounts[0])
    base_uri = acct.get("base_uri") or acct.get("baseUri")
    account_id = acct.get("account_id") or acct.get("accountId")
    if not base_uri or not account_id:
        raise AuthError(f"userinfo missing base_uri/account_id: {acct}")
    return DocuSignAccount(account_id=str(account_id), base_uri=str(base_uri))
