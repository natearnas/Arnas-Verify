"""Demo-only license issuance helpers.

DEMO ONLY — NOT A PRODUCTION TRUST ROOT.

Builds and signs flat license documents in the same shape used by Arnas
Technologies desktop products: RSA-PSS-SHA256 with PSS salt length 32 over
canonical JSON of every field except ``signature``, including a bound
``machine_id``. Production private keys and operator tools stay private.
"""

from __future__ import annotations

import base64
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .license import (
    EXPIRES_FORMAT,
    LICENSE_ALGORITHM,
    PSS_SALT_LENGTH,
    LicenseDocument,
    canonical_json,
)
from .machine import get_machine_id


def _load_private_key(path: str | Path) -> rsa.RSAPrivateKey:
    data = Path(path).read_bytes()
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise TypeError("Private key must be RSA")
    return key


def build_license_document(
    *,
    product: str,
    licensee: str,
    machine_id: Optional[str] = None,
    email: str = "",
    license_type: str = "standard",
    expires: Optional[str] = None,
    features: Optional[List[Any]] = None,
    key_id: str = "v1",
    organization: Optional[str] = None,
) -> LicenseDocument:
    """Build an unsigned demo license document bound to a machine.

    Defaults: ``machine_id`` is this computer's fingerprint, ``expires`` is
    one year from today (a calendar date ``YYYY-MM-DD``, not “days of
    runtime”). There is no perpetual/never-expires flag; use a far-future
    date such as ``2100-01-01`` if you want that in practice. See the README
    section on license duration.
    """
    if expires is None:
        expires = (date.today() + timedelta(days=365)).strftime(EXPIRES_FORMAT)
    else:
        # Normalize / validate early.
        expires = date.fromisoformat(expires).strftime(EXPIRES_FORMAT)
    mid = (machine_id or get_machine_id()).strip()
    return LicenseDocument(
        product=product,
        licensee=licensee.strip(),
        email=(email or "").strip(),
        license_type=(license_type or "standard").strip().lower() or "standard",
        expires=expires,
        machine_id=mid,
        features=list(features or []),
        key_id=key_id,
        organization=(organization.strip() if organization else None),
    )


def sign_license_document(
    document: LicenseDocument, private_key_path: str | Path
) -> Dict[str, Any]:
    """Sign a license document with a demo private key (PSS salt length 32)."""
    private_key = _load_private_key(private_key_path)
    payload = document.to_dict()
    signature = private_key.sign(
        canonical_json(payload),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=PSS_SALT_LENGTH,
        ),
        hashes.SHA256(),
    )
    signed = dict(payload)
    signed["signature"] = base64.b64encode(signature).decode("ascii")
    # LICENSE_ALGORITHM is documentation only; not part of the signed blob.
    _ = LICENSE_ALGORITHM
    return signed
