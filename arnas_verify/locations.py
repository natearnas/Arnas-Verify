"""Standard on-disk locations for license files.

Where a license file is *placed* — machine-wide (one license shared by every
user of the machine) or per-user — is a deployment decision made by each
product's installer, not by this library. This module standardizes only the
*lookup*: the ordered list of places a verifier looks, per-user first, then
machine-wide, so products and the CLI agree on the convention.

Nothing here reads the network or writes to disk.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional


def default_license_paths(
    app_id: str, *, vendor: str, filename: str = "license.json"
) -> List[Path]:
    """Return the ordered candidate paths for a product's license file.

    Per-user locations come first so a user-specific license can override a
    machine-wide one:

    - Windows: ``%LOCALAPPDATA%\\<vendor>\\<app_id>\\<filename>`` then
      ``%PROGRAMDATA%\\<vendor>\\<app_id>\\<filename>``.
    - Other platforms: ``$XDG_DATA_HOME`` (default ``~/.local/share``) then
      ``/etc``, each with ``<vendor>/<app_id>/<filename>`` appended.

    This is a pure function of the environment; it does not touch the disk.
    """
    candidates: List[Path] = []
    if sys.platform == "win32":
        per_user_root = os.environ.get("LOCALAPPDATA")
        machine_root = os.environ.get("PROGRAMDATA")
        if per_user_root:
            candidates.append(Path(per_user_root) / vendor / app_id / filename)
        if machine_root:
            candidates.append(Path(machine_root) / vendor / app_id / filename)
    else:
        data_home = os.environ.get("XDG_DATA_HOME")
        per_user_root = Path(data_home) if data_home else Path.home() / ".local" / "share"
        candidates.append(per_user_root / vendor / app_id / filename)
        candidates.append(Path("/etc") / vendor / app_id / filename)
    return candidates


def locate_license_file(
    app_id: str, *, vendor: str, filename: str = "license.json"
) -> Optional[Path]:
    """Return the first existing license file among the standard locations.

    Returns ``None`` when no candidate exists. Existence is the only check
    performed here; validation is the verifier's job.
    """
    for candidate in default_license_paths(app_id, vendor=vendor, filename=filename):
        if candidate.is_file():
            return candidate
    return None
