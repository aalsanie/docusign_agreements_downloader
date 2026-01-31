from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DocuSignAccount(BaseModel):
    account_id: str
    base_uri: str


class OAuthToken(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(..., ge=1)


class EnvelopeSummary(BaseModel):
    envelope_id: str
    status: str
    subject: Optional[str] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    created_date_time: Optional[datetime] = None
    completed_date_time: Optional[datetime] = None


class DocumentInfo(BaseModel):
    document_id: str
    name: str
    type: Optional[str] = None
    uri: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Agreement(BaseModel):
    """Normalized domain model ('agreement' = one DocuSign envelope)."""

    envelope: EnvelopeSummary
    documents: list[DocumentInfo] = Field(default_factory=list)


class ExportedAgreement(BaseModel):
    agreement: Agreement
    agreement_dir: Path
    agreement_json_path: Path
    documents_dir: Path
    downloaded_files: list[Path] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)


class DownloadResult(BaseModel):
    out_dir: Path
    exported: list[ExportedAgreement] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime
    status: Literal["ok", "partial", "failed"]
