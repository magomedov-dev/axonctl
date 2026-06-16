# Writing scenarios


A scenario is just an `async` function that takes a [`Device`][axonctl.Device] and
returns whatever you want. The library defines the [`Scenario`][axonctl.Scenario]
type for it and runs it across device groups; it knows nothing about the body.

```python
from axonctl import Device, Selector

async def login(device: Device) -> str:
    await device.launch("com.example.app")
    await device.wait_for(Selector.id("com.example.app:id/user"))
    await device.set_text(Selector.id("com.example.app:id/user"), "alice")
    await device.set_text(Selector.id("com.example.app:id/pass"), "secret")
    await device.click(Selector.text("Sign in"))
    return await device.wait_toast(timeout=5)
```

## Selectors

Build selectors with the factories and compose them:

```python
Selector.id("com.app:id/login")
Selector.text("Sign in")
Selector.text_contains("Signing")
Selector.desc("Profile photo")
Selector.cls("android.widget.EditText", index=0)
Selector.text("OK", match="regex")           # matches anywhere; anchor with ^ $
Selector.text("Delete").within(Selector.id("com.app:id/dialog"))
```

`find`/`find_all`/`wait_for` evaluate selectors on the PC over a dump, including
`.within(...)`. Node **actions** (`click`, `set_text`, ...) send the selector to
the agent, which does not support `.within(...)`: passing a `.within(...)`
selector to an action raises [`UnsupportedSelector`][axonctl.UnsupportedSelector]
(never a silent wrong-target click). For "inside a dialog", pass a `window_id`
(from [`windows`][axonctl.Device.windows]); for "inside a container", use a more
specific selector or `tap(node.center)` after a `find`.

A node returned by `find`/`wait_for` is a **snapshot** of the dump, not a live
handle — act on it via criteria (`click(Selector...)`) or `tap(node.center)`, not
the node object itself.

## Finding vs waiting

```python
# one dump + search:
node = await device.find(Selector.id("com.app:id/title"))

# reuse one dump for several queries:
tree = await device.dump()
title = tree.find(Selector.id("com.app:id/title"))
buttons = tree.find_all(Selector.cls("android.widget.Button"))

# event-driven wait (preferred over find-in-a-loop):
await device.wait_for(Selector.text("Continue"), timeout=10)
await device.wait_gone(Selector.id("com.app:id/spinner"), timeout=15)
```

## Acting

```python
await device.click(Selector.text("Next"))
await device.set_text(Selector.id("com.app:id/search"), "hello")
await device.scroll(Selector.cls("androidx.recyclerview.widget.RecyclerView"), "forward")
await device.tap(540, 1200)
await device.swipe(540, 1600, 540, 600)
await device.long_tap(300, 800)
shot = await device.screenshot(format="png")     # ~1/sec rate limit
ok = await device.global_action("home")
```

## Retries

Node actions retry automatically on `STALE` (configurable via `[retry]`). For your
own helpers, use the decorator:

```python
from axonctl import retry_on_stale

@retry_on_stale(attempts=5)
async def tap_continue(device):
    await device.click(Selector.text("Continue"))
```

## Stay non-blocking

Your scenario shares one event loop with every other device. Keep everything fast
or awaited (see [Concepts](concepts.md) for the full rule and the
blocking→async table).

```python
import asyncio
import httpx

async def enrich(device):
    # GOOD: await async I/O and the device's own sleep
    await device.sleep(1.0)                       # not time.sleep
    async with httpx.AsyncClient() as client:     # not requests
        resp = await client.get("https://api.example.com/next")
    await device.set_text(Selector.id("com.app:id/code"), resp.text)
```

Heavy CPU work belongs in a pool:

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

POOL = ProcessPoolExecutor()

async def solve(device):
    image = await device.screenshot()
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(POOL, expensive_cv, image)  # off the loop
    await device.set_text(Selector.id("com.app:id/answer"), answer)
```

## Handling errors

Catch the typed exceptions you care about; everything else surfaces in the run's
[`Results`][axonctl.Results] as a failed [`Outcome`][axonctl.Outcome].

```python
from axonctl import NodeNotFound, WaitTimeout

async def maybe_dismiss(device):
    try:
        await device.click(Selector.text("Not now"))
    except NodeNotFound:
        pass  # nothing to dismiss
    try:
        await device.wait_for(Selector.id("com.app:id/home"), timeout=8)
    except WaitTimeout:
        return "stuck"
    return "home"
```
