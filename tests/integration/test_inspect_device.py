"""Integration test for Device.inspect against the fake agent."""

from __future__ import annotations

from pathlib import Path

from fake_agent import fake_agent

from axonctl import connect_device


async def test_inspect_writes_self_contained_html(tmp_path: Path) -> None:
    out = tmp_path / "ui.html"
    async with fake_agent() as uri, connect_device("d", uri=uri) as device:
        path = await device.inspect(out)
    assert path == out
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    # the fake agent's screenshot is PNG; dump has the login button
    assert "data:image/png;base64," in html
    assert "com.app:id/login" in html
    assert "Sign in" in html
