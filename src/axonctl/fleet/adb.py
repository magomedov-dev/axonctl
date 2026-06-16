"""adb bridge.

A thin async wrapper over ``adbutils`` for the host-side operations the agent does
not do: port forwarding, shell, app launch/stop, and install. ``adbutils`` is
synchronous, so every call is offloaded to a worker thread to keep the event loop
free.

The adb binary is resolved as ``$AXONCTL_ADB`` -> ``.tooling/platform-tools/adb``
-> ``adb`` on ``PATH`` (see ``scripts/install-adb.sh``).
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Protocol

import adbutils


class Adb(Protocol):
    """Host-side adb operations needed by the fleet and devices."""

    async def forward(self, serial: str, local_port: int, remote_port: int) -> None:
        """Create a ``tcp:local -> tcp:remote`` forward for ``serial``."""
        ...

    async def remove_forward(self, serial: str, local_port: int) -> None:
        """Remove the ``tcp:local`` forward for ``serial``."""
        ...

    async def shell(self, serial: str, command: str) -> str:
        """Run a shell command on ``serial`` and return its output."""
        ...

    async def launch(self, serial: str, package: str) -> None:
        """Launch ``package`` on ``serial``."""
        ...

    async def force_stop(self, serial: str, package: str) -> None:
        """Force-stop ``package`` on ``serial``."""
        ...

    async def install(self, serial: str, apk_path: str) -> None:
        """Install an APK onto ``serial``."""
        ...


def resolve_adb_path(explicit: str | None = None) -> str | None:
    """Resolve the adb binary path.

    Order: ``explicit`` arg, ``$AXONCTL_ADB``, ``.tooling/platform-tools/adb``
    (relative to the current directory), then ``adb`` on ``PATH``.

    Args:
        explicit: An explicit path to prefer.

    Returns:
        The resolved path, or ``None`` if adb could not be found.
    """
    candidates = [
        explicit,
        os.environ.get("AXONCTL_ADB"),
        str(Path(".tooling/platform-tools/adb")),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return shutil.which("adb")


class AdbBridge:
    """An :class:`Adb` implementation backed by ``adbutils``."""

    def __init__(self, adb_path: str | None = None) -> None:
        """Initialize the bridge.

        Args:
            adb_path: Explicit adb binary path; resolved if omitted.
        """
        resolved = resolve_adb_path(adb_path)
        if resolved:
            # adbutils starts/locates the adb server using this binary.
            os.environ.setdefault("ADBUTILS_ADB_PATH", resolved)
        self._client = adbutils.AdbClient()

    def _device(self, serial: str) -> adbutils.AdbDevice:
        return self._client.device(serial)

    async def forward(self, serial: str, local_port: int, remote_port: int) -> None:
        await asyncio.to_thread(
            self._device(serial).forward, f"tcp:{local_port}", f"tcp:{remote_port}"
        )

    async def remove_forward(self, serial: str, local_port: int) -> None:
        await asyncio.to_thread(
            self._device(serial).forward_remove, f"tcp:{local_port}", False
        )

    async def shell(self, serial: str, command: str) -> str:
        result = await asyncio.to_thread(self._device(serial).shell, command)
        return str(result)

    async def launch(self, serial: str, package: str) -> None:
        await asyncio.to_thread(self._device(serial).app_start, package)

    async def force_stop(self, serial: str, package: str) -> None:
        await asyncio.to_thread(self._device(serial).app_stop, package)

    async def install(self, serial: str, apk_path: str) -> None:
        await asyncio.to_thread(self._device(serial).install, apk_path)
