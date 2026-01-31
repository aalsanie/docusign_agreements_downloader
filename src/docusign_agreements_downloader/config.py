from __future__ import annotations

from pathlib import Path
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables.

    Credentials are required (no defaults) to avoid unsafe assumptions.
    """

    model_config = SettingsConfigDict(env_prefix="DS_", case_sensitive=False)

    auth_server: AnyHttpUrl = Field(
        ...,
        description="DocuSign OAuth base URL (demo: https://account-d.docusign.com, prod: https://account.docusign.com)",
    )
    integration_key: str = Field(..., min_length=10, description="DocuSign integration key (client_id)")
    user_id: str = Field(..., min_length=10, description="DocuSign user GUID to impersonate (JWT grant)")
    private_key_pem_path: Path = Field(..., description="Path to RSA private key PEM for JWT signing")
    scopes: str = Field("signature impersonation", description="OAuth scopes (space-separated)")

    http_timeout_s: float = Field(30.0, ge=1.0, le=300.0, description="HTTP timeout (seconds)")

    def private_key_pem_bytes(self) -> bytes:
        p = self.private_key_pem_path.expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Private key PEM not found: {p}")
        return p.read_bytes()
