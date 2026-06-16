# Changelog

**English** · [Русский](CHANGELOG.ru.md)

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-06-16

### Fixed
- CI lint: combine a nested `async with` in a test that a newer `ruff` flags
  (SIM117), so `main`/`develop` CI is green again. No library changes.

## [0.2.0] - 2026-06-16

### Added
- GitHub Actions: a `ci` workflow (ruff / black / mypy / pytest on push & PR) and
  a `docs` workflow that publishes the MkDocs site to `gh-pages` on each push to
  `main`.
- Comprehensive bilingual user guide: a full multi-section manual — Installation,
  Troubleshooting, Selectors, The UI tree, Waiting, Actions & gestures,
  Screenshots, Windows & dialogs, Configuration reference, Error handling,
  Cookbook, and Architecture — alongside the existing Concepts/Fleet/Scenarios
  pages. The docs site now uses Material's built-in language selector instead of
  per-page switcher links (which are kept only in the top-level repo files).
- `FleetController` waits for present devices to connect on `start()`/`async with`
  by default (`wait_ready` / `ready_timeout`, and a public `wait_ready()`), closing
  the race where an immediate `run()` saw an empty registry.
- `Device.wait_package()` (honest name: matches the foreground package). The agent
  exposes no activity name; `wait_activity()` is kept as an alias.
- Typed exceptions `UnsupportedSelector` and `DeviceNotConnected`.
- `connect_device(...)` is now usable as `async with connect_device(...)` directly
  (still awaitable too).
- ASCII-only guard test for protocol keys/identifiers.

### Changed
- The event stream is enabled automatically on connect (and re-enabled on
  reconnect); `wait_toast()` now also returns a toast that fired just before the
  call (buffered), closing the toast race.
- `run()` target resolution for a group/tag name, predicate, or serial list now
  resolves against the **configured** fleet: a configured-but-disconnected member
  surfaces as a failed `Outcome` (`DeviceNotConnected`) instead of being silently
  skipped. `targets=None` still means all connected devices. An empty target set
  logs a warning.
- Passing a `.within(...)` selector to a node action now raises
  `UnsupportedSelector` (was a generic `ValueError`) — never a silent
  wrong-target action.

## [0.1.0] - 2026-06-16

### Added
- Repository scaffolding and tooling baseline:
  - `src`-layout package `axonctl` with a `py.typed` marker (PEP 561) and an
    explicit, initially empty public `__all__`.
  - Internal layer packages with layer docstrings: `conn`, `rpc`, `events`,
    `tree`, `fleet`.
  - Test layout (`tests/unit`, `tests/integration`) with `pytest-asyncio` in
    auto mode and a smoke test.
  - Quality tooling configured in `pyproject.toml`: `ruff`, `black`,
    `mypy --strict`, `pytest`.
  - Project-local toolchain under `.tooling/` provisioned by `scripts/`
    (`uv`, a uv-managed CPython, the dev venv, and Android `adb`) so nothing is
    installed system-wide.
  - Vendored protocol reference `docs/PROTOCOL.md` (synced from the Axon agent
    repository), `CONTRIBUTING.md`, and this changelog.
  - Bilingual documentation: English is canonical (`FILE.md`), Russian is the
    mirror (`FILE.ru.md`).
- Staged implementation plan (`IMPLEMENTATION_PLAN.md`).
- **Stage 1 — transport + RPC + minimal `Device`** (first vertical slice):
  - WebSocket transport (`WsClient`) behind a `WebSocketTransport` seam, frame
    router, pending-request registry with variant-A binary correlation, request-
    id generator, reconnect backoff policy, and the per-device connection with
    read/ping loops and clean cancellation.
  - `RpcClient` with a per-call timeout; the full typed exception hierarchy
    (`AxonError`, `RpcError` + protocol subclasses, `RpcTimeout`,
    `ConnectionLost`) and the wire-code mapping.
  - Configuration model (`FleetConfig`, `Timeouts`, `Backoff`) loadable from TOML.
  - Minimal parsed UI tree (`UiTree`, `UiNode`, `Bounds`, `Point`).
  - `Device` facade with `ping()` and `dump()`, plus the provisional
    `connect_device` helper; first public `__all__`.
  - Unit + integration tests (against an in-process fake agent); verified
    end-to-end against a real device.
- **Stage 2 — UI tree, selectors, and windows** (pure layer, no I/O):
  - `Selector` with `exact`/`contains`/`regex` matching, positional `index`,
    `.within(...)` scoping, and factories (`id`, `text`, `text_contains`,
    `desc`, `cls`); all matching runs on the PC over a dump.
  - `UiNode` navigation: `descendants`/`walk`/`find`/`find_all` plus lazily
    linked `parent`/`ancestors` (a dump you only serialize never pays for
    linking).
  - `Window`/`WindowList` parsing of `getWindows` (topmost first) with
    `active`/`focused`/`by_type`/`ime`/`dialogs` selections.
  - `Device.windows()`, `Device.find()`, and `Device.find_all()`.
- **Stage 3 — events and event-driven waits** (the core of the architecture):
  - Per-device `EventBus` (fan-out subscriptions, close sentinel that wakes
    blocked waiters) and `ScreenState` tracker, wired into the frame router in
    place of the Stage 1 stub.
  - Lazy `setEventStream` enablement on the connection.
  - `WaitEngine`: subscribe → enable stream → baseline dump → re-dump only on a
    `screenChanged` with a newer screen — never polling — all under one deadline.
  - `Device.wait_for()`, `wait_gone()`, `wait_activity()`, `wait_toast()`, and
    the `sleep()` helper; new `WaitTimeout` exception.
  - Tests against a scripted fake agent (including a no-polling proof via dump
    counting); verified end-to-end against a real device's event stream.
- **Stage 4 — full Device facade: gestures, actions, screenshot, retry**:
  - `GestureBuilder` (pure stroke assembly) and `Device.tap`/`long_tap`/
    `double_tap`/`swipe`/`drag`/`pinch`.
  - Node actions via `nodeAction`: `click`, `long_click`, `set_text`, `clear`,
    `scroll`, `focus`, `clear_focus`, `select`, `set_selection` (with
    `window_id`); `global_action`.
  - `Device.screenshot()` returning image bytes (variant-A metadata+binary
    correlation; ~1/sec rate limit surfaced as `InternalError`).
  - `RetryPolicy` + `retry_on_stale` decorator and a `Retry` config; node
    actions automatically retry on `STALE`.
  - Tests: gesture assembly, retry policy, screenshot, actions, STALE retry;
    verified against a real device.
- **Stage 5 — fleet management and reconnect**:
  - `FleetController` (async context manager, `from_config`): watches adb for
    attach/detach, allocates a port, sets up the forward, connects, and registers
    a `Device`; on detach it closes (stopping reconnect), removes the forward,
    and frees the port. `devices()`/`get()`/`group()`/`on_attached`/`on_detached`.
  - `AdbWatcher` (over `adbutils.track_devices()`), `AdbBridge` (forward/shell/
    launch/force_stop/install, off-loaded to threads), `PortAllocator`,
    `TagIndex` + `DeviceGroup` + target resolution (name / serial list /
    predicate / all).
  - Auto-reconnect in `DeviceConnection`: a supervisor reopens the socket with
    backoff after a drop (without touching adb), failing in-flight calls/waiters
    while keeping the bus usable; an explicit close stops it cleanly.
  - `Device.launch()`/`kill()`/`install()` (over the bound adb bridge); adb path
    resolved as `$AXONCTL_ADB` → `.tooling/platform-tools/adb` → `PATH`.
  - Waits now tolerate a transient `ACCESSIBILITY_DISABLED` dump (e.g. mid app
    launch) instead of failing.
  - Tests: ports, tag index/resolution, fleet attach/detach/group, reconnect;
    verified end-to-end against a real device.
- **Stage 6 — scenario executor**:
  - `FleetController.run(scenario, targets=None, concurrency=None)` (and the
    underlying `FleetExecutor`): snapshots the target set, runs the scenario as
    one task per device, and collects per-device outcomes.
  - One global concurrency semaphore per controller (from `config.concurrency`),
    shared across all concurrent runs (USB-bus protection); an optional per-run
    `concurrency` adds a second cap.
  - `Scenario` type alias, `Outcome` (value/error + `ok`/`unwrap`), and `Results`
    (a `serial -> Outcome` mapping with `all_ok`/`succeeded`/`failed`). A failing
    or detached device becomes a failed outcome rather than aborting the run.
  - Tests: result collection, failure isolation, target selection, per-run and
    shared-global concurrency caps, detach-mid-run; verified on a real device.
- **Stage 7 — documentation, examples, release**:
  - Bilingual MkDocs site (`mkdocs.yml`, `mkdocs-static-i18n`): Overview,
    Quickstart, Concepts (stateless principle, event-driven waits, the
    execution model + blocking→async table), Fleet management, Writing
    scenarios, auto-generated API Reference (mkdocstrings), and the Protocol.
  - `examples/` — standalone scripts importing the installed library
    (`single_device`, `inspect_ui`, `run_group`, `fleet.toml`).
