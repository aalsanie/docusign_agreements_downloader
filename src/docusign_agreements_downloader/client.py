from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


class ApiError(RuntimeError):
    pass


class TransientApiError(ApiError):
    pass


def _is_transient_status(code: int) -> bool:
    return code in (408, 409, 425, 429, 500, 502, 503, 504)


@dataclass(frozen=True)
class ApiContext:
    base_uri: str
    account_id: str


class DocuSignClient:
    """Thin DocuSign eSignature REST client with retries for transient failures."""

    def __init__(self, http: httpx.Client, ctx: ApiContext, access_token: str):
        self._http = http
        self._ctx = ctx
        self._access_token = access_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"}

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        msg = f"{resp.request.method} {resp.request.url} -> {resp.status_code}: {resp.text}"
        if _is_transient_status(resp.status_code):
            raise TransientApiError(msg)
        raise ApiError(msg)

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, TransientApiError)),
        stop=stop_after_attempt(7),
        wait=wait_exponential_jitter(initial=0.5, max=30.0),
        reraise=True,
    )
    def list_envelopes(
        self,
        from_date: str,
        to_date: Optional[str],
        status: str,
        start_position: int = 0,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """List envelopes (listStatusChanges) using from_date + optional to_date."""
        url = f"{self._ctx.base_uri.rstrip('/')}/restapi/v2.1/accounts/{self._ctx.account_id}/envelopes"
        params: dict[str, str] = {
            "from_date": from_date,
            "status": status,
            "start_position": str(start_position),
            "count": str(page_size),
        }
        if to_date:
            params["to_date"] = to_date
        resp = self._http.get(url, headers=self._headers(), params=params)
        self._raise_for_status(resp)
        return resp.json()

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, TransientApiError)),
        stop=stop_after_attempt(7),
        wait=wait_exponential_jitter(initial=0.5, max=30.0),
        reraise=True,
    )
    def list_envelope_documents(self, envelope_id: str) -> dict[str, Any]:
        url = f"{self._ctx.base_uri.rstrip('/')}/restapi/v2.1/accounts/{self._ctx.account_id}/envelopes/{envelope_id}/documents"
        resp = self._http.get(url, headers=self._headers())
        self._raise_for_status(resp)
        return resp.json()

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, TransientApiError)),
        stop=stop_after_attempt(7),
        wait=wait_exponential_jitter(initial=0.5, max=30.0),
        reraise=True,
    )
    def get_document_stream(self, envelope_id: str, document_id: str) -> httpx.Response:
        url = (
            f"{self._ctx.base_uri.rstrip('/')}/restapi/v2.1/accounts/{self._ctx.account_id}"
            f"/envelopes/{envelope_id}/documents/{document_id}"
        )
        resp = self._http.get(url, headers=self._headers(), follow_redirects=True)
        self._raise_for_status(resp)
        return resp
