"""In-process fake Axon agent for integration tests.

A real asyncio WebSocket server that speaks just enough of the protocol to
exercise the full controller path (transport -> router -> pending -> RpcClient ->
Device) without a physical device. Handlers are pluggable so tests can simulate
timeouts, errors, dropped connections, and two-part screenshot replies.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import orjson
from websockets.asyncio.server import ServerConnection, serve

Handler = Callable[[ServerConnection], Awaitable[None]]

FAKE_PACKAGE = "com.axon.agent"


def _ok(req_id: Any, result: dict[str, Any]) -> str:
    return orjson.dumps({"id": req_id, "result": result}).decode()


def _err(req_id: Any, code: str, message: str) -> str:
    return orjson.dumps(
        {"id": req_id, "error": {"code": code, "message": message}}
    ).decode()


def _dump_result() -> dict[str, Any]:
    return {
        "screen": 1,
        "package": FAKE_PACKAGE,
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
                "resourceId": "com.app:id/login",
                "contentDesc": None,
                "clickable": True,
                "enabled": True,
                "focused": False,
                "bounds": {"left": 40, "top": 100, "right": 200, "bottom": 160},
                "children": [],
            }
        ],
    }


def _windows_result(include_tree: bool) -> dict[str, Any]:
    app: dict[str, Any] = {
        "windowId": 12,
        "type": "application",
        "layer": 1,
        "active": True,
        "focused": True,
        "title": "Axon",
        "package": FAKE_PACKAGE,
        "bounds": {"left": 0, "top": 0, "right": 1080, "bottom": 2280},
    }
    system: dict[str, Any] = {
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
        app["root"] = _dump_result()
    return {"screen": 1, "windows": [app, system]}


async def default_handler(connection: ServerConnection) -> None:
    """Answer ping/dump/getWindows/setEventStream/screenshot; error otherwise."""
    async for raw in connection:
        request: dict[str, Any] = orjson.loads(raw)
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        if method == "ping":
            await connection.send(_ok(req_id, {"pong": True, "ts": 1781552384385}))
        elif method == "dumpHierarchy":
            await connection.send(_ok(req_id, _dump_result()))
        elif method == "getWindows":
            await connection.send(
                _ok(req_id, _windows_result(bool(params.get("includeTree"))))
            )
        elif method in ("gesture", "nodeAction") or method == "globalAction":
            await connection.send(_ok(req_id, {"success": True}))
        elif method == "setEventStream":
            await connection.send(
                _ok(
                    req_id,
                    {"success": True, "enabled": bool(params.get("enabled", False))},
                )
            )
        elif method == "screenshot":
            payload = b"\x89PNG\r\n\x1a\n-fake-image"
            await connection.send(
                _ok(
                    req_id,
                    {
                        "screen": 1,
                        "format": "png",
                        "width": 2,
                        "height": 2,
                        "bytes": len(payload),
                    },
                )
            )
            await connection.send(int(req_id).to_bytes(4, "big") + payload)
        else:
            await connection.send(
                _err(req_id, "METHOD_NOT_FOUND", f"unknown method {method}")
            )


async def silent_handler(connection: ServerConnection) -> None:
    """Consume requests but never reply (drives timeout tests)."""
    async for _raw in connection:
        pass


async def closing_handler(connection: ServerConnection) -> None:
    """Close the connection on the first request (drives ConnectionLost tests)."""
    async for _raw in connection:
        await connection.close()
        return


def accessibility_disabled_handler() -> Handler:
    """Return a handler whose ``dumpHierarchy`` fails with ACCESSIBILITY_DISABLED."""

    async def handler(connection: ServerConnection) -> None:
        async for raw in connection:
            request: dict[str, Any] = orjson.loads(raw)
            req_id = request.get("id")
            if request.get("method") == "dumpHierarchy":
                await connection.send(
                    _err(req_id, "ACCESSIBILITY_DISABLED", "no active window")
                )
            else:
                await connection.send(_ok(req_id, {"pong": True, "ts": 1}))

    return handler


class ScriptedAgent:
    """A controllable fake agent for event-driven wait tests.

    The test drives state (target presence, foreground package) and pushes
    ``screenChanged``/``toast`` events to the live connection, while
    ``dump_count`` records how many dumps the controller performed — letting a
    test prove a wait is event-driven (re-dumps only on events), not polling.
    """

    def __init__(self) -> None:
        self.ready = asyncio.Event()
        self.dump_count = 0
        self._conn: ServerConnection | None = None
        self._screen = 1
        self._package = FAKE_PACKAGE
        self._target = False

    def set_target(self, present: bool) -> None:
        """Set whether the target node is in the dump."""
        self._target = present

    def set_package(self, package: str) -> None:
        """Set the foreground package reported by dumps."""
        self._package = package

    async def emit_screen_changed(self, *, package: str | None = None) -> None:
        """Bump the screen generation and push a ``screenChanged`` event."""
        assert self._conn is not None
        self._screen += 1
        await self._conn.send(
            orjson.dumps(
                {
                    "event": "screenChanged",
                    "screen": self._screen,
                    "package": package or self._package,
                }
            ).decode()
        )

    async def emit_toast(self, text: str) -> None:
        """Push a ``toast`` event."""
        assert self._conn is not None
        await self._conn.send(
            orjson.dumps(
                {"event": "toast", "text": text, "package": self._package}
            ).decode()
        )

    async def close_connection(self) -> None:
        """Drop the connection (drives ConnectionLost-during-wait tests)."""
        assert self._conn is not None
        await self._conn.close()

    def _dump(self) -> dict[str, Any]:
        children: list[dict[str, Any]] = []
        if self._target:
            children.append(
                {
                    "nodeId": 1,
                    "parentId": 0,
                    "class": "android.widget.TextView",
                    "text": "Ready",
                    "resourceId": "com.app:id/target",
                    "contentDesc": None,
                    "clickable": False,
                    "enabled": True,
                    "focused": False,
                    "bounds": {"left": 0, "top": 0, "right": 10, "bottom": 10},
                    "children": [],
                }
            )
        return {
            "screen": self._screen,
            "package": self._package,
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
            "children": children,
        }

    async def handler(self, connection: ServerConnection) -> None:
        self._conn = connection
        self.ready.set()
        async for raw in connection:
            request: dict[str, Any] = orjson.loads(raw)
            req_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or {}
            if method == "ping":
                await connection.send(_ok(req_id, {"pong": True, "ts": 1}))
            elif method == "setEventStream":
                await connection.send(
                    _ok(
                        req_id,
                        {"success": True, "enabled": bool(params.get("enabled"))},
                    )
                )
            elif method == "dumpHierarchy":
                self.dump_count += 1
                await connection.send(_ok(req_id, self._dump()))
            else:
                await connection.send(
                    _err(req_id, "METHOD_NOT_FOUND", f"unknown {method}")
                )


def stale_then_ok_handler(stale_times: int) -> Handler:
    """Return a handler whose ``nodeAction`` fails ``STALE`` ``stale_times`` times.

    After that many STALE responses it succeeds — exercising retry behaviour.
    """
    state = {"count": 0}

    async def handler(connection: ServerConnection) -> None:
        async for raw in connection:
            request: dict[str, Any] = orjson.loads(raw)
            req_id = request.get("id")
            method = request.get("method")
            if method == "nodeAction":
                if state["count"] < stale_times:
                    state["count"] += 1
                    await connection.send(_err(req_id, "STALE", "node changed"))
                else:
                    await connection.send(_ok(req_id, {"success": True}))
            elif method == "ping":
                await connection.send(_ok(req_id, {"pong": True, "ts": 1}))
            else:
                await connection.send(_ok(req_id, {"success": True}))

    return handler


@contextlib.asynccontextmanager
async def fake_agent(handler: Handler = default_handler) -> AsyncIterator[str]:
    """Run the fake agent on an ephemeral port and yield its ``ws://`` URI.

    Args:
        handler: The per-connection coroutine implementing the protocol subset.

    Yields:
        The WebSocket URI to connect to.
    """
    async with serve(handler, "127.0.0.1", 0) as server:
        sock = next(iter(server.sockets))
        port = sock.getsockname()[1]
        yield f"ws://127.0.0.1:{port}"
