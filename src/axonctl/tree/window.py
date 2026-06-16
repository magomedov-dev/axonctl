"""Window model.

Parses the ``getWindows`` result into a :class:`WindowList` of :class:`Window`
objects covering *all* interactive windows — application, IME, system bars,
dialogs, overlays, split-screen — not just the active one. Windows are kept
topmost-first (the agent sorts by descending layer). Pure parsing, no I/O.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .geom import Bounds
from .tree import UiTree

#: Window kinds reported by the agent.
WindowType = Literal[
    "application",
    "inputMethod",
    "system",
    "accessibilityOverlay",
    "splitScreenDivider",
    "magnification",
    "unknown",
]


@dataclass(slots=True)
class Window:
    """A single interactive window.

    Attributes:
        window_id: Stable id for this window (usable as ``window_id`` in dumps
            and node actions).
        type: The window kind.
        layer: Z-order layer (higher is closer to the top).
        active: Whether this is the active window.
        focused: Whether this window has input focus.
        title: Window title, or ``None`` for system windows.
        package: Owning package, or ``None`` for system windows.
        bounds: Window rectangle, or ``None`` if absent.
        root: The window's UI tree, present only when dumped with
            ``include_tree=True``.
    """

    window_id: int
    type: WindowType
    layer: int
    active: bool
    focused: bool
    title: str | None
    package: str | None
    bounds: Bounds | None
    root: UiTree | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, screen: int) -> Window:
        """Parse a :class:`Window` from one entry of ``getWindows``.

        Args:
            data: A single window object.
            screen: The screen generation from the enclosing ``getWindows``
                result, attached to ``root`` when present.

        Returns:
            The parsed window.
        """
        bounds_raw = data.get("bounds")
        bounds = Bounds.from_dict(bounds_raw) if bounds_raw is not None else None
        package = data.get("package")
        root_raw = data.get("root")
        root = (
            UiTree.from_node_dict(root_raw, screen=screen, package=package or "")
            if root_raw is not None
            else None
        )
        return cls(
            window_id=int(data["windowId"]),
            type=data.get("type", "unknown"),
            layer=int(data.get("layer", 0)),
            active=bool(data.get("active", False)),
            focused=bool(data.get("focused", False)),
            title=data.get("title"),
            package=package,
            bounds=bounds,
            root=root,
        )


@dataclass(slots=True)
class WindowList:
    """All windows from one ``getWindows`` call, topmost first.

    Attributes:
        screen: Screen generation at enumeration time.
        windows: Windows ordered by descending layer (topmost first).
    """

    screen: int
    windows: list[Window]

    def __iter__(self) -> Iterator[Window]:
        return iter(self.windows)

    def __len__(self) -> int:
        return len(self.windows)

    def active(self) -> Window | None:
        """Return the active window, or ``None``."""
        return next((w for w in self.windows if w.active), None)

    def focused(self) -> Window | None:
        """Return the focused window, or ``None``."""
        return next((w for w in self.windows if w.focused), None)

    def by_type(self, window_type: WindowType) -> list[Window]:
        """Return all windows of ``window_type`` (topmost first).

        Args:
            window_type: The kind to filter by.

        Returns:
            Matching windows in top-to-bottom order.
        """
        return [w for w in self.windows if w.type == window_type]

    def ime(self) -> list[Window]:
        """Return input-method (keyboard) windows."""
        return self.by_type("inputMethod")

    def dialogs(self) -> list[Window]:
        """Return dialog-like windows (heuristic).

        Application windows stacked above the backmost application window — i.e.
        modal dialogs/popups over the base app. Returns an empty list when there
        is at most one application window.

        Returns:
            Application windows above the base app, topmost first.
        """
        apps = self.by_type("application")
        return apps[:-1] if len(apps) > 1 else []

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WindowList:
        """Parse a :class:`WindowList` from a ``getWindows`` result.

        Args:
            data: The ``result`` object with ``screen`` and ``windows``.

        Returns:
            The parsed window list (order preserved: topmost first).
        """
        screen = int(data["screen"])
        windows = [Window.from_dict(w, screen=screen) for w in data.get("windows", [])]
        return cls(screen=screen, windows=windows)
