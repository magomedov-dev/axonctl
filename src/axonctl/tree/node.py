"""UI node model.

A parsed accessibility node: the protocol's node schema mapped to snake_case
fields, plus its children. This is the minimal Stage 1 shape — pure parsing, no
navigation or selector evaluation yet (those arrive with the tree/selector
stage).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .geom import Bounds, Point


@dataclass(slots=True)
class UiNode:
    """A single node in a UI dump.

    ``node_id`` is valid only within the dump it came from. ``center`` is computed
    from ``bounds`` when the agent omitted it (``compress: true``).

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

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UiNode:
        """Parse a node (and its subtree) from a dump mapping.

        Args:
            data: A node object from ``dumpHierarchy``.

        Returns:
            The parsed node with its children.
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
