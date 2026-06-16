# Установка


## Требования

- **Python 3.11+** (axonctl использует `asyncio.TaskGroup` и `asyncio.timeout`).
- Бинарник Android **`adb`** (из Android platform-tools).
- Одно или несколько устройств с запущенным **агентом Axon** (APK) и выданным
  разрешением Accessibility.

## Установка библиотеки

```bash
pip install axonctl
```

Это подтянет рантайм-зависимости (`websockets`, `orjson`, `adbutils`). Пакет
поставляется с информацией о типах (`py.typed`), поэтому ваш проверяльщик типов
видит типы axonctl без дополнительных стабов.

## Разрешение adb

axonctl нужен бинарник `adb`, чтобы пробрасывать порты и управлять приложениями.
Он ищется в таком порядке:

1. `$AXONCTL_ADB` — явный путь, который вы задали.
2. `.tooling/platform-tools/adb` — локальная копия в проекте (см. ниже).
3. `adb` в вашем `PATH` — системная установка.

Также можно задать его в конфиге: `adb_path = "/path/to/adb"`.

## Локальный тулчейн проекта (опционально, рекомендуется для разработки)

Если вы работаете **в репозитории axonctl**, всё — `uv`, управляемый Python,
dev-виртуалокружение и `adb` — устанавливается в локальную для проекта директорию
`.tooling/`, так что ничего не затрагивает вашу систему:

```bash
scripts/bootstrap.sh          # uv + Python + venv + adb, всё под .tooling/
source .tooling/venv/bin/activate
```

Доступны и отдельные шаги (`scripts/install-uv.sh`, `scripts/setup-venv.sh`,
`scripts/install-adb.sh`).

Для **вашего собственного** проекта автоматизации достаточно обычного
виртуалокружения и `pip install axonctl`; укажите axonctl на системный `adb` (или
задайте `$AXONCTL_ADB`).

## Подготовка устройства

1. Установите и включите агент Axon на устройстве.
2. Выдайте ему разрешение **Accessibility** (Настройки → Спец. возможности).
3. Подключитесь по USB и убедитесь, что `adb devices` показывает устройство как
   `device` (а не `unauthorized` / `offline`).

Агент слушает `0.0.0.0:9008`; контроллер сам настраивает
`adb forward tcp:<local> tcp:9008` за вас — вручную его запускать не нужно при
использовании [`FleetController`][axonctl.FleetController].

## Проверка установки

```python
import asyncio
from axonctl import connect_device

async def main():
    # set up a forward first for this one-off check:
    #   adb forward tcp:10001 tcp:9008
    async with connect_device("YOUR_SERIAL", uri="ws://127.0.0.1:10001") as device:
        print(await device.ping())

asyncio.run(main())
```

`{'pong': True, 'ts': ...}` означает, что весь конвейер (сокет → агент) жив.

Далее: [Быстрый старт](quickstart.md).
