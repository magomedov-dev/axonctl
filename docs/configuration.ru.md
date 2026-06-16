# Конфигурация


Парк описывается через [`FleetConfig`][axonctl.FleetConfig], который загружается из
TOML с помощью [`from_config`][axonctl.FleetController.from_config] либо собирается
программно.

## Полный справочник по TOML

```toml
# fleet.toml
agent_port = 9008        # порт, который слушает агент на устройстве (цель форварда)
concurrency = 10         # глобальный лимит одновременных операций с устройствами (шина USB)
adb_path = ""            # явный путь к adb; пропустите/оставьте пустым для авторазрешения

[ports]                  # диапазон локальных портов для adb-форвардов
start = 10000
end = 11000

[timeouts]               # секунды
connect = 10             # открытие WebSocket
rpc = 15                 # дедлайн по умолчанию на один вызов
ping_interval = 5        # период heartbeat
ping_timeout = 5         # дедлайн ответа heartbeat, после которого связь считается «мёртвой»

[backoff]                # backoff переподключения: min(base*factor**n, max) ± jitter
base = 0.5
factor = 2.0
max = 30
jitter = 0.1             # доля (0..1)

[retry]                  # ретрай STALE для действий над узлами
attempts = 3             # всего попыток, включая первую
delay = 0.1              # секунды между попытками

[devices]                # serial -> теги (объявленный парк)
"ABC123" = ["group_us", "pixel"]
"DEF456" = ["group_eu"]
```

Любая секция необязательна; пропущенные ключи используют значения по умолчанию,
показанные выше.

## Программная конфигурация

```python
from axonctl import FleetConfig, Timeouts, Backoff, Retry, FleetController

config = FleetConfig(
    concurrency=20,
    devices={"ABC123": frozenset({"group_us"})},
    timeouts=Timeouts(rpc=20),
    backoff=Backoff(base=1.0, max=60),
    retry=Retry(attempts=5, delay=0.2),
)
fleet = FleetController(config)
```

## Справочник по полям

| Поле | По умолчанию | Значение |
|-------|---------|---------|
| `agent_port` | `9008` | Порт, который слушает агент (цель форварда). |
| `port_range` | `(10000, 11000)` | Включительный диапазон локальных портов для форвардов. |
| `concurrency` | `8` | Размер глобального семафора, общий для всех запусков (лимит шины USB). |
| `adb_path` | `None` | Явный путь к adb; авторазрешается, если не задан. |
| `timeouts.connect` | `10` | Таймаут открытия WebSocket (с). |
| `timeouts.rpc` | `15` | Дедлайн по умолчанию на один вызов (с). |
| `timeouts.ping_interval` | `5` | Период heartbeat (с). |
| `timeouts.ping_timeout` | `5` | Дедлайн ответа heartbeat (с). |
| `backoff.base/factor/max/jitter` | `0.5 / 2.0 / 30 / 0.1` | Backoff переподключения. |
| `retry.attempts/delay` | `3 / 0.1` | Ретрай STALE для действий над узлами. |
| `devices` | `{}` | `serial -> tags` — объявленный парк. |

## Параметры готовности

`FleetController` / `from_config` также принимают параметры готовности (аргументы
конструктора, а не TOML):

- `wait_ready` (по умолчанию `True`) — `start()`/`async with` ждёт подключения
  присутствующих устройств, прежде чем вернуть управление.
- `ready_timeout` (по умолчанию `30.0`) — как долго ждать.

```python
async with FleetController.from_config("fleet.toml", ready_timeout=15) as fleet:
    ...
```

## Теги и группы

Теги **статические** — объявляются здесь, а не читаются с устройства. Они управляют
выбором цели по группам в [`run`][axonctl.FleetController.run]
(`targets="group_us"`), который разрешается по этой настроенной карте. См.
[Управление парком](fleet.md).
