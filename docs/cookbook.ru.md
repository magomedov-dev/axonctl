# Cookbook


Практичные паттерны, готовые к копированию. Все сценарии — это `async def (device) -> T`.

## Войти и прочитать результат

```python
from axonctl import Device, Selector

async def login(device: Device) -> str:
    await device.launch("com.example.app")
    await device.wait_for(Selector.id("com.example.app:id/user"))
    await device.set_text(Selector.id("com.example.app:id/user"), "alice")
    await device.set_text(Selector.id("com.example.app:id/pass"), "secret")
    await device.click(Selector.text("Sign in"))
    return await device.wait_toast(timeout=5)   # form feedback
```

## Закрыть необязательный диалог

```python
from axonctl import NodeNotFound

async def dismiss_if_present(device):
    try:
        await device.click(Selector.text("Not now"))
    except NodeNotFound:
        pass  # not shown this time
```

## Скроллить, пока элемент не появится

```python
from axonctl import WaitTimeout

async def scroll_to(device, label, *, max_swipes=10):
    target = Selector.text(label)
    for _ in range(max_swipes):
        if await device.find(target):
            await device.click(target)
            return True
        await device.swipe(540, 1600, 540, 600, duration=200)
        await device.sleep(0.3)
    return False
```

## Действовать внутри диалога (window_id)

```python
async def confirm_in_dialog(device):
    windows = await device.windows()
    dialog = next(iter(windows.dialogs()), None)
    if dialog is None:
        return False
    await device.click(Selector.text("OK"), window_id=dialog.window_id)
    return True
```

## Повторить нестабильный шаг при STALE

```python
from axonctl import retry_on_stale

@retry_on_stale(attempts=5)
async def tap_continue(device):
    await device.click(Selector.text("Continue"))
```

## Вызвать собственный async API посреди сценария

```python
import httpx

async def submit_code(device):
    async with httpx.AsyncClient() as client:           # async, not requests
        code = (await client.get("https://api.example.com/code")).text
    await device.set_text(Selector.id("com.app:id/code"), code)
    await device.click(Selector.text("Verify"))
```

## Вынести тяжёлый CPU (работа с изображениями)

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

POOL = ProcessPoolExecutor()

async def solve_captcha(device):
    img = await device.screenshot()
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(POOL, solve, img)   # off the loop
    await device.set_text(Selector.id("com.app:id/captcha"), answer)
```

## Запустить на группе и подвести итог

```python
async def main(fleet):
    results = await fleet.run(login, targets="group_us", concurrency=10)
    ok = results.succeeded()        # serial -> value
    bad = results.failed()          # serial -> exception
    print(f"{len(ok)} ok, {len(bad)} failed")
    for serial, err in bad.items():
        print(serial, type(err).__name__, err)
```

## Реагировать на подключение/отключение устройств

```python
fleet.on_attached(lambda d: print("attached", d.serial))
fleet.on_detached(lambda s: print("detached", s))
```

## Полноценная запускаемая программа

Смотри `examples/run_group.py`, `examples/single_device.py` и
`examples/inspect_ui.py` в репозитории — они импортируют установленную библиотеку
ровно так же, как это делал бы твой собственный проект.

См. также: [Написание сценариев](scenarios.md) и [Обработка ошибок](errors.md).
