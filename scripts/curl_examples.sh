#!/usr/bin/env bash
set -euo pipefail

echo "DocuSign endpoints used:"
echo "  POST ${DS_AUTH_SERVER}/oauth/token"
echo "  GET  ${DS_AUTH_SERVER}/oauth/userinfo"
echo "  GET  {base_uri}/restapi/v2.1/accounts/{accountId}/envelopes?from_date=...&status=..."
echo "  GET  {base_uri}/restapi/v2.1/accounts/{accountId}/envelopes/{envelopeId}/documents"
echo "  GET  {base_uri}/restapi/v2.1/accounts/{accountId}/envelopes/{envelopeId}/documents/{documentId}"

echo
echo "Tip: run the Python CLI, then inspect out/index.json for the base_uri/accountId usage."
