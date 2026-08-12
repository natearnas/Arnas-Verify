# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-12

Public reference release of Arnas Verify: offline, **computer-locked**
(machine-bound) signed license verification.

### Added

- Verifier library for flat signed JSON licenses: RSA-PSS-SHA256 (PSS salt
  length 32) over canonical JSON, with **product** binding, mandatory
  **machine_id** binding, and calendar expiry (`YYYY-MM-DD`).
- Machine fingerprint helper (`get_machine_id` / `arnas-verify
  --print-machine-id`): Windows WMI hardware fingerprint (UUID + baseboard +
  BIOS serial), with portable mac/hostname fallback for other platforms and
  CI.
- Standard license-file lookup locations (per-user first, then machine-wide)
  for Windows and POSIX systems.
- `arnas-verify` CLI with documented exit codes.
- Intentionally committed demo keypair, demo-only issuance module, and a
  signed example license.
- Deployment-hardening guidance (build-time public-key embedding, private-key
  custody, native verify, issuer ledger).
- Test suite covering cryptographic, structural, machine-binding, CLI, and
  location behavior.

Licensed under the PolyForm Noncommercial License 1.0.0, with commercial
licenses available from Arnas Technologies, LLC.
