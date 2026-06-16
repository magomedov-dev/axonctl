# Installation


## Requirements

- **Python 3.11+** (axonctl uses `asyncio.TaskGroup` and `asyncio.timeout`).
- The Android **`adb`** binary (from Android platform-tools).
- One or more devices running the **Axon agent** (the APK) with the Accessibility
  permission granted.

## Install the library

```bash
pip install axonctl
```

This pulls the runtime dependencies (`websockets`, `orjson`, `adbutils`). The
package ships type information (`py.typed`), so your type checker sees axonctl's
types with no extra stubs.

## adb resolution

axonctl needs the `adb` binary to forward ports and manage apps. It is resolved in
this order:

1. `$AXONCTL_ADB` — an explicit path you set.
2. `.tooling/platform-tools/adb` — a project-local copy (see below).
3. `adb` on your `PATH` — a system install.

You can also set it in config: `adb_path = "/path/to/adb"`.

## Project-local toolchain (optional, recommended for development)

If you are working **in the axonctl repository**, everything — `uv`, a managed
Python, the dev virtualenv, and `adb` — installs into a project-local `.tooling/`
directory so nothing touches your system:

```bash
scripts/bootstrap.sh          # uv + Python + venv + adb, all under .tooling/
source .tooling/venv/bin/activate
```

Individual steps are available too (`scripts/install-uv.sh`,
`scripts/setup-venv.sh`, `scripts/install-adb.sh`).

For your **own** automation project, a normal virtualenv plus `pip install axonctl`
is all you need; point axonctl at a system `adb` (or set `$AXONCTL_ADB`).

## Prepare a device

1. Install and enable the Axon agent on the device.
2. Grant it the **Accessibility** permission (Settings → Accessibility).
3. Connect over USB and confirm `adb devices` lists it as `device` (not
   `unauthorized` / `offline`).

The agent listens on `0.0.0.0:9008`; the controller sets up the
`adb forward tcp:<local> tcp:9008` for you — you do not run it manually when using
[`FleetController`][axonctl.FleetController].

## Verify the install

```python
import asyncio
from axonctl import connect_device

async def main():
    # set up a forward first for this one-off check:
    #   adb forward tcp:10001 tcp:9008
    async with connect_device("YOUR_SERIAL", uri="ws://127.0.0.1:10001") as device:
        print(await device.ping())

asyncio.run(main())
```

A `{'pong': True, 'ts': ...}` means the whole pipeline (socket → agent) is alive.

Next: the [Quickstart](quickstart.md).
