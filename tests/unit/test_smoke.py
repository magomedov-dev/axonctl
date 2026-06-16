"""Smoke tests: the package imports and the async test harness works.

These prove the Stage 0 scaffolding is sound (installable package, importable
under the src layout, working pytest-asyncio) before any real layer lands.
"""

from __future__ import annotations

import asyncio

import axonctl


def test_package_has_version() -> None:
    assert isinstance(axonctl.__version__, str)
    assert axonctl.__version__


def test_public_api_is_an_explicit_list() -> None:
    # The public surface grows stage by stage; for now it is intentionally empty.
    assert isinstance(axonctl.__all__, list)


async def test_async_harness_runs() -> None:
    await asyncio.sleep(0)
