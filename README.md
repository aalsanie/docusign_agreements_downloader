# DocuSign Agreements Downloader

## Prerequisites

You must have a DocuSign integration set up with JWT Grant:

1. Create an **Integration Key** (Client ID) in the DocuSign Developer Center.
2. Enable **JWT Grant** for the integration and upload your public key.
3. Identify the **User ID** (GUID).
4. Ensure the user has granted consent for the scopes you request (typically `signature impersonation`).

---

## Install

Python 3.11+ recommended.

```bash
cd docusign_agreements_downloader
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -U pip
pip install -e ".[dev]"
```

---

## Configuration

Set these environment variables:

```bash
export DS_AUTH_SERVER="https://account-d.docusign.com"   # test: account-d; prod: account
export DS_INTEGRATION_KEY="YOUR_INTEGRATION_KEY"
export DS_USER_ID="YOUR_USER_GUID"
export DS_PRIVATE_KEY_PEM_PATH="/absolute/path/to/private_key.pem"
export DS_SCOPES="signature impersonation"
```

Notes:
- Demo auth server: `https://account-d.docusign.com`
- Production auth server: `https://account.docusign.com`

---

## Run

You must provide a **date window** for listing envelopes because DocuSign listing/search APIs are date-filtered.

Example: download completed envelopes for today:

```bash
dsa download   --from-date "2025-12-31T00:00:00Z"   --to-date   "2026-01-31T23:59:59Z"   --status completed   --out ./out
```

What it writes:

```
out/
  index.json
  <envelope_id>/
    agreement.json
    documents/
      <document_id>_<safe_name>.<ext>
```

---

## Test

Run unit tests + coverage:

```bash
pytest -q
pytest --cov=docusign_agreements_downloader --cov-report=term-missing --cov-fail-under=90
```

---

## How to execute and validate

1. Export environment vars
2. Run the downloader:
   ```bash
   dsa download --from-date "2026-01-30T00:00:00Z" --to-date "2026-01-31T23:59:59Z" --status completed --out ./out
   ```
3. Confirm:
   - `out/index.json` exists
   - For at least one envelope, you see `agreement.json` and files under `documents/`
