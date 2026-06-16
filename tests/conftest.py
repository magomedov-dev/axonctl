"""Shared pytest configuration for the axonctl test suite.

``asyncio_mode = "auto"`` (set in ``pyproject.toml``) means ``async def`` tests
run without an explicit ``@pytest.mark.asyncio`` decorator. Unit tests live under
``tests/unit`` (pure logic, no sockets); integration tests under
``tests/integration`` (run against an in-process fake agent).
"""

from __future__ import annotations
