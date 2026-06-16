# Быстрый старт

[English](quickstart.md) · **Русский**

## Установка

```bash
pip install axonctl   # требуется Python 3.11+
```

`axonctl` нужен бинарь Android `adb`. Он ищется в порядке:
`$AXONCTL_ADB` → `.tooling/platform-tools/adb` → `adb` в `PATH`. Если работаешь из
этого репозитория, `scripts/bootstrap.sh` разворачивает всё (включая `adb`) в
локальную для проекта папку `.tooling/`.

## Подготовка устройства

1. Установи и включи агент Axon (APK) на устройстве; выдай разрешение
   Accessibility.
2. Подключи устройство по USB и убедись, что `adb devices` его видит.

Контроллер сам поднимает `adb forward` — вручную его запускать не нужно.

## Первый сценарий

Опиши свой парк в `fleet.toml`:

```toml
concurrency = 8

[devices]
"YOUR_SERIAL" = ["demo"]
```

Затем напиши сценарий и запусти его:

```python
import asyncio
from axonctl import FleetController, Selector

async def open_settings(device):
    await device.launch("com.android.settings")
    await device.wait_package("com.android.settings", timeout=10)
    tree = await device.dump()
    return tree.package

async def main():
    async with FleetController.from_config("fleet.toml") as fleet:
        results = await fleet.run(open_settings, targets="demo")
        for serial, outcome in results.items():
            print(serial, "->", outcome.value if outcome.ok else outcome.error)

asyncio.run(main())
```

## Одно устройство, без парка

Для быстрых экспериментов можно подключиться к одному устройству напрямую
(сначала подними forward сам, напр. `adb forward tcp:10001 tcp:9008`):

```python
import asyncio
from axonctl import connect_device, Selector

async def main():
    async with connect_device("YOUR_SERIAL", uri="ws://127.0.0.1:10001") as device:
        print(await device.ping())
        node = await device.find(Selector.text_contains("Settings"))
        print(node)

asyncio.run(main())
```

!!! note
    `connect_device` — удобство для экспериментов и тестов; продакшен-код должен
    использовать [`FleetController`][axonctl.FleetController], который сам
    управляет форвардами, портами, реконнектом и группами.

Дальше: [Концепции](concepts.md) и [Написание сценариев](scenarios.md).
