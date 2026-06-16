"""Unit tests for selector matching on a fixture tree."""

from __future__ import annotations

from typing import Any

import pytest

from axonctl import Selector, UiTree


def _node(node_id: int, **kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "nodeId": node_id,
        "parentId": kw.pop("parent_id", None),
        "class": kw.pop("cls", "android.view.View"),
        "text": kw.pop("text", None),
        "resourceId": kw.pop("rid", None),
        "contentDesc": kw.pop("desc", None),
        "clickable": kw.pop("clickable", False),
        "enabled": True,
        "focused": False,
        "bounds": {"left": 0, "top": 0, "right": 10, "bottom": 10},
        "children": kw.pop("children", []),
    }
    return base


def _tree() -> UiTree:
    dump = _node(
        0,
        cls="android.widget.FrameLayout",
        children=[
            _node(
                1,
                cls="android.widget.LinearLayout",
                rid="com.app:id/form",
                children=[
                    _node(2, cls="android.widget.EditText", rid="com.app:id/user"),
                    _node(3, cls="android.widget.EditText", rid="com.app:id/pass"),
                    _node(
                        4, cls="android.widget.Button", text="Sign in", clickable=True
                    ),
                ],
            ),
            _node(5, cls="android.widget.TextView", text="Sign in"),
            _node(
                6, cls="android.widget.TextView", text="Welcome back", desc="greeting"
            ),
        ],
    )
    dump["screen"] = 1
    dump["package"] = "com.app"
    return UiTree.from_dict(dump)


def test_find_by_id() -> None:
    node = _tree().find(Selector.id("com.app:id/form"))
    assert node is not None
    assert node.node_id == 1


def test_find_all_by_text_finds_both() -> None:
    nodes = _tree().find_all(Selector.text("Sign in"))
    assert [n.node_id for n in nodes] == [4, 5]


def test_within_restricts_to_container() -> None:
    sel = Selector.text("Sign in").within(Selector.id("com.app:id/form"))
    nodes = _tree().find_all(sel)
    assert [n.node_id for n in nodes] == [4]


def test_index_selects_nth_match() -> None:
    node = _tree().find(Selector.text("Sign in", index=1))
    assert node is not None
    assert node.node_id == 5


def test_index_out_of_range_returns_none() -> None:
    assert _tree().find(Selector.text("Sign in", index=5)) is None


def test_contains_match() -> None:
    node = _tree().find(Selector.text_contains("Welcome"))
    assert node is not None
    assert node.node_id == 6


def test_regex_matches_anywhere() -> None:
    nodes = _tree().find_all(Selector.text(r"Sign.*", match="regex"))
    assert [n.node_id for n in nodes] == [4, 5]


def test_regex_anchored() -> None:
    nodes = _tree().find_all(Selector.text(r"^Welcome back$", match="regex"))
    assert [n.node_id for n in nodes] == [6]


def test_select_by_class_and_desc() -> None:
    tree = _tree()
    edits = tree.find_all(Selector.cls("android.widget.EditText"))
    assert [n.node_id for n in edits] == [2, 3]
    greeting = tree.find(Selector.desc("greeting"))
    assert greeting is not None
    assert greeting.node_id == 6


def test_no_match() -> None:
    tree = _tree()
    assert tree.find(Selector.id("nope")) is None
    assert tree.find_all(Selector.id("nope")) == []


def test_invalid_selector_fields() -> None:
    with pytest.raises(ValueError, match="by"):
        Selector(by="bogus", value="x")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="match"):
        Selector(by="text", value="x", match="fuzzy")  # type: ignore[arg-type]
