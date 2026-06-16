"""Screen-state tracker.

Holds the latest ``screen`` generation and foreground ``package`` seen for a
device, updated from both ``screenChanged`` events and dumps. ``screen`` is
monotonic, so a newer value means "something changed — a fresh dump may be
warranted". Informational; each wait tracks its own baseline locally.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScreenState:
    """Last known screen generation and foreground package.

    Attributes:
        screen: Latest screen generation (-1 until first observed).
        package: Latest foreground package, or ``None`` if unknown.
    """

    screen: int = -1
    package: str | None = None

    def observe(self, screen: int, package: str | None) -> None:
        """Record an observation, keeping the highest ``screen`` seen.

        Args:
            screen: Observed screen generation.
            package: Observed foreground package (ignored if empty).
        """
        if screen >= self.screen:
            self.screen = screen
            if package:
                self.package = package
