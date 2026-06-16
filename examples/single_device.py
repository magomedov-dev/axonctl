"""Minimal single-device example: connect, wait for an element, and read it.

This imports ``axonctl`` exactly as an external user would. It uses
``connect_device`` (a convenience for experiments); real projects should use
``FleetController`` instead — see ``run_group.py``.

Set up the forward yourself first, e.g.::

    adb forward tcp:10001 tcp:9008

Then run::

    python examples/single_device.py <serial>
"""

from __future__ import annotations

import asyncio
import sys

from axonctl import Selector, connect_device


async def main(serial: str) -> None:
    async with connect_device(serial, uri="ws://127.0.0.1:10001") as device:
        print("ping:", dict(await device.ping()))
        await device.global_action("home")
        node = await device.wait_for(Selector.text_contains("Settings"), timeout=10)
        print("found:", repr(node.text), "at", node.center)


if __name__ == "__main__":
    serial = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
    asyncio.run(main(serial))
