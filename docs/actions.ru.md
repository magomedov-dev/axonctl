# Действия и жесты


## Действия над узлами

Действия над узлами нацеливаются на узел через [`Selector`][axonctl.Selector];
агент заново находит его от свежего корня и выполняет действие. При `STALE` они
автоматически ретраятся (см. ниже).

```python
await device.click(Selector.text("Next"))
await device.long_click(Selector.id("com.app:id/item"))
await device.set_text(Selector.id("com.app:id/search"), "hello")
await device.clear(Selector.id("com.app:id/search"))
await device.scroll(Selector.cls("...RecyclerView"), "forward")   # or "backward"
await device.focus(Selector.id("com.app:id/field"))
await device.clear_focus(Selector.id("com.app:id/field"))
await device.select(Selector.id("com.app:id/item"))
await device.set_selection(Selector.id("com.app:id/field"), 0, 4)
```

Все они принимают `window_id=`, чтобы действовать внутри конкретного окна (из
[`windows`][axonctl.Device.windows]). Они поднимают соответствующую типизированную
ошибку — `NodeNotFound`, `AmbiguousMatch`, `ActionNotSupported`, `NotEditable`,
`WindowNotFound`, `Stale` или `UnsupportedSelector` (для селектора с
`.within(...)`). См. [Обработку ошибок](errors.md).

!!! note "Селекторы для действий"
    Действия используют `by`/`value`/`match`/`index` (+ опционально `window_id`).
    `.within(...)` — это ограничение области только для запросов, и оно поднимает
    `UnsupportedSelector`, если передать его в действие — используйте `window_id`
    или более конкретный селектор.

## Жесты (координаты)

Жесты принимают сырые экранные координаты (длительности в миллисекундах):

```python
await device.tap(540, 1200)
await device.double_tap(540, 1200)
await device.long_tap(300, 800, duration=800)
await device.swipe(540, 1600, 540, 600, duration=250)            # flick
await device.drag(200, 400, 800, 400, duration=800)             # slow drag
await device.pinch(540, 1000, start_radius=300, end_radius=80)  # pinch in (zoom out)
```

Тап по найденному узлу через его центр:

```python
node = await device.find(Selector.text("Menu"))
if node and node.center:
    await device.tap(node.center.x, node.center.y)
```

Жесты поднимают [`GestureFailed`][axonctl.GestureFailed], если жест отменён или
его невозможно доставить.

## Глобальные действия

```python
await device.global_action("home")          # back | home | recents | notifications
await device.global_action("back")          # quickSettings | powerDialog | lockScreen
```

Возвращает платформенный результат типа `bool`; поднимает `InvalidParams` для
неизвестного действия.

## Ретраи при STALE

`STALE` означает, что агент нашёл узел, но тот изменился до того, как действие
сработало, — транзиентное состояние. Ретраит контроллер (а не устройство): каждый
ретрай заново отправляет `nodeAction`, который заново ищет от свежего корня.
Настраивается через конфиг `[retry]` (`attempts`, `delay`).

Для собственных многошаговых хелперов используйте декоратор:

```python
from axonctl import retry_on_stale

@retry_on_stale(attempts=5)
async def confirm(device):
    await device.click(Selector.text("Confirm"))
```

## Действия на стороне adb

Когда устройство получено из [`FleetController`][axonctl.FleetController], оно
привязано к adb и может управлять приложениями:

```python
await device.launch("com.example.app")
await device.kill("com.example.app")
await device.install("/path/to/app.apk")
```

(Для отдельного устройства из `connect_device` без привязки к adb эти вызовы
поднимают `RuntimeError`.)

См. также: [Ожидания](waiting.md) и [Скриншоты](screenshots.md).
