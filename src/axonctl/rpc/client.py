"""The RPC client.

Turns ``await call("method", params)`` into a request on the wire and an
awaitable reply, with a deadline on every call. Error responses are raised as the
matching :class:`~axonctl.rpc.errors.RpcError` subclass; a missed deadline raises
:class:`~axonctl.rpc.errors.RpcTimeout`. The client is transport-agnostic: it is
handed a ``send`` coroutine, the shared :class:`PendingRegistry`, and an
:class:`IdGenerator`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import orjson

from .errors import RpcTimeout, error_from_code
from .ids import IdGenerator
from .pending import PendingRegistry, Response


class RpcClient:
    """Issues JSON-RPC calls over a device connection."""

    def __init__(
        self,
        *,
        send: Callable[[str], Awaitable[None]],
        pending: PendingRegistry,
        ids: IdGenerator,
        timeout: float,
    ) -> None:
        """Initialize the client.

        Args:
            send: Coroutine that puts a text frame on the wire.
            pending: Shared registry the router resolves replies into.
            ids: Request-id generator for this connection.
            timeout: Default per-call deadline in seconds.
        """
        self._send = send
        self._pending = pending
        self._ids = ids
        self._timeout = timeout

    async def call(
        self,
        method: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Call ``method`` and return its ``result`` object.

        Args:
            method: RPC method name.
            params: Optional params object.
            timeout: Override for the per-call deadline in seconds.

        Returns:
            The ``result`` object (empty dict if the agent sent none).

        Raises:
            RpcError: Any protocol error returned by the agent (the concrete
                subclass depends on the error code).
            RpcTimeout: If no reply arrives within the deadline.
            ConnectionLost: If the connection drops while awaiting the reply.
        """
        response = await self._request(
            method, params, expects_binary=False, timeout=timeout
        )
        if response.error is not None:
            raise error_from_code(
                str(response.error.get("code", "INTERNAL")),
                str(response.error.get("message", "")),
            )
        return dict(response.result or {})

    async def call_binary(
        self,
        method: str,
        params: Mapping[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> tuple[dict[str, Any], bytes]:
        """Call ``method`` expecting a two-part (metadata + binary) reply.

        Args:
            method: RPC method name (e.g. ``"screenshot"``).
            params: Optional params object.
            timeout: Override for the per-call deadline in seconds.

        Returns:
            A ``(metadata, payload)`` tuple.

        Raises:
            RpcError: Any protocol error returned by the agent.
            RpcTimeout: If the reply does not complete within the deadline.
            ConnectionLost: If the connection drops while awaiting the reply.
        """
        response = await self._request(
            method, params, expects_binary=True, timeout=timeout
        )
        if response.error is not None:
            raise error_from_code(
                str(response.error.get("code", "INTERNAL")),
                str(response.error.get("message", "")),
            )
        if response.binary is None:
            raise error_from_code("INTERNAL", f"{method}: expected a binary frame")
        return dict(response.result or {}), response.binary

    async def _request(
        self,
        method: str,
        params: Mapping[str, Any] | None,
        *,
        expects_binary: bool,
        timeout: float | None,
    ) -> Response:
        req_id = self._ids.next()
        future = self._pending.register(req_id, expects_binary=expects_binary)
        payload: dict[str, Any] = {"id": req_id, "method": method}
        if params:
            payload["params"] = dict(params)
        text = orjson.dumps(payload).decode("utf-8")
        deadline = self._timeout if timeout is None else timeout
        try:
            await self._send(text)
            async with asyncio.timeout(deadline):
                return await future
        except TimeoutError as exc:
            raise RpcTimeout(f"{method} timed out after {deadline}s") from exc
        finally:
            self._pending.pop(req_id)
