# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately:

- Preferred: GitHub private vulnerability reporting on this repository
  ("Report a vulnerability" under the Security tab).
- Alternatively: the contact form at <https://arnastech.com>.

Reports are handled on a best-effort basis (see [SUPPORT.md](SUPPORT.md)).
Only the latest release is supported.

## In scope

Ways the verifier could be made to **accept an invalid document**, for
example:

- Signature verification bypass or downgrade.
- Canonicalization ambiguity that lets two different payloads verify against
  one signature, or lets signer and verifier disagree about the signed bytes.
- Product-binding, machine-binding, expiry, or payload-validation bypass.
- Crashes on untrusted input — the verifier must fail closed with a reason.

## Out of scope — not vulnerabilities

- **Anything premised on possessing `demo_keys/private_key.pem`.** The demo
  keypair is intentionally public and carries no trust; producing a "valid"
  demo-signed license is the documented purpose of that key. The demo keypair
  is not the trust root of any Arnas Technologies product.
- The documented threat-model exclusions in the README: binary patching of
  the verifying application, system clock rollback, hardware/VM fingerprint
  spoofing, and the absence of revocation.
