"""Svix signature verification for the Clerk webhook (svix 2: verify() returns None)."""

import base64
import json
import secrets
from datetime import UTC, datetime

import pytest
from svix.webhooks import Webhook

from src.exceptions import ValidationError
from src.routers.webhooks import _verify_svix_signature

SECRET = "whsec_" + base64.b64encode(secrets.token_bytes(24)).decode()  # pragma: allowlist secret


def _signed(payload: dict) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload)
    msg_id = "msg_test"
    ts = datetime.now(UTC)
    signature = Webhook(SECRET).sign(msg_id, ts, body)
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": str(int(ts.timestamp())),
        "svix-signature": signature,
    }
    return body.encode(), headers


@pytest.mark.unit
class TestVerifySvixSignature:
    def test_valid_signature_returns_parsed_payload(self):
        body, headers = _signed({"type": "user.deleted", "data": {"id": "user_1"}})
        event = _verify_svix_signature(body, headers, SECRET)
        assert event == {"type": "user.deleted", "data": {"id": "user_1"}}

    def test_bad_signature_is_rejected(self):
        body, headers = _signed({"type": "user.deleted"})
        headers["svix-signature"] = "v1,AAAA"
        with pytest.raises(ValidationError, match="Invalid webhook signature"):
            _verify_svix_signature(body, headers, SECRET)

    def test_missing_secret_is_rejected(self):
        with pytest.raises(ValidationError, match="not configured"):
            _verify_svix_signature(b"{}", {}, "")

    def test_non_object_payload_is_rejected(self):
        body, headers = _signed([1, 2])  # type: ignore[arg-type]
        with pytest.raises(ValidationError, match="not an object"):
            _verify_svix_signature(body, headers, SECRET)
