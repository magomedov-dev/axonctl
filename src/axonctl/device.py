"""The :class:`Device` facade.

The object user scenarios talk to. Stage 1 exposes the minimal vertical slice —
``ping`` and ``dump`` — over a :class:`~axonctl.conn.connection.DeviceConnection`;
gestures, actions, waits and the rest are layered on in later stages. A scenario
never reaches into the connection or RPC layers directly.

:func:`connect_device` is a provisional convenience constructor for testing and
the first vertical slice; the public entry point becomes
:class:`~axonctl.FleetController` once the fleet layer lands.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from .config import FleetConfig
from .conn.connection import ConnectionState, DeviceConnection
from .conn.ws import WebSocketTransport, WsClient
from .fleet.adb import Adb
from .gestures import GestureBuilder
from .retry import RetryPolicy
from .tree.node import UiNode
from .tree.selector import Selector
from .tree.tree import UiTree
from .tree.window import WindowList
from .wait import WaitEngine

#: Scroll direction for :meth:`Device.scroll`.
ScrollDirection = Literal["forward", "backward"]
#: Screenshot encoding for :meth:`Device.screenshot`.
ScreenshotFormat = Literal["jpeg", "png"]
#: System-level action for :meth:`Device.global_action`.
GlobalAction = Literal[
    "back",
    "home",
    "recents",
    "notifications",
    "quickSettings",
    "powerDialog",
    "lockScreen",
]


class Device:
    """A single Android device under control.

    Attributes are read via properties; everything a scenario needs is a method
    on this object.
    """

    def __init__(
        self,
        *,
        serial: str,
        tags: Iterable[str],
        connection: DeviceConnection,
        adb: Adb | None = None,
    ) -> None:
        """Wrap an established connection.

        Args:
            serial: Device serial.
            tags: Static group tags for this device.
            connection: The live device connection.
            adb: Optional adb bridge enabling ``launch``/``kill``/``install``
                (bound by the fleet controller; ``None`` for standalone use).
        """
        self._serial = serial
        self._tags = frozenset(tags)
        self._conn = connection
        self._adb = adb
        self._retry = RetryPolicy(connection.config.retry)
        self._waits = WaitEngine(
            events=connection.events,
            ensure_stream=connection.ensure_event_stream,
            dump=self.dump,
        )

    @property
    def serial(self) -> str:
        """The device serial."""
        return self._serial

    @property
    def tags(self) -> frozenset[str]:
        """The device's static group tags."""
        return self._tags

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._conn.state

    async def ping(self) -> Mapping[str, Any]:
        """Check application-level liveness.

        Returns:
            The agent's ``{"pong": True, "ts": <epoch millis>}`` result.

        Raises:
            RpcTimeout: If the agent does not reply within the deadline.
            ConnectionLost: If the connection drops during the call.
        """
        return await self._conn.rpc.call("ping")

    async def dump(
        self,
        *,
        compress: bool = True,
        max_depth: int | None = None,
        window_id: int | None = None,
    ) -> UiTree:
        """Dump the UI hierarchy and parse it into a :class:`UiTree`.

        Args:
            compress: Drop recomputable ``center`` and empty ``children`` to save
                bandwidth (recommended on dense screens).
            max_depth: Maximum tree depth (root is 0); ``None`` for unbounded.
            window_id: Dump a specific window (from ``getWindows``); ``None`` uses
                the active window.

        Returns:
            The parsed UI tree.

        Raises:
            AccessibilityDisabled: If there is no active-window root.
            WindowNotFound: If ``window_id`` has no matching window.
            RpcTimeout: If the agent does not reply within the deadline.
            ConnectionLost: If the connection drops during the call.
        """
        params: dict[str, Any] = {"compress": compress}
        if max_depth is not None:
            params["maxDepth"] = max_depth
        if window_id is not None:
            params["windowId"] = window_id
        result = await self._conn.rpc.call("dumpHierarchy", params)
        tree = UiTree.from_dict(result)
        self._conn.screen.observe(tree.screen, tree.package)
        return tree

    async def windows(
        self,
        *,
        include_tree: bool = False,
        compress: bool = True,
        max_depth: int | None = None,
    ) -> WindowList:
        """Enumerate all interactive windows via ``getWindows``.

        Lists every window (application, IME, system bars, dialogs, overlays,
        split-screen), topmost first — not just the active one.

        Args:
            include_tree: Attach each window's UI tree under ``root``.
            compress: Drop recomputable ``center`` and empty ``children`` in any
                attached trees.
            max_depth: Maximum depth for attached trees; ``None`` for unbounded.

        Returns:
            The parsed :class:`~axonctl.WindowList` (topmost first).

        Raises:
            RpcTimeout: If the agent does not reply within the deadline.
            ConnectionLost: If the connection drops during the call.
        """
        params: dict[str, Any] = {"includeTree": include_tree, "compress": compress}
        if max_depth is not None:
            params["maxDepth"] = max_depth
        result = await self._conn.rpc.call("getWindows", params)
        return WindowList.from_dict(result)

    async def find(
        self,
        selector: Selector,
        *,
        compress: bool = True,
        max_depth: int | None = None,
        window_id: int | None = None,
    ) -> UiNode | None:
        """Dump the UI and return the first node matching ``selector``.

        A convenience for "dump then search" in one call. For repeated queries on
        the same screen, prefer :meth:`dump` once and reuse the tree.

        Args:
            selector: The selector to evaluate.
            compress: See :meth:`dump`.
            max_depth: See :meth:`dump`.
            window_id: See :meth:`dump`.

        Returns:
            The matching node, or ``None``.

        Raises:
            AccessibilityDisabled: If there is no active-window root.
            WindowNotFound: If ``window_id`` has no matching window.
            RpcTimeout: If the agent does not reply within the deadline.
            ConnectionLost: If the connection drops during the call.
        """
        tree = await self.dump(
            compress=compress, max_depth=max_depth, window_id=window_id
        )
        return tree.find(selector)

    async def find_all(
        self,
        selector: Selector,
        *,
        compress: bool = True,
        max_depth: int | None = None,
        window_id: int | None = None,
    ) -> list[UiNode]:
        """Dump the UI and return all nodes matching ``selector``.

        Args:
            selector: The selector to evaluate.
            compress: See :meth:`dump`.
            max_depth: See :meth:`dump`.
            window_id: See :meth:`dump`.

        Returns:
            All matching nodes (pre-order).

        Raises:
            AccessibilityDisabled: If there is no active-window root.
            WindowNotFound: If ``window_id`` has no matching window.
            RpcTimeout: If the agent does not reply within the deadline.
            ConnectionLost: If the connection drops during the call.
        """
        tree = await self.dump(
            compress=compress, max_depth=max_depth, window_id=window_id
        )
        return tree.find_all(selector)

    # -- Gestures ----------------------------------------------------------

    async def tap(self, x: int, y: int, *, duration: int = 50) -> None:
        """Tap at screen coordinates ``(x, y)``.

        Args:
            x: Horizontal coordinate in pixels.
            y: Vertical coordinate in pixels.
            duration: Press duration in milliseconds.

        Raises:
            GestureFailed: If the gesture is cancelled or cannot be dispatched.
            ConnectionLost: If the connection drops during the call.
        """
        await self._conn.rpc.call(
            "gesture", GestureBuilder.tap(x, y, duration=duration)
        )

    async def long_tap(self, x: int, y: int, *, duration: int = 600) -> None:
        """Long-press at ``(x, y)``.

        Raises:
            GestureFailed: If the gesture is cancelled or cannot be dispatched.
            ConnectionLost: If the connection drops during the call.
        """
        await self._conn.rpc.call(
            "gesture", GestureBuilder.long_tap(x, y, duration=duration)
        )

    async def double_tap(self, x: int, y: int, *, duration: int = 50) -> None:
        """Double-tap at ``(x, y)``.

        Raises:
            GestureFailed: If the gesture is cancelled or cannot be dispatched.
            ConnectionLost: If the connection drops during the call.
        """
        await self._conn.rpc.call(
            "gesture", GestureBuilder.double_tap(x, y, duration=duration)
        )

    async def swipe(
        self, x1: int, y1: int, x2: int, y2: int, *, duration: int = 300
    ) -> None:
        """Swipe (flick) from ``(x1, y1)`` to ``(x2, y2)``.

        Raises:
            GestureFailed: If the gesture is cancelled or cannot be dispatched.
            ConnectionLost: If the connection drops during the call.
        """
        await self._conn.rpc.call(
            "gesture", GestureBuilder.swipe(x1, y1, x2, y2, duration=duration)
        )

    async def drag(
        self, x1: int, y1: int, x2: int, y2: int, *, duration: int = 800
    ) -> None:
        """Slow drag from ``(x1, y1)`` to ``(x2, y2)``.

        Raises:
            GestureFailed: If the gesture is cancelled or cannot be dispatched.
            ConnectionLost: If the connection drops during the call.
        """
        await self._conn.rpc.call(
            "gesture", GestureBuilder.drag(x1, y1, x2, y2, duration=duration)
        )

    async def pinch(
        self,
        cx: int,
        cy: int,
        *,
        start_radius: int,
        end_radius: int,
        duration: int = 300,
    ) -> None:
        """Two-finger pinch around ``(cx, cy)``.

        ``start_radius > end_radius`` pinches in (zoom out); the reverse pinches
        out (zoom in).

        Raises:
            GestureFailed: If the gesture is cancelled or cannot be dispatched.
            ConnectionLost: If the connection drops during the call.
        """
        await self._conn.rpc.call(
            "gesture",
            GestureBuilder.pinch(
                cx,
                cy,
                start_radius=start_radius,
                end_radius=end_radius,
                duration=duration,
            ),
        )

    # -- Node actions ------------------------------------------------------

    async def click(self, selector: Selector, *, window_id: int | None = None) -> None:
        """Click the node matching ``selector``.

        Args:
            selector: Selector identifying the node (``.within(...)`` is not
                supported here — use ``window_id`` or a more specific selector).
            window_id: Search a specific window; ``None`` uses the active window.

        Raises:
            NodeNotFound: If nothing matches.
            AmbiguousMatch: If several match and no ``index`` is set.
            ActionNotSupported: If the node cannot be clicked.
            Stale: If the node keeps going stale across retries.
            WindowNotFound: If ``window_id`` has no matching window.
            ConnectionLost: If the connection drops during the call.
        """
        await self._node_action("click", selector, window_id=window_id)

    async def long_click(
        self, selector: Selector, *, window_id: int | None = None
    ) -> None:
        """Long-click the node matching ``selector``.

        Raises:
            NodeNotFound, AmbiguousMatch, ActionNotSupported, Stale,
            WindowNotFound: See :meth:`click`.
            ConnectionLost: If the connection drops during the call.
        """
        await self._node_action("longClick", selector, window_id=window_id)

    async def set_text(
        self, selector: Selector, text: str, *, window_id: int | None = None
    ) -> None:
        """Set the text of the editable node matching ``selector``.

        Raises:
            NodeNotFound, AmbiguousMatch, WindowNotFound: See :meth:`click`.
            NotEditable: If the node is not editable.
            Stale: If the node keeps going stale across retries.
            ConnectionLost: If the connection drops during the call.
        """
        await self._node_action(
            "setText", selector, window_id=window_id, extra={"text": text}
        )

    async def clear(self, selector: Selector, *, window_id: int | None = None) -> None:
        """Clear the text of the editable node matching ``selector``.

        Raises:
            NodeNotFound, AmbiguousMatch, WindowNotFound: See :meth:`click`.
            NotEditable: If the node is not editable.
            Stale: If the node keeps going stale across retries.
            ConnectionLost: If the connection drops during the call.
        """
        await self._node_action("clear", selector, window_id=window_id)

    async def scroll(
        self,
        selector: Selector,
        direction: ScrollDirection,
        *,
        window_id: int | None = None,
    ) -> None:
        """Scroll the node matching ``selector`` forward or backward.

        Args:
            selector: Selector identifying the scrollable node.
            direction: ``"forward"`` or ``"backward"``.
            window_id: Search a specific window; ``None`` uses the active window.

        Raises:
            NodeNotFound, AmbiguousMatch, ActionNotSupported, Stale,
            WindowNotFound: See :meth:`click`.
            ConnectionLost: If the connection drops during the call.
        """
        action = "scrollForward" if direction == "forward" else "scrollBackward"
        await self._node_action(action, selector, window_id=window_id)

    async def focus(self, selector: Selector, *, window_id: int | None = None) -> None:
        """Give input focus to the node matching ``selector``.

        Raises:
            NodeNotFound, AmbiguousMatch, ActionNotSupported, Stale,
            WindowNotFound: See :meth:`click`.
            ConnectionLost: If the connection drops during the call.
        """
        await self._node_action("focus", selector, window_id=window_id)

    async def clear_focus(
        self, selector: Selector, *, window_id: int | None = None
    ) -> None:
        """Clear input focus from the node matching ``selector``.

        Raises:
            NodeNotFound, AmbiguousMatch, ActionNotSupported, Stale,
            WindowNotFound: See :meth:`click`.
            ConnectionLost: If the connection drops during the call.
        """
        await self._node_action("clearFocus", selector, window_id=window_id)

    async def select(self, selector: Selector, *, window_id: int | None = None) -> None:
        """Select the node matching ``selector``.

        Raises:
            NodeNotFound, AmbiguousMatch, ActionNotSupported, Stale,
            WindowNotFound: See :meth:`click`.
            ConnectionLost: If the connection drops during the call.
        """
        await self._node_action("select", selector, window_id=window_id)

    async def set_selection(
        self,
        selector: Selector,
        start: int,
        end: int,
        *,
        window_id: int | None = None,
    ) -> None:
        """Set the text selection range on the node matching ``selector``.

        Raises:
            NodeNotFound, AmbiguousMatch, ActionNotSupported, Stale,
            WindowNotFound: See :meth:`click`.
            ConnectionLost: If the connection drops during the call.
        """
        await self._node_action(
            "setSelection",
            selector,
            window_id=window_id,
            extra={"start": start, "end": end},
        )

    # -- Other RPCs --------------------------------------------------------

    async def global_action(self, action: GlobalAction) -> bool:
        """Perform a system-level action (back, home, recents, ...).

        Args:
            action: The global action to perform.

        Returns:
            The platform's ``performGlobalAction`` result.

        Raises:
            InvalidParams: If the action is unknown.
            ConnectionLost: If the connection drops during the call.
        """
        result = await self._conn.rpc.call("globalAction", {"action": action})
        return bool(result.get("success", False))

    async def screenshot(
        self, *, format: ScreenshotFormat = "jpeg", quality: int = 80
    ) -> bytes:
        """Capture the screen and return the encoded image bytes.

        The agent is system-rate-limited to roughly one capture per second;
        calling faster fails with :class:`~axonctl.InternalError`. Pace
        screenshots accordingly.

        Args:
            format: ``"jpeg"`` (default) or ``"png"``.
            quality: JPEG quality 0..100 (ignored for PNG).

        Returns:
            The raw image bytes.

        Raises:
            InvalidParams: If ``format``/``quality`` are invalid.
            InternalError: If capture fails (e.g. rate limit exceeded).
            ConnectionLost: If the connection drops during the call.
        """
        params: dict[str, Any] = {"format": format, "quality": quality}
        _meta, payload = await self._conn.rpc.call_binary("screenshot", params)
        return payload

    # -- adb-side (requires a bound adb bridge) ----------------------------

    async def launch(self, package: str) -> None:
        """Launch an app by package name (over adb).

        Args:
            package: The package to launch.

        Raises:
            RuntimeError: If no adb bridge is bound (standalone device).
        """
        await self._require_adb().launch(self._serial, package)

    async def kill(self, package: str) -> None:
        """Force-stop an app by package name (over adb).

        Args:
            package: The package to stop.

        Raises:
            RuntimeError: If no adb bridge is bound (standalone device).
        """
        await self._require_adb().force_stop(self._serial, package)

    async def install(self, apk_path: str) -> None:
        """Install an APK onto the device (over adb).

        Args:
            apk_path: Path to the APK file.

        Raises:
            RuntimeError: If no adb bridge is bound (standalone device).
        """
        await self._require_adb().install(self._serial, apk_path)

    def _require_adb(self) -> Adb:
        if self._adb is None:
            raise RuntimeError(
                "no adb bridge bound to this device; use a FleetController for "
                "launch/kill/install"
            )
        return self._adb

    def _node_params(
        self, selector: Selector, *, window_id: int | None
    ) -> dict[str, Any]:
        if selector.container is not None:
            raise ValueError(
                "selectors with .within(...) are not supported for actions; "
                "use window_id or a more specific selector"
            )
        params: dict[str, Any] = {
            "by": selector.by,
            "value": selector.value,
            "match": selector.match,
        }
        if selector.index is not None:
            params["index"] = selector.index
        if window_id is not None:
            params["windowId"] = window_id
        return params

    async def _node_action(
        self,
        action: str,
        selector: Selector,
        *,
        window_id: int | None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        params = self._node_params(selector, window_id=window_id)
        params["action"] = action
        if extra:
            params.update(extra)
        await self._retry.run(lambda: self._conn.rpc.call("nodeAction", params))

    async def wait_for(self, selector: Selector, *, timeout: float = 10.0) -> UiNode:
        """Wait until ``selector`` matches a node, then return it.

        Event-driven: re-checks only when the screen changes, never by polling.

        Args:
            selector: The selector to wait for.
            timeout: Deadline in seconds.

        Returns:
            The first matching node.

        Raises:
            WaitTimeout: If no match appears within the deadline.
            AccessibilityDisabled: If a dump finds no active-window root.
            ConnectionLost: If the connection drops while waiting.
        """
        return await self._waits.wait_until(
            lambda tree: tree.find(selector),
            timeout=timeout,
            what=f"wait_for({selector!r})",
        )

    async def wait_gone(self, selector: Selector, *, timeout: float = 10.0) -> None:
        """Wait until ``selector`` matches nothing.

        Args:
            selector: The selector that should disappear.
            timeout: Deadline in seconds.

        Raises:
            WaitTimeout: If the node is still present at the deadline.
            AccessibilityDisabled: If a dump finds no active-window root.
            ConnectionLost: If the connection drops while waiting.
        """
        await self._waits.wait_until(
            lambda tree: True if tree.find(selector) is None else None,
            timeout=timeout,
            what=f"wait_gone({selector!r})",
        )

    async def wait_activity(self, package: str, *, timeout: float = 10.0) -> None:
        """Wait until the foreground package equals ``package``.

        Args:
            package: The package name to wait for.
            timeout: Deadline in seconds.

        Raises:
            WaitTimeout: If the package is not foreground at the deadline.
            AccessibilityDisabled: If a dump finds no active-window root.
            ConnectionLost: If the connection drops while waiting.
        """
        await self._waits.wait_until(
            lambda tree: True if tree.package == package else None,
            timeout=timeout,
            what=f"wait_activity({package!r})",
        )

    async def wait_toast(self, *, timeout: float = 5.0) -> str:
        """Wait for the next toast and return its text.

        Args:
            timeout: Deadline in seconds.

        Returns:
            The toast text.

        Raises:
            WaitTimeout: If no toast arrives within the deadline.
            ConnectionLost: If the connection drops while waiting.
        """
        return await self._waits.wait_toast(timeout=timeout)

    async def sleep(self, seconds: float) -> None:
        """Sleep without blocking the event loop (``asyncio.sleep`` wrapper).

        Use this instead of ``time.sleep`` inside scenarios — a blocking sleep
        freezes every device sharing the loop.

        Args:
            seconds: How long to sleep.
        """
        await asyncio.sleep(seconds)

    async def aclose(self) -> None:
        """Close the underlying connection and release its resources."""
        await self._conn.close()

    async def __aenter__(self) -> Device:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


async def connect_device(
    serial: str,
    *,
    uri: str | None = None,
    transport: WebSocketTransport | None = None,
    tags: Iterable[str] = (),
    config: FleetConfig | None = None,
) -> Device:
    """Open a connection and return a ready :class:`Device`.

    Provisional helper for the first vertical slice and tests. Provide either a
    ``uri`` (a real ``WsClient`` is created) or a ``transport`` (e.g. a fake).

    Args:
        serial: Device serial.
        uri: WebSocket URI to connect to, if no ``transport`` is given.
        transport: A pre-built transport (takes precedence over ``uri``).
        tags: Static group tags for the device.
        config: Fleet config; defaults are used when omitted.

    Returns:
        A connected :class:`Device`.

    Raises:
        ValueError: If neither ``uri`` nor ``transport`` is provided.
        ConnectionLost: If the socket cannot be opened.
    """
    config = config or FleetConfig()
    if transport is None:
        if uri is None:
            raise ValueError("connect_device requires either uri or transport")
        transport = WsClient(uri, open_timeout=config.timeouts.connect)
    connection = DeviceConnection(transport, serial=serial, config=config)
    await connection.connect()
    return Device(serial=serial, tags=tags, connection=connection)
