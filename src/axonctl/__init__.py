"""axonctl — PC-side async controller for the Axon Android device-fleet system.

`axonctl` connects to a fleet of Android devices over ``adb forward``, talks to
the on-device Accessibility agent via JSON-RPC over a WebSocket, and gives user
automation code an ergonomic, fully ``async`` API.

This package is a **reusable library**: install it and write your own automation
scenarios in your own project. A scenario is just an ``async`` function taking a
:class:`Device`; the library runs it across device groups.

The public API is intentionally narrow — only the names re-exported here (and
listed in :data:`__all__`) are a stable contract. Everything under the internal
layers (``conn``, ``rpc``, ``events``, parts of ``fleet``) is an implementation
detail and may change without notice.

Note:
    The public surface is built up stage by stage. As of Stage 1 it covers the
    transport/RPC vertical slice: :class:`Device` (``ping``/``dump``), the parsed
    UI tree types, configuration, and the exception hierarchy.
"""

from __future__ import annotations

from .config import Backoff, FleetConfig, Timeouts
from .conn.connection import ConnectionState
from .device import Device, connect_device
from .rpc.errors import (
    AccessibilityDisabled,
    ActionNotSupported,
    AmbiguousMatch,
    AxonError,
    ConnectionLost,
    GestureFailed,
    InternalError,
    InvalidParams,
    InvalidRequest,
    MethodNotFound,
    NodeNotFound,
    NotEditable,
    ParseError,
    RpcError,
    RpcTimeout,
    Stale,
    WaitTimeout,
    WindowNotFound,
)
from .tree.geom import Bounds, Point
from .tree.node import UiNode
from .tree.selector import Selector
from .tree.tree import UiTree
from .tree.window import Window, WindowList

__version__ = "0.1.0"

__all__ = [
    # Core facade
    "Device",
    "connect_device",
    # Configuration
    "FleetConfig",
    "Timeouts",
    "Backoff",
    # Connection
    "ConnectionState",
    # UI tree, selectors, and windows
    "UiTree",
    "UiNode",
    "Selector",
    "Window",
    "WindowList",
    "Bounds",
    "Point",
    # Exceptions — base + transport
    "AxonError",
    "RpcError",
    "RpcTimeout",
    "WaitTimeout",
    "ConnectionLost",
    # Exceptions — protocol error codes
    "ParseError",
    "InvalidRequest",
    "MethodNotFound",
    "InvalidParams",
    "InternalError",
    "AccessibilityDisabled",
    "WindowNotFound",
    "NodeNotFound",
    "AmbiguousMatch",
    "ActionNotSupported",
    "NotEditable",
    "Stale",
    "GestureFailed",
]
