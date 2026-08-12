# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-12

### Changed

- **Breaking:** license documents are now flat signed JSON (desktop-product
  protocol), not a versioned envelope. Fields: `product`, `licensee`,
  `email`, `license_type`, `expires` (`YYYY-MM-DD`), `features` (array),
  `machine_id`, optional `key_id` / `organization`, plus `signature`.
- **Breaking:** RSA-PSS salt length is 32 (was `MAX_LENGTH`), matching the
  product issuer.
- **Breaking:** CLI flag `--app-id` replaced by `--product`.
- Machine binding is mandatory: Windows WMI fingerprint
  (UUID + baseboard + BIOS serial, normalized), with mac/hostname fallback.

### Added

- `get_machine_id()` / `arnas-verify --print-machine-id` for customer→issuer
  machine-ID collection.

## [0.1.0] - 2026-08-12

First public release (envelope-format verifier without machine binding).

Licensed under the PolyForm Noncommercial License 1.0.0, with commercial
licenses available from Arnas Technologies, LLC.
