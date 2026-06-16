"""Unit tests for the HTML inspector renderer."""

from __future__ import annotations

from typing import Any

from axonctl import UiTree, build_inspector_html


def _tree() -> UiTree:
    dump: dict[str, Any] = {
        "screen": 7,
        "package": "com.x",
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
        "children": [
            {
                "nodeId": 1,
                "parentId": 0,
                "class": "android.widget.Button",
                "text": "Sign in",
                "resourceId": "com.x:id/login",
                "contentDesc": None,
                "clickable": True,
                "enabled": True,
                "focused": False,
                "bounds": {"left": 40, "top": 100, "right": 200, "bottom": 160},
                "children": [],
            },
            {
                "nodeId": 2,
                "parentId": 0,
                "class": "android.widget.Button",
                "text": "Cancel",
                "resourceId": None,
                "contentDesc": None,
                "clickable": True,
                "enabled": True,
                "focused": False,
                "bounds": {"left": 220, "top": 100, "right": 380, "bottom": 160},
                "children": [],
            },
        ],
    }
    return UiTree.from_dict(dump)


def test_renders_self_contained_html() -> None:
    html = build_inspector_html(
        _tree(), b"\x89PNG-bytes", image_mime="image/png", image_size=(1080, 2280)
    )
    assert html.startswith("<!DOCTYPE html>")
    # embedded image as a data URI (no external assets)
    assert "data:image/png;base64," in html
    assert "http://" not in html and "https://" not in html
    # node data is embedded
    assert "com.x:id/login" in html
    assert "Sign in" in html and "Cancel" in html
    assert '"package":"com.x"' in html
    assert '"screen":7' in html


def test_frame_uses_image_size() -> None:
    html = build_inspector_html(
        _tree(), b"x", image_size=(1080, 2400)
    )  # screenshot taller than root bounds
    assert '"frame":{"l":0,"t":0,"r":1080,"b":2400}' in html


def test_frame_falls_back_to_root_bounds() -> None:
    html = build_inspector_html(_tree(), b"x")  # no image_size
    assert '"frame":{"l":0,"t":0,"r":1080,"b":2280}' in html


def test_class_index_is_assigned_per_class() -> None:
    html = build_inspector_html(_tree(), b"x", image_size=(1080, 2280))
    # two buttons -> the second gets clsIndex 1
    assert '"clsIndex":0' in html
    assert '"clsIndex":1' in html


def test_title_is_html_escaped() -> None:
    html = build_inspector_html(_tree(), b"x", title="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
