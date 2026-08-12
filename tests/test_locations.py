from __future__ import annotations

import sys
from pathlib import Path

import pytest

from arnas_verify.locations import default_license_paths, locate_license_file


def test_windows_candidate_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\demo\AppData\Local")
    monkeypatch.setenv("PROGRAMDATA", r"C:\ProgramData")

    paths = default_license_paths("my_app", vendor="MyVendor")
    assert len(paths) == 2
    assert paths[0] == Path(r"C:\Users\demo\AppData\Local") / "MyVendor" / "my_app" / "license.json"
    assert paths[1] == Path(r"C:\ProgramData") / "MyVendor" / "my_app" / "license.json"


def test_posix_candidate_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "/home/demo/.local/share")

    paths = default_license_paths("my_app", vendor="MyVendor")
    assert len(paths) == 2
    assert paths[0] == Path("/home/demo/.local/share") / "MyVendor" / "my_app" / "license.json"
    assert paths[1] == Path("/etc") / "MyVendor" / "my_app" / "license.json"


def test_custom_filename(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "/data")
    paths = default_license_paths("app", vendor="V", filename="pro.lic")
    assert all(p.name == "pro.lic" for p in paths)


def test_locate_returns_first_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    per_user = tmp_path / "per_user"
    machine = tmp_path / "machine"
    for root in (per_user, machine):
        target = root / "MyVendor" / "my_app"
        target.mkdir(parents=True)
        (target / "license.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("LOCALAPPDATA", str(per_user))
    monkeypatch.setenv("PROGRAMDATA", str(machine))
    monkeypatch.setenv("XDG_DATA_HOME", str(per_user))

    found = locate_license_file("my_app", vendor="MyVendor")
    assert found is not None
    # Per-user candidate wins over machine-wide when both exist.
    assert found == per_user / "MyVendor" / "my_app" / "license.json"


def test_locate_returns_none_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert locate_license_file("my_app", vendor="MyVendor") is None


def test_posix_xdg_unset_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: Path("/home/demo"))

    paths = default_license_paths("my_app", vendor="MyVendor")
    assert paths[0] == (
        Path("/home/demo") / ".local" / "share" / "MyVendor" / "my_app" / "license.json"
    )
    assert paths[1] == Path("/etc") / "MyVendor" / "my_app" / "license.json"


def test_windows_unset_env_vars_skip_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setenv("PROGRAMDATA", r"C:\ProgramData")
    paths = default_license_paths("my_app", vendor="MyVendor")
    assert paths == [Path(r"C:\ProgramData") / "MyVendor" / "my_app" / "license.json"]

    monkeypatch.delenv("PROGRAMDATA", raising=False)
    assert default_license_paths("my_app", vendor="MyVendor") == []
    # locate must degrade gracefully, not raise, when nothing is configured.
    assert locate_license_file("my_app", vendor="MyVendor") is None
