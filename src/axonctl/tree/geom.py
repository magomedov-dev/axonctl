"""Geometry value types for the UI tree.

Immutable, hashable value objects mirroring the protocol's ``bounds`` and
``center`` shapes. Pure data — no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Point:
    """A 2D point in screen pixels.

    Attributes:
        x: Horizontal coordinate.
        y: Vertical coordinate.
    """

    x: int
    y: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Point:
        """Build a :class:`Point` from a ``{"x", "y"}`` mapping.

        Args:
            data: Mapping with integer ``x`` and ``y`` keys.

        Returns:
            The parsed point.
        """
        return cls(x=int(data["x"]), y=int(data["y"]))


@dataclass(frozen=True, slots=True)
class Bounds:
    """An axis-aligned rectangle, matching the protocol's ``bounds`` object.

    Attributes:
        left: Left edge (inclusive), in pixels.
        top: Top edge (inclusive), in pixels.
        right: Right edge, in pixels.
        bottom: Bottom edge, in pixels.
    """

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        """Rectangle width in pixels."""
        return self.right - self.left

    @property
    def height(self) -> int:
        """Rectangle height in pixels."""
        return self.bottom - self.top

    @property
    def center(self) -> Point:
        """The geometric center of the rectangle (integer-rounded)."""
        return Point(x=(self.left + self.right) // 2, y=(self.top + self.bottom) // 2)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Bounds:
        """Build :class:`Bounds` from a ``{"left","top","right","bottom"}`` mapping.

        Args:
            data: Mapping with the four integer edge keys.

        Returns:
            The parsed rectangle.
        """
        return cls(
            left=int(data["left"]),
            top=int(data["top"]),
            right=int(data["right"]),
            bottom=int(data["bottom"]),
        )
