"""Configuration model for axonctl.

Immutable dataclasses describing how a fleet connects to its devices: network
timeouts, the ``adb forward`` port range, reconnect backoff, the global
concurrency limit, and the static ``serial -> tags`` map. Values come from a TOML
file (:meth:`FleetConfig.from_toml`) or are constructed programmatically.

Example:
    ```toml
    # fleet.toml
    agent_port = 9008
    concurrency = 10

    [ports]
    start = 10000
    end = 11000

    [timeouts]
    rpc = 15

    [backoff]
    base = 0.5
    max = 30

    [devices]
    "276bcca9" = ["group_us", "pixel"]
    ```
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Port the on-device agent listens on (target of ``adb forward``).
DEFAULT_AGENT_PORT = 9008


@dataclass(frozen=True, slots=True)
class Timeouts:
    """Per-operation timeouts, in seconds.

    Attributes:
        connect: Opening the WebSocket.
        rpc: Default deadline for a single RPC call.
        ping_interval: Delay between application-level heartbeats.
        ping_timeout: Deadline for a heartbeat's reply before the link is
            considered dead.
    """

    connect: float = 10.0
    rpc: float = 15.0
    ping_interval: float = 5.0
    ping_timeout: float = 5.0


@dataclass(frozen=True, slots=True)
class Backoff:
    """Exponential reconnect backoff parameters.

    The delay for attempt ``n`` is ``min(base * factor**n, max)`` perturbed by
    ``±jitter`` (a fraction of the delay).

    Attributes:
        base: Initial delay in seconds.
        factor: Multiplier applied each attempt.
        max: Cap on the delay in seconds.
        jitter: Random fraction (``0..1``) of the delay added/subtracted.
    """

    base: float = 0.5
    factor: float = 2.0
    max: float = 30.0
    jitter: float = 0.1

    def __post_init__(self) -> None:
        if self.base < 0 or self.max < 0:
            raise ValueError("backoff base/max must be non-negative")
        if self.factor < 1:
            raise ValueError("backoff factor must be >= 1")
        if not 0 <= self.jitter <= 1:
            raise ValueError("backoff jitter must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class Retry:
    """Retry policy for node actions that fail with ``STALE``.

    Attributes:
        attempts: Total attempts including the first (>= 1).
        delay: Delay in seconds between attempts.
    """

    attempts: int = 3
    delay: float = 0.1

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("retry attempts must be >= 1")
        if self.delay < 0:
            raise ValueError("retry delay must be non-negative")


@dataclass(frozen=True, slots=True)
class FleetConfig:
    """Top-level configuration for a :class:`~axonctl.FleetController`.

    Attributes:
        agent_port: Port the agent listens on (forwarded over adb).
        port_range: Inclusive ``(start, end)`` local port range for forwards.
        concurrency: Global cap on simultaneous scenario tasks across the fleet.
        timeouts: Network and RPC timeouts.
        backoff: Reconnect backoff parameters.
        retry: Retry policy for ``STALE`` node actions.
        devices: Static ``serial -> tags`` map describing the fleet.
    """

    agent_port: int = DEFAULT_AGENT_PORT
    port_range: tuple[int, int] = (10000, 11000)
    concurrency: int = 8
    timeouts: Timeouts = field(default_factory=Timeouts)
    backoff: Backoff = field(default_factory=Backoff)
    retry: Retry = field(default_factory=Retry)
    devices: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        start, end = self.port_range
        if start > end:
            raise ValueError(f"port_range start {start} > end {end}")
        if self.concurrency < 1:
            raise ValueError("concurrency must be >= 1")

    def tags_for(self, serial: str) -> frozenset[str]:
        """Return the configured tags for ``serial`` (empty if unknown).

        Args:
            serial: Device serial.

        Returns:
            The configured tag set, or an empty set if the serial is not listed.
        """
        return self.devices.get(serial, frozenset())

    @classmethod
    def from_toml(cls, path: str | Path) -> FleetConfig:
        """Load a :class:`FleetConfig` from a TOML file.

        Args:
            path: Path to the TOML config file.

        Returns:
            The parsed configuration (missing keys fall back to defaults).

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            tomllib.TOMLDecodeError: If the file is not valid TOML.
            ValueError: If values are out of range (see ``__post_init__``).
        """
        raw: dict[str, Any] = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_mapping(raw)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> FleetConfig:
        """Build a :class:`FleetConfig` from an already-parsed mapping.

        Args:
            raw: Mapping shaped like the TOML document.

        Returns:
            The parsed configuration.
        """
        ports = raw.get("ports", {})
        timeouts = raw.get("timeouts", {})
        backoff = raw.get("backoff", {})
        retry = raw.get("retry", {})
        devices_raw: Mapping[str, Iterable[str]] = raw.get("devices", {})
        return cls(
            agent_port=int(raw.get("agent_port", DEFAULT_AGENT_PORT)),
            port_range=(
                int(ports.get("start", 10000)),
                int(ports.get("end", 11000)),
            ),
            concurrency=int(raw.get("concurrency", 8)),
            timeouts=Timeouts(
                connect=float(timeouts.get("connect", 10.0)),
                rpc=float(timeouts.get("rpc", 15.0)),
                ping_interval=float(timeouts.get("ping_interval", 5.0)),
                ping_timeout=float(timeouts.get("ping_timeout", 5.0)),
            ),
            backoff=Backoff(
                base=float(backoff.get("base", 0.5)),
                factor=float(backoff.get("factor", 2.0)),
                max=float(backoff.get("max", 30.0)),
                jitter=float(backoff.get("jitter", 0.1)),
            ),
            retry=Retry(
                attempts=int(retry.get("attempts", 3)),
                delay=float(retry.get("delay", 0.1)),
            ),
            devices={serial: frozenset(tags) for serial, tags in devices_raw.items()},
        )
