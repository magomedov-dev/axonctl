"""Scenario executor.

Runs a user scenario across a group of devices as concurrent asyncio tasks in the
one event loop — while one device waits on the socket, the loop serves the rest.
A single global semaphore (owned by the controller, shared by *all* concurrent
runs) caps how many device operations hit the shared USB bus at once; an optional
per-run ``concurrency`` adds a second cap for that run only.

A scenario is just an ``async`` function taking a :class:`~axonctl.Device`. Each
device's outcome — its return value or the exception it raised — is collected
into :class:`Results`, so one failing device never sinks the run.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar, cast

if TYPE_CHECKING:
    from ..device import Device
    from .groups import Targets

T = TypeVar("T")

#: A user scenario: an async function from a device to some result.
Scenario = Callable[["Device"], Awaitable[T]]


@dataclass(frozen=True, slots=True)
class Outcome(Generic[T]):
    """The result of running a scenario on one device.

    Exactly one of ``value``/``error`` is meaningful, per :attr:`ok`.

    Attributes:
        serial: The device serial.
        value: The scenario's return value on success (may itself be ``None``).
        error: The exception raised on failure, else ``None``.
    """

    serial: str
    value: T | None = None
    error: BaseException | None = None

    @property
    def ok(self) -> bool:
        """Whether the scenario completed without raising."""
        return self.error is None

    def unwrap(self) -> T:
        """Return the value, or re-raise the captured error.

        Returns:
            The scenario's return value.

        Raises:
            BaseException: The captured error, if the scenario failed.
        """
        if self.error is not None:
            raise self.error
        return cast(T, self.value)


class Results(Mapping[str, "Outcome[T]"], Generic[T]):
    """A per-device map of ``serial -> Outcome`` with convenience views."""

    def __init__(self, outcomes: Mapping[str, Outcome[T]]) -> None:
        """Initialize from a serial-keyed outcome mapping."""
        self._items: dict[str, Outcome[T]] = dict(outcomes)

    def __getitem__(self, serial: str) -> Outcome[T]:
        return self._items[serial]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"Results({self._items!r})"

    @property
    def all_ok(self) -> bool:
        """Whether every device succeeded."""
        return all(outcome.ok for outcome in self._items.values())

    def succeeded(self) -> dict[str, T]:
        """Return ``serial -> value`` for the devices that succeeded."""
        return {
            serial: cast(T, outcome.value)
            for serial, outcome in self._items.items()
            if outcome.ok
        }

    def failed(self) -> dict[str, BaseException]:
        """Return ``serial -> error`` for the devices that failed."""
        return {
            serial: cast(BaseException, outcome.error)
            for serial, outcome in self._items.items()
            if not outcome.ok
        }


class FleetExecutor:
    """Runs scenarios across devices under a shared global concurrency cap."""

    def __init__(
        self,
        *,
        resolve: Callable[[Targets], list[Device]],
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Initialize the executor.

        Args:
            resolve: Resolves a ``targets`` selection to a device list (a
                snapshot is taken at the start of each run).
            semaphore: The controller's global concurrency semaphore, shared by
                all runs (USB-bus protection).
        """
        self._resolve = resolve
        self._semaphore = semaphore

    async def run(
        self,
        scenario: Scenario[T],
        targets: Targets = None,
        *,
        concurrency: int | None = None,
    ) -> Results[T]:
        """Run ``scenario`` on every targeted device, collecting outcomes.

        The target set is snapshotted at the start (so the run is deterministic
        even as devices come and go); a device that drops mid-run surfaces as a
        failed outcome rather than aborting the run.

        Args:
            scenario: An ``async`` function taking a :class:`~axonctl.Device`.
            targets: A group/tag name, serial list, tag predicate, or ``None``
                for the whole fleet.
            concurrency: Optional per-run cap; the global semaphore always
                applies on top of it. Effective parallelism is the smaller of
                the two.

        Returns:
            A :class:`Results` mapping each serial to its :class:`Outcome`.
        """
        devices = self._resolve(targets)
        run_sem = asyncio.Semaphore(concurrency) if concurrency is not None else None
        outcomes = await asyncio.gather(
            *(self._run_one(scenario, device, run_sem) for device in devices)
        )
        return Results({outcome.serial: outcome for outcome in outcomes})

    async def _run_one(
        self,
        scenario: Scenario[T],
        device: Device,
        run_sem: asyncio.Semaphore | None,
    ) -> Outcome[T]:
        if run_sem is None:
            async with self._semaphore:
                return await self._invoke(scenario, device)
        async with run_sem, self._semaphore:
            return await self._invoke(scenario, device)

    async def _invoke(self, scenario: Scenario[T], device: Device) -> Outcome[T]:
        try:
            value = await scenario(device)
            return Outcome(serial=device.serial, value=value)
        except Exception as exc:  # noqa: BLE001 - isolate per-device scenario failures
            return Outcome(serial=device.serial, error=exc)
