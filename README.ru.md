# axonctl

[English](README.md) · **Русский**

> **Статус: ранняя разработка (0.1.0).** Публичный API формируется — см.
> [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

`axonctl` — **контроллер на стороне ПК** для [Axon](https://github.com/magomedov-dev/axon)
— системы автоматизации парка Android-устройств. На каждом устройстве агент
(APK на AccessibilityService) предоставляет stateless JSON-RPC API поверх
WebSocket; `axonctl` подключается к каждому устройству через `adb forward`,
управляет всем парком и даёт твоему коду автоматизации эргономичный `async` API.

Это **переиспользуемая библиотека**, а не приложение: ты устанавливаешь
`axonctl` и пишешь *свои* сценарии автоматизации в *своём* проекте. Библиотека
даёт фундамент (подключение к парку, поиск/ожидание/действия над UI, прогон
функций по группам устройств); сами сценарии — твой код, живущий вне этого
репозитория.

## Быстрый старт (целевой вид — пока не реализовано)

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
            print(serial, outcome)

asyncio.run(main())
```

## Установка (заглушка)

```bash
pip install axonctl          # ещё не опубликовано
```

Требуется Python 3.11+.

## Документация

- Справочник протокола: [`docs/PROTOCOL.md`](docs/PROTOCOL.md) (канонический
  источник: [репозиторий агента Axon](https://github.com/magomedov-dev/axon),
  `docs/PROTOCOL.md`).
- Полный сайт документации: на MkDocs (планируется).

## Дисклеймер

`axonctl` — инструмент для автоматизации и управления Android-устройствами,
**которыми ты владеешь или которыми вправе управлять легально**. Ты несёшь
ответственность за соблюдение применимого законодательства и условий
использования любого ПО, которое автоматизируешь.

## Лицензия

[MIT](LICENSE).
