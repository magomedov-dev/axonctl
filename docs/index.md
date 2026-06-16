# axonctl


`axonctl` is the **PC-side controller** for [Axon](https://github.com/magomedov-dev/axon),
an Android device-fleet automation system. Each device runs an Accessibility-service
agent (an APK) that exposes a **stateless** JSON-RPC API over a WebSocket;
`axonctl` connects to every device over `adb forward`, manages the whole fleet,
and gives your automation code an ergonomic, fully `async` API.

It is a **reusable library**, not an application: you install `axonctl` and write
*your own* scenarios in *your own* project. The library provides the foundation —
fleet connection, UI find/wait/act, running functions across device groups — and
your scenarios are just `async` functions that take a [`Device`][axonctl.Device].

## Why it is shaped this way

- **The device is stateless.** All state — what to wait for, retries, tree
  navigation, element search — lives on the PC. The agent exposes only atomic
  primitives. See [Concepts](concepts.md).
- **Waits are event-driven, not polling.** `wait_for`/`wait_gone` react to the
  agent's `screenChanged` stream, so they are cheap and fast.
- **One event loop, hundreds of devices.** Every scenario runs as a concurrent
  asyncio task in a single thread; while one device waits on the socket, the loop
  serves the others. This is why a blocking call in your scenario is dangerous —
  see [Writing scenarios](scenarios.md).

## A taste

```python
import asyncio
from axonctl import FleetController, Selector

async def login(device):
    await device.launch("com.example.app")
    await device.wait_for(Selector.id("com.example.app:id/user"))
    await device.set_text(Selector.id("com.example.app:id/user"), "alice")
    await device.click(Selector.text("Sign in"))
    return await device.wait_toast(timeout=5)

async def main():
    async with FleetController.from_config("fleet.toml") as fleet:
        results = await fleet.run(login, targets="group_us", concurrency=10)
        for serial, outcome in results.items():
            print(serial, outcome.ok, outcome.value or outcome.error)

asyncio.run(main())
```

## Where to go next

**Getting started**

- [Installation](installation.md) — requirements, adb, device prep.
- [Quickstart](quickstart.md) — run your first scenario.
- [Troubleshooting](troubleshooting.md) — common issues and fixes.

**Concepts**

- [Concepts](concepts.md) — the principles the API is built on (stateless device,
  event-driven waits, the single-loop execution model).

**Guides**

- [UI inspector](inspector.md) — interactive screen explorer (like Appium).
- [Selectors](selectors.md) · [The UI tree](tree.md) · [Waiting](waiting.md)
- [Actions & gestures](actions.md) · [Screenshots](screenshots.md) ·
  [Windows & dialogs](windows.md)
- [Fleet management](fleet.md) · [Writing scenarios](scenarios.md) ·
  [Configuration](configuration.md) · [Error handling](errors.md)
- [Cookbook](cookbook.md) — copy-pasteable patterns.

**Reference**

- [Architecture](architecture.md) — the internal layers (for contributors).
- [API Reference](api.md) — the full public API.
- [Protocol](PROTOCOL.md) — the device wire protocol.

## Disclaimer

`axonctl` automates and manages Android devices that **you own or are legally
authorized to control**. You are responsible for complying with all applicable
laws and the terms of service of any software you automate.
