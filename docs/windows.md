# Windows & dialogs


`dump()` covers the **active** window. To see *every* interactive window —
application, IME (keyboard), system bars, dialogs, overlays, split-screen — use
[`windows`][axonctl.Device.windows]:

```python
windows = await device.windows()                 # topmost first
windows = await device.windows(include_tree=True)  # attach each window's UI tree
```

[`WindowList`][axonctl.WindowList] is iterable and has convenience selections:

```python
windows.active()         # the active window, or None
windows.focused()        # the focused window, or None
windows.by_type("system")
windows.ime()            # input-method (keyboard) windows
windows.dialogs()        # application windows above the base app (heuristic)
len(windows)
```

Each [`Window`][axonctl.Window] has `window_id`, `type`, `layer`, `active`,
`focused`, `title`, `package`, `bounds`, and (with `include_tree=True`) `root` (a
[`UiTree`][axonctl.UiTree]). `title`/`package` may be `None` for system windows.

```python
for w in windows:
    print(w.window_id, w.type, w.package, w.title)
```

## Acting inside a specific window

Because `.within(...)` selectors are not allowed for actions, the reliable way to
target a dialog/IME/overlay is `window_id` — it is supported by `dump` and every
node action:

```python
windows = await device.windows()
dialog = next(iter(windows.dialogs()), None)
if dialog is not None:
    await device.click(Selector.text("OK"), window_id=dialog.window_id)
    tree = await device.dump(window_id=dialog.window_id)
```

## Inspecting a window's tree

```python
windows = await device.windows(include_tree=True)
app = windows.active()
if app and app.root:
    node = app.root.find(Selector.id("com.app:id/title"))
```

`window_type` values: `application`, `inputMethod`, `system`,
`accessibilityOverlay`, `splitScreenDivider`, `magnification`, `unknown`.

See also: [The UI tree](tree.md) and [Selectors](selectors.md).
