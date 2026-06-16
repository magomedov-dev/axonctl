# IMPLEMENTATION_PLAN — axonctl

PC-сторона системы Axon: асинхронный контроллер парка Android-устройств.
План построен **снизу вверх по слоям**. Каждый этап — это **работающий,
протестированный вертикальный срез**: после него `ruff check`, `black --check`,
`mypy` и `pytest` зелёные, а на `develop` остаётся стабильный код.

> Источник истины по протоколу: [`docs/PROTOCOL.md`](docs/PROTOCOL.md)
> (копия `axon/docs/PROTOCOL.md`, синхронизируется вручную при изменениях агента).

---

## Принципы, общие для всех этапов

- **Один event loop, никаких блокировок горячего пути.** Любой потенциально
  блокирующий вызов (синхронный `adbutils`, парсинг гигантских деревьев) — через
  `run_in_executor`. Событийные ожидания, не поллинг.
- **Полная независимость устройств.** `id`, pending-реестр, события, состояние —
  per-device. Единственный общий примитив — глобальный семафор конкурентности
  executor'а.
- **Таймаут на каждом `await` внешнего I/O.** Зависший запрос/ожидание не должен
  подвешивать таску устройства.
- **Корректная отмена.** При `close()/stop()` все таски (read-loop, ping-loop,
  reconnect) отменяются и дожидаются; `CancelledError` обрабатывается чисто.
- **Изоляция сбоев.** Падение одного устройства/сценария не роняет парк.
- **Качество = часть «готово».** Полные type hints (strict mypy), Google-style
  docstrings на всём публичном API (`Args/Returns/Raises/Example`), `Raises:`
  обязан перечислять подклассы `RpcError`. Без «голых» `except:`.
- **Публичный контракт узкий.** Наружу через `axonctl.__all__` — только
  `FleetController`, `Device`, `Selector`, `UiTree`/`UiNode`, `Window`/`WindowList`,
  иерархия исключений, value-типы (`Bounds`, `Point`), конфиг. Слои
  `conn/rpc/router/pending/events` — внутренние.
- **Документация двуязычна (EN канон + RU зеркало).** Вся проза для
  пользователя — на двух языках: английский канонический (`FILE.md`), русский
  зеркало (`FILE.ru.md`), со ссылкой-переключателем сверху. Касается README,
  CONTRIBUTING, CHANGELOG, PROTOCOL и всех guide-страниц сайта. При правке одного
  языка второй держим в синхронности в **том же коммите**. **Docstrings — только
  на английском** (это код; из них автогенерируется API Reference). Этот
  внутренний план (`IMPLEMENTATION_PLAN.md`) — рабочий документ, ведётся на
  русском и не зеркалится.

## Git-flow по этапам

- `feature/stageN-<short>` от `develop` → реализация + тесты + докстринги +
  зелёные линтеры/типы/тесты → merge в `develop` через `--no-ff` → удалить ветку.
- Коммиты — Conventional Commits, атомарные.
- Статусы в этом файле обновляются **отдельным коммитом** после завершения этапа.
- `main` — только релизы (тег `vX.Y.Z`). Релиз — через `release/x.y.z`.

## Замечание по порядку этапов (отклонение от брифа — осознанное)

Бриф предлагал «события и ожидания → потом дерево и фасад Device». Но событийный
`wait_for` по своей сути = «дамп по сигналу `screenChanged` → проверить
**Selector** на **UiTree**». То есть ожидания **зависят** от дерева и селектора.
Поэтому слой `tree/` (чистый, без I/O) ставится **до** событий/ожиданий
(Stage 2 → Stage 3). Stage 1 при этом тянет лишь **минимальный** разбор дампа в
`UiTree`, достаточный, чтобы доказать тракт «сокет→дерево».

---

## Stage 0 — Scaffolding & tooling baseline

**Цель.** Превратить скелет в устанавливаемый типизированный пакет с зелёной
инфраструктурой качества — фундамент, на который ложатся слои.

**Подзадачи.**
- `src/axonctl/__init__.py` с пустым (пока) `__all__` и докстрингом-обзором пакета.
- `src/axonctl/py.typed` (PEP 561).
- Структура пакетов-папок: `conn/ rpc/ events/ tree/ fleet/` с `__init__.py`.
- `tests/unit/` и `tests/integration/` с `conftest.py` (pytest-asyncio).
- Финализировать конфиги `ruff`/`black`/`mypy`/`pytest` в `pyproject.toml`.
- Скопировать `axon/docs/PROTOCOL.md` → `docs/PROTOCOL.md` с шапкой об источнике.
- `CHANGELOG.md` (Keep a Changelog, секция Unreleased), `CONTRIBUTING.md`
  (сборка, тесты, git-flow кратко).
- Smoke-тест: `import axonctl` работает; тривиальный async-тест проходит.

**Готово, когда.** `pip install -e .[dev]` ставит пакет; `import axonctl`
успешен; `ruff check`, `black --check`, `mypy`, `pytest` — зелёные на пустом
пакете.

**Как тестировать.** `pytest tests/unit/test_smoke.py`; запуск всех четырёх
инструментов качества.

**Ветка.** `feature/stage0-scaffolding`.

---

## Stage 1 — Transport + RPC + minimal Device (первый вертикальный срез)

**Цель.** Одно устройство «заговорило» по сокету: против фейкового агента
проходят `ping` и `dumpHierarchy` (с разбором в `UiTree`). Прогоняет тракт
**сокет → router → pending → RpcClient → Device → дерево** насквозь.

**Подзадачи.**
- `config.py` — dataclass-конфиг: таймауты (rpc, ping, connect), диапазон портов,
  backoff (base/max/jitter), concurrency, `serial→tags`. Загрузка из TOML
  (`tomllib`) и программно. (Полная валидация дозреет к Stage 5.)
- `conn/ws.py` — `WsClient`: тонкая обёртка над `websockets`
  (`open/send_text/recv()->str|bytes/close`). Шов для тестов (фейк).
- `conn/router.py` — `FrameRouter.classify(msg)`: `bytes`→бинарь (первые 4 байта
  BE = id)→`resolve_binary`; `str`+`event`→EventBus (заглушка-хук в Stage 1);
  `str`+`id`→`resolve`. Только диспетчеризация.
- `rpc/ids.py` — `IdGenerator`: монотонный `next()`, оборот в `[0, 2³²−1]`,
  не переиспользует id, висящие в реестре.
- `rpc/errors.py` — `RpcError` + иерархия (все коды протокола → классы:
  `NodeNotFound`, `AmbiguousMatch`, `Stale`, `NotEditable`,
  `AccessibilityDisabled`, `GestureFailed`, `ActionNotSupported`,
  `WindowNotFound`, `MethodNotFound`, `InvalidParams`, ...). Фабрика
  `from_code(code, message)`.
- `rpc/pending.py` — `PendingRegistry`: `register(id, deadline)->Future`,
  `resolve(id, msg)`, `resolve_binary(id, bytes)`. **Вариант А** для двухчастных
  (screenshot) ответов заложен сразу (мета + бинарь резолвят Future вместе);
  unit-тестируется здесь, интеграционно — в Stage 4. Дедлайн на каждый register.
- `conn/reconnect.py` — `ReconnectPolicy.next_delay(attempt)`: экспонента +
  потолок + джиттер. (Использование — в Stage 5; модуль чистый, тестируем сразу.)
- `conn/connection.py` — `DeviceConnection`: `connect()` открывает сокет,
  поднимает `_read_loop` (recv→router) и `_ping_loop` (ping с таймаутом → мёртв);
  `send(text)`, `state: ConnectionState`, владеет router+EventBus(заглушка);
  корректная отмена тасок в `close()`. (Реконнект-логика — каркас, активна в St.5.)
- `rpc/client.py` — `RpcClient.call(method, params)->dict` (поднимает `RpcError`
  при `error`), `call_binary(...)->(meta, bytes)` (каркас под screenshot). Таймаут
  на каждый вызов через `asyncio.timeout`.
- `tree/geom.py` — `Bounds`, `Point` (frozen dataclass).
- `tree/node.py` + `tree/tree.py` — **минимальный** `UiNode`/`UiTree`: разбор
  orjson-словаря дампа в дерево (поля схемы + `children`, `screen`, `package`).
  Навигация/Selector — заглушки до Stage 2.
- `device.py` — **минимальный** `Device`: `serial`, `tags`, `state`; методы
  `ping()`, `dump(...)->UiTree`. Делегирует `RpcClient`.

**Готово, когда.** Против фейкового агента: `await device.ping()` возвращает
`pong`; `await device.dump()` возвращает `UiTree` с корректными `screen`,
`package`, деревом узлов. Таймауты и отмена работают. Все 4 инструмента зелёные.

**Как тестировать.**
- *unit:* классификация фреймов (фейковый `WsClient`), оборот `IdGenerator`,
  маппинг `errors.from_code`, разбор дампа в `UiTree`, `PendingRegistry`
  (включая `resolve_binary` и таймаут register).
- *integration:* in-process WS-сервер (фейковый агент) на ping/dump → весь тракт
  `RpcClient↔connection↔router↔pending`; проверка таймаута зависшего вызова.

**Ветка.** `feature/stage1-transport-rpc`.

---

## Stage 2 — UI tree, Selector, Window/WindowList (чистый слой, без I/O)

**Цель.** Полноценный поиск/навигация по дереву на ПК (stateless-принцип) и
модель окон из `getWindows`. Эргономичный `Selector`.

**Подзадачи.**
- `tree/node.py` — навигация: `find/find_all(selector)`, `descendants()`,
  `parent` (ленивые parent-ссылки — строить только при запросе навигации вверх).
- `tree/selector.py` — `Selector(by, value, match, index)` + `within(other)`;
  фабрики `Selector.id(...)`, `Selector.text(...)`, `Selector.text_contains(...)`,
  `Selector.desc(...)`, `Selector.cls(...)`; match: `exact|contains|regex`.
  Оценка на `UiTree` (для regex — поведение как у Kotlin-regex агента: matches
  anywhere, якоря `^/$`).
- `tree/window.py` — `Window` (window_id, type, layer, active, focused, title,
  package, bounds, root?: UiTree) + `WindowList` (топовое первым; `active()`,
  `by_type(t)`, `ime()`, `dialogs()`). Чистый разбор результата `getWindows`.
- `tree/tree.py` — `UiTree.find/find_all` (делегируют корню), фабрика из словаря.
- Подключить к `Device`: `dump()` уже возвращает полноценный `UiTree`;
  `windows(include_tree=...)->WindowList` (метод `getWindows`); `find(selector)`
  (дамп + поиск одним вызовом).

**Готово, когда.** На фикстурах-деревьях работают exact/contains/regex, `index`,
`within`, навигация вверх/вниз; `getWindows` парсится в `WindowList` с выборками.

**Как тестировать.** *unit:* богатый набор фикстур дерева/окон — все режимы
матчинга, `within`, неоднозначность, границы. *integration:* `device.windows()`
и `device.find(selector)` против фейкового агента.

**Ветка.** `feature/stage2-tree-selector`.

---

## Stage 3 — Events + событийные ожидания

**Цель.** Событийные (не поллинг) ожидания — смысл архитектуры.

**Подзадачи.**
- `events/bus.py` — `EventBus` (per-device): `emit(event)`, подписка через
  `asyncio.Queue`/async-генератор; `screen_flow()` для WaitEngine. Включить в
  `FrameRouter` (заглушка из Stage 1 заменяется реальным).
- `events/state.py` — `ScreenState`: последний `screen:int` + `package:str` из
  событий и дампов — чтобы ожидание понимало, нужен ли свежий дамп.
- `setEventStream` в `RpcClient`/`Device`: ленивое включение «крана» событий.
- `wait.py` — `WaitEngine`: включить стрим (если ещё нет) → подписаться на
  `screenChanged` → дамп по сигналу → проверить предикат на `UiTree` → таймаут
  через `asyncio.timeout`. Без поллинга. Учитывать монотонность `screen`
  (стартовый дамп + реакция на инкремент).
- `Device`: `wait_for(selector, timeout)->UiNode`, `wait_gone(selector, timeout)`,
  `wait_activity(package, timeout)`, `wait_toast(timeout)->str` (через `toast`).
- Async-хелперы: `device.sleep(...)` (обёртка `asyncio.sleep`).

**Готово, когда.** Против фейкового агента, эмитящего `screenChanged`/`toast`:
`wait_for` резолвится по событию (а не таймауту), `wait_gone`/`wait_activity`/
`wait_toast` работают; таймаут поднимает корректное исключение.

**Как тестировать.** *integration:* фейковый агент шлёт `screenChanged` после
«действия» → `wait_for` ловит появление элемента; сценарий «элемент исчез»;
`toast`-фидбэк; проверка, что **нет** поллинга (дамп делается только по событию).

**Ветка.** `feature/stage3-events-waits`.

---

## Stage 4 — Полный фасад Device: жесты, действия, screenshot, retry

**Цель.** Закрыть весь набор атомарных действий устройства + корреляцию бинаря +
ретраи STALE на стороне ПК.

**Подзадачи.**
- `gestures.py` — `GestureBuilder`: чистая сборка `strokes` для tap/long/double/
  swipe/drag/pinch (точки, `startTime`, `duration`).
- `Device` жесты: `tap`, `long_tap`, `swipe`, `drag`, `pinch` → `gesture`.
- `Device` действия: `click`, `set_text`, `clear`, `scroll(direction)`,
  `focus`/`clear_focus`/`select`/`set_selection` → `nodeAction`
  (с `window_id`, `match`, `index`).
- `Device.global_action(action)` → `globalAction`.
- `Device.screenshot(format, quality)->bytes` → `call_binary`; интеграционная
  проверка **варианта А** (мета JSON + бинарь, идущие подряд, резолвят один
  Future). Учесть rate-limit ~1/сек как контракт (док).
- `retry.py` — `RetryPolicy`: при `Stale` передампить и повторить N раз
  (конфигурируемо); опциональный retry-декоратор поверх корутин-действий.
  Применить к node-actions.

**Готово, когда.** Против фейкового агента проходят жесты/действия/screenshot;
`Stale` от агента вызывает контролируемый ретрай; бинарь скриншота корректно
коррелируется по id.

**Как тестировать.** *unit:* `GestureBuilder` (tap/swipe/pinch → корректные
strokes), `RetryPolicy` (счётчик повторов на `Stale`). *integration:* screenshot
(JSON+бинарь), `nodeAction` с `index`/`window_id`, ретрай при `Stale`.

**Ветка.** `feature/stage4-device-facade`.

---

## Stage 5 — Обвязка парка: watcher, ports, adb, группы, FleetController

**Цель.** Управление парком: attach/detach, форварды, порты, группы, реконнект.

**Подзадачи.**
- `fleet/watcher.py` — `AdbWatcher` над `adbutils.track_devices()`: эмитит
  attach/detach (без поллинга). Синхронный adbutils — в `run_in_executor`/поток.
- `fleet/ports.py` — `PortAllocator.acquire(serial)->int`/`release(serial)` из
  диапазона.
- `fleet/adb.py` — `AdbBridge`: `forward/remove_forward/shell/launch/force_stop/
  install` — тонкая обёртка над adbutils (блокирующее — в executor).
- `fleet/groups.py` — `TagIndex` (обратный индекс `tag→set[serial]`, обновляется
  на attach/detach) + `DeviceGroup.resolve(registry)->set[Device]`. Разрешение
  `targets`: `str|Callable|list[str]|None`.
- `conn/connection.py` — активировать реконнект: чинит обрывы сокета (сервис
  перезапустился), пока устройство present, через `ReconnectPolicy`. **Граница:**
  сам в adb не лезет.
- `fleet/controller.py` — `FleetController`: реестр `serial→Device`, watcher,
  ports, adb, TagIndex; `start()/stop()`, `async with`, `from_config(path)` и
  `FleetController(config=...)`; `devices()/get()/group()/on_attached/on_detached`.
  На attach: port→forward→DeviceConnection→Device→реестр+TagIndex. На detach:
  гасит reconnect (`close()`), снимает forward, освобождает порт; reattach →
  пересоздаёт Device. Координация «reconnect vs detach» — без гонок.

**Готово, когда.** Контроллер как `async with` поднимает соединения на attach,
корректно гасит парк на выходе; detach снимает forward/порт и не воюет с
reconnect; группы резолвятся через TagIndex.

**Как тестировать.** *unit:* `PortAllocator`, `TagIndex`, разрешение `targets`,
`ReconnectPolicy`. *integration:* фейковый watcher (attach/detach события) +
фейковый агент → реестр обновляется; разрыв сокета → reconnect; detach →
очистка и отсутствие reconnect. adbutils — за абстракцией `AdbBridge` (фейк).

**Ветка.** `feature/stage5-fleet`.

---

## Stage 6 — FleetExecutor: run / targets / concurrency / Results

**Цель.** Прогон пользовательского сценария по группам устройств.

**Подзадачи.**
- `fleet/executor.py` — `FleetExecutor.run(scenario, targets, concurrency)`:
  resolve `targets` → **снапшот** целевого множества (детерминизм) → глобальный
  `asyncio.Semaphore` (один на контроллер, общий для всех одновременных прогонов)
  → таска на устройство → `asyncio.gather(return_exceptions=True)` → `Results`.
- `Outcome`/`Results` — структура per-device (`serial → ok(value)|error(exc)`).
  Отвалившиеся по ходу → `failed` в результатах, прогон не падает.
- Тип/протокол `Scenario` = `async (device: Device) -> T`.
- `FleetController.run(...)` делегирует executor'у; общий семафор.

**Готово, когда.** `await fleet.run(scenario, targets=..., concurrency=N)`
возвращает `Results`; падение сценария на одном устройстве не роняет остальные;
несколько одновременных `run()` делят один семафор; снапшот целей детерминирован.

**Как тестировать.** *integration:* несколько фейковых устройств; сценарий с
исключением на одном → в `Results` ошибка только у него; проверка соблюдения
лимита конкурентности; два параллельных `run()` с общим семафором; detach
устройства во время прогона → `failed` в `Results`.

**Ветка.** `feature/stage6-executor`.

---

## Stage 7 — Документация, примеры, релиз 0.1.0

**Цель.** Оформить как полноценную библиотеку и зарелизить.

**Подзадачи.**
- `__init__.py`: финальный публичный `__all__` (фасад + исключения + value-типы).
- `mkdocs.yml` + `docs/`: Overview, Quickstart, Concepts (stateless,
  событийные ожидания, группы, **модель исполнения сценариев** + таблица
  «блокирующее → async-замена»), Fleet management, Writing scenarios,
  API Reference (mkdocstrings, авто из docstrings — на EN), Protocol (инклуд
  PROTOCOL.md). **Двуязычный сайт** через `mkdocs-static-i18n` (en/ru): каждая
  guide-страница — в двух языках; API Reference остаётся на EN (источник —
  docstrings). Переключатель языка в шапке.
- `examples/` — автономные демо, импортирующие установленный `axonctl` как
  внешний пользователь (НЕ часть пакета): минимальный wait_for→click, прогон по
  группе, обработка `Results`. Сверить примеры с актуальным API.
- `CHANGELOG.md` — наполнить Unreleased.
- **Релиз.** `release/0.1.0` от `develop`: бамп версии (уже 0.1.0), финал
  CHANGELOG → merge в `main` с аннотированным тегом `v0.1.0` → merge обратно в
  `develop`.

**Готово, когда.** `mkdocs build` без ошибок; примеры запускаются против
фейкового/реального агента; на `main` стоит тег `v0.1.0`.

**Ветка.** `feature/stage7-docs-examples` → затем `release/0.1.0`.

---

## Статусы

| Stage | Описание | Статус |
|-------|----------|--------|
| 0 | Scaffolding & tooling | ✅ готов |
| 1 | Transport + RPC + minimal Device | ✅ готов |
| 2 | UI tree / Selector / Windows | ✅ готов |
| 3 | Events + waits | ✅ готов |
| 4 | Device facade (gestures/actions/screenshot/retry) | ✅ готов |
| 5 | Fleet (watcher/ports/adb/groups/controller) | ✅ готов |
| 6 | Executor (run/targets/Results) | ⬜ не начат |
| 7 | Docs / examples / release 0.1.0 | ⬜ не начат |

Легенда: ⬜ не начат · 🟡 в работе · ✅ готов (merged в develop).
