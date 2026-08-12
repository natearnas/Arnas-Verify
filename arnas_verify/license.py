"""Verification side of the Arnas Verify reference licensing scheme.

This module is the part a product would ship: it loads a signed license
document (JSON), verifies its RSA-PSS-SHA256 signature against a trusted
public key, and enforces app binding, expiry, and structural validation.

Public/private split
--------------------
This public repository deliberately contains no production trust material.
The demo issuance helpers live in :mod:`arnas_verify.demo_issuance` and exist
only so the examples and tests can produce signed documents. The real signing
authority (private keys, customer ledger, issuance flow) is a separate,
private project and is not part of this codebase.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

#: Envelope version this verifier accepts.
LICENSE_VERSION = 1

#: Signature algorithm this verifier accepts.
LICENSE_ALGORITHM = "RSA-PSS-SHA256"

#: Timestamps in license payloads must use this exact UTC format.
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

#: Tolerance applied to the issued_at check so a freshly issued license is
#: not rejected when the authority's clock is slightly ahead of this machine.
ISSUED_AT_LEEWAY = timedelta(minutes=5)

_REQUIRED_STRING_FIELDS = ("app_id", "issued_at", "expires_at", "customer", "nonce")
_REQUIRED_FIELDS = _REQUIRED_STRING_FIELDS + ("features",)


class LicenseError(ValueError):
    """Raised when a license payload is structurally invalid."""


@dataclass
class LicenseDocument:
    """The signed portion of a license: the claims the authority vouches for."""

    app_id: str
    issued_at: str
    expires_at: str
    customer: str
    features: Dict[str, Any]
    nonce: str

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "LicenseDocument":
        """Build a document from a payload dict, enforcing shape and types.

        Raises:
            LicenseError: if the payload is not an object, a required field is
                missing, a string field is not a string, or ``features`` is
                not an object.
        """
        if not isinstance(payload, dict):
            raise LicenseError("payload must be a JSON object")
        missing = [name for name in _REQUIRED_FIELDS if name not in payload]
        if missing:
            raise LicenseError(f"missing required fields: {', '.join(missing)}")
        for name in _REQUIRED_STRING_FIELDS:
            if not isinstance(payload[name], str):
                raise LicenseError(f"field '{name}' must be a string")
        if not isinstance(payload["features"], dict):
            raise LicenseError("field 'features' must be an object")
        return LicenseDocument(
            app_id=payload["app_id"],
            issued_at=payload["issued_at"],
            expires_at=payload["expires_at"],
            customer=payload["customer"],
            features=payload["features"],
            nonce=payload["nonce"],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return the payload dict in the shape that gets signed."""
        return {
            "app_id": self.app_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "customer": self.customer,
            "features": self.features,
            "nonce": self.nonce,
        }


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a license check.

    Truthy when the license is valid. On failure, ``reason`` holds a concise
    human-readable explanation suitable for logs and CLI output.
    """

    ok: bool
    reason: Optional[str] = None

    def __bool__(self) -> bool:
        return self.ok


_VALID = VerificationResult(True)


def _fail(reason: str) -> VerificationResult:
    return VerificationResult(False, reason)


def canonical_json(payload: Dict[str, Any]) -> bytes:
    """Serialize a payload in the canonical form that is signed and verified.

    The convention is compact separators, lexicographically sorted keys,
    UTF-8 encoding, and strictly finite numbers (no NaN/Infinity, which are
    not valid JSON). Payloads must be JSON-native data with string keys.
    Signer and verifier must both use this exact form; it is defined here,
    in one place, so they cannot drift apart.
    """
    return json.dumps(
        payload, separators=(",", ":"), sort_keys=True, allow_nan=False
    ).encode("utf-8")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.strptime(value, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    # strptime tolerates 1-digit fields; require the exact documented form.
    if parsed.strftime(TIMESTAMP_FORMAT) != value:
        raise ValueError(f"timestamp not in exact format: {value!r}")
    return parsed


def _reject_nonfinite(token: str) -> Any:
    raise ValueError(f"non-finite JSON token not allowed: {token}")


def _load_public_key(path: str | Path) -> rsa.RSAPublicKey:
    """Load the trusted RSA public key.

    Problems here (missing file, corrupt PEM, non-RSA key) are deployment
    errors in the verifying application, not untrusted input, so they raise
    instead of returning a failed :class:`VerificationResult`.
    """
    data = Path(path).read_bytes()
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, rsa.RSAPublicKey):
        raise TypeError("Public key must be RSA")
    return key


def _check_envelope_and_signature(
    doc: Any, public_key_path: str | Path
) -> VerificationResult:
    """Check the envelope shape, version, algorithm, and signature.

    The signature is verified before the payload is interpreted in any way;
    everything after this gate operates on authenticated data only.
    """
    if not isinstance(doc, dict):
        return _fail("malformed document: not a JSON object")
    payload = doc.get("payload")
    signature = doc.get("signature")
    if not isinstance(payload, dict):
        return _fail("malformed document: 'payload' must be an object")
    if not isinstance(signature, str):
        return _fail("malformed document: 'signature' must be a string")
    version = doc.get("version")
    # Exact int comparison: bool/float equal-comparing to 1 must not pass.
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version != LICENSE_VERSION
    ):
        return _fail(f"unsupported version: {version!r}")
    algorithm = doc.get("algorithm")
    if algorithm != LICENSE_ALGORITHM:
        return _fail(f"unsupported algorithm: {algorithm!r}")

    public_key = _load_public_key(public_key_path)
    try:
        sig = base64.b64decode(signature.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError):
        return _fail("signature is not valid base64")
    try:
        raw = canonical_json(payload)
    except (TypeError, ValueError, RecursionError):
        return _fail("payload is not canonically serializable JSON")
    try:
        public_key.verify(
            sig,
            raw,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return _fail("signature verification failed")
    return _VALID


def check_license_document(
    doc: Dict[str, Any], *, public_key_path: str | Path, app_id: str
) -> VerificationResult:
    """Fully validate a signed license document for one application.

    Check order: envelope shape, version, algorithm, signature, payload
    structure, app binding, timestamp format, not-yet-issued (with a small
    clock-skew leeway, :data:`ISSUED_AT_LEEWAY`), not-expired. Returns a
    :class:`VerificationResult` whose ``reason`` names the first failed
    check.

    Raises:
        OSError, ValueError, TypeError: if the public key itself cannot be
            loaded (deployment error, not untrusted input).
    """
    result = _check_envelope_and_signature(doc, public_key_path)
    if not result:
        return result

    try:
        document = LicenseDocument.from_dict(doc["payload"])
    except LicenseError as exc:
        return _fail(f"invalid payload: {exc}")

    if document.app_id != app_id:
        return _fail(
            f"app_id mismatch: expected '{app_id}', got '{document.app_id}'"
        )

    try:
        issued_dt = _parse_timestamp(document.issued_at)
        expires_dt = _parse_timestamp(document.expires_at)
    except ValueError:
        return _fail(
            "invalid timestamp format: expected YYYY-MM-DDTHH:MM:SSZ (UTC)"
        )

    now = _utc_now()
    if issued_dt > now + ISSUED_AT_LEEWAY:
        return _fail("issued_at is in the future")
    if now > expires_dt:
        return _fail(f"license expired at {document.expires_at}")

    return _VALID


def check_license_file(
    path: str | Path, public_key_path: str | Path, *, app_id: str
) -> VerificationResult:
    """Load a license file and fully validate it for one application.

    Unreadable or non-JSON license files are untrusted input and produce a
    failed result with a reason; public-key problems raise (see
    :func:`check_license_document`).
    """
    try:
        # utf-8-sig also accepts a UTF-8 BOM, which Windows editors add.
        text = Path(path).read_bytes().decode("utf-8-sig")
    except OSError as exc:
        return _fail(f"cannot read license file: {exc}")
    except UnicodeDecodeError:
        return _fail("license file is not valid UTF-8")
    try:
        doc = json.loads(text, parse_constant=_reject_nonfinite)
    except (ValueError, RecursionError):
        return _fail("license file is not valid JSON")
    return check_license_document(doc, public_key_path=public_key_path, app_id=app_id)


def verify_license_document(doc: Dict[str, Any], public_key_path: str | Path) -> bool:
    """Check only the envelope and cryptographic signature of a document.

    This deliberately skips app binding, expiry, and payload validation —
    use :func:`check_license_document` (or :func:`validate_license_document`)
    for a full check.
    """
    return bool(_check_envelope_and_signature(doc, public_key_path))


def validate_license_document(
    doc: Dict[str, Any], *, public_key_path: str | Path, app_id: str
) -> bool:
    """Boolean form of :func:`check_license_document`."""
    return bool(
        check_license_document(doc, public_key_path=public_key_path, app_id=app_id)
    )


def verify_license_file(
    path: str | Path, public_key_path: str | Path, *, app_id: str
) -> bool:
    """Boolean form of :func:`check_license_file`.

    ``app_id`` is required: file-level verification always enforces app
    binding and expiry, so a valid signature alone never passes.
    """
    return bool(check_license_file(path, public_key_path, app_id=app_id))
