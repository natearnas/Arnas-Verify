from __future__ import annotations

import base64
import json
import secrets
from pathlib import Path
from typing import Any, Dict

import pytest

from arnas_verify import (
    LicenseDocument,
    LicenseError,
    VerificationResult,
    check_license_document,
    check_license_file,
    get_machine_id,
    unsigned_payload,
    validate_license_document,
    verify_license_document,
    verify_license_file,
)
from arnas_verify.demo_issuance import build_license_document, sign_license_document
from tests.conftest import FIXTURE_MACHINE_ID


def _valid_payload() -> Dict[str, Any]:
    return {
        "product": "demo_app",
        "licensee": "A",
        "email": "a@example.com",
        "license_type": "standard",
        "expires": "2100-01-01",
        "machine_id": FIXTURE_MACHINE_ID,
        "features": [],
        "key_id": "v1",
    }


def test_demo_license_roundtrip(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    assert verify_license_document(signed_license, demo_public_key) is True
    assert (
        validate_license_document(
            signed_license,
            public_key_path=demo_public_key,
            product="demo_app",
            machine_id=FIXTURE_MACHINE_ID,
        )
        is True
    )
    result = check_license_document(
        signed_license,
        public_key_path=demo_public_key,
        product="demo_app",
        machine_id=FIXTURE_MACHINE_ID,
    )
    assert result.ok is True
    assert result.reason is None


def test_invalid_product_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    result = check_license_document(
        signed_license,
        public_key_path=demo_public_key,
        product="other_app",
        machine_id=FIXTURE_MACHINE_ID,
    )
    assert not result
    assert "product" in result.reason


def test_machine_id_mismatch_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    result = check_license_document(
        signed_license,
        public_key_path=demo_public_key,
        product="demo_app",
        machine_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    assert not result
    assert "machine_id" in result.reason


def test_license_bound_to_this_machine_passes(
    demo_private_key: Path, demo_public_key: Path
) -> None:
    mid = get_machine_id()
    doc = build_license_document(
        product="demo_app",
        licensee="Local",
        machine_id=mid,
        expires="2100-01-01",
    )
    signed = sign_license_document(doc, demo_private_key)
    result = check_license_document(
        signed, public_key_path=demo_public_key, product="demo_app"
    )
    assert result.ok is True, result.reason


def test_expired_license_fails(
    demo_private_key: Path, demo_public_key: Path
) -> None:
    doc = build_license_document(
        product="demo_app",
        licensee="A",
        machine_id=FIXTURE_MACHINE_ID,
        expires="2000-01-01",
    )
    signed = sign_license_document(doc, demo_private_key)
    result = check_license_document(
        signed,
        public_key_path=demo_public_key,
        product="demo_app",
        machine_id=FIXTURE_MACHINE_ID,
    )
    assert not result
    assert "expired" in result.reason


def test_wrong_public_key_fails(
    signed_license: Dict[str, Any], wrong_public_key: Path
) -> None:
    assert verify_license_document(signed_license, wrong_public_key) is False


def test_tampered_payload_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    signed_license["licensee"] = "Mallory"
    assert verify_license_document(signed_license, demo_public_key) is False


def test_invalid_base64_signature_fails(demo_public_key: Path) -> None:
    fake = _valid_payload()
    fake["signature"] = "not-valid-base64!!!"
    assert verify_license_document(fake, demo_public_key) is False


def test_valid_base64_wrong_signature_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    signed_license["signature"] = base64.b64encode(secrets.token_bytes(256)).decode(
        "ascii"
    )
    assert verify_license_document(signed_license, demo_public_key) is False


def test_signed_but_missing_field_fails(
    demo_public_key: Path, sign_raw_payload
) -> None:
    payload = _valid_payload()
    del payload["machine_id"]
    doc = sign_raw_payload(payload)
    assert verify_license_document(doc, demo_public_key) is True
    result = check_license_document(
        doc,
        public_key_path=demo_public_key,
        product="demo_app",
        machine_id=FIXTURE_MACHINE_ID,
    )
    assert not result
    assert "payload" in result.reason


def test_check_license_file_valid(
    tmp_path: Path, signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    path = tmp_path / "license.json"
    path.write_text(json.dumps(signed_license), encoding="utf-8")
    result = check_license_file(
        path,
        demo_public_key,
        product="demo_app",
        machine_id=FIXTURE_MACHINE_ID,
    )
    assert result.ok is True
    assert (
        verify_license_file(
            path,
            demo_public_key,
            product="demo_app",
            machine_id=FIXTURE_MACHINE_ID,
        )
        is True
    )


def test_check_license_file_missing_file(
    tmp_path: Path, demo_public_key: Path
) -> None:
    missing = tmp_path / "no_such_license.json"
    result = check_license_file(missing, demo_public_key, product="demo_app")
    assert not result
    assert "read" in result.reason


def test_from_dict_missing_fields_raises() -> None:
    payload = _valid_payload()
    del payload["licensee"]
    del payload["machine_id"]
    with pytest.raises(LicenseError) as excinfo:
        LicenseDocument.from_dict(payload)
    assert "licensee" in str(excinfo.value)
    assert "machine_id" in str(excinfo.value)


def test_verification_result_truthiness() -> None:
    assert bool(VerificationResult(ok=True)) is True
    assert bool(VerificationResult(ok=False, reason="x")) is False


def test_unsigned_payload_strips_signature(
    signed_license: Dict[str, Any],
) -> None:
    payload = unsigned_payload(signed_license)
    assert "signature" not in payload
    assert "machine_id" in payload


def test_committed_example_license_verifies(
    repo_root: Path, demo_public_key: Path
) -> None:
    """Known-answer: committed example verifies with its embedded machine_id."""
    example = repo_root / "examples" / "example_license.json"
    doc = json.loads(example.read_text(encoding="utf-8"))
    mid = doc["machine_id"]
    result = check_license_file(
        example, demo_public_key, product="demo_app", machine_id=mid
    )
    assert result.ok is True, result.reason


def test_get_machine_id_shape() -> None:
    mid = get_machine_id()
    assert len(mid) in (32, 64)
    assert all(c in "0123456789abcdef" for c in mid)
