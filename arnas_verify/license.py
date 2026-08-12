"""Verification side of the Arnas Verify reference licensing scheme.

Protocol (aligned with Arnas Technologies desktop product licensing)
--------------------------------------------------------------------
A license is a flat JSON object. The issuer signs every field except
``signature`` with RSA-PSS-SHA256 (PSS salt length = 32). The shipped
application verifies the signature with an embedded public key, then enforces
``product`` binding, ``machine_id`` binding, and calendar expiry.

Public/private split
--------------------
This public repository contains no production trust material. Demo issuance
helpers live in :mod:`arnas_verify.demo_issuance`. Real private keys, customer
ledgers, and operator GUIs stay in a separate private project.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .machine import get_machine_id, is_plausible_machine_id

#: Signature algorithm this verifier accepts (documented; not a signed field).
LICENSE_ALGORITHM = "RSA-PSS-SHA256"

#: PSS salt length used by the issuer and accepted by this verifier.
PSS_SALT_LENGTH = 32

#: Expiration dates use this calendar form (UTC date, no time component).
EXPIRES_FORMAT = "%Y-%m-%d"

_REQUIRED_STRING_FIELDS = (
    "product",
    "licensee",
    "email",
    "license_type",
    "expires",
    "machine_id",
)
_OPTIONAL_STRING_FIELDS = ("key_id", "organization")


class LicenseError(ValueError):
    """Raised when a license payload is structurally invalid."""


@dataclass
class LicenseDocument:
    """The signed claims in a license (everything except ``signature``)."""

    product: str
    licensee: str
    email: str
    license_type: str
    expires: str
    machine_id: str
    features: List[Any]
    key_id: Optional[str] = None
    organization: Optional[str] = None

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "LicenseDocument":
        if not isinstance(payload, dict):
            raise LicenseError("payload must be a JSON object")
        missing = [name for name in _REQUIRED_STRING_FIELDS if name not in payload]
        if missing:
            raise LicenseError(f"missing required fields: {', '.join(missing)}")
        if "features" not in payload:
            raise LicenseError("missing required fields: features")
        for name in _REQUIRED_STRING_FIELDS:
            if not isinstance(payload[name], str):
                raise LicenseError(f"field '{name}' must be a string")
        if not isinstance(payload["features"], list):
            raise LicenseError("field 'features' must be an array")
        for name in _OPTIONAL_STRING_FIELDS:
            if name in payload and payload[name] is not None:
                if not isinstance(payload[name], str):
                    raise LicenseError(f"field '{name}' must be a string")
        if not is_plausible_machine_id(payload["machine_id"]):
            raise LicenseError(
                "field 'machine_id' must be a 32- or 64-character lowercase hex fingerprint"
            )
        try:
            datetime.strptime(payload["expires"], EXPIRES_FORMAT).date()
        except ValueError as exc:
            raise LicenseError(
                f"field 'expires' must be YYYY-MM-DD, got {payload['expires']!r}"
            ) from exc
        return LicenseDocument(
            product=payload["product"],
            licensee=payload["licensee"],
            email=payload["email"],
            license_type=payload["license_type"],
            expires=payload["expires"],
            machine_id=payload["machine_id"],
            features=list(payload["features"]),
            key_id=payload.get("key_id"),
            organization=payload.get("organization"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return the unsigned payload dict in the shape that gets signed."""
        payload: Dict[str, Any] = {
            "product": self.product,
            "licensee": self.licensee,
            "email": self.email,
            "license_type": self.license_type,
            "expires": self.expires,
            "machine_id": self.machine_id,
            "features": list(self.features),
        }
        if self.key_id is not None:
            payload["key_id"] = self.key_id
        if self.organization is not None:
            payload["organization"] = self.organization
        return payload


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
    """Serialize a payload in the canonical form that is signed and verified."""
    return json.dumps(
        payload, separators=(",", ":"), sort_keys=True, allow_nan=False
    ).encode("utf-8")


def unsigned_payload(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``doc`` without the ``signature`` field."""
    payload = dict(doc)
    payload.pop("signature", None)
    return payload


def _load_public_key(path: str | Path) -> rsa.RSAPublicKey:
    data = Path(path).read_bytes()
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, rsa.RSAPublicKey):
        raise TypeError("Public key must be RSA")
    return key


def _check_signature(doc: Any, public_key_path: str | Path) -> VerificationResult:
    """Verify document shape and cryptographic signature only."""
    if not isinstance(doc, dict):
        return _fail("malformed document: not a JSON object")
    signature = doc.get("signature")
    if not isinstance(signature, str):
        return _fail("malformed document: 'signature' must be a string")

    payload = unsigned_payload(doc)
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
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=PSS_SALT_LENGTH,
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return _fail("signature verification failed")
    return _VALID


def check_license_document(
    doc: Dict[str, Any],
    *,
    public_key_path: str | Path,
    product: str,
    machine_id: Optional[str] = None,
) -> VerificationResult:
    """Fully validate a signed license for one product on one machine.

    Check order: signature, payload structure, product binding, machine
    binding, not-expired. ``machine_id`` defaults to :func:`get_machine_id`.
    """
    result = _check_signature(doc, public_key_path)
    if not result:
        return result

    try:
        document = LicenseDocument.from_dict(unsigned_payload(doc))
    except LicenseError as exc:
        return _fail(f"invalid payload: {exc}")

    if document.product != product:
        return _fail(
            f"product mismatch: expected '{product}', got '{document.product}'"
        )

    current_id = machine_id if machine_id is not None else get_machine_id()
    if document.machine_id != current_id:
        return _fail(
            "machine_id mismatch: "
            f"license '{document.machine_id}', this machine '{current_id}'"
        )

    expires = datetime.strptime(document.expires, EXPIRES_FORMAT).date()
    if date.today() > expires:
        return _fail(f"license expired on {document.expires}")

    return _VALID


def check_license_file(
    path: str | Path,
    public_key_path: str | Path,
    *,
    product: str,
    machine_id: Optional[str] = None,
) -> VerificationResult:
    """Load a license file and fully validate it."""
    try:
        text = Path(path).read_bytes().decode("utf-8-sig")
    except OSError as exc:
        return _fail(f"cannot read license file: {exc}")
    except UnicodeDecodeError:
        return _fail("license file is not valid UTF-8")
    try:
        doc = json.loads(text)
    except (ValueError, RecursionError):
        return _fail("license file is not valid JSON")
    return check_license_document(
        doc,
        public_key_path=public_key_path,
        product=product,
        machine_id=machine_id,
    )


def verify_license_document(doc: Dict[str, Any], public_key_path: str | Path) -> bool:
    """Check only the cryptographic signature (no product/machine/expiry)."""
    return bool(_check_signature(doc, public_key_path))


def validate_license_document(
    doc: Dict[str, Any],
    *,
    public_key_path: str | Path,
    product: str,
    machine_id: Optional[str] = None,
) -> bool:
    """Boolean form of :func:`check_license_document`."""
    return bool(
        check_license_document(
            doc,
            public_key_path=public_key_path,
            product=product,
            machine_id=machine_id,
        )
    )


def verify_license_file(
    path: str | Path,
    public_key_path: str | Path,
    *,
    product: str,
    machine_id: Optional[str] = None,
) -> bool:
    """Boolean form of :func:`check_license_file`."""
    return bool(
        check_license_file(
            path,
            public_key_path,
            product=product,
            machine_id=machine_id,
        )
    )
