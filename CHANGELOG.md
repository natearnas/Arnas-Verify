# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-12

First public release.

### Added

- Verifier library: RSA-PSS-SHA256 over canonical JSON with app binding,
  expiry (with clock-skew leeway), structured payload validation, and
  reasoned `VerificationResult` failures.
- Standard license-file lookup locations (per-user first, then machine-wide)
  for Windows and POSIX systems.
- `arnas-verify` command-line interface with documented exit codes.
- Intentionally committed demo keypair, demo-only issuance module, and a
  signed example license.
- Test suite (48 tests) covering cryptographic, structural, CLI, and
  location behavior.

Licensed under the PolyForm Noncommercial License 1.0.0, with commercial
licenses available from Arnas Technologies, LLC.
