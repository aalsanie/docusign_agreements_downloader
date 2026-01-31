from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Agreement, ExportedAgreement


_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def safe_filename(name: str, max_len: int = 120) -> str:
    cleaned = _SAFE.sub("_", name).strip("._-")
    if not cleaned:
        cleaned = "document"
    return cleaned[:max_len]


class FilesystemExporter:
    """Writes agreements and documents to disk in a predictable structure."""

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir.resolve()

    def prepare_agreement_dirs(self, envelope_id: str) -> tuple[Path, Path, Path]:
        agreement_dir = self.out_dir / envelope_id
        documents_dir = agreement_dir / "documents"
        agreement_dir.mkdir(parents=True, exist_ok=True)
        documents_dir.mkdir(parents=True, exist_ok=True)
        agreement_json = agreement_dir / "agreement.json"
        return agreement_dir, documents_dir, agreement_json

    def write_agreement_json(self, agreement: Agreement, agreement_json_path: Path) -> None:
        agreement_json_path.write_text(agreement.model_dump_json(indent=2), encoding="utf-8")

    def write_index(self, exported: list[ExportedAgreement]) -> Path:
        index_path = self.out_dir / "index.json"
        rows = []
        for e in exported:
            rows.append(
                {
                    "envelope_id": e.agreement.envelope.envelope_id,
                    "status": e.agreement.envelope.status,
                    "subject": e.agreement.envelope.subject,
                    "agreement_json": str(e.agreement_json_path),
                    "documents_dir": str(e.documents_dir),
                    "downloaded_files": [str(p) for p in e.downloaded_files],
                    "failures": e.failures,
                }
            )
        index_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return index_path

    def open_binary_for_write(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.open("wb")
