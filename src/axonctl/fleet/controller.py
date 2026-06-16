"""The fleet controller.

The public entry point for managing a park of devices. It watches adb for
attach/detach, and on attach it allocates a local port, sets up the forward,
opens a :class:`~axonctl.conn.connection.DeviceConnection`, and registers a
:class:`~axonctl.Device`; on detach it closes the connection (stopping any
reconnect), removes the forward, and frees the port. Tags come from config, so
group membership updates as devices come and go.

Use it as an async context manager:

    ```python
    async with FleetController.from_config("fleet.toml") as fleet:
        for device in fleet.devices():
            await device.ping()
    ```
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from ..config import FleetConfig
from ..conn.connection import DeviceConnection
from ..conn.ws import WebSocketTransport, WsClient
from ..device import Device
from .adb import Adb, AdbBridge
from .executor import FleetExecutor, Results, Scenario
from .groups import DeviceGroup, TagIndex, Targets, resolve_targets
from .ports import PortAllocator
from .watcher import AdbWatcher, Watcher

#: Builds a transport for a device given its serial and allocated local port.
TransportFactory = Callable[[str, int], WebSocketTransport]

_T = TypeVar("_T")


class FleetController:
    """Owns the device registry and the attach/detach lifecycle."""

    def __init__(
        self,
        config: FleetConfig | None = None,
        *,
        adb: Adb | None = None,
        watcher: Watcher | None = None,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        """Create a controller (does not start watching yet).

        Args:
            config: Fleet configuration; defaults are used when omitted.
            adb: adb bridge; a real :class:`AdbBridge` is built if omitted.
            watcher: Device watcher; a real :class:`AdbWatcher` is built if
                omitted.
            transport_factory: Builds a transport from ``(serial, port)``;
                defaults to a local ``WsClient``. Injectable for tests.
        """
        self._config = config or FleetConfig()
        self._adb: Adb = adb or AdbBridge(self._config.adb_path)
        self._watcher: Watcher = watcher or AdbWatcher(self._config.adb_path)
        self._transport_factory = transport_factory or self._default_transport
        self._registry: dict[str, Device] = {}
        self._ports = PortAllocator(self._config.port_range)
        self._tags = TagIndex()
        # One global semaphore per controller, shared by all runs (USB-bus cap).
        self._semaphore = asyncio.Semaphore(self._config.concurrency)
        self._executor = FleetExecutor(
            resolve=self._resolve_targets, semaphore=self._semaphore
        )
        self._watch_task: asyncio.Task[None] | None = None
        self._on_attached: list[Callable[[Device], None]] = []
        self._on_detached: list[Callable[[str], None]] = []
        self._log = logging.getLogger("axonctl.fleet")

    @classmethod
    def from_config(cls, path: str | Path) -> FleetController:
        """Build a controller from a TOML config file.

        Args:
            path: Path to the fleet TOML config.

        Returns:
            A configured (not yet started) controller.
        """
        return cls(FleetConfig.from_toml(path))

    @property
    def config(self) -> FleetConfig:
        """The fleet configuration in effect."""
        return self._config

    def _default_transport(self, serial: str, port: int) -> WebSocketTransport:
        return WsClient(
            f"ws://127.0.0.1:{port}", open_timeout=self._config.timeouts.connect
        )

    async def start(self) -> None:
        """Start watching adb for attach/detach (idempotent)."""
        if self._watch_task is not None:
            return
        self._watch_task = asyncio.create_task(self._watch(), name="axon-fleet-watch")

    async def stop(self) -> None:
        """Stop watching and tear down every device, forward, and port."""
        if self._watch_task is not None:
            self._watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watch_task
            self._watch_task = None
        for serial in list(self._registry):
            await self._handle_detach(serial)

    async def __aenter__(self) -> FleetController:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    def devices(self) -> list[Device]:
        """Return all currently-attached devices."""
        return list(self._registry.values())

    def get(self, serial: str) -> Device | None:
        """Return the device for ``serial``, or ``None`` if not attached."""
        return self._registry.get(serial)

    def group(self, name: str) -> DeviceGroup:
        """Return a live group view for the tag ``name``.

        Args:
            name: The tag name.

        Returns:
            A :class:`DeviceGroup` resolving to the current members.
        """
        return DeviceGroup(
            name, lambda: resolve_targets(name, self._registry, self._tags)
        )

    def _resolve_targets(self, targets: Targets) -> list[Device]:
        return resolve_targets(targets, self._registry, self._tags)

    async def run(
        self,
        scenario: Scenario[_T],
        targets: Targets = None,
        *,
        concurrency: int | None = None,
    ) -> Results[_T]:
        """Run ``scenario`` across the targeted devices and collect outcomes.

        The target set is snapshotted at the start. A device that fails or drops
        mid-run becomes a failed outcome rather than aborting the run. The global
        concurrency cap (``config.concurrency``) is shared with every other
        concurrent run; ``concurrency`` optionally caps this run further.

        Args:
            scenario: An ``async`` function taking a :class:`~axonctl.Device`.
            targets: Group/tag name, serial list, tag predicate, or ``None`` for
                the whole fleet.
            concurrency: Optional additional per-run concurrency cap.

        Returns:
            A :class:`~axonctl.Results` mapping each serial to its outcome.
        """
        return await self._executor.run(scenario, targets, concurrency=concurrency)

    def on_attached(self, callback: Callable[[Device], None]) -> None:
        """Register a callback invoked with each newly attached device."""
        self._on_attached.append(callback)

    def on_detached(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked with the serial of each detached device."""
        self._on_detached.append(callback)

    async def _watch(self) -> None:
        async for event in self._watcher.events():
            try:
                if event.present:
                    await self._handle_attach(event.serial)
                else:
                    await self._handle_detach(event.serial)
            except Exception:  # noqa: BLE001 - one device must not kill the watcher
                self._log.exception(
                    "[%s] error handling %s", event.serial, event.present
                )

    async def _handle_attach(self, serial: str) -> None:
        if serial in self._registry:
            return
        tags = self._config.tags_for(serial)
        port = self._ports.acquire(serial)
        try:
            await self._adb.forward(serial, port, self._config.agent_port)
            transport = self._transport_factory(serial, port)
            connection = DeviceConnection(transport, serial=serial, config=self._config)
            await connection.connect()
        except Exception:  # noqa: BLE001 - attach failure must not crash the fleet
            self._ports.release(serial)
            self._log.exception("[%s] attach failed", serial)
            return
        device = Device(serial=serial, tags=tags, connection=connection, adb=self._adb)
        self._registry[serial] = device
        self._tags.add(serial, tags)
        self._log.info("[%s] attached (port %d, tags %s)", serial, port, sorted(tags))
        self._fire(self._on_attached, device)

    async def _handle_detach(self, serial: str) -> None:
        device = self._registry.pop(serial, None)
        if device is None:
            return
        self._tags.remove(serial)
        with contextlib.suppress(Exception):
            await device.aclose()  # stops any reconnect before we drop the forward
        port = self._ports.port_for(serial)
        if port is not None:
            with contextlib.suppress(Exception):
                await self._adb.remove_forward(serial, port)
        self._ports.release(serial)
        self._log.info("[%s] detached", serial)
        self._fire(self._on_detached, serial)

    def _fire(self, callbacks: list[Callable[[_T], None]], arg: _T) -> None:
        for callback in callbacks:
            try:
                callback(arg)
            except Exception:  # noqa: BLE001 - a bad callback must not break lifecycle
                self._log.exception("callback error")
