# Screenshots


[`Device.screenshot`][axonctl.Device.screenshot] captures the screen and returns
the encoded image **bytes**:

```python
jpeg = await device.screenshot()                 # jpeg, quality 80
jpeg = await device.screenshot(quality=60)
png = await device.screenshot(format="png")      # quality is ignored for PNG

from pathlib import Path
Path("shot.png").write_bytes(png)
```

## Rate limit

The platform throttles captures to roughly **one per second**; calling faster
fails with [`InternalError`][axonctl.InternalError]. Pace your screenshots:

```python
shot1 = await device.screenshot()
await device.sleep(1.1)        # respect the ~1/sec limit
shot2 = await device.screenshot()
```

## How it works (variant A)

The screenshot reply is two messages — JSON metadata immediately followed by a
binary frame whose 4-byte big-endian header carries the request id. axonctl's
pending registry correlates the pair and resolves the call only when both have
arrived, so you just get clean `bytes` back. You never deal with the framing.

## Heavy processing belongs off the loop

Decoding/analyzing an image is CPU-bound. Doing it inline blocks the event loop
and stalls every other device. Hand it to a pool:

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

POOL = ProcessPoolExecutor()

async def analyze(device):
    img = await device.screenshot()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(POOL, heavy_cv, img)   # off the loop
    return result
```

See [Concepts](concepts.md) for the execution-model rules.
