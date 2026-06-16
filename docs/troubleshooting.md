# Troubleshooting


## `run()` returns an empty `Results` / nothing happens

The fleet was still connecting when you called `run()`. By default
`FleetController.start()` / `async with` waits for present devices
(`wait_ready=True`); if you disabled it, either re-enable it or
`await fleet.wait_ready()` before running. An empty target set also logs a warning
— check that your `targets` group/tag matches the configured `[devices]`.

## A device in my group didn't run

If a configured group member isn't connected, it appears in `Results` as a **failed
outcome** carrying [`DeviceNotConnected`][axonctl.DeviceNotConnected] (not silently
skipped). Check the device is plugged in, authorized (`adb devices` shows
`device`), and running the agent.

## `AccessibilityDisabled` on every call

The agent has no active-window root — usually the **Accessibility permission is
off**, or the screen is locked / has no foreground app. Re-grant the permission
(Settings → Accessibility) and unlock the device. A *transient*
`AccessibilityDisabled` mid app-launch is normal and tolerated by waits.

## `adb` not found

axonctl resolves adb as `$AXONCTL_ADB` → `.tooling/platform-tools/adb` → `PATH`.
Set `$AXONCTL_ADB`, run `scripts/install-adb.sh` (in the repo), or set `adb_path`
in config.

## `ConnectionLost` during a scenario

The socket dropped (often the agent service restarted). While the device stays
present, the controller reconnects automatically with backoff; the in-flight call
fails with `ConnectionLost`, but the device becomes usable again. In a `run`, this
is captured as a failed outcome — the rest of the fleet keeps going.

## `wait_for` always times out

- The element never appears — verify the selector with `examples/inspect_ui.py`.
- You waited for an **activity name**: `wait_package` matches the foreground
  *package*; the agent does not expose activity names.
- The screen genuinely never changes — waits are event-driven, so if nothing
  emits `screenChanged`, only the timeout fires. Increase `timeout` or check the
  app state.

## `UnsupportedSelector` when clicking

You passed a `.within(...)` selector to an action. `.within(...)` is query-only.
Use `window_id` (for a dialog/IME) or a more specific selector, or
`tap(node.center)` after a `find`. See [Selectors](selectors.md).

## `screenshot` fails with `InternalError`

The platform throttles captures to ~1/sec. Pace them (`await device.sleep(1.1)`
between shots). See [Screenshots](screenshots.md).

## The whole fleet is mysteriously slow

Almost always a **blocking call inside a scenario** (`time.sleep`, synchronous
`requests`, a blocking DB driver, or seconds of CPU). It freezes the single event
loop and stalls every device. Use async equivalents or a pool — see the
blocking→async table in [Concepts](concepts.md).

## `RuntimeError: no adb bridge bound`

You called `launch`/`kill`/`install` on a device from `connect_device` (which binds
no adb). Use a [`FleetController`][axonctl.FleetController] for app management.

## Enabling logs

axonctl logs under the `axonctl` logger namespace (per-device serials included).
Turn it up while debugging:

```python
import logging
logging.basicConfig(level=logging.INFO)        # or DEBUG for more
logging.getLogger("axonctl").setLevel(logging.DEBUG)
```
