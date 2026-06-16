# Configuration


A fleet is described by [`FleetConfig`][axonctl.FleetConfig], loaded from TOML with
[`from_config`][axonctl.FleetController.from_config] or built programmatically.

## Full TOML reference

```toml
# fleet.toml
agent_port = 9008        # port the on-device agent listens on (forward target)
concurrency = 10         # global cap on simultaneous device operations (USB bus)
adb_path = ""            # explicit adb path; omit/empty to auto-resolve

[ports]                  # local port range for adb forwards
start = 10000
end = 11000

[timeouts]               # seconds
connect = 10             # opening the WebSocket
rpc = 15                 # default per-call deadline
ping_interval = 5        # heartbeat period
ping_timeout = 5         # heartbeat reply deadline before the link is "dead"

[backoff]                # reconnect backoff: min(base*factor**n, max) ± jitter
base = 0.5
factor = 2.0
max = 30
jitter = 0.1             # fraction (0..1)

[retry]                  # STALE retry for node actions
attempts = 3             # total attempts incl. the first
delay = 0.1              # seconds between attempts

[devices]                # serial -> tags (the declared fleet)
"ABC123" = ["group_us", "pixel"]
"DEF456" = ["group_eu"]
```

Every section is optional; omitted keys use the defaults shown above.

## Programmatic config

```python
from axonctl import FleetConfig, Timeouts, Backoff, Retry, FleetController

config = FleetConfig(
    concurrency=20,
    devices={"ABC123": frozenset({"group_us"})},
    timeouts=Timeouts(rpc=20),
    backoff=Backoff(base=1.0, max=60),
    retry=Retry(attempts=5, delay=0.2),
)
fleet = FleetController(config)
```

## Field reference

| Field | Default | Meaning |
|-------|---------|---------|
| `agent_port` | `9008` | Port the agent listens on (forward target). |
| `port_range` | `(10000, 11000)` | Inclusive local port range for forwards. |
| `concurrency` | `8` | Global semaphore size, shared by all runs (USB-bus cap). |
| `adb_path` | `None` | Explicit adb path; auto-resolved when unset. |
| `timeouts.connect` | `10` | WebSocket open timeout (s). |
| `timeouts.rpc` | `15` | Default per-call deadline (s). |
| `timeouts.ping_interval` | `5` | Heartbeat period (s). |
| `timeouts.ping_timeout` | `5` | Heartbeat reply deadline (s). |
| `backoff.base/factor/max/jitter` | `0.5 / 2.0 / 30 / 0.1` | Reconnect backoff. |
| `retry.attempts/delay` | `3 / 0.1` | STALE retry for node actions. |
| `devices` | `{}` | `serial -> tags` — the declared fleet. |

## Readiness options

`FleetController` / `from_config` also accept readiness controls (constructor
args, not TOML):

- `wait_ready` (default `True`) — `start()`/`async with` waits for present devices
  to connect before returning.
- `ready_timeout` (default `30.0`) — how long to wait.

```python
async with FleetController.from_config("fleet.toml", ready_timeout=15) as fleet:
    ...
```

## Tags and groups

Tags are **static** — declared here, not read from the device. They drive group
targeting in [`run`][axonctl.FleetController.run] (`targets="group_us"`), which
resolves against this configured map. See [Fleet management](fleet.md).
