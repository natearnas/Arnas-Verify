"""Public reference implementation for local signed license verification.

The top-level package exposes the verification-side API — the part a product
would ship. Demo-only issuance helpers live in
:mod:`arnas_verify.demo_issuance` and must be imported explicitly.
"""

from .license import (
    EXPIRES_FORMAT,
    LICENSE_ALGORITHM,
    PSS_SALT_LENGTH,
    LicenseDocument,
    LicenseError,
    VerificationResult,
    canonical_json,
    check_license_document,
    check_license_file,
    unsigned_payload,
    validate_license_document,
    verify_license_document,
    verify_license_file,
)
from .locations import default_license_paths, locate_license_file
from .machine import get_machine_id, is_plausible_machine_id

__all__ = [
    "EXPIRES_FORMAT",
    "LICENSE_ALGORITHM",
    "PSS_SALT_LENGTH",
    "LicenseDocument",
    "LicenseError",
    "VerificationResult",
    "canonical_json",
    "check_license_document",
    "check_license_file",
    "default_license_paths",
    "get_machine_id",
    "is_plausible_machine_id",
    "locate_license_file",
    "unsigned_payload",
    "validate_license_document",
    "verify_license_document",
    "verify_license_file",
]
