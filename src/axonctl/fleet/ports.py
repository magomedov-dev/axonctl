"""Local port allocation for adb forwards.

Hands out a distinct local TCP port per device serial from a configured range
and tracks the assignment so it can be reused for ``remove_forward`` and freed on
detach. One allocator per :class:`~axonctl.FleetController`.
"""

from __future__ import annotations


class PortAllocator:
    """Allocates local ports from an inclusive range, one per serial."""

    def __init__(self, port_range: tuple[int, int]) -> None:
        """Initialize the allocator.

        Args:
            port_range: Inclusive ``(start, end)`` range of local ports.
        """
        self._start, self._end = port_range
        self._by_serial: dict[str, int] = {}
        self._used: set[int] = set()

    def acquire(self, serial: str) -> int:
        """Return a port for ``serial``, allocating one if needed.

        Args:
            serial: Device serial.

        Returns:
            The allocated local port (stable for the serial until released).

        Raises:
            RuntimeError: If the range is exhausted.
        """
        existing = self._by_serial.get(serial)
        if existing is not None:
            return existing
        for port in range(self._start, self._end + 1):
            if port not in self._used:
                self._used.add(port)
                self._by_serial[serial] = port
                return port
        raise RuntimeError(f"no free port in range {self._start}-{self._end}")

    def release(self, serial: str) -> int | None:
        """Free the port held by ``serial``.

        Args:
            serial: Device serial.

        Returns:
            The freed port, or ``None`` if the serial held none.
        """
        port = self._by_serial.pop(serial, None)
        if port is not None:
            self._used.discard(port)
        return port

    def port_for(self, serial: str) -> int | None:
        """Return the port currently held by ``serial`` (or ``None``)."""
        return self._by_serial.get(serial)
