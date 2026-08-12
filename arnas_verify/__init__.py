"""Public reference implementation for local signed license verification.

The top-level package exposes only the verification-side API — the part a
product would ship. Demo-only issuance helpers (building and signing license
documents with the committed demo keypair) live in
:mod:`arnas_verify.demo_issuance` and must be imported explicitly; they are
deliberately not re-exported here. The production signing authority is a
separate, private project.
"""

from .license import (
    LICENSE_ALGORITHM,
    LICENSE_VERSION,
    TIMESTAMP_FORMAT,
    LicenseDocument,
    LicenseError,
    VerificationResult,
    canonical_json,
    check_license_document,
    check_license_file,
    validate_license_document,
    verify_license_document,
    verify_license_file,
)
from .locations import default_license_paths, locate_license_file

__all__ = [
    "LICENSE_ALGORITHM",
    "LICENSE_VERSION",
    "TIMESTAMP_FORMAT",
    "LicenseDocument",
    "LicenseError",
    "VerificationResult",
    "canonical_json",
    "check_license_document",
    "check_license_file",
    "default_license_paths",
    "locate_license_file",
    "validate_license_document",
    "verify_license_document",
    "verify_license_file",
]
