"""Command-line license verification and machine-ID helper.

Exit codes: 0 = success; 1 = license invalid, not found, or a key/file
error; 2 = usage error (argparse).
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .license import check_license_file
from .locations import locate_license_file
from .machine import get_machine_id


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arnas-verify",
        description=(
            "Verify a signed local license document, or print this machine's "
            "fingerprint for license issuance."
        ),
    )
    parser.add_argument(
        "--print-machine-id",
        action="store_true",
        help="Print this computer's machine ID and exit (for license requests).",
    )
    parser.add_argument(
        "--license",
        help=(
            "Path to the signed license JSON file. If omitted, the standard "
            "per-user and machine-wide locations are searched (requires "
            "--vendor)."
        ),
    )
    parser.add_argument(
        "--public-key",
        help="Path to the trusted public key used to verify the signature.",
    )
    parser.add_argument(
        "--product",
        help="Expected product identifier (signed 'product' field).",
    )
    parser.add_argument(
        "--vendor",
        help=(
            "Vendor name used to locate the license file in the standard "
            "locations when --license is omitted."
        ),
    )
    args = parser.parse_args(argv)

    if args.print_machine_id:
        print(get_machine_id())
        return 0

    if not args.public_key:
        parser.error("--public-key is required unless --print-machine-id is set")
    if not args.product:
        parser.error("--product is required unless --print-machine-id is set")

    license_path = args.license
    if license_path is None:
        if not args.vendor:
            parser.error("--vendor is required when --license is omitted")
        found = locate_license_file(args.product, vendor=args.vendor)
        if found is None:
            print(
                f"No license file found in the standard locations for vendor "
                f"'{args.vendor}', product '{args.product}'.",
                file=sys.stderr,
            )
            return 1
        license_path = str(found)

    try:
        result = check_license_file(
            license_path, args.public_key, product=args.product
        )
    except (OSError, ValueError, TypeError) as exc:
        print(f"Public key error: {exc}", file=sys.stderr)
        return 1

    if result:
        print(f"License valid for product '{args.product}' on this machine.")
        return 0
    print(
        f"License invalid for product '{args.product}': {result.reason}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
