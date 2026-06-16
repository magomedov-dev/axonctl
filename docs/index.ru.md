# axonctl


`axonctl` — **контроллер на стороне ПК** для [Axon](https://github.com/magomedov-dev/axon),
системы автоматизации парка Android-устройств. На каждом устройстве работает агент
(APK на AccessibilityService), который предоставляет **stateless** JSON-RPC API
поверх WebSocket; `axonctl` подключается к каждому устройству через `adb forward`,
управляет всем парком и даёт твоему коду автоматизации эргономичный, полностью
`async` API.

Это **переиспользуемая библиотека**, а не приложение: ты ставишь `axonctl` и
пишешь *свои* сценарии в *своём* проекте. Библиотека даёт фундамент — подключение
к парку, поиск/ожидание/действия над UI, прогон функций по группам устройств — а
сценарии это просто `async`-функции, принимающие [`Device`][axonctl.Device].

## Почему так устроено

- **Устройство без состояния.** Всё состояние — что ждём, ретраи, навигация по
  дереву, поиск элементов — живёт на ПК. Агент отдаёт только атомарные примитивы.
  См. [Концепции](concepts.md).
- **Ожидания событийные, не поллинг.** `wait_for`/`wait_gone` реагируют на поток
  `screenChanged` агента, поэтому они дёшевы и быстры.
- **Один event loop, сотни устройств.** Каждый сценарий выполняется как
  конкурентная asyncio-таска в одном потоке; пока одно устройство ждёт сокет, loop
  обслуживает остальные. Именно поэтому блокирующий вызов в сценарии опасен — см.
  [Написание сценариев](scenarios.md).

## На вкус

```python
import asyncio
from axonctl import FleetController, Selector

async def login(device):
    await device.launch("com.example.app")
    await device.wait_for(Selector.id("com.example.app:id/user"))
    await device.set_text(Selector.id("com.example.app:id/user"), "alice")
    await device.click(Selector.text("Sign in"))
    return await device.wait_toast(timeout=5)

async def main():
    async with FleetController.from_config("fleet.toml") as fleet:
        results = await fleet.run(login, targets="group_us", concurrency=10)
        for serial, outcome in results.items():
            print(serial, outcome.ok, outcome.value or outcome.error)

asyncio.run(main())
```

## Куда дальше

**Начало работы**

- [Установка](installation.md) — требования, adb, подготовка устройства.
- [Быстрый старт](quickstart.md) — первый сценарий.
- [Решение проблем](troubleshooting.md) — частые проблемы и их фиксы.

**Концепции**

- [Концепции](concepts.md) — принципы, на которых построен API (устройство без
  состояния, событийные ожидания, модель исполнения в одном loop).

**Гайды**

- [Селекторы](selectors.md) · [Дерево UI](tree.md) · [Ожидания](waiting.md)
- [Действия и жесты](actions.md) · [Скриншоты](screenshots.md) ·
  [Окна и диалоги](windows.md)
- [Управление парком](fleet.md) · [Написание сценариев](scenarios.md) ·
  [Конфигурация](configuration.md) · [Обработка ошибок](errors.md)
- [Cookbook](cookbook.md) — готовые паттерны.

**Справка**

- [Архитектура](architecture.md) — внутренние слои (для контрибьюторов).
- [Справочник API](api.md) — полный публичный API.
- [Протокол](PROTOCOL.md) — проводной протокол устройства.

## Дисклеймер

`axonctl` автоматизирует и управляет Android-устройствами, **которыми ты владеешь
или которыми вправе управлять легально**. Ты несёшь ответственность за соблюдение
применимого законодательства и условий использования любого ПО, которое
автоматизируешь.
