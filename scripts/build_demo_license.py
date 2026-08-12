"""Regenerate examples/example_license.json using the demo keypair.

Demo-only: this mimics what the private production authority does, using the
intentionally committed demo private key. See arnas_verify.demo_issuance.
"""

from __future__ import annotations

import json
from pathlib import Path

from arnas_verify.demo_issuance import build_license_document, sign_license_document


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    private_key_path = root / "demo_keys" / "private_key.pem"
    output_path = root / "examples" / "example_license.json"

    doc = build_license_document(
        app_id="demo_app",
        customer="Demo Customer",
        features={"tier": "trial", "seats": 1},
        expires_at="2100-01-01T00:00:00Z",
    )
    signed = sign_license_document(doc, private_key_path)
    output_path.write_text(
        json.dumps(signed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote demo license to {output_path}")


if __name__ == "__main__":
    main()
