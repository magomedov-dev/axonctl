# Обработка ошибок


Каждый сбой — это типизированное исключение, поэтому сценарии ловят ровно то, что
имеют в виду. Все исключения axonctl наследуются от [`AxonError`][axonctl.AxonError].

## Иерархия

```
AxonError
├── RpcError                 # ответ с ошибкой протокола (есть .code, .message)
│   ├── ParseError           # PARSE_ERROR
│   ├── InvalidRequest       # INVALID_REQUEST
│   ├── MethodNotFound       # METHOD_NOT_FOUND
│   ├── InvalidParams        # INVALID_PARAMS
│   ├── InternalError        # INTERNAL  (например, лимит частоты скриншотов)
│   ├── AccessibilityDisabled# ACCESSIBILITY_DISABLED (нет активного окна)
│   ├── WindowNotFound       # WINDOW_NOT_FOUND
│   ├── NodeNotFound         # NODE_NOT_FOUND
│   ├── AmbiguousMatch       # AMBIGUOUS_MATCH (несколько совпадений, нет индекса)
│   ├── ActionNotSupported   # ACTION_NOT_SUPPORTED
│   ├── NotEditable          # NOT_EDITABLE
│   ├── Stale                # STALE (узел изменился во время действия)
│   └── GestureFailed        # GESTURE_FAILED
├── RpcTimeout               # вызов превысил свой дедлайн
├── WaitTimeout              # условие ожидания не выполнилось вовремя
├── ConnectionLost           # сокет отвалился / стал непригоден
├── UnsupportedSelector      # селектор .within(...) передан в действие
└── DeviceNotConnected       # целевой серийник не подключён (в Results)
```

`RpcError` несёт `.code` (стабильный wire-код) и `.message`. Неизвестный код
становится обычным `RpcError` с сохранённым кодом.

## Ловим именно то, что нужно

```python
from axonctl import NodeNotFound, WaitTimeout, Stale

async def maybe_dismiss(device):
    try:
        await device.click(Selector.text("Not now"))
    except NodeNotFound:
        pass  # нечего закрывать — это нормально

    try:
        await device.wait_for(Selector.id("com.app:id/home"), timeout=8)
    except WaitTimeout:
        return "stuck"
    return "home"
```

## Какие методы что бросают

В докстринге каждого метода перечислено его `Raises:`. Типичные случаи:

| Операция | Типичные ошибки |
|-----------|----------------|
| `dump` / `find` / `wait_*` | `AccessibilityDisabled`, `WindowNotFound`, `RpcTimeout`, `ConnectionLost`, `WaitTimeout` (ожидания) |
| `click` / `set_text` / `scroll` / ... | `NodeNotFound`, `AmbiguousMatch`, `ActionNotSupported`, `NotEditable` (текст), `Stale`, `WindowNotFound`, `UnsupportedSelector` |
| `tap` / `swipe` / `pinch` / ... | `GestureFailed`, `ConnectionLost` |
| `screenshot` | `InvalidParams`, `InternalError` (лимит частоты), `ConnectionLost` |
| `global_action` | `InvalidParams`, `ConnectionLost` |
| `launch` / `kill` / `install` | `RuntimeError` (adb не привязан) |

## Ошибки при прогоне на парке

Внутри [`run`][axonctl.FleetController.run] сбой на отдельном устройстве **не**
прерывает прогон — он фиксируется как неуспешный [`Outcome`][axonctl.Outcome]:

```python
results = await fleet.run(login, targets="group_us")
for serial, outcome in results.items():
    if outcome.ok:
        print(serial, "->", outcome.value)
    else:
        print(serial, "failed:", type(outcome.error).__name__, outcome.error)

print("failures:", results.failed())   # serial -> exception
```

Целевое, но отключённое устройство появляется как неуспешный outcome, несущий
[`DeviceNotConnected`][axonctl.DeviceNotConnected], — и никогда не пропадает молча.

`Outcome.unwrap()` возвращает значение или повторно бросает зафиксированную ошибку,
если вам удобнее обрабатывать сбои через `try/except` по каждому устройству.

См. также: [Написание сценариев](scenarios.md) и [Управление парком](fleet.md).
