"""Unit tests for geometry and UI-tree parsing."""

from __future__ import annotations

from typing import Any

from axonctl.tree.geom import Bounds, Point
from axonctl.tree.tree import UiTree


def test_bounds_geometry() -> None:
    b = Bounds(left=0, top=0, right=10, bottom=20)
    assert b.width == 10
    assert b.height == 20
    assert b.center == Point(5, 10)


def _dump(*, compress: bool) -> dict[str, Any]:
    child: dict[str, Any] = {
        "nodeId": 1,
        "parentId": 0,
        "class": "android.widget.Button",
        "text": "Sign in",
        "resourceId": "com.app:id/login",
        "contentDesc": None,
        "clickable": True,
        "enabled": True,
        "focused": False,
        "bounds": {"left": 0, "top": 0, "right": 100, "bottom": 50},
    }
    if not compress:
        child["center"] = {"x": 50, "y": 25}
        child["children"] = []
    return {
        "screen": 3,
        "package": "com.axon.agent",
        "nodeId": 0,
        "parentId": None,
        "class": "android.widget.FrameLayout",
        "text": None,
        "resourceId": None,
        "contentDesc": None,
        "clickable": False,
        "enabled": True,
        "focused": False,
        "bounds": {"left": 0, "top": 0, "right": 1080, "bottom": 2280},
        "children": [child],
    }


def test_tree_parse_basic() -> None:
    tree = UiTree.from_dict(_dump(compress=False))
    assert tree.screen == 3
    assert tree.package == "com.axon.agent"
    root = tree.root
    assert root.node_id == 0
    assert root.parent_id is None
    assert root.class_name == "android.widget.FrameLayout"
    assert len(root.children) == 1
    child = root.children[0]
    assert child.resource_id == "com.app:id/login"
    assert child.text == "Sign in"
    assert child.clickable is True
    assert child.center == Point(50, 25)


def test_compressed_center_is_computed_from_bounds() -> None:
    tree = UiTree.from_dict(_dump(compress=True))
    child = tree.root.children[0]
    # No "center" supplied -> derived from bounds (0,0,100,50).
    assert child.center == Point(50, 25)
