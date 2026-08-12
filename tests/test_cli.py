from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from arnas_verify.cli import main


@pytest.fixture
def license_file(tmp_path: Path, signed_license: Dict[str, Any]) -> Path:
    path = tmp_path / "license.json"
    path.write_text(json.dumps(signed_license), encoding="utf-8")
    return path


def test_cli_valid_license_exit_0(
    license_file: Path, demo_public_key: Path, capsys: pytest.CaptureFixture
) -> None:
    code = main(
        [
            "--license", str(license_file),
            "--public-key", str(demo_public_key),
            "--app-id", "demo_app",
        ]
    )
    assert code == 0
    assert "valid" in capsys.readouterr().out


def test_cli_wrong_app_id_exit_1(
    license_file: Path, demo_public_key: Path, capsys: pytest.CaptureFixture
) -> None:
    code = main(
        [
            "--license", str(license_file),
            "--public-key", str(demo_public_key),
            "--app-id", "other_app",
        ]
    )
    assert code == 1
    assert "app_id" in capsys.readouterr().err


def test_cli_missing_license_file_exit_1(
    tmp_path: Path, demo_public_key: Path, capsys: pytest.CaptureFixture
) -> None:
    code = main(
        [
            "--license", str(tmp_path / "nope.json"),
            "--public-key", str(demo_public_key),
            "--app-id", "demo_app",
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
            "--app-id", "demo_app",
        ]
    )
    assert code == 1
    assert "key" in capsys.readouterr().err.lower()


def test_cli_corrupt_public_key_exit_1(
    license_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    bad_key = tmp_path / "corrupt.pem"
    bad_key.write_text("this is not a PEM file", encoding="utf-8")
    code = main(
        [
            "--license", str(license_file),
            "--public-key", str(bad_key),
            "--app-id", "demo_app",
        ]
    )
    assert code == 1
    assert "key" in capsys.readouterr().err.lower()


def test_cli_non_rsa_public_key_exit_1(
    license_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    ec_key = ec.generate_private_key(ec.SECP256R1())
    key_path = tmp_path / "ec.pem"
    key_path.write_bytes(
        ec_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    code = main(
        [
            "--license", str(license_file),
            "--public-key", str(key_path),
            "--app-id", "demo_app",
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
        main(["--public-key", str(demo_public_key), "--app-id", "demo_app"])
    assert excinfo.value.code == 2


def test_cli_locates_license_from_standard_location(
    tmp_path: Path,
    signed_license: Dict[str, Any],
    demo_public_key: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    # First search root is %LOCALAPPDATA% on Windows, $XDG_DATA_HOME elsewhere.
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    target = tmp_path / "DemoVendor" / "demo_app"
    target.mkdir(parents=True)
    (target / "license.json").write_text(
        json.dumps(signed_license), encoding="utf-8"
    )

    code = main(
        [
            "--public-key", str(demo_public_key),
            "--app-id", "demo_app",
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
            "--app-id", "demo_app",
            "--vendor", "DemoVendor",
        ]
    )
    assert code == 1
    assert "No license file found" in capsys.readouterr().err
