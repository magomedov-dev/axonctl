# Concepts

**English** · [Русский](concepts.ru.md)

## The device is stateless

The on-device agent keeps no state between calls. Every dump starts from a fresh
root; node ids are valid only within one dump and never travel back to the device.
**All** state lives in the controller:

- Element search, tree navigation (parents/children/descendants), partial and
  regex matching — all run on the PC over a dump (see [`Selector`][axonctl.Selector],
  [`UiTree`][axonctl.UiTree]).
- Waits live on the PC and are event-driven.
- Retries (e.g. on `STALE`) are decided by the controller; the device never
  retries.

This keeps the device simple and fast, and puts all the logic where you can test
it.

## Event-driven waits, not polling

A wait subscribes to the agent's `screenChanged` event stream, takes a baseline
dump, and then re-dumps **only** when the screen actually changes. There is no
polling loop. The `screen` counter is monotonic, so "something changed" is a
cheap signal to re-check.

```python
# Resolves the moment the element appears — no busy-waiting.
node = await device.wait_for(Selector.id("com.app:id/ok"), timeout=10)
```

A transient "no active window" mid-transition (e.g. during an app launch) is
tolerated: the wait simply keeps waiting rather than failing.

The library enables the agent's event stream **automatically when a device
connects** (and re-enables it after a reconnect), so events flow from the start —
you never call `setEventStream` yourself. Because the stream is on early,
`wait_toast` can also return a toast that fired in the short window *just before*
the call, closing the race where a form's feedback ("Wrong password") appears
between an action returning and the wait subscribing.

## Groups and tags

Tags are **static**, declared in config (`serial -> tags`). They are not read
from the device and do not change at runtime; the tag index updates only as
devices attach and detach. A [`run`][axonctl.FleetController.run] targets a group
by name, an explicit serial list, a tag predicate, or the whole fleet.

## Execution model — one loop, many devices

This is the most important thing to understand before writing scenarios.

Every scenario, on every device, runs as a **concurrent asyncio task in a single
thread and a single event loop** — not threads, not processes. This is what lets
one process drive hundreds of devices: the work is almost entirely I/O (waiting on
the network and the phones), which costs no CPU. While device A waits for a socket
reply, the loop serves B, C, D.

The consequence: **one mistake in your scenario can stall the entire fleet.** The
rule is — inside a scenario, everything must be either *fast* (milliseconds) or
*awaited*.

Three cases for handling data inside a scenario:

1. **Fast work (ms):** parsing, conditionals, deciding the next action. Nothing to
   do — a millisecond CPU blip is invisible to other devices (they are waiting on
   their own I/O anyway).
2. **Work that waits on external I/O** (your API, a database, a download, a pause):
   use async tools — `httpx`/`aiohttp` instead of `requests`, an async DB driver,
   `await device.sleep(...)` / `await asyncio.sleep(...)` instead of
   `time.sleep(...)`. Then the wait overlaps and the fleet keeps moving.
3. **Heavy CPU for seconds** (images, ML, crypto): move it off the loop with
   `await loop.run_in_executor(pool, fn, data)` — a `ProcessPoolExecutor` for CPU,
   a `ThreadPoolExecutor` for blocking I/O that has no async version.

### Antipattern: blocking the loop

Any blocking call inside a scenario — `time.sleep`, synchronous `requests`, a
blocking DB driver, a multi-second CPU loop — **freezes the event loop and stops
every other device at once.** This is the number-one cause of "mysterious fleet
slowdowns".

| Blocking call            | Async replacement                               |
|--------------------------|-------------------------------------------------|
| `time.sleep(n)`          | `await device.sleep(n)` / `await asyncio.sleep(n)` |
| `requests.get(...)`      | `await httpx.AsyncClient().get(...)` / `aiohttp` |
| sync DB driver           | async driver (`asyncpg`, `aiosqlite`, ...)      |
| `open(...).read()` (big) | `await loop.run_in_executor(pool, ...)` / `aiofiles` |
| CPU-bound `fn(data)`     | `await loop.run_in_executor(process_pool, fn, data)` |
| `subprocess.run(...)`    | `await asyncio.create_subprocess_exec(...)`     |

The [`Device`][axonctl.Device] itself is already non-blocking; the responsibility
for non-blocking *user* code is on the scenario author.

See [Writing scenarios](scenarios.md) for the practical patterns.
