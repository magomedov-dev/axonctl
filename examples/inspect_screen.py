"""Generate an interactive HTML inspector of the current screen.

Set up a forward first (``adb forward tcp:10001 tcp:9008``), then::

    python examples/inspect_screen.py <serial> [output.html]

Open the resulting file in a browser: hover/click the screenshot or the tree to
inspect elements and copy ready-made selectors.
"""

from __future__ import annotations

import asyncio
import sys

from axonctl import connect_device


async def main(serial: str, out: str) -> None:
    async with connect_device(serial, uri="ws://127.0.0.1:10001") as device:
        path = await device.inspect(out, format="png")
        print("inspector written to", path)


if __name__ == "__main__":
    serial = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
    out = sys.argv[2] if len(sys.argv) > 2 else "inspector.html"
    asyncio.run(main(serial, out))
