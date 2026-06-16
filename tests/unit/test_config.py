"""Unit tests for configuration parsing and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from axonctl.config import Backoff, FleetConfig, Timeouts


def test_defaults() -> None:
    cfg = FleetConfig()
    assert cfg.agent_port == 9008
    assert cfg.concurrency == 8
    assert cfg.timeouts == Timeouts()
    assert cfg.backoff == Backoff()
    assert cfg.tags_for("unknown") == frozenset()


def test_from_mapping_parses_devices_and_ports() -> None:
    cfg = FleetConfig.from_mapping(
        {
            "agent_port": 9008,
            "concurrency": 10,
            "ports": {"start": 10000, "end": 10500},
            "timeouts": {"rpc": 20},
            "backoff": {"base": 1.0, "max": 60},
            "devices": {"276bcca9": ["group_us", "pixel"]},
        }
    )
    assert cfg.concurrency == 10
    assert cfg.port_range == (10000, 10500)
    assert cfg.timeouts.rpc == 20.0
    assert cfg.backoff.max == 60.0
    assert cfg.tags_for("276bcca9") == frozenset({"group_us", "pixel"})


def test_from_toml(tmp_path: Path) -> None:
    toml = tmp_path / "fleet.toml"
    toml.write_text(
        'concurrency = 4\n[devices]\n"abc" = ["a"]\n',
        encoding="utf-8",
    )
    cfg = FleetConfig.from_toml(toml)
    assert cfg.concurrency == 4
    assert cfg.tags_for("abc") == frozenset({"a"})


def test_invalid_port_range() -> None:
    with pytest.raises(ValueError, match="port_range"):
        FleetConfig(port_range=(20000, 10000))


def test_invalid_backoff() -> None:
    with pytest.raises(ValueError, match="factor"):
        Backoff(factor=0.5)
