# axonctl

> **Status: early development (0.1.0).** Public API is taking shape — see
> [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

`axonctl` is the **PC-side controller** for [Axon](https://github.com/magomedov-dev/axon)
— an Android device-fleet automation system. On each device an Accessibility-service agent (APK) exposes a
stateless JSON-RPC API over a WebSocket; `axonctl` connects to every device over
`adb forward`, manages the whole fleet, and gives your automation code an
ergonomic `async` API.

It is a **reusable library**, not an application: you install `axonctl` and write
*your own* automation scenarios in *your own* project. The library provides the
foundation (fleet connection, UI find/wait/act, running functions across device
groups); the scenarios are your code, living outside this repository.

## Quick start (target shape — not yet implemented)

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
            print(serial, outcome)

asyncio.run(main())
```

## Installation (placeholder)

```bash
pip install axonctl          # not yet published
```

Requires Python 3.11+.

## Documentation

- Protocol reference: [`docs/PROTOCOL.md`](docs/PROTOCOL.md) (canonical source:
  the [Axon agent repo](https://github.com/magomedov-dev/axon), `docs/PROTOCOL.md`).
- Full docs site: built with MkDocs (planned).

## Disclaimer

`axonctl` is a tool for automating and managing Android devices that **you own or
are legally authorized to control**. You are responsible for complying with all
applicable laws and the terms of service of any software you automate.

## License

[MIT](LICENSE).
