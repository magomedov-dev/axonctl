# Actions & gestures


## Node actions

Node actions target a node by [`Selector`][axonctl.Selector]; the agent re-finds
it from a fresh root and acts. They retry automatically on `STALE` (see below).

```python
await device.click(Selector.text("Next"))
await device.long_click(Selector.id("com.app:id/item"))
await device.set_text(Selector.id("com.app:id/search"), "hello")
await device.clear(Selector.id("com.app:id/search"))
await device.scroll(Selector.cls("...RecyclerView"), "forward")   # or "backward"
await device.focus(Selector.id("com.app:id/field"))
await device.clear_focus(Selector.id("com.app:id/field"))
await device.select(Selector.id("com.app:id/item"))
await device.set_selection(Selector.id("com.app:id/field"), 0, 4)
```

All accept `window_id=` to act within a specific window (from
[`windows`][axonctl.Device.windows]). They raise the matching typed error —
`NodeNotFound`, `AmbiguousMatch`, `ActionNotSupported`, `NotEditable`,
`WindowNotFound`, `Stale`, or `UnsupportedSelector` (for a `.within(...)`
selector). See [Error handling](errors.md).

!!! note "Selectors for actions"
    Actions use `by`/`value`/`match`/`index` (+ optional `window_id`).
    `.within(...)` is a query-only scoping and raises `UnsupportedSelector` if
    passed to an action — use `window_id` or a more specific selector.

## Gestures (coordinates)

Gestures take raw screen coordinates (milliseconds for durations):

```python
await device.tap(540, 1200)
await device.double_tap(540, 1200)
await device.long_tap(300, 800, duration=800)
await device.swipe(540, 1600, 540, 600, duration=250)            # flick
await device.drag(200, 400, 800, 400, duration=800)             # slow drag
await device.pinch(540, 1000, start_radius=300, end_radius=80)  # pinch in (zoom out)
```

Tap a found node via its center:

```python
node = await device.find(Selector.text("Menu"))
if node and node.center:
    await device.tap(node.center.x, node.center.y)
```

Gestures raise [`GestureFailed`][axonctl.GestureFailed] if cancelled or
undispatchable.

## Global actions

```python
await device.global_action("home")          # back | home | recents | notifications
await device.global_action("back")          # quickSettings | powerDialog | lockScreen
```

Returns the platform's `bool` result; raises `InvalidParams` for an unknown action.

## STALE retries

`STALE` means the agent found a node but it changed before the action landed — a
transient condition. The controller (not the device) retries: each retry re-issues
the `nodeAction`, which re-finds from a fresh root. Tune via the `[retry]` config
(`attempts`, `delay`).

For your own multi-step helpers, use the decorator:

```python
from axonctl import retry_on_stale

@retry_on_stale(attempts=5)
async def confirm(device):
    await device.click(Selector.text("Confirm"))
```

## adb-side actions

When a device comes from a [`FleetController`][axonctl.FleetController], it is bound
to adb and can manage apps:

```python
await device.launch("com.example.app")
await device.kill("com.example.app")
await device.install("/path/to/app.apk")
```

(For a standalone `connect_device` device with no adb bound, these raise
`RuntimeError`.)

See also: [Waiting](waiting.md) and [Screenshots](screenshots.md).
