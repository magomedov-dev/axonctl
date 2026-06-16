# Управление парком


[`FleetController`][axonctl.FleetController] — точка входа. Он следит за adb на
attach/detach, поднимает форварды, подключает устройства, ведёт реестр и
прогоняет твои сценарии по группам.

## Конфигурация

Опиши парк в TOML и загрузи через
[`from_config`][axonctl.FleetController.from_config]:

```toml
# fleet.toml
agent_port = 9008        # порт, который слушает агент (цель форварда)
concurrency = 10         # глобальный лимит одновременных операций над устройствами

[ports]
start = 10000            # диапазон локальных портов для adb forward
end = 11000

[timeouts]
connect = 10
rpc = 15
ping_interval = 5
ping_timeout = 5

[backoff]                # backoff реконнекта
base = 0.5
factor = 2.0
max = 30
jitter = 0.1

[retry]                  # политика ретраев STALE для действий над узлами
attempts = 3
delay = 0.1

[devices]                # serial -> tags
"ABC123" = ["group_us", "pixel"]
"DEF456" = ["group_eu"]
```

Можно собрать [`FleetConfig`][axonctl.FleetConfig] программно и передать как
`FleetController(config=...)`.

## Жизненный цикл

Используй контроллер как асинхронный контекст-менеджер — вход стартует watcher и
поднимает устройства, выход корректно гасит весь парк.

По умолчанию `start()` (и `async with`) **ждёт, пока устройства, присутствующие в
adb на старте, подключатся**, прежде чем вернуть управление (до `ready_timeout`),
поэтому парк сразу готов — без ручного «дождись устройств». Отключается через
`FleetController(..., wait_ready=False)` / `from_config(..., wait_ready=False)`,
либо вызови `await fleet.wait_ready(timeout=...)` сам.

```python
async with FleetController.from_config("fleet.toml") as fleet:
    print([d.serial for d in fleet.devices()])
    device = fleet.get("ABC123")
```

Attach/detach автоматический. На attach контроллер выделяет порт, поднимает
форвард, подключается и регистрирует [`Device`][axonctl.Device]. На detach
закрывает соединение (останавливая реконнект), снимает форвард и освобождает порт.
Колбэки — [`on_attached`][axonctl.FleetController.on_attached] /
[`on_detached`][axonctl.FleetController.on_detached].

Обрыв сокета (например, перезапуск сервиса агента) чинится автоматически с backoff,
**пока устройство present**; текущие вызовы падают с `ConnectionLost`, но
устройство снова становится рабочим после реконнекта.

## Группы и прогон сценариев

[`run`][axonctl.FleetController.run] выполняет сценарий по целевому множеству и
возвращает [`Results`][axonctl.Results] — маппинг `serial -> Outcome`.

```python
# targets: имя группы/тега, список серийников, предикат по тегам или None (все)
results = await fleet.run(login, targets="group_us", concurrency=10)
results = await fleet.run(login, targets=["ABC123", "DEF456"])
results = await fleet.run(login, targets=lambda tags: "pixel" in tags)
results = await fleet.run(login)  # весь парк

for serial, outcome in results.items():
    if outcome.ok:
        print(serial, "->", outcome.value)
    else:
        print(serial, "failed:", outcome.error)

print("all ok:", results.all_ok)
print("failures:", results.failed())
```

Целевое множество **снимается снапшотом** в начале прогона, поэтому он
детерминирован, даже когда устройства появляются и исчезают. Устройство, которое
упало или отвалилось по ходу, становится failed-[`Outcome`][axonctl.Outcome] — оно
никогда не роняет прогон.

**Разрешение targets.** Имя группы/тега, предикат по тегам или явный список
серийников разрешаются по **конфигу** — поэтому сконфигурированный член, который
сейчас не подключён, *не* пропадает молча; он попадает в результаты как
failed-[`Outcome`][axonctl.Outcome] с [`DeviceNotConnected`][axonctl.DeviceNotConnected].
`targets=None` прогоняет по всем подключённым сейчас устройствам. («Прогони на
группе *us*» означает все *us*, а отключённые — отмечены как ошибки, а не тихо
выпали.)

### Конкурентность

Есть **один глобальный семафор на контроллер** (`config.concurrency`), общий для
всех одновременных прогонов — он защищает общую USB-шину. Опциональный аргумент
`concurrency` у `run` добавляет второй, per-run лимит. Эффективная параллельность
прогона — меньшее из двух.

## Резолв adb

Бинарь adb ищется как `$AXONCTL_ADB` → `.tooling/platform-tools/adb` → `adb` в
`PATH`, либо задай `adb_path` в конфиге.
