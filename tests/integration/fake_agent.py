"""In-process fake Axon agent for integration tests.

A real asyncio WebSocket server that speaks just enough of the protocol to
exercise the full controller path (transport -> router -> pending -> RpcClient ->
Device) without a physical device. Handlers are pluggable so tests can simulate
timeouts, errors, dropped connections, and two-part screenshot replies.
"""

from __future__ import annotations

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
