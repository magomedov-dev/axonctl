# Error handling


Every failure is a typed exception, so scenarios catch exactly what they mean to.
All axonctl exceptions derive from [`AxonError`][axonctl.AxonError].

## Hierarchy

```
AxonError
├── RpcError                 # a protocol error response (has .code, .message)
│   ├── ParseError           # PARSE_ERROR
│   ├── InvalidRequest       # INVALID_REQUEST
│   ├── MethodNotFound       # METHOD_NOT_FOUND
│   ├── InvalidParams        # INVALID_PARAMS
│   ├── InternalError        # INTERNAL  (e.g. screenshot rate limit)
│   ├── AccessibilityDisabled# ACCESSIBILITY_DISABLED (no active window)
│   ├── WindowNotFound       # WINDOW_NOT_FOUND
│   ├── NodeNotFound         # NODE_NOT_FOUND
│   ├── AmbiguousMatch       # AMBIGUOUS_MATCH (several matched, no index)
│   ├── ActionNotSupported   # ACTION_NOT_SUPPORTED
│   ├── NotEditable          # NOT_EDITABLE
│   ├── Stale                # STALE (node changed under the action)
│   └── GestureFailed        # GESTURE_FAILED
├── RpcTimeout               # a call exceeded its deadline
├── WaitTimeout              # a wait condition was not met in time
├── ConnectionLost           # the socket dropped / could not be used
├── UnsupportedSelector      # a .within(...) selector passed to an action
└── DeviceNotConnected       # a targeted serial is not connected (in Results)
```

`RpcError` carries `.code` (the stable wire code) and `.message`. An unknown code
becomes a plain `RpcError` with that code preserved.

## Catching what you mean

```python
from axonctl import NodeNotFound, WaitTimeout, Stale

async def maybe_dismiss(device):
    try:
        await device.click(Selector.text("Not now"))
    except NodeNotFound:
        pass  # nothing to dismiss — fine

    try:
        await device.wait_for(Selector.id("com.app:id/home"), timeout=8)
    except WaitTimeout:
        return "stuck"
    return "home"
```

## Which methods raise what

Each method's docstring lists its `Raises:`. The common cases:

| Operation | Typical errors |
|-----------|----------------|
| `dump` / `find` / `wait_*` | `AccessibilityDisabled`, `WindowNotFound`, `RpcTimeout`, `ConnectionLost`, `WaitTimeout` (waits) |
| `click` / `set_text` / `scroll` / ... | `NodeNotFound`, `AmbiguousMatch`, `ActionNotSupported`, `NotEditable` (text), `Stale`, `WindowNotFound`, `UnsupportedSelector` |
| `tap` / `swipe` / `pinch` / ... | `GestureFailed`, `ConnectionLost` |
| `screenshot` | `InvalidParams`, `InternalError` (rate limit), `ConnectionLost` |
| `global_action` | `InvalidParams`, `ConnectionLost` |
| `launch` / `kill` / `install` | `RuntimeError` (no adb bound) |

## Errors in a fleet run

Inside [`run`][axonctl.FleetController.run], a per-device failure does **not**
abort the run — it is captured as a failed [`Outcome`][axonctl.Outcome]:

```python
results = await fleet.run(login, targets="group_us")
for serial, outcome in results.items():
    if outcome.ok:
        print(serial, "->", outcome.value)
    else:
        print(serial, "failed:", type(outcome.error).__name__, outcome.error)

print("failures:", results.failed())   # serial -> exception
```

A targeted-but-disconnected device appears as a failed outcome carrying
[`DeviceNotConnected`][axonctl.DeviceNotConnected] — never silently missing.

`Outcome.unwrap()` returns the value or re-raises the captured error, if you
prefer to handle failures with `try/except` per device.

See also: [Writing scenarios](scenarios.md) and [Fleet management](fleet.md).
