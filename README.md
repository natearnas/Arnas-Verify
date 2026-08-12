# Arnas Verify

[![Tests](https://github.com/natearnas/Arnas-Verify/actions/workflows/test.yml/badge.svg)](https://github.com/natearnas/Arnas-Verify/actions/workflows/test.yml)

A **reference implementation** of local, offline, **machine-bound** signed
license verification in Python. It shows how a desktop application validates a
signed JSON license file against an embedded public key — enforcing signature
integrity, product binding, **machine ID binding**, and expiry — with no
network access. Published by [Arnas Technologies](https://arnastech.com).

## What this is — and deliberately is not

This is:

- A minimal, production-quality **verifier** library (`arnas_verify`).
- A CLI (`arnas-verify`) for checking a license file and printing a machine ID.
- The same licensing **protocol** used by Arnas Technologies desktop products:
  flat signed JSON, RSA-PSS-SHA256 (PSS salt length 32), WMI hardware
  fingerprint on Windows (with a portable fallback elsewhere).
- Demo keys, a sample signed license, and a pytest suite.

This is deliberately **not**:

- The live licensing system of any shipping product.
- A production signing authority. Real issuance (private keys, customer
  ledger, signing service) lives in a separate **private** project and is not
  part of this repository.
- A license **issuance** or **entitlement-management** system. Arnas Verify
  does not record licenses issued, customers, or seat counts. Issuers keep
  that ledger themselves — CRM, database, or private tooling — separate from
  this verifier. The verifier **does** enforce the `machine_id` claim that the
  issuer embedded when signing.
- A GUI or operator console for creating and signing licenses. Those belong
  in a private issuance workflow, not in this reference verifier.
- A remote activation system. There is no server, no telemetry, no network
  code anywhere in this package.

The demo keypair in `demo_keys/` — including the **private** key — is
committed on purpose so the examples and tests work out of the box. It
confers no trust; see [demo_keys/README.md](demo_keys/README.md).

## Getting started

Arnas Verify runs on **Windows, Linux, and macOS** — pure Python with a
single dependency (`cryptography`), and license-lookup paths for both Windows
and POSIX.

### 1. Prerequisites

- Python 3.10 or newer
- git
- No administrator rights required

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

### 3. Verify the install

```bash
python -m pytest
arnas-verify --print-machine-id
```

Bind a demo license to **this** computer and verify it:

```bash
python scripts/build_demo_license.py --this-machine
arnas-verify --license examples/example_license.json --public-key demo_keys/public_key.pem --product demo_app
```

Expected output:

```text
License valid for product 'demo_app' on this machine.
```

### 4. Customer → issuer workflow (real deployments)

1. On the target PC, run `arnas-verify --print-machine-id` (or an equivalent
   button in your application) and send that ID to the issuer.
2. The issuer signs a license whose `machine_id` field equals that value.
3. The customer installs the license file; the app verifies signature,
   product, machine ID, and expiry offline.

### 5. Troubleshooting

- PowerShell refuses to activate the venv: run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then retry.
- `python` not found on Windows: try `py`.
- A license valid on one PC fails on another with `machine_id mismatch` —
  that is correct; request a re-issue for the new machine ID.

## CLI usage

```text
arnas-verify --print-machine-id
arnas-verify --license <path> --public-key <path> --product <id> [--vendor <name>]
```

Exit codes: `0` success · `1` invalid / not found / key error · `2` usage error.

## Library usage

```python
from arnas_verify import check_license_file, get_machine_id

print(get_machine_id())  # send this to the issuer

result = check_license_file(
    "path/to/license.json",
    "path/to/public_key.pem",
    product="demo_app",
)

if not result.ok:
    raise RuntimeError(f"License is invalid: {result.reason}")
```

## License document format

A license is a **flat** JSON object. The signature covers every field except
`signature`, serialized as canonical JSON (sorted keys, compact separators):

```json
{
  "email": "demo@example.com",
  "expires": "2100-01-01",
  "features": ["tier:trial"],
  "key_id": "v1",
  "license_type": "trial",
  "licensee": "Demo Customer",
  "machine_id": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "product": "demo_app",
  "signature": "<base64 RSA-PSS-SHA256 signature>"
}
```

| Field | Type | Meaning |
| ----- | ---- | ------- |
| `product` | string | Product this license is bound to |
| `licensee` | string | Licensee display name |
| `email` | string | Contact email (may be empty) |
| `license_type` | string | e.g. `standard`, `academic`, `trial` |
| `expires` | string | Calendar date `YYYY-MM-DD` |
| `machine_id` | string | 32- or 64-char hex fingerprint of the target PC |
| `features` | array | Feature flags / entitlements |
| `key_id` | string | Optional key-rotation label (demo uses `v1`) |
| `signature` | string | Base64 RSA-PSS-SHA256 over the canonical unsigned payload |

**Machine fingerprint**

- **Windows:** SHA-256 (64 hex chars) of
  `normalize(UUID) + "|" + normalize(BaseBoard serial) + "|" + normalize(BIOS serial)`
  from WMI (`Win32_ComputerSystemProduct`, `Win32_BaseBoard`, `Win32_BIOS`).
  Normalization keeps alphanumeric characters and uppercases them.
- **Elsewhere / WMI unavailable:** first 32 hex chars of
  SHA-256(`mac-hostname`) — for development and CI.

## Architecture and trust model

```text
arnas_verify/
  license.py        <- verification (signature, product, machine, expiry)
  machine.py        <- machine fingerprint
  locations.py      <- standard license-file lookup paths
  cli.py            <- command-line wrapper
  demo_issuance.py  <- DEMO-ONLY signing; production equivalent is private
```

Validation order in `check_license_document`:

1. RSA-PSS-SHA256 signature (PSS salt length 32) over canonical unsigned JSON.
2. Payload structure (required fields and types).
3. Product binding.
4. Machine ID binding (must match this computer unless overridden in tests).
5. Expiry (`expires` date not in the past).

## Where the license file lives

Lookupers choose per-user vs machine-wide placement. Lookup order is per-user
first, then machine-wide:

| Platform | Per-user (checked first) | Machine-wide |
| -------- | ------------------------ | ------------ |
| Windows  | `%LOCALAPPDATA%\<vendor>\<product>\` | `%PROGRAMDATA%\<vendor>\<product>\` |
| Other    | `$XDG_DATA_HOME/<vendor>/<product>/` | `/etc/<vendor>/<product>/` |

Default filename: `license.json`.

## Threat model and limitations

Offline verification stops:

- **Forged licenses** — no private key, no valid signature.
- **Tampered licenses** — any field edit invalidates the signature.
- **Cross-product reuse** — wrong `product` fails.
- **Copied licenses** — wrong `machine_id` fails on another computer.
- **Expired licenses** — under an honest system clock.

It cannot stop, by design:

- **Binary patching** of the verifying application or embedded public key.
- **Clock rollback**.
- **Hardware / VM spoofing** of the fingerprint inputs.
- **Central license inventory** — no built-in customer ledger in this repo.
- **Revocation** before expiry without a network path.

Treat local verification as an honest-user convention, not DRM. The demo
keypair is intentionally public and trust-free; see [SECURITY.md](SECURITY.md).

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python demo_keys/generate_demo_keys.py
python scripts/build_demo_license.py              # stable demo machine_id
python scripts/build_demo_license.py --this-machine
```

## Project layout

```text
arnas_verify/         verifier, machine fingerprint, locations, CLI
demo_keys/            intentionally committed demo keypair + warning README
examples/             sample signed license document
scripts/              demo license regeneration
tests/                pytest suite
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Support

See [SUPPORT.md](SUPPORT.md). Commercial support: <https://arnastech.com>.

## Citation

See [CITATION.cff](CITATION.cff).

## Licensing

Arnas Verify is free for **noncommercial use** under the
[PolyForm Noncommercial License 1.0.0](LICENSE).

**Commercial use requires a separate license** from Arnas Technologies, LLC.
See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

This summary is informational, not legal advice; attorney review recommended.
The license text governs.
