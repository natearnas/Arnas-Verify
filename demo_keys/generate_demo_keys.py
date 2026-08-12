"""Generate the demo RSA keypair committed in this directory.

DEMO ONLY: the resulting private key is committed to a public repository and
therefore confers no trust whatsoever. See demo_keys/README.md. A production
deployment generates and guards its own keypair in a private signing
authority that is not part of this repo.
"""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    root = Path(__file__).resolve().parent
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    (root / "private_key.pem").write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    (root / "public_key.pem").write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    print(f"Generated demo keys in {root}")


if __name__ == "__main__":
    main()
