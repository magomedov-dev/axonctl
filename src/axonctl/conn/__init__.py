"""Transport layer (internal).

WebSocket client, frame routing, the per-device connection, and the reconnect
policy. This layer knows about sockets and message framing but nothing about the
RPC semantics above it. Not part of the public API.
"""

from __future__ import annotations
