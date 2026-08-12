from __future__ import annotations

from datetime import timezone
from pathlib import Path

from arnas_verify import TIMESTAMP_FORMAT, check_license_document
from arnas_verify.demo_issuance import build_license_document, sign_license_document
from arnas_verify.license import _parse_timestamp


def test_defaults_produce_verifiable_license(
    demo_private_key: Path, demo_public_key: Path
) -> None:
    """A document built with only app_id and customer must pass a full check."""
    doc = build_license_document(app_id="demo_app", customer="Demo Customer")
    signed = sign_license_document(doc, demo_private_key)
    result = check_license_document(
        signed, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert result.ok is True, result.reason


def test_default_expiry_is_365_days() -> None:
    doc = build_license_document(app_id="demo_app", customer="A")
    issued = _parse_timestamp(doc.issued_at)
    expires = _parse_timestamp(doc.expires_at)
    assert (expires - issued).days == 365
    assert issued.tzinfo is timezone.utc
    # Defaults must round-trip through the exact documented format.
    assert issued.strftime(TIMESTAMP_FORMAT) == doc.issued_at
    assert expires.strftime(TIMESTAMP_FORMAT) == doc.expires_at


def test_default_nonces_are_unique_and_nonempty() -> None:
    first = build_license_document(app_id="demo_app", customer="A")
    second = build_license_document(app_id="demo_app", customer="A")
    assert first.nonce
    assert second.nonce
    assert first.nonce != second.nonce
