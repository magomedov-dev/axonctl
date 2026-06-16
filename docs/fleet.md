# Fleet management

**English** · [Русский](fleet.ru.md)

The [`FleetController`][axonctl.FleetController] is the entry point. It watches
adb for attach/detach, sets up forwards, connects devices, keeps a registry, and
runs your scenarios across groups.

## Configuration

Describe your fleet in TOML and load it with
[`from_config`][axonctl.FleetController.from_config]:

```toml
# fleet.toml
agent_port = 9008        # port the agent listens on (forward target)
concurrency = 10         # global cap on simultaneous device operations

[ports]
start = 10000            # local port range for adb forwards
end = 11000

[timeouts]
connect = 10
rpc = 15
ping_interval = 5
ping_timeout = 5

[backoff]                # reconnect backoff
base = 0.5
factor = 2.0
max = 30
jitter = 0.1

[retry]                  # STALE retry policy for node actions
attempts = 3
delay = 0.1

[devices]                # serial -> tags
"ABC123" = ["group_us", "pixel"]
"DEF456" = ["group_eu"]
```

You can also build [`FleetConfig`][axonctl.FleetConfig] programmatically and pass
it as `FleetController(config=...)`.

## Lifecycle

Use the controller as an async context manager — entering starts the watcher and
brings devices up; exiting tears the whole fleet down cleanly.

```python
async with FleetController.from_config("fleet.toml") as fleet:
    print([d.serial for d in fleet.devices()])
    device = fleet.get("ABC123")
```

Attach/detach is automatic. On attach the controller allocates a port, sets up the
forward, connects, and registers a [`Device`][axonctl.Device]. On detach it closes
the connection (stopping any reconnect), removes the forward, and frees the port.
Register callbacks with
[`on_attached`][axonctl.FleetController.on_attached] /
[`on_detached`][axonctl.FleetController.on_detached].

A dropped socket (e.g. the agent service restarted) is repaired automatically with
backoff **while the device is still present**; in-flight calls fail with
`ConnectionLost`, but the device becomes usable again once reconnected.

## Groups and running scenarios

[`run`][axonctl.FleetController.run] executes a scenario across a target set and
returns [`Results`][axonctl.Results] — a `serial -> Outcome` map.

```python
# targets can be: a group/tag name, a serial list, a tag predicate, or None (all)
results = await fleet.run(login, targets="group_us", concurrency=10)
results = await fleet.run(login, targets=["ABC123", "DEF456"])
results = await fleet.run(login, targets=lambda tags: "pixel" in tags)
results = await fleet.run(login)  # whole fleet

for serial, outcome in results.items():
    if outcome.ok:
        print(serial, "->", outcome.value)
    else:
        print(serial, "failed:", outcome.error)

print("all ok:", results.all_ok)
print("failures:", results.failed())
```

The target set is **snapshotted** at the start of the run, so it is deterministic
even as devices come and go. A device that fails or detaches mid-run becomes a
failed [`Outcome`][axonctl.Outcome] — it never aborts the run.

### Concurrency

There is **one global semaphore per controller** (`config.concurrency`), shared by
all concurrent runs — it protects the shared USB bus. The optional `concurrency`
argument to `run` adds a second, per-run cap. Effective parallelism for a run is
the smaller of the two.

## adb resolution

The adb binary is resolved as `$AXONCTL_ADB` → `.tooling/platform-tools/adb` →
`adb` on `PATH`, or set `adb_path` in config.
