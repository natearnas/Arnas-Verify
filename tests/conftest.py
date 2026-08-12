from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from arnas_verify import canonical_json
from arnas_verify.demo_issuance import build_license_document, sign_license_document

_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return _REPO_ROOT


@pytest.fixture(scope="session")
def demo_private_key(repo_root: Path) -> Path:
    return repo_root / "demo_keys" / "private_key.pem"


@pytest.fixture(scope="session")
def demo_public_key(repo_root: Path) -> Path:
    return repo_root / "demo_keys" / "public_key.pem"


@pytest.fixture
def signed_license(demo_private_key: Path) -> Dict[str, Any]:
    """A freshly built and signed demo license (function-scoped: mutate freely)."""
    doc = build_license_document(
        app_id="demo_app",
        customer="Demo Customer",
        features={"tier": "trial", "seats": 1},
        expires_at="2100-01-01T00:00:00Z",
    )
    return sign_license_document(doc, demo_private_key)


@pytest.fixture(scope="session")
def wrong_public_key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A valid RSA public key that did NOT sign anything in this repo."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path = tmp_path_factory.mktemp("wrong_key") / "public_key.pem"
    path.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return path


@pytest.fixture(scope="session")
def sign_raw_payload(demo_private_key: Path):
    """Sign an arbitrary payload dict with the demo key.

    Bypasses LicenseDocument on purpose: this produces documents whose
    signature is genuinely valid but whose payload is malformed, proving the
    structural checks run on authenticated data rather than replacing the
    signature check.
    """
    key = serialization.load_pem_private_key(
        demo_private_key.read_bytes(), password=None
    )

    def _sign(payload: Dict[str, Any]) -> Dict[str, Any]:
        signature = key.sign(
            canonical_json(payload),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        return {
            "payload": payload,
            "signature": base64.b64encode(signature).decode("ascii"),
            "algorithm": "RSA-PSS-SHA256",
            "version": 1,
        }

    return _sign
