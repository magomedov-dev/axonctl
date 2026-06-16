# Waiting


Waits are the speed-critical core of axonctl. They are **event-driven, never
polling**: a wait subscribes to the agent's `screenChanged` stream, takes a
baseline dump, and re-dumps **only** when the screen actually changes.

## The wait methods

```python
node = await device.wait_for(Selector.id("com.app:id/ok"), timeout=10)   # -> UiNode
await device.wait_gone(Selector.id("com.app:id/spinner"), timeout=15)    # -> None
await device.wait_package("com.android.settings", timeout=10)            # -> None
toast = await device.wait_toast(timeout=5)                               # -> str
```

- [`wait_for`][axonctl.Device.wait_for] resolves when the selector matches; returns
  the node.
- [`wait_gone`][axonctl.Device.wait_gone] resolves when the selector matches
  nothing.
- [`wait_package`][axonctl.Device.wait_package] resolves when the foreground
  package equals the given value. (The agent does not expose activity names —
  pass a **package**, e.g. `"com.android.settings"`. `wait_activity` is a kept
  alias.)
- [`wait_toast`][axonctl.Device.wait_toast] returns the next toast's text.

All raise [`WaitTimeout`][axonctl.WaitTimeout] on deadline, and
[`ConnectionLost`][axonctl.ConnectionLost] if the link drops mid-wait.

## Why not just loop on `find`?

A `find`-in-a-loop polls: it re-dumps on a timer whether or not anything changed,
wasting work and adding latency. An event-driven wait re-dumps only on a real
change, so it is both cheaper and faster to react. Prefer `wait_for` over manual
retry loops.

## The event stream is automatic

The library enables the agent's event stream **when a device connects** (and
re-enables it after a reconnect) — you never call `setEventStream` yourself.
Because it is on from the start, waits work immediately and toasts are captured
even before you ask for them.

## Toasts are ephemeral — the race is handled

Toasts fire immediately (no debounce) and vanish in a fraction of a second. The
classic pattern is "do something, then read the feedback":

```python
await device.click(Selector.text("Sign in"))
feedback = await device.wait_toast(timeout=5)   # e.g. "Wrong password"
```

If the toast fired in the gap between `click` returning and `wait_toast`
subscribing, a naive implementation would miss it. axonctl buffers the last toast
with a timestamp, so `wait_toast` returns one that fired in the short window
*before* the call (tunable via `lookback`).

## Transient "no active window"

During app launches a dump can momentarily fail with
`ACCESSIBILITY_DISABLED` (no foreground window yet). Waits tolerate this — they
keep waiting and re-check on the next event rather than failing.

## Timeouts

Every wait takes a `timeout` (seconds) and raises `WaitTimeout` if the condition
is not met in time:

```python
from axonctl import WaitTimeout

try:
    await device.wait_for(Selector.id("com.app:id/home"), timeout=8)
except WaitTimeout:
    ...  # handle the slow/stuck case
```

See also: [Actions & gestures](actions.md) and [Concepts](concepts.md).
