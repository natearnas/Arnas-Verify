"""Regenerate examples/example_license.json using the demo keypair.

Demo-only: binds the example to a stable demo machine_id so CI can verify it
without sharing hardware fingerprints. For a license bound to *this* computer,
pass --this-machine.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from arnas_verify.demo_issuance import build_license_document, sign_license_document
from arnas_verify.machine import get_machine_id

# Stable fingerprint used only by the committed example (not a real machine).
EXAMPLE_MACHINE_ID = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--this-machine",
        action="store_true",
        help="Bind the example license to this computer's machine ID.",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    private_key_path = root / "demo_keys" / "private_key.pem"
    output_path = root / "examples" / "example_license.json"

    machine_id = get_machine_id() if args.this_machine else EXAMPLE_MACHINE_ID
    doc = build_license_document(
        product="demo_app",
        licensee="Demo Customer",
        email="demo@example.com",
        license_type="trial",
        features=["tier:trial"],
        expires="2100-01-01",
        machine_id=machine_id,
    )
    signed = sign_license_document(doc, private_key_path)
    output_path.write_text(
        json.dumps(signed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote demo license to {output_path}")
    print(f"Bound machine_id: {machine_id}")


if __name__ == "__main__":
    main()
