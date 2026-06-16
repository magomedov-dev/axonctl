"""Integration tests for tree queries and window enumeration via Device."""

from __future__ import annotations

from fake_agent import FAKE_PACKAGE, fake_agent

from axonctl import Selector, connect_device


async def test_find_returns_matching_node() -> None:
    async with fake_agent() as uri, await connect_device("fake", uri=uri) as device:
        node = await device.find(Selector.id("com.app:id/login"))
        assert node is not None
        assert node.text == "Sign in"


async def test_find_all_and_parent_navigation() -> None:
    async with fake_agent() as uri, await connect_device("fake", uri=uri) as device:
        tree = await device.dump()
        button = tree.find(Selector.text("Sign in"))
        assert button is not None
        # find() linked the tree, so upward navigation works.
        assert button.parent is not None
        assert button.parent.node_id == 0


async def test_windows_enumerates_all() -> None:
    async with fake_agent() as uri, await connect_device("fake", uri=uri) as device:
        windows = await device.windows()
        assert [w.window_id for w in windows] == [12, 4]
        active = windows.active()
        assert active is not None
        assert active.package == FAKE_PACKAGE
        assert active.type == "application"


async def test_windows_with_tree() -> None:
    async with fake_agent() as uri, await connect_device("fake", uri=uri) as device:
        windows = await device.windows(include_tree=True)
        app = windows.active()
        assert app is not None
        assert app.root is not None
        node = app.root.find(Selector.id("com.app:id/login"))
        assert node is not None
