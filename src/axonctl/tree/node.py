"""UI node model and navigation.

A parsed accessibility node: the protocol's node schema mapped to snake_case
fields, plus its children and (lazily) its parent. Downward navigation
(``descendants``/``walk``) and selector search need no parent links; upward
navigation (``parent``/``ancestors``) requires linking, which the tree does on
demand (see :meth:`UiTree.link`). Pure data — no I/O.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .geom import Bounds, Point

if TYPE_CHECKING:
    from .selector import Selector


@dataclass(slots=True)
class UiNode:
    """A single node in a UI dump.

    ``node_id`` is valid only within the dump it came from. ``center`` is computed
    from ``bounds`` when the agent omitted it (``compress: true``). ``parent`` is
    ``None`` until the owning tree is linked (see :meth:`UiTree.link`).

    Attributes:
        node_id: Pre-order id, unique within this dump (root = 0).
        parent_id: Parent's ``node_id``, or ``None`` for the root.
        class_name: Android view class (protocol ``class``).
        text: Visible text, or ``None``.
        resource_id: View resource id, or ``None``.
        content_desc: Content description, or ``None``.
        clickable: Whether the node is clickable.
        enabled: Whether the node is enabled.
        focused: Whether the node is focused.
        bounds: Screen rectangle, or ``None`` if absent.
        center: Center point (computed from ``bounds`` if not supplied).
        children: Child nodes (empty list when none).
    """

    node_id: int
    parent_id: int | None
    class_name: str | None
    text: str | None
    resource_id: str | None
    content_desc: str | None
    clickable: bool
    enabled: bool
    focused: bool
    bounds: Bounds | None
    center: Point | None
    children: list[UiNode]
    # Set lazily by UiTree.link(); excluded from eq/repr to avoid upward cycles.
    _parent: UiNode | None = field(default=None, init=False, repr=False, compare=False)

    @property
    def parent(self) -> UiNode | None:
        """The parent node, or ``None`` for the root or an unlinked tree."""
        return self._parent

    def descendants(self) -> Iterator[UiNode]:
        """Yield every descendant in pre-order (children, grandchildren, ...)."""
        for child in self.children:
            yield child
            yield from child.descendants()

    def walk(self) -> Iterator[UiNode]:
        """Yield this node followed by all its descendants, in pre-order."""
        yield self
        yield from self.descendants()

    def ancestors(self) -> Iterator[UiNode]:
        """Yield ancestors from the immediate parent up to the root.

        Yields nothing unless the owning tree has been linked.
        """
        node = self._parent
        while node is not None:
            yield node
            node = node._parent

    def find(self, selector: Selector) -> UiNode | None:
        """Return the first node in this subtree matching ``selector``.

        Args:
            selector: The selector to evaluate.

        Returns:
            The matching node, or ``None``.
        """
        return selector.find(self)

    def find_all(self, selector: Selector) -> list[UiNode]:
        """Return all nodes in this subtree matching ``selector``.

        Args:
            selector: The selector to evaluate.

        Returns:
            All matching nodes (pre-order).
        """
        return selector.find_all(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UiNode:
        """Parse a node (and its subtree) from a dump mapping.

        Args:
            data: A node object from ``dumpHierarchy``.

        Returns:
            The parsed node with its children (parent links not yet set).
        """
        bounds_raw = data.get("bounds")
        bounds = Bounds.from_dict(bounds_raw) if bounds_raw is not None else None
        center_raw = data.get("center")
        if center_raw is not None:
            center: Point | None = Point.from_dict(center_raw)
        else:
            center = bounds.center if bounds is not None else None
        children = [cls.from_dict(child) for child in data.get("children", [])]
        parent_id = data.get("parentId")
        return cls(
            node_id=int(data["nodeId"]),
            parent_id=int(parent_id) if parent_id is not None else None,
            class_name=data.get("class"),
            text=data.get("text"),
            resource_id=data.get("resourceId"),
            content_desc=data.get("contentDesc"),
            clickable=bool(data.get("clickable", False)),
            enabled=bool(data.get("enabled", False)),
            focused=bool(data.get("focused", False)),
            bounds=bounds,
            center=center,
            children=children,
        )


def link_parents(root: UiNode, parent: UiNode | None = None) -> None:
    """Recursively set ``_parent`` on ``root`` and its subtree.

    Args:
        root: Subtree root to link.
        parent: Parent to assign to ``root`` (``None`` for the tree root).
    """
    root._parent = parent
    for child in root.children:
        link_parents(child, root)
