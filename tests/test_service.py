from pathlib import Path

import httpx
import respx

from docusign_agreements_downloader.config import Settings
from docusign_agreements_downloader.service import AgreementDownloadService


def _settings(tmp_path: Path) -> Settings:
    k = tmp_path / "k.pem"
    k.write_text(
        """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAz3p0WZ9V7O8OARQeFq+8t2S9sJpGqf5v5t5w9nHTuE1c7oVh
y3u6JmD0Jv9e1tKQxq8b8QzqfF1bJw0R2r1hQ6rjSxy3e5j5xwBq0nA0cFJYB6bG
zN4pXQbW1m6g5iZy1tZB2r0h2f7q3mE0d5uOqK7zQwZ2Zt8rQxQy3j9JxwIDAQAB
AoIBABQxq9w0hY7lR+8YJ3h5V5QKpZQXoO6f3B6i0QYt2b0HhEwH7l2Tg5n4uH6L
7ZQ9hQkPpM0cDqB2Ck1o8mK3Jm4dJk7q3qG7x9Kp9GJx8b8yWqWlYlOeY7y2aJcV
p5o8yS8q2a9p9Qy8f7wzq7y0nQvOZkqW8k1p1S0VZkECgYEA+9x8l9m3jzGmY2xT
oVn1uM1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o
o0kCgYEA0Kp7c+2Qm3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5
m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3kCgYEA0Yc+2Qm3y5m3y5m3y5m3y5m3
y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m3y5m
3kCgYB1uM1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o1m1o
1m1o1m1o1m1o1m1o1m1o1m0CgYB2Ck1o8mK3Jm4dJk7q3qG7x9Kp9GJx8b8yWqW
lYlOeY7y2aJcVp5o8yS8q2a9p9Qy8f7wzq7y0nQvOZkqW8k1p1S0VZk=
-----END RSA PRIVATE KEY-----""",
        encoding="utf-8",
    )
    return Settings(
        auth_server="https://account-d.docusign.com",
        integration_key="INTEGRATION_KEY_12345",
        user_id="USER_GUID_12345",
        private_key_pem_path=k,
        scopes="signature impersonation",
    )


@respx.mock
def test_service_download_happy_path(tmp_path: Path):
    s = _settings(tmp_path)
    out = tmp_path / "out"

    # auth
    respx.post("https://account-d.docusign.com/oauth/token").respond(
        200, json={"access_token":"tok","token_type":"Bearer","expires_in":3600}
    )
    respx.get("https://account-d.docusign.com/oauth/userinfo").respond(
        200, json={"accounts":[{"account_id":"acc","base_uri":"https://demo.docusign.net","is_default":True}]}
    )

    # list envelopes (single page)
    respx.get("https://demo.docusign.net/restapi/v2.1/accounts/acc/envelopes").respond(
        200,
        json={
            "resultSetSize": 1,
            "startPosition": 0,
            "totalSetSize": 1,
            "envelopes":[{"envelopeId":"e1","status":"completed","emailSubject":"S"}],
        },
    )

    # list docs
    respx.get("https://demo.docusign.net/restapi/v2.1/accounts/acc/envelopes/e1/documents").respond(
        200,
        json={"envelopeDocuments":[{"documentId":"1","name":"Agreement"}]},
    )

    # download doc
    respx.get("https://demo.docusign.net/restapi/v2.1/accounts/acc/envelopes/e1/documents/1").respond(
        200,
        headers={"content-type":"application/pdf"},
        content=b"%PDF-1.4 ...",
    )

    svc = AgreementDownloadService(s)
    result = svc.download(out_dir=out, from_date="2026-01-01T00:00:00Z", to_date=None, status="completed")

    assert result.status == "ok"
    assert (out / "index.json").exists()
    assert (out / "e1" / "agreement.json").exists()
    docs = list((out / "e1" / "documents").glob("*"))
    assert len(docs) == 1
    assert docs[0].read_bytes().startswith(b"%PDF")


@respx.mock
def test_service_records_failure_and_continues(tmp_path: Path):
    s = _settings(tmp_path)
    out = tmp_path / "out"

    respx.post("https://account-d.docusign.com/oauth/token").respond(
        200, json={"access_token":"tok","token_type":"Bearer","expires_in":3600}
    )
    respx.get("https://account-d.docusign.com/oauth/userinfo").respond(
        200, json={"accounts":[{"account_id":"acc","base_uri":"https://demo.docusign.net","is_default":True}]}
    )

    respx.get("https://demo.docusign.net/restapi/v2.1/accounts/acc/envelopes").respond(
        200,
        json={
            "resultSetSize": 2,
            "startPosition": 0,
            "totalSetSize": 2,
            "envelopes":[
                {"envelopeId":"e1","status":"completed","emailSubject":"S"},
                {"envelopeId":"e2","status":"completed","emailSubject":"S2"},
            ],
        },
    )

    respx.get("https://demo.docusign.net/restapi/v2.1/accounts/acc/envelopes/e1/documents").respond(
        500, text="boom"
    )
    respx.get("https://demo.docusign.net/restapi/v2.1/accounts/acc/envelopes/e2/documents").respond(
        200, json={"envelopeDocuments":[{"documentId":"1","name":"Agreement"}]}
    )
    respx.get("https://demo.docusign.net/restapi/v2.1/accounts/acc/envelopes/e2/documents/1").respond(
        200, headers={"content-type":"application/pdf"}, content=b"%PDF"
    )

    svc = AgreementDownloadService(s)
    result = svc.download(out_dir=out, from_date="2026-01-01T00:00:00Z", to_date=None, status="completed")

    assert result.status in ("partial", "ok")
    assert len(result.exported) == 2
    assert len(result.failures) >= 1
