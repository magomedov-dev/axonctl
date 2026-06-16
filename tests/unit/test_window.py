"""Unit tests for window-list parsing and selections."""

from __future__ import annotations

from typing import Any

from axonctl import WindowList


def _windows(*, include_tree: bool = False) -> dict[str, Any]:
    app_root: dict[str, Any] = {
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
        "children": [],
    }
    dialog = {
        "windowId": 20,
        "type": "application",
        "layer": 3,
        "active": True,
        "focused": True,
        "title": "Confirm",
        "package": "com.app",
        "bounds": {"left": 100, "top": 800, "right": 980, "bottom": 1400},
    }
    ime = {
        "windowId": 15,
        "type": "inputMethod",
        "layer": 2,
        "active": False,
        "focused": False,
        "title": "Keyboard",
        "package": "com.google.android.inputmethod",
        "bounds": {"left": 0, "top": 1400, "right": 1080, "bottom": 2280},
    }
    app = {
        "windowId": 12,
        "type": "application",
        "layer": 1,
        "active": False,
        "focused": False,
        "title": "App",
        "package": "com.app",
        "bounds": {"left": 0, "top": 0, "right": 1080, "bottom": 2280},
    }
    system = {
        "windowId": 4,
        "type": "system",
        "layer": 0,
        "active": False,
        "focused": False,
        "title": None,
        "package": None,
        "bounds": {"left": 0, "top": 0, "right": 1080, "bottom": 80},
    }
    if include_tree:
        app["root"] = app_root
    return {"screen": 7, "windows": [dialog, ime, app, system]}


def test_parse_preserves_top_to_bottom_order() -> None:
    wl = WindowList.from_dict(_windows())
    assert wl.screen == 7
    assert [w.window_id for w in wl.windows] == [20, 15, 12, 4]
    assert len(wl) == 4
    assert [w.window_id for w in wl] == [20, 15, 12, 4]


def test_active_and_focused() -> None:
    wl = WindowList.from_dict(_windows())
    active = wl.active()
    assert active is not None and active.window_id == 20
    focused = wl.focused()
    assert focused is not None and focused.window_id == 20


def test_by_type_and_ime() -> None:
    wl = WindowList.from_dict(_windows())
    assert [w.window_id for w in wl.by_type("application")] == [20, 12]
    assert [w.window_id for w in wl.ime()] == [15]


def test_dialogs_are_apps_above_base() -> None:
    wl = WindowList.from_dict(_windows())
    assert [w.window_id for w in wl.dialogs()] == [20]


def test_system_window_allows_null_title_and_package() -> None:
    wl = WindowList.from_dict(_windows())
    system = next(w for w in wl.windows if w.window_id == 4)
    assert system.title is None
    assert system.package is None
    assert system.root is None


def test_include_tree_attaches_root() -> None:
    wl = WindowList.from_dict(_windows(include_tree=True))
    app = next(w for w in wl.windows if w.window_id == 12)
    assert app.root is not None
    assert app.root.screen == 7
    assert app.root.package == "com.app"
    assert app.root.root.node_id == 0
