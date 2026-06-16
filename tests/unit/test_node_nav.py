"""Unit tests for node navigation (descendants/walk/parent/ancestors)."""

from __future__ import annotations

from typing import Any

from axonctl import Selector, UiTree


def _tree() -> UiTree:
    dump: dict[str, Any] = {
        "screen": 1,
        "package": "com.app",
        "nodeId": 0,
        "parentId": None,
        "class": "Root",
        "text": None,
        "resourceId": None,
        "contentDesc": None,
        "clickable": False,
        "enabled": True,
        "focused": False,
        "bounds": {"left": 0, "top": 0, "right": 1, "bottom": 1},
        "children": [
            {
                "nodeId": 1,
                "parentId": 0,
                "class": "Mid",
                "text": None,
                "resourceId": "com.app:id/form",
                "contentDesc": None,
                "clickable": False,
                "enabled": True,
                "focused": False,
                "bounds": {"left": 0, "top": 0, "right": 1, "bottom": 1},
                "children": [
                    {
                        "nodeId": 2,
                        "parentId": 1,
                        "class": "Leaf",
                        "text": None,
                        "resourceId": "com.app:id/user",
                        "contentDesc": None,
                        "clickable": False,
                        "enabled": True,
                        "focused": False,
                        "bounds": {"left": 0, "top": 0, "right": 1, "bottom": 1},
                        "children": [],
                    }
                ],
            }
        ],
    }
    return UiTree.from_dict(dump)


def test_descendants_and_walk() -> None:
    tree = _tree()
    assert [n.node_id for n in tree.root.descendants()] == [1, 2]
    assert [n.node_id for n in tree.root.walk()] == [0, 1, 2]


def test_parent_is_none_before_linking() -> None:
    tree = _tree()
    # Unlinked: walking down works, but parent links are not built yet.
    leaf = next(n for n in tree.root.walk() if n.node_id == 2)
    assert leaf.parent is None


def test_parent_and_ancestors_after_find() -> None:
    tree = _tree()
    leaf = tree.find(Selector.id("com.app:id/user"))  # find() links the tree
    assert leaf is not None
    assert leaf.parent is not None
    assert leaf.parent.resource_id == "com.app:id/form"
    assert [a.node_id for a in leaf.ancestors()] == [1, 0]
    assert tree.root.parent is None


def test_explicit_link() -> None:
    tree = _tree()
    tree.link()
    leaf = next(n for n in tree.root.walk() if n.node_id == 2)
    assert [a.node_id for a in leaf.ancestors()] == [1, 0]
