"""Typed exception hierarchy for axonctl.

Every protocol error ``code`` maps to a distinct, catchable exception class so
user scenarios can handle failures precisely (``except NodeNotFound``). Transport
and timeout failures get their own types. All library exceptions derive from
:class:`AxonError`.

The mapping from a wire ``code`` to a class is :func:`error_from_code`.
"""

from __future__ import annotations


class AxonError(Exception):
    """Base class for every exception raised by axonctl."""


class RpcError(AxonError):
    """A JSON-RPC error response returned by the device agent.

    Attributes:
        code: The stable protocol error code (e.g. ``"NODE_NOT_FOUND"``).
        message: Human-readable message from the agent.
    """

    # Default code; subclasses override it and instances may shadow it with the
    # original wire code for unrecognized errors.
    code: str = "RPC_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        """Initialize the error.

        Args:
            message: Human-readable message from the agent.
            code: Override for the protocol code; defaults to the subclass code.
        """
        # Instance attribute shadows the class default; lets unknown codes keep
        # their original wire value while known subclasses use their fixed code.
        self.code = code if code is not None else type(self).code
        self.message = message
        super().__init__(f"[{self.code}] {message}")


class ParseError(RpcError):
    """Request was not valid JSON (``PARSE_ERROR``)."""

    code = "PARSE_ERROR"


class InvalidRequest(RpcError):
    """Valid JSON but not a proper request (``INVALID_REQUEST``)."""

    code = "INVALID_REQUEST"


class MethodNotFound(RpcError):
    """Unknown method (``METHOD_NOT_FOUND``)."""

    code = "METHOD_NOT_FOUND"


class InvalidParams(RpcError):
    """Params missing or wrong for the method (``INVALID_PARAMS``)."""

    code = "INVALID_PARAMS"


class InternalError(RpcError):
    """Unexpected server-side failure (``INTERNAL``)."""

    code = "INTERNAL"


class AccessibilityDisabled(RpcError):
    """No active-window root: service off or no foreground window.

    Wire code ``ACCESSIBILITY_DISABLED``.
    """

    code = "ACCESSIBILITY_DISABLED"


class WindowNotFound(RpcError):
    """A given ``windowId`` has no matching window (``WINDOW_NOT_FOUND``)."""

    code = "WINDOW_NOT_FOUND"


class NodeNotFound(RpcError):
    """Node-action criteria matched nothing (``NODE_NOT_FOUND``)."""

    code = "NODE_NOT_FOUND"


class AmbiguousMatch(RpcError):
    """Criteria matched several nodes and no ``index`` was given.

    Wire code ``AMBIGUOUS_MATCH``.
    """

    code = "AMBIGUOUS_MATCH"


class ActionNotSupported(RpcError):
    """The node does not support the requested action (``ACTION_NOT_SUPPORTED``)."""

    code = "ACTION_NOT_SUPPORTED"


class NotEditable(RpcError):
    """``setText``/``clear`` on a non-editable node (``NOT_EDITABLE``)."""

    code = "NOT_EDITABLE"


class Stale(RpcError):
    """``performAction`` returned false — the node went stale (``STALE``).

    Not retried on the device; the controller decides whether to re-dump and
    retry.
    """

    code = "STALE"


class GestureFailed(RpcError):
    """Gesture was cancelled or could not be dispatched (``GESTURE_FAILED``)."""

    code = "GESTURE_FAILED"


class RpcTimeout(AxonError):
    """An RPC call did not receive a response within its deadline."""


class WaitTimeout(AxonError):
    """An event-driven wait condition was not met within its deadline."""


class ConnectionLost(AxonError):
    """The underlying WebSocket connection dropped or could not be used."""


# Wire code -> exception class. Kept beside the classes so adding a code is a
# one-line change here plus the class above.
_CODE_MAP: dict[str, type[RpcError]] = {
    cls.code: cls
    for cls in (
        ParseError,
        InvalidRequest,
        MethodNotFound,
        InvalidParams,
        InternalError,
        AccessibilityDisabled,
        WindowNotFound,
        NodeNotFound,
        AmbiguousMatch,
        ActionNotSupported,
        NotEditable,
        Stale,
        GestureFailed,
    )
}


def error_from_code(code: str, message: str) -> RpcError:
    """Build the typed :class:`RpcError` for a wire error code.

    Args:
        code: The protocol error code from the response.
        message: The accompanying human-readable message.

    Returns:
        An instance of the matching :class:`RpcError` subclass, or a plain
        :class:`RpcError` (carrying ``code``) for an unrecognized code.
    """
    cls = _CODE_MAP.get(code)
    if cls is None:
        return RpcError(message, code=code)
    return cls(message)
