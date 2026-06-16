# История изменений

[English](CHANGELOG.md) · **Русский**

Все значимые изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [семантического версионирования](https://semver.org/lang/ru/).

## [Unreleased]

### Добавлено
- Каркас репозитория и базис инструментария:
  - Пакет `axonctl` в `src`-layout с маркером `py.typed` (PEP 561) и явным,
    изначально пустым публичным `__all__`.
  - Внутренние пакеты-слои с docstring-описанием: `conn`, `rpc`, `events`,
    `tree`, `fleet`.
  - Структура тестов (`tests/unit`, `tests/integration`) с `pytest-asyncio` в
    auto-режиме и smoke-тестом.
  - Инструменты качества в `pyproject.toml`: `ruff`, `black`,
    `mypy --strict`, `pytest`.
  - Локальный для проекта тулчейн в `.tooling/`, разворачиваемый скриптами
    `scripts/` (`uv`, uv-managed CPython, dev-venv и Android `adb`) — ничего не
    ставится системно.
  - Вендорная копия справочника протокола `docs/PROTOCOL.md` (синхронизирована
    из репозитория агента Axon), `CONTRIBUTING.md` и эта история изменений.
  - Двуязычная документация: EN — канон (`FILE.md`), RU — зеркало
    (`FILE.ru.md`).
- Поэтапный план реализации (`IMPLEMENTATION_PLAN.md`).
