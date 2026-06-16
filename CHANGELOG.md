# Changelog

**English** · [Русский](CHANGELOG.ru.md)

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
