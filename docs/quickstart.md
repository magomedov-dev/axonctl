# Quickstart

**English** · [Русский](quickstart.ru.md)

## Install

```bash
pip install axonctl   # requires Python 3.11+
```

`axonctl` needs the Android `adb` binary. It is resolved in this order:
`$AXONCTL_ADB` → `.tooling/platform-tools/adb` → `adb` on `PATH`. If you are
working from this repository, `scripts/bootstrap.sh` provisions everything
(including `adb`) into a project-local `.tooling/`.

## Prepare a device

1. Install and enable the Axon agent (the APK) on the device; grant it the
   Accessibility permission.
2. Connect the device over USB and confirm `adb devices` lists it.

The controller sets up the `adb forward` for you — you do not run it manually.

## Your first scenario

Describe your fleet in `fleet.toml`:

```toml
concurrency = 8

[devices]
"YOUR_SERIAL" = ["demo"]
```

Then write a scenario and run it:

```python
import asyncio
from axonctl import FleetController, Selector

async def open_settings(device):
    await device.launch("com.android.settings")
    await device.wait_package("com.android.settings", timeout=10)
    tree = await device.dump()
    return tree.package

async def main():
    async with FleetController.from_config("fleet.toml") as fleet:
        results = await fleet.run(open_settings, targets="demo")
        for serial, outcome in results.items():
            print(serial, "->", outcome.value if outcome.ok else outcome.error)

asyncio.run(main())
```

## A single device, without the fleet

For quick experiments you can connect to one device directly (set up the forward
yourself first, e.g. `adb forward tcp:10001 tcp:9008`):

```python
import asyncio
from axonctl import connect_device, Selector

async def main():
    async with connect_device("YOUR_SERIAL", uri="ws://127.0.0.1:10001") as device:
        print(await device.ping())
        node = await device.find(Selector.text_contains("Settings"))
        print(node)

asyncio.run(main())
```

!!! note
    `connect_device` is a convenience for experiments and tests; production code
    should use [`FleetController`][axonctl.FleetController], which manages forwards,
    ports, reconnection, and groups for you.

Next: [Concepts](concepts.md) and [Writing scenarios](scenarios.md).
