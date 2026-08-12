from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from arnas_verify.cli import main
from arnas_verify.demo_issuance import build_license_document, sign_license_document
from arnas_verify.machine import get_machine_id


@pytest.fixture
def license_file(tmp_path: Path, demo_private_key: Path) -> Path:
    """License bound to this machine so the CLI can verify without overrides."""
    doc = build_license_document(
        product="demo_app",
        licensee="Demo Customer",
        machine_id=get_machine_id(),
        expires="2100-01-01",
    )
    signed = sign_license_document(doc, demo_private_key)
    path = tmp_path / "license.json"
    path.write_text(json.dumps(signed), encoding="utf-8")
    return path


def test_cli_print_machine_id(capsys: pytest.CaptureFixture) -> None:
    code = main(["--print-machine-id"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert out == get_machine_id()


def test_cli_valid_license_exit_0(
    license_file: Path, demo_public_key: Path, capsys: pytest.CaptureFixture
) -> None:
    code = main(
        [
            "--license", str(license_file),
            "--public-key", str(demo_public_key),
            "--product", "demo_app",
        ]
    )
    assert code == 0
    assert "valid" in capsys.readouterr().out


def test_cli_wrong_product_exit_1(
    license_file: Path, demo_public_key: Path, capsys: pytest.CaptureFixture
) -> None:
    code = main(
        [
            "--license", str(license_file),
            "--public-key", str(demo_public_key),
            "--product", "other_app",
        ]
    )
    assert code == 1
    assert "product" in capsys.readouterr().err


def test_cli_missing_license_file_exit_1(
    tmp_path: Path, demo_public_key: Path, capsys: pytest.CaptureFixture
) -> None:
    code = main(
        [
            "--license", str(tmp_path / "nope.json"),
            "--public-key", str(demo_public_key),
            "--product", "demo_app",
        ]
    )
    assert code == 1
    assert "read" in capsys.readouterr().err


def test_cli_missing_public_key_exit_1(
    license_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    code = main(
        [
            "--license", str(license_file),
            "--public-key", str(tmp_path / "no_key.pem"),
            "--product", "demo_app",
        ]
    )
    assert code == 1
    assert "key" in capsys.readouterr().err.lower()


def test_cli_missing_required_arg_exits_2(license_file: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--license", str(license_file)])
    assert excinfo.value.code == 2


def test_cli_no_license_requires_vendor(demo_public_key: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--public-key", str(demo_public_key), "--product", "demo_app"])
    assert excinfo.value.code == 2


def test_cli_locates_license_from_standard_location(
    tmp_path: Path,
    demo_private_key: Path,
    demo_public_key: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    doc = build_license_document(
        product="demo_app",
        licensee="Demo",
        machine_id=get_machine_id(),
        expires="2100-01-01",
    )
    signed = sign_license_document(doc, demo_private_key)
    target = tmp_path / "DemoVendor" / "demo_app"
    target.mkdir(parents=True)
    (target / "license.json").write_text(json.dumps(signed), encoding="utf-8")

    code = main(
        [
            "--public-key", str(demo_public_key),
            "--product", "demo_app",
            "--vendor", "DemoVendor",
        ]
    )
    assert code == 0
    assert "valid" in capsys.readouterr().out


def test_cli_locate_not_found_exit_1(
    tmp_path: Path,
    demo_public_key: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    code = main(
        [
            "--public-key", str(demo_public_key),
            "--product", "demo_app",
            "--vendor", "DemoVendor",
        ]
    )
    assert code == 1
    assert "No license file found" in capsys.readouterr().err
