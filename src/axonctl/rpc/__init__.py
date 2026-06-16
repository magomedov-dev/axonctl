"""JSON-RPC layer (internal).

Request-id generation, the pending-request registry (including the two-part
screenshot correlation), the typed error hierarchy, and the RPC client. Maps the
wire protocol onto awaitable calls. Only the error classes are surfaced publicly
(re-exported from :mod:`axonctl`); the rest is an implementation detail.
"""

from __future__ import annotations
