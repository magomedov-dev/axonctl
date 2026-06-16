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
