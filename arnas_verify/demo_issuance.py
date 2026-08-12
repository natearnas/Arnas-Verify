"""Demo-only license issuance helpers.

DEMO ONLY — NOT A PRODUCTION TRUST ROOT.

Production issuance (real private keys, customer ledger, signing service)
lives in a separate PRIVATE signing authority and is deliberately not part of
this repository. This module exists so the examples and tests can produce
signed documents with the intentionally committed demo keypair under
``demo_keys/``. Never ship the demo private key, never accept licenses signed
by it in a real product, and never treat these helpers as the production
issuance flow.

These helpers are intentionally not re-exported from the top-level
``arnas_verify`` package: any call site that issues licenses must import
``arnas_verify.demo_issuance`` explicitly, which keeps the verification-only
public API honest.
"""

from __future__ import annotations

import base64
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .license import (
    LICENSE_ALGORITHM,
    LICENSE_VERSION,
    TIMESTAMP_FORMAT,
    LicenseDocument,
    canonical_json,
)
from .license import _utc_now


def _load_private_key(path: str | Path) -> rsa.RSAPrivateKey:
    data = Path(path).read_bytes()
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise TypeError("Private key must be RSA")
    return key


def build_license_document(
    *,
    app_id: str,
    customer: str,
    features: Optional[Dict[str, Any]] = None,
    issued_at: Optional[str] = None,
    expires_at: Optional[str] = None,
    nonce: Optional[str] = None,
) -> LicenseDocument:
    """Build an unsigned demo license document.

    Defaults: ``issued_at`` is now, ``expires_at`` is approximately one year
    from now (365 days), and ``nonce`` is 16 random bytes, base64url-encoded.
    """
    now = _utc_now()
    if issued_at is None:
        issued_at = now.strftime(TIMESTAMP_FORMAT)
    if expires_at is None:
        expires_at = (now + timedelta(days=365)).strftime(TIMESTAMP_FORMAT)
    if nonce is None:
        nonce = (
            base64.urlsafe_b64encode(secrets.token_bytes(16))
            .decode("ascii")
            .rstrip("=")
        )
    return LicenseDocument(
        app_id=app_id,
        issued_at=issued_at,
        expires_at=expires_at,
        customer=customer,
        features=features or {},
        nonce=nonce,
    )


def sign_license_document(
    document: LicenseDocument, private_key_path: str | Path
) -> Dict[str, Any]:
    """Sign a license document with a demo private key.

    Returns the full envelope: ``payload``, base64 ``signature`` over the
    canonical JSON form of the payload, plus ``algorithm`` and ``version``
    fields that the verifier checks before verifying the signature.
    """
    private_key = _load_private_key(private_key_path)
    payload = document.to_dict()
    signature = private_key.sign(
        canonical_json(payload),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256(),
    )
    return {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
        "algorithm": LICENSE_ALGORITHM,
        "version": LICENSE_VERSION,
    }
