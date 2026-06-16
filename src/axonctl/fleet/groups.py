"""Device grouping and target resolution.

Tags are static, declared in config (``serial -> tags``); they are not read from
the device. :class:`TagIndex` keeps a reverse ``tag -> serials`` index for fast
group lookups, updated on attach/detach. :func:`resolve_targets` turns the
flexible ``targets`` argument (a group name, a tag predicate, an explicit serial
list, or ``None`` for the whole fleet) into a concrete device list.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..device import Device

#: A target selection: a group/tag name, an explicit serial list, a predicate
#: over a device's tags, or ``None`` for the entire registry.
Targets = str | Sequence[str] | Callable[[frozenset[str]], bool] | None


class TagIndex:
    """Reverse index from tag to the set of serials carrying it."""

    def __init__(self) -> None:
        self._by_tag: dict[str, set[str]] = {}

    def add(self, serial: str, tags: Iterable[str]) -> None:
        """Index ``serial`` under each of ``tags``.

        Args:
            serial: Device serial.
            tags: Tags to associate with the serial.
        """
        for tag in tags:
            self._by_tag.setdefault(tag, set()).add(serial)

    def remove(self, serial: str) -> None:
        """Remove ``serial`` from every tag (on detach).

        Args:
            serial: Device serial.
        """
        for serials in self._by_tag.values():
            serials.discard(serial)

    def serials_with(self, tag: str) -> set[str]:
        """Return the serials carrying ``tag`` (a copy).

        Args:
            tag: The tag to look up.

        Returns:
            A new set of serials.
        """
        return set(self._by_tag.get(tag, ()))


@dataclass(frozen=True)
class DeviceGroup:
    """A named, live view over the devices carrying a tag.

    Attributes:
        name: The group's tag name.
    """

    name: str
    _resolve: Callable[[], list[Device]]

    def devices(self) -> list[Device]:
        """Return the devices currently in this group."""
        return self._resolve()


def resolve_targets(
    targets: Targets,
    registry: Mapping[str, Device],
    tag_index: TagIndex,
) -> list[Device]:
    """Resolve a ``targets`` selection to a concrete device list.

    Args:
        targets: A group/tag name, a serial list, a tag predicate, or ``None``.
        registry: The current ``serial -> Device`` registry.
        tag_index: The tag index for name lookups.

    Returns:
        Matching devices currently in the registry. Unknown serials/tags yield no
        device rather than an error.
    """
    if targets is None:
        return list(registry.values())
    if isinstance(targets, str):
        return [registry[s] for s in tag_index.serials_with(targets) if s in registry]
    if callable(targets):
        return [device for device in registry.values() if targets(device.tags)]
    return [registry[s] for s in targets if s in registry]
