"""Machine fingerprint for license binding.

Matches the desktop product strategy:

- **Windows (preferred):** SHA-256 hex (64 chars) of
  ``normalize(UUID) + "|" + normalize(BaseBoard serial) + "|" + normalize(BIOS serial)``
  from WMI ``Win32_ComputerSystemProduct``, ``Win32_BaseBoard``, and
  ``Win32_BIOS``. Normalization keeps alphanumeric characters and uppercases
  them (same rules as the native fingerprint used in shipping builds).
- **Fallback (non-Windows, or WMI unavailable):** first 32 hex chars of
  SHA-256(``mac-hostname``), for development and CI.

The customer reports this ID; the issuer embeds it in the signed license; the
verifier rejects a mismatch. Nothing here phones home.
"""

from __future__ import annotations

import hashlib
import platform
import re
import subprocess
import uuid


def _normalize_component(value: str) -> str:
    """Keep alphanumeric characters and uppercase — matches native normalize."""
    return "".join(ch.upper() for ch in value if ch.isalnum())


def _legacy_machine_id() -> str:
    """Dev/CI fallback used when a native/WMI fingerprint is unavailable."""
    mac = hex(uuid.getnode())
    hostname = platform.node()
    raw = f"{mac}-{hostname}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def _wmi_machine_id_windows() -> str | None:
    """Return the WMI hardware fingerprint on Windows, or None on failure."""
    if platform.system() != "Windows":
        return None
    script = (
        "$ErrorActionPreference='Stop'; "
        "$u=(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID; "
        "$b=(Get-CimInstance -ClassName Win32_BaseBoard).SerialNumber; "
        "$s=(Get-CimInstance -ClassName Win32_BIOS).SerialNumber; "
        "Write-Output $u; Write-Output $b; Write-Output $s"
    )
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return None

    lines = [ln.strip() for ln in completed.stdout.splitlines() if ln.strip()]
    if len(lines) < 3:
        return None
    uuid_s, board_s, bios_s = lines[0], lines[1], lines[2]
    normalized = (
        _normalize_component(uuid_s)
        + "|"
        + _normalize_component(board_s)
        + "|"
        + _normalize_component(bios_s)
    )
    if not normalized.replace("|", ""):
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


_MACHINE_ID_RE = re.compile(r"^[0-9a-f]{32}$|^[0-9a-f]{64}$")


def is_plausible_machine_id(value: str) -> bool:
    """True if ``value`` looks like a legacy (32) or WMI (64) hex fingerprint."""
    return bool(_MACHINE_ID_RE.fullmatch(value))


def get_machine_id() -> str:
    """Return this computer's machine ID for license binding."""
    wmi_id = _wmi_machine_id_windows()
    if wmi_id is not None:
        return wmi_id
    return _legacy_machine_id()
