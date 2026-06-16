"""Unit tests for the tag index and target resolution."""

from __future__ import annotations

from axonctl.fleet.groups import TagIndex, resolve_targets


class FakeDevice:
    """Minimal stand-in carrying a serial and tags for resolution tests."""

    def __init__(self, serial: str, tags: set[str]) -> None:
        self.serial = serial
        self.tags = frozenset(tags)


def _fixture() -> tuple[dict[str, FakeDevice], TagIndex]:
    devices = {
        "d1": FakeDevice("d1", {"us", "pixel"}),
        "d2": FakeDevice("d2", {"eu"}),
        "d3": FakeDevice("d3", {"us"}),
    }
    index = TagIndex()
    for serial, dev in devices.items():
        index.add(serial, dev.tags)
    return devices, index


def test_tag_index_lookup_and_remove() -> None:
    _devices, index = _fixture()
    assert index.serials_with("us") == {"d1", "d3"}
    index.remove("d1")
    assert index.serials_with("us") == {"d3"}


def test_resolve_none_returns_all() -> None:
    devices, index = _fixture()
    result = resolve_targets(None, devices, index)  # type: ignore[arg-type]
    assert {d.serial for d in result} == {"d1", "d2", "d3"}


def test_resolve_by_tag_name() -> None:
    devices, index = _fixture()
    result = resolve_targets("us", devices, index)  # type: ignore[arg-type]
    assert {d.serial for d in result} == {"d1", "d3"}


def test_resolve_by_serial_list() -> None:
    devices, index = _fixture()
    result = resolve_targets(["d2", "missing"], devices, index)  # type: ignore[arg-type]
    assert [d.serial for d in result] == ["d2"]


def test_resolve_by_predicate() -> None:
    devices, index = _fixture()
    result = resolve_targets(  # type: ignore[arg-type]
        lambda tags: "pixel" in tags, devices, index
    )
    assert {d.serial for d in result} == {"d1"}
