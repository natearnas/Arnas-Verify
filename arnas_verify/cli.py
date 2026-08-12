"""Command-line license verification.

Exit codes: 0 = license valid; 1 = license invalid, not found, or a key/file
error; 2 = usage error (argparse).
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .license import check_license_file
from .locations import locate_license_file


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arnas-verify",
        description="Verify a signed local license document.",
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
        required=True,
        help="Path to the trusted public key used to verify the signature.",
    )
    parser.add_argument(
        "--app-id", required=True, help="Expected application identifier."
    )
    parser.add_argument(
        "--vendor",
        help=(
            "Vendor name used to locate the license file in the standard "
            "locations when --license is omitted."
        ),
    )
    args = parser.parse_args(argv)

    license_path = args.license
    if license_path is None:
        if not args.vendor:
            parser.error("--vendor is required when --license is omitted")
        found = locate_license_file(args.app_id, vendor=args.vendor)
        if found is None:
            print(
                f"No license file found in the standard locations for vendor "
                f"'{args.vendor}', app '{args.app_id}'.",
                file=sys.stderr,
            )
            return 1
        license_path = str(found)

    try:
        result = check_license_file(
            license_path, args.public_key, app_id=args.app_id
        )
    except (OSError, ValueError, TypeError) as exc:
        print(f"Public key error: {exc}", file=sys.stderr)
        return 1

    if result:
        print(f"License valid for app '{args.app_id}'.")
        return 0
    print(
        f"License invalid for app '{args.app_id}': {result.reason}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
