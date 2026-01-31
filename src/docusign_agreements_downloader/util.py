from __future__ import annotations

from typing import Optional


def guess_extension(content_type: Optional[str]) -> str:
    if not content_type:
        return "bin"
    ct = content_type.split(";")[0].strip().lower()
    return {
        "application/pdf": "pdf",
        "application/zip": "zip",
        "application/json": "json",
        "text/plain": "txt",
        "text/html": "html",
        "image/png": "png",
        "image/jpeg": "jpg",
    }.get(ct, "bin")
