from pathlib import Path
import os

import respx
import httpx
from typer.testing import CliRunner

from docusign_agreements_downloader.cli import app

runner = CliRunner()


@respx.mock
def test_cli_download_runs(tmp_path: Path, monkeypatch):
    # env config
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
    monkeypatch.setenv("DS_AUTH_SERVER", "https://account-d.docusign.com")
    monkeypatch.setenv("DS_INTEGRATION_KEY", "INTEGRATION_KEY_12345")
    monkeypatch.setenv("DS_USER_ID", "USER_GUID_12345")
    monkeypatch.setenv("DS_PRIVATE_KEY_PEM_PATH", str(k))
    monkeypatch.setenv("DS_SCOPES", "signature impersonation")

    # mocks
    respx.post("https://account-d.docusign.com/oauth/token").respond(
        200, json={"access_token":"tok","token_type":"Bearer","expires_in":3600}
    )
    respx.get("https://account-d.docusign.com/oauth/userinfo").respond(
        200, json={"accounts":[{"account_id":"acc","base_uri":"https://demo.docusign.net","is_default":True}]}
    )
    respx.get("https://demo.docusign.net/restapi/v2.1/accounts/acc/envelopes").respond(
        200,
        json={"resultSetSize": 0, "startPosition": 0, "totalSetSize": 0, "envelopes":[]},
    )

    result = runner.invoke(
        app,
        ["download", "--from-date", "2026-01-01T00:00:00Z", "--status", "completed", "--out", str(tmp_path / "out")],
    )
    assert result.exit_code == 0
    assert "out_dir" in result.stdout
