# История изменений

[English](CHANGELOG.md) · **Русский**

Все значимые изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [семантического версионирования](https://semver.org/lang/ru/).

## [Unreleased]

## [0.1.0] - 2026-06-16

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
- **Этап 2 — дерево UI, селекторы и окна** (чистый слой, без I/O):
  - `Selector` с режимами `exact`/`contains`/`regex`, позиционным `index`,
    областью `.within(...)` и фабриками (`id`, `text`, `text_contains`,
    `desc`, `cls`); весь матчинг — на ПК поверх дампа.
  - Навигация `UiNode`: `descendants`/`walk`/`find`/`find_all` плюс лениво
    связываемые `parent`/`ancestors` (дамп, который только сериализуют, не
    платит за связывание).
  - Разбор `getWindows` в `Window`/`WindowList` (топовое первым) с выборками
    `active`/`focused`/`by_type`/`ime`/`dialogs`.
  - `Device.windows()`, `Device.find()` и `Device.find_all()`.
- **Этап 3 — события и событийные ожидания** (ядро архитектуры):
  - Per-device `EventBus` (fan-out подписки, sentinel закрытия, будящий
    заблокированных ждунов) и трекер `ScreenState`, встроены в роутер фреймов
    вместо заглушки из этапа 1.
  - Ленивое включение `setEventStream` на соединении.
  - `WaitEngine`: подписка → включить стрим → базовый дамп → передамп только по
    `screenChanged` с большим screen — никакого поллинга — всё под одним
    дедлайном.
  - `Device.wait_for()`, `wait_gone()`, `wait_activity()`, `wait_toast()` и
    помощник `sleep()`; новое исключение `WaitTimeout`.
  - Тесты против управляемого фейкового агента (включая доказательство
    «без поллинга» через подсчёт дампов); проверено end-to-end на потоке
    событий реального устройства.
- **Этап 4 — полный фасад Device: жесты, действия, скриншот, ретраи**:
  - `GestureBuilder` (чистая сборка strokes) и `Device.tap`/`long_tap`/
    `double_tap`/`swipe`/`drag`/`pinch`.
  - Действия через `nodeAction`: `click`, `long_click`, `set_text`, `clear`,
    `scroll`, `focus`, `clear_focus`, `select`, `set_selection` (с `window_id`);
    `global_action`.
  - `Device.screenshot()` возвращает байты изображения (корреляция мета+бинарь
    по варианту А; rate-limit ~1/сек отдаётся как `InternalError`).
  - `RetryPolicy` + декоратор `retry_on_stale` и конфиг `Retry`; действия над
    узлами автоматически повторяются при `STALE`.
  - Тесты: сборка жестов, политика ретраев, скриншот, действия, ретрай STALE;
    проверено на реальном устройстве.
- **Этап 5 — управление парком и реконнект**:
  - `FleetController` (async-контекст, `from_config`): следит за adb на
    attach/detach, выделяет порт, поднимает forward, подключается и
    регистрирует `Device`; на detach закрывает (останавливая реконнект),
    снимает forward и освобождает порт.
    `devices()`/`get()`/`group()`/`on_attached`/`on_detached`.
  - `AdbWatcher` (поверх `adbutils.track_devices()`), `AdbBridge`
    (forward/shell/launch/force_stop/install в потоках), `PortAllocator`,
    `TagIndex` + `DeviceGroup` + резолв targets (имя / список серийников /
    предикат / все).
  - Авто-реконнект в `DeviceConnection`: супервизор переоткрывает сокет с
    backoff после обрыва (не трогая adb), роняя текущие вызовы/ожидания, но
    сохраняя шину рабочей; явный close корректно его останавливает.
  - `Device.launch()`/`kill()`/`install()` (через привязанный adb); путь к adb
    резолвится как `$AXONCTL_ADB` → `.tooling/platform-tools/adb` → `PATH`.
  - Ожидания теперь терпят транзиентный `ACCESSIBILITY_DISABLED` в дампе
    (например, в момент запуска приложения), а не падают.
  - Тесты: порты, tag-индекс/резолв, attach/detach/группы парка, реконнект;
    проверено end-to-end на реальном устройстве.
- **Этап 6 — исполнитель сценариев**:
  - `FleetController.run(scenario, targets=None, concurrency=None)` (и базовый
    `FleetExecutor`): снимает снапшот целевого множества, запускает сценарий
    одной таской на устройство и собирает per-device исходы.
  - Один глобальный семафор конкурентности на контроллер (из
    `config.concurrency`), общий для всех одновременных прогонов (защита
    USB-шины); опциональный per-run `concurrency` добавляет второй лимит.
  - Алиас `Scenario`, `Outcome` (value/error + `ok`/`unwrap`) и `Results`
    (маппинг `serial -> Outcome` с `all_ok`/`succeeded`/`failed`). Упавшее или
    отвалившееся устройство становится failed-исходом, а не роняет прогон.
  - Тесты: сбор результатов, изоляция падений, выбор targets, per-run и общий
    глобальный лимиты конкурентности, detach по ходу; проверено на реальном
    устройстве.
- **Этап 7 — документация, примеры, релиз**:
  - Двуязычный сайт на MkDocs (`mkdocs.yml`, `mkdocs-static-i18n`): Overview,
    Quickstart, Концепции (принцип stateless, событийные ожидания, модель
    исполнения + таблица блокирующее→async), Управление парком, Написание
    сценариев, автогенерируемый API Reference (mkdocstrings) и Протокол.
  - `examples/` — автономные скрипты, импортирующие установленную библиотеку
    (`single_device`, `inspect_ui`, `run_group`, `fleet.toml`).
