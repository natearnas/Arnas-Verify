from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from arnas_verify import EXPIRES_FORMAT, check_license_document, get_machine_id
from arnas_verify.demo_issuance import build_license_document, sign_license_document


def test_defaults_produce_verifiable_license(
    demo_private_key: Path, demo_public_key: Path
) -> None:
    """A document built with product + licensee must pass on this machine."""
    doc = build_license_document(product="demo_app", licensee="Demo Customer")
    signed = sign_license_document(doc, demo_private_key)
    result = check_license_document(
        signed, public_key_path=demo_public_key, product="demo_app"
    )
    assert result.ok is True, result.reason
    assert doc.machine_id == get_machine_id()


def test_default_expiry_is_365_days() -> None:
    doc = build_license_document(product="demo_app", licensee="A")
    expires = date.fromisoformat(doc.expires)
    assert expires == date.today() + timedelta(days=365)
    assert doc.expires == expires.strftime(EXPIRES_FORMAT)


def test_explicit_machine_id_is_preserved() -> None:
    mid = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    doc = build_license_document(
        product="demo_app", licensee="A", machine_id=mid
    )
    assert doc.machine_id == mid
