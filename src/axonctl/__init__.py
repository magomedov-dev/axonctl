"""axonctl — PC-side async controller for the Axon Android device-fleet system.

`axonctl` connects to a fleet of Android devices over ``adb forward``, talks to
the on-device Accessibility agent via JSON-RPC over a WebSocket, and gives user
automation code an ergonomic, fully ``async`` API.

This package is a **reusable library**: install it and write your own automation
scenarios in your own project. A scenario is just an ``async`` function taking a
:class:`~axonctl.Device`; the library runs it across device groups.

The public API is intentionally narrow — only the names re-exported here (and
listed in :data:`__all__`) are a stable contract. Everything under the internal
layers (``conn``, ``rpc``, ``events``, parts of ``fleet``) is an implementation
detail and may change without notice.

Note:
    The public surface is built up stage by stage; ``__all__`` is empty until the
    relevant layers land (see ``IMPLEMENTATION_PLAN.md``).
"""

from __future__ import annotations

__version__ = "0.1.0"

# The public API is exported here as each stage lands. Keep this list the single
# source of truth for what `from axonctl import *` and external users may rely on.
__all__: list[str] = []
