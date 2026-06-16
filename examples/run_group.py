"""Fleet example: run a scenario across a group and print per-device results.

Edit ``examples/fleet.toml`` with your device serial(s), then run::

    python examples/run_group.py
"""

from __future__ import annotations

import asyncio

from axonctl import Device, FleetController, Selector


async def open_and_read(device: Device) -> str:
    """Open Settings and return the first visible text — a tiny demo scenario."""
    await device.launch("com.android.settings")
    await device.wait_package("com.android.settings", timeout=10)
    title = await device.find(Selector.cls("android.widget.TextView"))
    return title.text if title and title.text else "(no title)"


async def main() -> None:
    async with FleetController.from_config("examples/fleet.toml") as fleet:
        results = await fleet.run(open_and_read, targets="demo", concurrency=5)
        for serial, outcome in results.items():
            status = outcome.value if outcome.ok else f"FAILED: {outcome.error}"
            print(f"{serial}: {status}")
        print("all ok:", results.all_ok)


if __name__ == "__main__":
    asyncio.run(main())
