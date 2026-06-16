"""Dump the current UI and print a compact tree — handy for finding selectors.

Set up the forward first (``adb forward tcp:10001 tcp:9008``), then::

    python examples/inspect_ui.py <serial>
"""

from __future__ import annotations

import asyncio
import sys

from axonctl import UiNode, connect_device


def show(node: UiNode, depth: int = 0) -> None:
    label = node.resource_id or (repr(node.text) if node.text else node.class_name)
    print("  " * depth + f"{label}")
    for child in node.children:
        show(child, depth + 1)


async def main(serial: str) -> None:
    async with await connect_device(serial, uri="ws://127.0.0.1:10001") as device:
        tree = await device.dump()
        print(f"package={tree.package} screen={tree.screen}")
        show(tree.root)


if __name__ == "__main__":
    serial = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
    asyncio.run(main(serial))
