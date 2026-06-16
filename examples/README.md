# axonctl examples

**English** · [Русский](README.ru.md)

Standalone scripts that import `axonctl` exactly as an external project would.
They are **not** part of the package.

| Script | What it shows |
|--------|---------------|
| `single_device.py` | Connect to one device, wait for an element, read it. |
| `inspect_ui.py` | Dump the UI and print a compact tree (find selectors). |
| `run_group.py` | `FleetController` + `run` across a group, with `Results`. |
| `fleet.toml` | Sample fleet configuration. |

## Running

Install the library, then for the single-device scripts set up a forward first:

```bash
pip install axonctl
adb forward tcp:10001 tcp:9008
python examples/single_device.py <serial>
python examples/inspect_ui.py <serial>
```

For the fleet example, edit `fleet.toml` with your serial(s) and run:

```bash
python examples/run_group.py
```

The fleet controller sets up forwards for you, so no manual `adb forward` is
needed there.
