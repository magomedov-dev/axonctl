"""Parsed UI tree.

The result of a ``dumpHierarchy`` call: the root node plus the dump's ``screen``
generation and foreground ``package``. Search delegates to :class:`Selector`;
upward navigation requires parent links, which are built lazily here — a dump you
only serialize never pays for linking.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .node import UiNode, link_parents

if TYPE_CHECKING:
    from .selector import Selector


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
    _linked: bool = field(default=False, init=False, repr=False, compare=False)

    def link(self) -> None:
        """Build parent links across the tree (idempotent).

        Called automatically by :meth:`find`/:meth:`find_all`; call it directly
        if you traverse :attr:`root` manually and need ``parent``/``ancestors``.
        """
        if self._linked:
            return
        link_parents(self.root, None)
        self._linked = True

    def find(self, selector: Selector) -> UiNode | None:
        """Return the first node matching ``selector`` (or ``None``).

        Args:
            selector: The selector to evaluate against the whole tree.

        Returns:
            The matching node, or ``None``.
        """
        self.link()
        return selector.find(self.root)

    def find_all(self, selector: Selector) -> list[UiNode]:
        """Return all nodes matching ``selector`` (pre-order).

        Args:
            selector: The selector to evaluate against the whole tree.

        Returns:
            All matching nodes.
        """
        self.link()
        return selector.find_all(self.root)

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

    @classmethod
    def from_node_dict(
        cls, data: Mapping[str, Any], *, screen: int, package: str
    ) -> UiTree:
        """Parse a tree from a bare node object plus external ``screen``/``package``.

        Used for a window's ``root`` in ``getWindows`` output, where ``screen``
        and ``package`` live outside the node object.

        Args:
            data: A bare root node object (no ``screen``/``package`` keys).
            screen: Screen generation to attach.
            package: Package to attach.

        Returns:
            The parsed tree.
        """
        return cls(root=UiNode.from_dict(data), screen=screen, package=package)
