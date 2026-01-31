import httpx
import pytest

from docusign_agreements_downloader.client import DocuSignClient, ApiContext, ApiError, TransientApiError


def test_raise_for_status_transient():
    c = DocuSignClient(http=httpx.Client(), ctx=ApiContext(base_uri="https://b", account_id="a"), access_token="t")
    req = httpx.Request("GET", "https://example.com")
    resp = httpx.Response(500, request=req, text="oops")
    with pytest.raises(TransientApiError):
        c._raise_for_status(resp)


def test_raise_for_status_fatal():
    c = DocuSignClient(http=httpx.Client(), ctx=ApiContext(base_uri="https://b", account_id="a"), access_token="t")
    req = httpx.Request("GET", "https://example.com")
    resp = httpx.Response(400, request=req, text="bad")
    with pytest.raises(ApiError):
        c._raise_for_status(resp)
