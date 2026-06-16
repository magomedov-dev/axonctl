# Написание сценариев


Сценарий — это просто `async`-функция, принимающая [`Device`][axonctl.Device] и
возвращающая что угодно. Библиотека определяет для него тип
[`Scenario`][axonctl.Scenario] и прогоняет его по группам устройств; про тело она
ничего не знает.

```python
from axonctl import Device, Selector

async def login(device: Device) -> str:
    await device.launch("com.example.app")
    await device.wait_for(Selector.id("com.example.app:id/user"))
    await device.set_text(Selector.id("com.example.app:id/user"), "alice")
    await device.set_text(Selector.id("com.example.app:id/pass"), "secret")
    await device.click(Selector.text("Sign in"))
    return await device.wait_toast(timeout=5)
```

## Селекторы

Собирай селекторы через фабрики и комбинируй:

```python
Selector.id("com.app:id/login")
Selector.text("Sign in")
Selector.text_contains("Signing")
Selector.desc("Profile photo")
Selector.cls("android.widget.EditText", index=0)
Selector.text("OK", match="regex")           # matches anywhere; якоря ^ $
Selector.text("Delete").within(Selector.id("com.app:id/dialog"))
```

`find`/`find_all`/`wait_for` оценивают селекторы на ПК поверх дампа, включая
`.within(...)`. **Действия** над узлами (`click`, `set_text`, ...) отправляют
селектор агенту, который `.within(...)` не поддерживает: передача
`.within(...)`-селектора в действие поднимает
[`UnsupportedSelector`][axonctl.UnsupportedSelector] (а не молчаливый клик не
туда). Для «внутри диалога» передавай `window_id` (из
[`windows`][axonctl.Device.windows]); для «внутри контейнера» — более конкретный
селектор или `tap(node.center)` после `find`.

Узел, возвращённый `find`/`wait_for`, — это **снимок** дампа, а не живая ручка:
действуй через критерии (`click(Selector...)`) или `tap(node.center)`, а не через
сам объект узла.

## Поиск против ожидания

```python
# один дамп + поиск:
node = await device.find(Selector.id("com.app:id/title"))

# переиспользовать один дамп для нескольких запросов:
tree = await device.dump()
title = tree.find(Selector.id("com.app:id/title"))
buttons = tree.find_all(Selector.cls("android.widget.Button"))

# событийное ожидание (предпочтительнее find в цикле):
await device.wait_for(Selector.text("Continue"), timeout=10)
await device.wait_gone(Selector.id("com.app:id/spinner"), timeout=15)
```

## Действия

```python
await device.click(Selector.text("Next"))
await device.set_text(Selector.id("com.app:id/search"), "hello")
await device.scroll(Selector.cls("androidx.recyclerview.widget.RecyclerView"), "forward")
await device.tap(540, 1200)
await device.swipe(540, 1600, 540, 600)
await device.long_tap(300, 800)
shot = await device.screenshot(format="png")     # rate-limit ~1/сек
ok = await device.global_action("home")
```

## Ретраи

Действия над узлами автоматически ретраятся при `STALE` (настраивается через
`[retry]`). Для своих помощников используй декоратор:

```python
from axonctl import retry_on_stale

@retry_on_stale(attempts=5)
async def tap_continue(device):
    await device.click(Selector.text("Continue"))
```

## Оставайся неблокирующим

Твой сценарий делит один event loop со всеми остальными устройствами. Держи всё
быстрым или await-ным (полное правило и таблицу блокирующее→async см. в
[Концепциях](concepts.md)).

```python
import asyncio
import httpx

async def enrich(device):
    # ХОРОШО: await async-I/O и собственный sleep устройства
    await device.sleep(1.0)                       # не time.sleep
    async with httpx.AsyncClient() as client:     # не requests
        resp = await client.get("https://api.example.com/next")
    await device.set_text(Selector.id("com.app:id/code"), resp.text)
```

Тяжёлый CPU — в пул:

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

POOL = ProcessPoolExecutor()

async def solve(device):
    image = await device.screenshot()
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(POOL, expensive_cv, image)  # с loop долой
    await device.set_text(Selector.id("com.app:id/answer"), answer)
```

## Обработка ошибок

Лови типизированные исключения, которые тебе важны; всё остальное всплывёт в
[`Results`][axonctl.Results] прогона как failed-[`Outcome`][axonctl.Outcome].

```python
from axonctl import NodeNotFound, WaitTimeout

async def maybe_dismiss(device):
    try:
        await device.click(Selector.text("Not now"))
    except NodeNotFound:
        pass  # нечего закрывать
    try:
        await device.wait_for(Selector.id("com.app:id/home"), timeout=8)
    except WaitTimeout:
        return "stuck"
    return "home"
```
