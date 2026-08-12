from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from arnas_verify import PSS_SALT_LENGTH, canonical_json
from arnas_verify.demo_issuance import build_license_document, sign_license_document

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Stable ID for fixtures (not this host's fingerprint).
FIXTURE_MACHINE_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


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
    """Freshly signed demo license bound to FIXTURE_MACHINE_ID."""
    doc = build_license_document(
        product="demo_app",
        licensee="Demo Customer",
        email="demo@example.com",
        license_type="trial",
        features=["tier:trial"],
        expires="2100-01-01",
        machine_id=FIXTURE_MACHINE_ID,
    )
    return sign_license_document(doc, demo_private_key)


@pytest.fixture(scope="session")
def wrong_public_key(tmp_path_factory: pytest.TempPathFactory) -> Path:
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
    """Sign an arbitrary payload dict with the demo key (bypasses LicenseDocument)."""
    key = serialization.load_pem_private_key(
        demo_private_key.read_bytes(), password=None
    )

    def _sign(payload: Dict[str, Any]) -> Dict[str, Any]:
        signature = key.sign(
            canonical_json(payload),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=PSS_SALT_LENGTH,
            ),
            hashes.SHA256(),
        )
        signed = dict(payload)
        signed["signature"] = base64.b64encode(signature).decode("ascii")
        return signed

    return _sign
