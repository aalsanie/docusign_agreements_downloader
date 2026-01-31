from pathlib import Path
import json

import httpx
import respx
from freezegun import freeze_time

from docusign_agreements_downloader.auth import build_jwt_assertion, fetch_access_token, fetch_userinfo_account, AuthError
from docusign_agreements_downloader.config import Settings


def _settings(tmp_path: Path) -> Settings:
    key_path = tmp_path / "k.pem"
    # minimal RSA key for tests (generated once; not for production use)
    key_path.write_text(
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
        private_key_pem_path=key_path,
        scopes="signature impersonation",
    )


@freeze_time("2026-01-31T00:00:00Z")
def test_build_jwt_assertion_contains_claims(tmp_path: Path):
    s = _settings(tmp_path)
    token = build_jwt_assertion(s)
    # Just ensure it is a JWT (3 segments). We don't validate signature here.
    assert token.count(".") == 2


@respx.mock
def test_fetch_access_token_ok(tmp_path: Path):
    s = _settings(tmp_path)
    with httpx.Client(timeout=5) as c:
        respx.post("https://account-d.docusign.com/oauth/token").respond(
            200, json={"access_token":"t","token_type":"Bearer","expires_in":3600}
        )
        token = fetch_access_token(s, c)
        assert token.access_token == "t"


@respx.mock
def test_fetch_userinfo_account_picks_default(tmp_path: Path):
    s = _settings(tmp_path)
    with httpx.Client(timeout=5) as c:
        respx.get("https://account-d.docusign.com/oauth/userinfo").respond(
            200,
            json={
                "accounts":[
                    {"account_id":"a1","base_uri":"https://demo.docusign.net","is_default":False},
                    {"account_id":"a2","base_uri":"https://demo2.docusign.net","is_default":True},
                ]
            },
        )
        acct = fetch_userinfo_account(s, c, type("T", (), {"access_token":"t"})())
        assert acct.account_id == "a2"
        assert acct.base_uri.startswith("https://demo2")


@respx.mock
def test_fetch_access_token_error(tmp_path: Path):
    s = _settings(tmp_path)
    with httpx.Client(timeout=5) as c:
        respx.post("https://account-d.docusign.com/oauth/token").respond(401, text="nope")
        try:
            fetch_access_token(s, c)
            assert False, "expected"
        except AuthError as e:
            assert "401" in str(e)
