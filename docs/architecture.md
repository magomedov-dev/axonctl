# Architecture


This page is for contributors and the curious. It maps the internal layers behind
the public API. Only the names re-exported from `axonctl` are a stable contract;
everything below is an implementation detail.

## Layers (bottom up)

```
PC client ──(adb forward tcp:<port> tcp:9008)──► on-device agent

fleet/      controller · watcher · ports · adb · groups · executor   (the park)
device.py   Device facade · gestures · wait · retry
tree/       geom · node · tree · window · selector   (pure, no I/O)
events/     bus · state                              (per-device)
rpc/        client · pending · ids · errors
conn/       ws · router · connection · reconnect     (transport)
```

Each device is fully independent: its own connection, id generator, pending
registry, and event bus. The only shared primitive is the executor's global
concurrency semaphore.

## Transport (`conn/`)

- **`WsClient`** (`ws.py`) — a thin wrapper over `websockets` behind the
  `WebSocketTransport` protocol (the seam tests fake). `max_size` is disabled
  because dumps can be large.
- **`FrameRouter`** (`router.py`) — classifies each inbound frame: binary
  (first 4 bytes BE = id) → pending; text + `id` → pending; text + `event` →
  event bus.
- **`DeviceConnection`** (`connection.py`) — one per device. A single
  **supervisor** task runs the read loop and ping loop and, on a drop, reconnects
  with backoff (reopening the same URI; it never touches adb). It enables the event
  stream on connect (concurrently, so a drop is detected even if the agent never
  answers). `close()` stops everything cleanly.
- **`ReconnectPolicy`** (`reconnect.py`) — exponential backoff with cap and
  jitter.

## RPC (`rpc/`)

- **`IdGenerator`** — monotonic ids, wrap at 2³²−1, never reusing a pending id.
- **`PendingRegistry`** — id → future. Handles the two-part (variant A) screenshot
  reply (metadata + binary resolve together); `cancel_all` wakes everyone on a
  drop.
- **`RpcClient`** — `call`/`call_binary` with a per-call `asyncio.timeout` and
  guaranteed cleanup. Error responses become typed `RpcError` subclasses.
- **`errors.py`** — the exception hierarchy and wire-code → class mapping.

## Events (`events/`)

- **`EventBus`** — per-device fan-out to short-lived subscribers (one queue each);
  `interrupt()` wakes waiters on a transient drop, `close()` on a permanent one.
- **`ScreenState`** — last `screen` + `package`, fed by events and dumps.

## UI tree (`tree/`, pure)

`Bounds`/`Point`, `UiNode`/`UiTree` (parse + navigation; parent links built
lazily), `Window`/`WindowList`, and `Selector` (evaluated on the PC). No I/O —
trivially testable.

## Device facade (`device.py`, `gestures.py`, `wait.py`, `retry.py`)

`Device` composes the above into the user-facing API. `WaitEngine` runs the
event-driven waits; `GestureBuilder` assembles stroke params; `RetryPolicy`
handles `STALE`.

## Fleet (`fleet/`)

- **`AdbWatcher`** — wraps `adbutils.track_devices()` (a blocking iterator bridged
  from a daemon thread) into an async attach/detach stream.
- **`AdbBridge`** — adb operations (`forward`, `shell`, `launch`, ...) off-loaded
  to threads; **`PortAllocator`** hands out local ports.
- **`TagIndex` / `DeviceGroup`** — tag → serials, and target resolution.
- **`FleetController`** — the registry and lifecycle: attach → port → forward →
  connect → register; detach → close (stop reconnect) → remove forward → free
  port. Coordinates reconnect-vs-detach so they never race.
- **`FleetExecutor`** — runs a scenario per device under the shared global
  semaphore, collecting per-device `Outcome`s into `Results`.

## Design invariants

- **Never block the event loop.** Blocking adb / parsing go through threads/pools.
- **A timeout on every external await.** No call or wait hangs forever.
- **Clean cancellation.** `close()/stop()` cancel and await every task.
- **Per-device isolation.** No global locks on the hot path; one device's failure
  never sinks the fleet.
- **Event-driven, not polling.** Waits react to `screenChanged`.

## Testing

- **unit** — pure logic (tree/selectors, gesture assembly, id rollover, error
  mapping, frame classification, ports, groups), plus an ASCII guard on protocol
  keys.
- **integration** — an in-process fake agent (a real WebSocket server) drives the
  whole path: ping/dump, event-driven waits, screenshot correlation, reconnect,
  fleet attach/detach, and the executor.

See the [Protocol](PROTOCOL.md) for the wire format.
