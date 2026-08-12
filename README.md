# Arnas Verify

[![Tests](https://github.com/natearnas/Arnas-Verify/actions/workflows/test.yml/badge.svg)](https://github.com/natearnas/Arnas-Verify/actions/workflows/test.yml)

A **reference implementation** of local, offline, signed per-application
license verification in Python. Educational and verifier-side only: this repo
shows how a desktop application can validate a signed JSON license file
against an embedded public key — enforcing signature integrity, app binding,
and expiry — without any network access. Arnas Verify is published by
[Arnas Technologies](https://arnastech.com), maker of scientific imaging
software.

## What this is — and deliberately is not

This is:

- A minimal, production-quality **verifier** library (`arnas_verify`).
- A CLI (`arnas-verify`) for checking a license file.
- Demo keys, a sample signed license, and a pytest suite.

This is deliberately **not**:

- The live licensing system of any shipping product.
- A production signing authority. Real issuance (private keys, customer
  ledger, signing service) lives in a separate **private** project and is not
  part of this repository.
- A remote activation system. There is no server, no telemetry, no network
  code anywhere in this package.

The demo keypair in `demo_keys/` — including the **private** key — is
committed on purpose so the examples and tests work out of the box. It
confers no trust; see [demo_keys/README.md](demo_keys/README.md).

## Getting started

Arnas Verify runs on **Windows, Linux, and macOS** — it is pure Python with a
single dependency (`cryptography`, prebuilt wheels, no compiler needed), and
the license-lookup convention has both Windows and POSIX paths built in.

### 1. Prerequisites

- Python 3.10 or newer (`python --version` to check; on some systems the
  command is `python3` or `py`)
- git
- No administrator rights required.

### 2. Set up an environment and install

Windows (PowerShell):

```powershell
git clone https://github.com/natearnas/Arnas-Verify.git
cd Arnas-Verify
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Linux / macOS (bash):

```bash
git clone https://github.com/natearnas/Arnas-Verify.git
cd Arnas-Verify
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

To use the library in your own project without cloning, install straight
from GitHub instead:

```bash
python -m pip install "git+https://github.com/natearnas/Arnas-Verify.git"
```

### 3. Verify the install

```bash
python -m pytest
```

Expect `48 passed`. Then verify the bundled example license:

```bash
arnas-verify --license examples/example_license.json --public-key demo_keys/public_key.pem --app-id demo_app
```

Expected output:

```text
License valid for app 'demo_app'.
```

### 4. Use your own keys

```bash
python demo_keys/generate_demo_keys.py     # fresh RSA keypair (overwrites the demo pair)
python scripts/build_demo_license.py       # sign a new example license with it
arnas-verify --license examples/example_license.json --public-key demo_keys/public_key.pem --app-id demo_app
```

In a real deployment, the private key never touches the shipped product or a
public repository: issuance happens in a private signing authority, and only
the public key ships with the application. See "Architecture and trust
model" below.

### 5. Troubleshooting

- PowerShell refuses to activate the venv: run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then retry.
- `python` not found on Windows: try `py` (the Python launcher).
- `cryptography` installs from a prebuilt wheel on all supported platforms —
  if pip tries to compile it, your Python or pip is likely very old; upgrade
  pip first.

## CLI usage

```text
arnas-verify --license <path> --public-key <path> --app-id <id> [--vendor <name>]
```

- `--license` — path to the signed license JSON file. If omitted, the
  standard per-user and machine-wide locations are searched (requires
  `--vendor`; see "Where the license file lives").
- `--public-key` — path to the trusted public key (PEM).
- `--app-id` — the application identifier the license must be bound to.
- `--vendor` — vendor name used for the standard-location search.

On failure the CLI prints the specific reason to stderr:

```text
License invalid for app 'other_app': app_id mismatch: expected 'other_app', got 'demo_app'
```

Exit codes: `0` license valid · `1` license invalid, not found, or key/file
error · `2` usage error.

## Library usage

```python
from arnas_verify import check_license_file

result = check_license_file(
    "examples/example_license.json",
    "demo_keys/public_key.pem",
    app_id="demo_app",
)

if not result.ok:
    raise RuntimeError(f"License is invalid: {result.reason}")
```

`check_license_file` / `check_license_document` return a `VerificationResult`
with `ok` and a human-readable `reason` on failure. Boolean wrappers
(`verify_license_file`, `validate_license_document`) exist for call sites
that only need pass/fail. `app_id` is always required at the file level, so a
valid signature alone never passes a full check. Only
`verify_license_document` checks the bare envelope + signature, and says so
in its name.

## License document format

A license is a JSON envelope around a signed payload:

```json
{
  "payload": {
    "app_id": "demo_app",
    "customer": "Demo Customer",
    "features": {"tier": "trial", "seats": 1},
    "issued_at": "2026-08-11T23:38:24Z",
    "expires_at": "2100-01-01T00:00:00Z",
    "nonce": "8LjlnALvKGtnKCyfzddDVA"
  },
  "signature": "<base64 RSA-PSS-SHA256 signature>",
  "algorithm": "RSA-PSS-SHA256",
  "version": 1
}
```

| Payload field | Type   | Meaning                                        |
| ------------- | ------ | ---------------------------------------------- |
| `app_id`      | string | Application this license is bound to           |
| `customer`    | string | Licensee display name                          |
| `features`    | object | Free-form feature flags / entitlements         |
| `issued_at`   | string | UTC timestamp, `YYYY-MM-DDTHH:MM:SSZ`          |
| `expires_at`  | string | UTC timestamp, `YYYY-MM-DDTHH:MM:SSZ`          |
| `nonce`       | string | Random value making each issued document unique |

The signature covers the **canonical JSON** form of the payload: compact
separators, lexicographically sorted keys, UTF-8, strictly finite numbers
(no `NaN`/`Infinity`) — `canonical_json()` in `license.py`, one definition
shared by signer and verifier so they cannot drift.

## Architecture and trust model

```text
arnas_verify/
  license.py        <- verification: the part a product ships
  locations.py      <- standard license-file lookup paths
  cli.py            <- command-line wrapper
  demo_issuance.py  <- DEMO-ONLY signing; production equivalent is private
```

- The **trust root** is a public key embedded in (or shipped with) the
  application. Whoever holds the matching private key is the licensing
  authority.
- In this repo that keypair is a worthless demo pair. In a real deployment
  the private key never leaves the private signing authority; the public repo
  and the shipped product contain only the public key.
- `demo_issuance` is not re-exported from the package root: code that issues
  licenses must `import arnas_verify.demo_issuance` explicitly, keeping the
  shipped surface verification-only.

Validation order in `check_license_document`:

1. Envelope shape (`payload` object, `signature` string).
2. `version` is `1` and `algorithm` is `RSA-PSS-SHA256`.
3. RSA-PSS-SHA256 signature over the canonical payload JSON. Everything after
   this step operates on authenticated data only.
4. Payload structure (all required fields present with correct types).
5. App binding (`app_id` matches).
6. Timestamp format, `issued_at` not in the future (beyond a 5-minute
   clock-skew leeway), `expires_at` not passed.

The first failed check produces a `VerificationResult` with a reason;
problems with the public key itself (missing file, corrupt PEM) raise
instead, because they are deployment errors rather than untrusted input.

## Where the license file lives

Whether a product uses **machine-wide** licensing (one license for every user
of the machine) or **per-user** licensing is a deployment decision made by
each product's installer — not by this library. A machine-wide install
typically writes to a shared location and needs admin rights once; a per-user
install writes to the user profile and needs none.

The library standardizes only the **lookup order**, per-user first so a
user-specific license can override a machine-wide one:

| Platform | Per-user (checked first)                    | Machine-wide                       |
| -------- | ------------------------------------------- | ---------------------------------- |
| Windows  | `%LOCALAPPDATA%\<vendor>\<app_id>\`         | `%PROGRAMDATA%\<vendor>\<app_id>\` |
| Other    | `$XDG_DATA_HOME/<vendor>/<app_id>/` (default `~/.local/share/...`) | `/etc/<vendor>/<app_id>/` |

The file searched for is named `license.json` by default (customizable via
the `filename=` keyword). `default_license_paths(app_id, vendor=...)` returns
the ordered candidates; `locate_license_file(app_id, vendor=...)` returns the
first that exists. The CLI uses the same convention when `--license` is
omitted.

## Threat model and limitations

Offline signature verification stops:

- **Forged licenses** — no private key, no valid signature.
- **Tampered licenses** — any payload edit invalidates the signature.
- **Cross-app reuse** — a license for one `app_id` fails for another.
- **Expired licenses** — under an honest system clock.

It cannot stop, by design:

- **Binary patching** — an attacker who modifies the shipped application can
  bypass any local check or swap the embedded public key.
- **Clock rollback** — expiry enforcement trusts the system clock.
- **License copying** — a valid license file works on any machine; there is
  no machine binding here.
- **Revocation** — with no network there is no way to revoke an issued
  license before it expires.

These are out of scope for this reference implementation; treat local
verification as a honest-user convention, not DRM.

One consequence worth spelling out: the demo keypair in `demo_keys/` —
private key included — is intentionally public and carries no trust. A
"forged" license signed with the demo private key demonstrates the threat
model working as documented; it is not a vulnerability, and the demo keypair
is not the trust root of any Arnas Technologies product. See
[SECURITY.md](SECURITY.md) for what does count as a reportable issue.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest                          # run the test suite
python demo_keys/generate_demo_keys.py    # regenerate the demo keypair
python scripts/build_demo_license.py      # re-sign examples/example_license.json
```

## Project layout

```text
arnas_verify/         the installable package (verifier, locations, CLI)
demo_keys/            intentionally committed demo keypair + warning README
examples/             sample signed license document
scripts/              demo license regeneration
tests/                pytest suite (crypto, validation, CLI, locations)
CHANGELOG.md          release history
CITATION.cff          citation metadata
CODE_OF_CONDUCT.md    community standards
COMMERCIAL-LICENSE.md commercial licensing contact
CONTRIBUTING.md       how to contribute
SECURITY.md           vulnerability reporting policy
SUPPORT.md            support expectations
```

## Contributing

Small fixes are welcome; for anything nontrivial, open an issue first — this
repo deliberately stays minimal. See [CONTRIBUTING.md](CONTRIBUTING.md),
including the licensing terms for contributions.

## Support

Provided as-is with no support obligation; GitHub Issues are answered
best-effort. Commercial support is available from Arnas Technologies, LLC
via <https://arnastech.com>. See [SUPPORT.md](SUPPORT.md).

## Citation

If you use Arnas Verify in academic work, please cite it —
[CITATION.cff](CITATION.cff) has machine-readable metadata (GitHub renders a
"Cite this repository" button from it).

## Licensing

Arnas Verify is free for **noncommercial use** — including academic research,
teaching, personal projects, and evaluation — under the
[PolyForm Noncommercial License 1.0.0](LICENSE).

**Commercial use requires a separate license** from Arnas Technologies, LLC.
See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md) and get in touch via
<https://arnastech.com>.

This summary is informational, not legal advice; attorney review recommended.
The license text governs.
