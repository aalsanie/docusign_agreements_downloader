from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from .auth import fetch_access_token, fetch_userinfo_account
from .client import ApiContext, DocuSignClient, ApiError
from .config import Settings
from .exporter import FilesystemExporter, safe_filename
from .models import Agreement, DocumentInfo, EnvelopeSummary, ExportedAgreement, DownloadResult
from .util import guess_extension


class AgreementDownloadService:
    """High-level orchestration: auth -> list envelopes -> list docs -> download -> export."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _http_client(self) -> httpx.Client:
        return httpx.Client(timeout=httpx.Timeout(self.settings.http_timeout_s))

    def _to_envelope_summary(self, raw: dict[str, Any]) -> EnvelopeSummary:
        env_id = raw.get("envelopeId") or raw.get("envelope_id")
        if not env_id:
            raise ValueError(f"Envelope missing envelopeId: {raw}")
        return EnvelopeSummary(
            envelope_id=str(env_id),
            status=str(raw.get("status") or ""),
            subject=raw.get("emailSubject") or raw.get("subject"),
            sender_email=raw.get("senderEmail"),
            sender_name=raw.get("senderName"),
            created_date_time=_parse_dt(raw.get("createdDateTime")),
            completed_date_time=_parse_dt(raw.get("completedDateTime")),
        )

    def _to_documents(self, raw_docs: list[dict[str, Any]]) -> list[DocumentInfo]:
        docs: list[DocumentInfo] = []
        for d in raw_docs:
            doc_id = d.get("documentId") or d.get("document_id")
            if doc_id is None:
                continue
            doc_id = str(doc_id)
            name = str(d.get("name") or d.get("documentName") or f"document_{doc_id}")
            docs.append(
                DocumentInfo(
                    document_id=doc_id,
                    name=name,
                    type=d.get("type"),
                    uri=d.get("uri"),
                    raw={k: v for k, v in d.items() if k not in {"documentId", "name", "type", "uri"}},
                )
            )
        return docs

    def download(
        self,
        out_dir: Path,
        from_date: str,
        to_date: Optional[str],
        status: str,
        page_size: int = 100,
    ) -> DownloadResult:
        started = datetime.now(tz=timezone.utc)
        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        exporter = FilesystemExporter(out_dir)

        exported: list[ExportedAgreement] = []
        failures: list[str] = []

        with self._http_client() as http:
            token = fetch_access_token(self.settings, http)
            acct = fetch_userinfo_account(self.settings, http, token)
            ctx = ApiContext(base_uri=acct.base_uri, account_id=acct.account_id)
            api = DocuSignClient(http=http, ctx=ctx, access_token=token.access_token)

            start_position = 0
            while True:
                page = api.list_envelopes(
                    from_date=from_date,
                    to_date=to_date,
                    status=status,
                    start_position=start_position,
                    page_size=page_size,
                )
                envelopes = page.get("envelopes") or []
                if not envelopes:
                    break

                for env in envelopes:
                    try:
                        env_summary = self._to_envelope_summary(env)
                        env_id = env_summary.envelope_id

                        agreement_dir, documents_dir, agreement_json = exporter.prepare_agreement_dirs(env_id)
                        exported_agreement = ExportedAgreement(
                            agreement=Agreement(envelope=env_summary, documents=[]),
                            agreement_dir=agreement_dir,
                            agreement_json_path=agreement_json,
                            documents_dir=documents_dir,
                        )

                        docs_payload = api.list_envelope_documents(env_id)
                        raw_docs = docs_payload.get("envelopeDocuments") or docs_payload.get("documents") or []
                        exported_agreement.agreement.documents = self._to_documents(raw_docs)

                        exporter.write_agreement_json(exported_agreement.agreement, agreement_json)

                        for doc in exported_agreement.agreement.documents:
                            resp = api.get_document_stream(env_id, doc.document_id)
                            ext = guess_extension(resp.headers.get("content-type"))
                            file_name = f"{doc.document_id}_{safe_filename(doc.name)}.{ext}"
                            out_path = documents_dir / file_name

                            with exporter.open_binary_for_write(out_path) as f:
                                for chunk in resp.iter_bytes():
                                    if chunk:
                                        f.write(chunk)
                            exported_agreement.downloaded_files.append(out_path)

                    except (ApiError, Exception) as e:
                        env_id = str(env.get("envelopeId") or "unknown")
                        msg = f"Envelope {env_id} failed: {e}"
                        failures.append(msg)
                        exported_agreement = ExportedAgreement(
                            agreement=Agreement(
                                envelope=EnvelopeSummary(envelope_id=env_id, status=str(env.get("status") or "")),
                                documents=[],
                            ),
                            agreement_dir=out_dir / env_id,
                            agreement_json_path=out_dir / env_id / "agreement.json",
                            documents_dir=out_dir / env_id / "documents",
                            failures=[msg],
                        )
                    exported.append(exported_agreement)

                # pagination: use DocuSign's startPosition/resultSetSize/totalSetSize when provided
                result_set_size = int(page.get("resultSetSize") or len(envelopes))
                total_set_size = int(page.get("totalSetSize") or (start_position + len(envelopes)))
                next_start = start_position + result_set_size
                if next_start >= total_set_size:
                    break
                start_position = next_start

        exporter.write_index(exported)
        finished = datetime.now(tz=timezone.utc)
        if exported and failures:
            status_out = "partial"
        elif exported and not failures:
            status_out = "ok"
        else:
            status_out = "failed"
        return DownloadResult(
            out_dir=out_dir,
            exported=exported,
            failures=failures,
            started_at=started,
            finished_at=finished,
            status=status_out,
        )


def _parse_dt(v: Any):
    if not v:
        return None
    try:
        s = str(v).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None
