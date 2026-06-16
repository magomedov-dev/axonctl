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
- **Этап 1 — транспорт + RPC + минимальный `Device`** (первый вертикальный
  срез):
  - WebSocket-транспорт (`WsClient`) за швом `WebSocketTransport`, роутер
    фреймов, реестр ожидающих запросов с корреляцией бинаря (вариант А),
    генератор id, политика backoff реконнекта и per-device соединение с
    read/ping-циклами и корректной отменой.
  - `RpcClient` с таймаутом на каждый вызов; полная типизированная иерархия
    исключений (`AxonError`, `RpcError` + подклассы протокола, `RpcTimeout`,
    `ConnectionLost`) и маппинг кодов протокола.
  - Модель конфигурации (`FleetConfig`, `Timeouts`, `Backoff`) с загрузкой из
    TOML.
  - Минимальное дерево UI (`UiTree`, `UiNode`, `Bounds`, `Point`).
  - Фасад `Device` с `ping()` и `dump()`, плюс временный помощник
    `connect_device`; первый публичный `__all__`.
  - Unit- и интеграционные тесты (против in-process фейкового агента);
    проверено end-to-end на реальном устройстве.
