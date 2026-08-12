# Contributing

Arnas Verify is a deliberately small reference implementation. The bar for
new features is high: please open an issue to discuss before writing a
nontrivial pull request. Scope-expanding features (network activation,
machine binding, plugin systems) will usually be declined — the point of
this repo is to stay readable.

## Development setup

Windows (PowerShell):

```powershell
git clone https://github.com/natearnas/Arnas-Verify.git
cd Arnas-Verify
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Linux / macOS (bash):

```bash
git clone https://github.com/natearnas/Arnas-Verify.git
cd Arnas-Verify
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

All 48 tests should pass before and after your change.

## Expectations

- Tests stay green on Windows, Linux, and macOS (CI runs all three).
- New behavior comes with tests.
- No new runtime dependencies without prior discussion — the package is
  deliberately stdlib + `cryptography` only.
- Match the existing fully-typed, documented style.

## Licensing of contributions

By submitting a contribution you certify that you have the right to submit
it, and you agree that Arnas Technologies, LLC may license your contribution
under this repository's license and under any commercial license it offers
for this software.
