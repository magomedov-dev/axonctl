# Окна и диалоги


`dump()` охватывает **активное** окно. Чтобы увидеть *каждое* интерактивное окно —
приложение, IME (клавиатуру), системные панели, диалоги, оверлеи, разделённый
экран — используйте [`windows`][axonctl.Device.windows]:

```python
windows = await device.windows()                 # topmost first
windows = await device.windows(include_tree=True)  # attach each window's UI tree
```

[`WindowList`][axonctl.WindowList] итерируем и предоставляет удобные выборки:

```python
windows.active()         # the active window, or None
windows.focused()        # the focused window, or None
windows.by_type("system")
windows.ime()            # input-method (keyboard) windows
windows.dialogs()        # application windows above the base app (heuristic)
len(windows)
```

У каждого [`Window`][axonctl.Window] есть `window_id`, `type`, `layer`, `active`,
`focused`, `title`, `package`, `bounds`, и (при `include_tree=True`) `root` (это
[`UiTree`][axonctl.UiTree]). Для системных окон `title`/`package` могут быть `None`.

```python
for w in windows:
    print(w.window_id, w.type, w.package, w.title)
```

## Действия внутри конкретного окна

Поскольку селекторы `.within(...)` для действий не допускаются, надёжный способ
нацелиться на диалог/IME/оверлей — это `window_id`: он поддерживается `dump` и
каждым действием над узлом:

```python
windows = await device.windows()
dialog = next(iter(windows.dialogs()), None)
if dialog is not None:
    await device.click(Selector.text("OK"), window_id=dialog.window_id)
    tree = await device.dump(window_id=dialog.window_id)
```

## Инспекция дерева окна

```python
windows = await device.windows(include_tree=True)
app = windows.active()
if app and app.root:
    node = app.root.find(Selector.id("com.app:id/title"))
```

Значения `window_type`: `application`, `inputMethod`, `system`,
`accessibilityOverlay`, `splitScreenDivider`, `magnification`, `unknown`.

См. также: [Дерево UI](tree.md) и [Селекторы](selectors.md).
