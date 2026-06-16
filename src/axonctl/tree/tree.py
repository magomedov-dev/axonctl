"""Parsed UI tree.

The result of a ``dumpHierarchy`` call: the root node plus the dump's ``screen``
generation and foreground ``package``. Selector evaluation and navigation are
added in the tree/selector stage; Stage 1 only parses.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .node import UiNode


@dataclass(slots=True)
class UiTree:
    """A snapshot of one window's accessibility tree.

    Attributes:
        root: The root node of the dump.
        screen: Screen-state generation at dump time (see ``screenChanged``).
        package: Foreground app package the dump came from.
    """

    root: UiNode
    screen: int
    package: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UiTree:
        """Parse a :class:`UiTree` from a ``dumpHierarchy`` result.

        The result *is* the root node object with extra top-level ``screen`` and
        ``package`` fields.

        Args:
            data: The ``result`` object from ``dumpHierarchy``.

        Returns:
            The parsed tree.
        """
        return cls(
            root=UiNode.from_dict(data),
            screen=int(data["screen"]),
            package=str(data["package"]),
        )
