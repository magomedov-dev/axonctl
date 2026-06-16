"""Event layer (internal).

The per-device event bus (server-push ``screenChanged`` / ``toast``) and the
screen-state tracker that lets event-driven waits decide when a fresh dump is
needed. Not part of the public API.
"""

from __future__ import annotations
