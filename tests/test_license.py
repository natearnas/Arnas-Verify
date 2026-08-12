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
    validate_license_document,
    verify_license_document,
    verify_license_file,
)
from arnas_verify.demo_issuance import build_license_document, sign_license_document


def _valid_payload() -> Dict[str, Any]:
    return {
        "app_id": "demo_app",
        "issued_at": "2026-01-01T00:00:00Z",
        "expires_at": "2100-01-01T00:00:00Z",
        "customer": "A",
        "features": {},
        "nonce": "x",
    }


def test_demo_license_roundtrip(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    assert verify_license_document(signed_license, demo_public_key) is True
    assert (
        validate_license_document(
            signed_license, public_key_path=demo_public_key, app_id="demo_app"
        )
        is True
    )
    result = check_license_document(
        signed_license, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert result.ok is True
    assert result.reason is None


def test_invalid_app_id_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    result = check_license_document(
        signed_license, public_key_path=demo_public_key, app_id="other_app"
    )
    assert not result
    assert "app_id" in result.reason


def test_expired_license_fails(
    demo_private_key: Path, demo_public_key: Path
) -> None:
    doc = build_license_document(
        app_id="demo_app", customer="A", expires_at="2000-01-01T00:00:00Z"
    )
    signed = sign_license_document(doc, demo_private_key)
    result = check_license_document(
        signed, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result
    assert "expired" in result.reason


def test_invalid_base64_signature_fails(demo_public_key: Path) -> None:
    fake = {
        "payload": _valid_payload(),
        "signature": "not-valid-base64!!!",
        "algorithm": "RSA-PSS-SHA256",
        "version": 1,
    }
    assert verify_license_document(fake, demo_public_key) is False


def test_wrong_public_key_fails(
    signed_license: Dict[str, Any], wrong_public_key: Path
) -> None:
    assert verify_license_document(signed_license, wrong_public_key) is False


def test_valid_base64_wrong_signature_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    signed_license["signature"] = base64.b64encode(secrets.token_bytes(256)).decode(
        "ascii"
    )
    assert verify_license_document(signed_license, demo_public_key) is False


def test_tampered_payload_intact_signature_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    signed_license["payload"]["customer"] = "Mallory"
    assert verify_license_document(signed_license, demo_public_key) is False


def test_algorithm_mismatch_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    signed_license["algorithm"] = "RSA-PKCS1-SHA256"
    result = check_license_document(
        signed_license, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result
    assert "algorithm" in result.reason


def test_version_mismatch_fails(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    signed_license["version"] = 2
    result = check_license_document(
        signed_license, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result
    assert "version" in result.reason


def test_signed_but_missing_field_fails(
    demo_public_key: Path, sign_raw_payload
) -> None:
    payload = _valid_payload()
    del payload["nonce"]
    doc = sign_raw_payload(payload)
    # The signature itself is genuinely valid for this payload...
    assert verify_license_document(doc, demo_public_key) is True
    # ...but full validation rejects the malformed (yet authenticated) payload.
    result = check_license_document(
        doc, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result
    assert "payload" in result.reason


def test_future_issued_at_fails(
    demo_private_key: Path, demo_public_key: Path
) -> None:
    doc = build_license_document(
        app_id="demo_app",
        customer="A",
        issued_at="2099-01-01T00:00:00Z",
        expires_at="2100-01-01T00:00:00Z",
    )
    signed = sign_license_document(doc, demo_private_key)
    result = check_license_document(
        signed, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result
    assert "future" in result.reason


def test_bad_timestamp_format_fails(
    demo_public_key: Path, sign_raw_payload
) -> None:
    payload = _valid_payload()
    payload["expires_at"] = "2100-01-01 00:00:00"
    doc = sign_raw_payload(payload)
    result = check_license_document(
        doc, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result
    assert "timestamp" in result.reason


def test_check_license_file_missing_file(
    tmp_path: Path, demo_public_key: Path
) -> None:
    missing = tmp_path / "no_such_license.json"
    result = check_license_file(missing, demo_public_key, app_id="demo_app")
    assert not result
    assert "read" in result.reason
    assert verify_license_file(missing, demo_public_key, app_id="demo_app") is False


def test_check_license_file_corrupt_json(
    tmp_path: Path, demo_public_key: Path
) -> None:
    corrupt = tmp_path / "license.json"
    corrupt.write_text("{not json", encoding="utf-8")
    result = check_license_file(corrupt, demo_public_key, app_id="demo_app")
    assert not result
    assert "JSON" in result.reason


def test_check_license_file_valid(
    tmp_path: Path, signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    path = tmp_path / "license.json"
    path.write_text(json.dumps(signed_license), encoding="utf-8")
    result = check_license_file(path, demo_public_key, app_id="demo_app")
    assert result.ok is True
    assert verify_license_file(path, demo_public_key, app_id="demo_app") is True


def test_from_dict_missing_fields_raises() -> None:
    payload = _valid_payload()
    del payload["customer"]
    del payload["nonce"]
    with pytest.raises(LicenseError) as excinfo:
        LicenseDocument.from_dict(payload)
    assert "customer" in str(excinfo.value)
    assert "nonce" in str(excinfo.value)


def test_from_dict_wrong_types_raise() -> None:
    payload = _valid_payload()
    payload["features"] = "not-an-object"
    with pytest.raises(LicenseError):
        LicenseDocument.from_dict(payload)
    payload = _valid_payload()
    payload["app_id"] = 42
    with pytest.raises(LicenseError):
        LicenseDocument.from_dict(payload)


def test_verification_result_truthiness() -> None:
    assert bool(VerificationResult(ok=True)) is True
    assert bool(VerificationResult(ok=False, reason="x")) is False


def test_committed_example_license_verifies(
    repo_root: Path, demo_public_key: Path
) -> None:
    """Known-answer test: the committed example license must verify as-is.

    This is the only test that does not re-sign in-process, so it catches
    signer/verifier conventions drifting together (canonical JSON form, PSS
    parameters, timestamp format) and demo keys rotated without re-signing
    the example.
    """
    example = repo_root / "examples" / "example_license.json"
    result = check_license_file(example, demo_public_key, app_id="demo_app")
    assert result.ok is True, result.reason


def test_non_dict_document_fails(
    tmp_path: Path, demo_public_key: Path
) -> None:
    for content in ("[]", '"text"', "42"):
        path = tmp_path / "license.json"
        path.write_text(content, encoding="utf-8")
        result = check_license_file(path, demo_public_key, app_id="demo_app")
        assert not result
        assert "malformed" in result.reason


def test_missing_or_mistyped_envelope_fields_fail(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    no_payload = dict(signed_license)
    del no_payload["payload"]
    result = check_license_document(
        no_payload, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result and "payload" in result.reason

    bad_payload = dict(signed_license)
    bad_payload["payload"] = ["not", "an", "object"]
    result = check_license_document(
        bad_payload, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result and "payload" in result.reason

    no_signature = dict(signed_license)
    del no_signature["signature"]
    result = check_license_document(
        no_signature, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result and "signature" in result.reason

    bad_signature = dict(signed_license)
    bad_signature["signature"] = 12345
    result = check_license_document(
        bad_signature, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result and "signature" in result.reason


def test_version_bool_and_float_fail(
    signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    # True == 1 and 1.0 == 1 in Python; the version gate must be exact.
    for bogus in (True, 1.0, "1"):
        doc = dict(signed_license)
        doc["version"] = bogus
        result = check_license_document(
            doc, public_key_path=demo_public_key, app_id="demo_app"
        )
        assert not result
        assert "version" in result.reason


def test_non_utf8_license_file_fails(
    tmp_path: Path, demo_public_key: Path
) -> None:
    path = tmp_path / "license.json"
    path.write_bytes(b"\xff\xfe\x00broken")
    result = check_license_file(path, demo_public_key, app_id="demo_app")
    assert not result
    assert "UTF-8" in result.reason


def test_utf8_bom_license_file_verifies(
    tmp_path: Path, signed_license: Dict[str, Any], demo_public_key: Path
) -> None:
    path = tmp_path / "license.json"
    path.write_text(json.dumps(signed_license), encoding="utf-8-sig")
    result = check_license_file(path, demo_public_key, app_id="demo_app")
    assert result.ok is True, result.reason


def test_nan_token_in_license_file_fails(
    tmp_path: Path, demo_public_key: Path
) -> None:
    path = tmp_path / "license.json"
    path.write_text('{"payload": {"x": NaN}, "signature": "x"}', encoding="utf-8")
    result = check_license_file(path, demo_public_key, app_id="demo_app")
    assert not result
    assert "JSON" in result.reason


def test_deeply_nested_license_file_fails_gracefully(
    tmp_path: Path, demo_public_key: Path
) -> None:
    path = tmp_path / "license.json"
    depth = 20000
    path.write_text("[" * depth + "]" * depth, encoding="utf-8")
    result = check_license_file(path, demo_public_key, app_id="demo_app")
    assert not result  # must return a failed result, not raise RecursionError


def test_lenient_timestamp_digits_rejected(
    demo_public_key: Path, sign_raw_payload
) -> None:
    # strptime alone would accept 1-digit fields; the exact format must not.
    payload = _valid_payload()
    payload["expires_at"] = "2100-1-1T0:0:0Z"
    doc = sign_raw_payload(payload)
    result = check_license_document(
        doc, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert not result
    assert "timestamp" in result.reason


def test_issued_at_within_leeway_passes(
    demo_private_key: Path, demo_public_key: Path
) -> None:
    from datetime import datetime, timedelta, timezone

    from arnas_verify import TIMESTAMP_FORMAT

    slightly_ahead = datetime.now(timezone.utc) + timedelta(seconds=60)
    doc = build_license_document(
        app_id="demo_app",
        customer="A",
        issued_at=slightly_ahead.strftime(TIMESTAMP_FORMAT),
        expires_at="2100-01-01T00:00:00Z",
    )
    signed = sign_license_document(doc, demo_private_key)
    result = check_license_document(
        signed, public_key_path=demo_public_key, app_id="demo_app"
    )
    assert result.ok is True, result.reason
