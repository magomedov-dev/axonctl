# Скриншоты


[`Device.screenshot`][axonctl.Device.screenshot] делает снимок экрана и возвращает
закодированные **байты** изображения:

```python
jpeg = await device.screenshot()                 # jpeg, quality 80
jpeg = await device.screenshot(quality=60)
png = await device.screenshot(format="png")      # quality is ignored for PNG

from pathlib import Path
Path("shot.png").write_bytes(png)
```

## Лимит частоты

Платформа ограничивает снимки примерно **одним в секунду**; вызовы чаще падают с
[`InternalError`][axonctl.InternalError]. Распределяйте скриншоты во времени:

```python
shot1 = await device.screenshot()
await device.sleep(1.1)        # respect the ~1/sec limit
shot2 = await device.screenshot()
```

## Как это работает (вариант A)

Ответ на скриншот — это два сообщения: JSON-метаданные, сразу за которыми идёт
бинарный кадр, чей 4-байтовый заголовок big-endian несёт id запроса. Реестр
ожидающих запросов в axonctl сопоставляет эту пару и резолвит вызов только когда
оба сообщения пришли, поэтому вы просто получаете чистые `bytes`. С кадрированием
вам иметь дело не приходится.

## Тяжёлая обработка — за пределами loop

Декодирование/анализ изображения нагружает CPU. Делать это прямо в потоке
исполнения значит блокировать event loop и тормозить все остальные устройства.
Передайте работу в пул:

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

POOL = ProcessPoolExecutor()

async def analyze(device):
    img = await device.screenshot()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(POOL, heavy_cv, img)   # off the loop
    return result
```

Правила модели исполнения — в [Концепциях](concepts.md).
